package org.lychd.companion.protocol;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.Protocol.*;
import static org.lychd.companion.protocol.ProtocolTest.*;

class ActionInboxTest {
    static class FakeActuator implements Actuator {
        final List<String> effects = new ArrayList<>();
        String mode = "idle";
        public void stop() { effects.add("stop"); mode = "stopped"; }
        public Outcome apply(Action action, long nowMs) {
            effects.add(action.kind()); mode = action.kind();
            return new Outcome(true, "test applied", action.kind().equals("state"));
        }
        public State snapshot(long generation, int queue, long nowMs) {
            return new State(1, BOOT, generation, ACTOR, mode, List.of(0., 64., 0.), 0., 0., queue, null, List.of(), nowMs);
        }
    }
    static ActionInbox inbox(int capacity) { return new ActionInbox(BOOT, ACTOR, capacity, new FakeActuator().snapshot(0, 0, 0)); }
    static UUID submit(ActionInbox inbox, long generation, long expiry, String kind, long now) {
        UUID id = UUID.randomUUID();
        String body = action(id, generation, expiry, kind, "{}");
        inbox.submit(StrictJson.action(body), body, now);
        return id;
    }
    @Test void sameBodyDuplicateNeverRepeatsAndChangedIdentityConflicts() {
        var inbox = inbox(3); var actuator = new FakeActuator();
        UUID id = UUID.randomUUID();
        String body = action(id, 0, 500, "idle", "{}");
        inbox.submit(StrictJson.action(body), body, 0);
        inbox.submit(StrictJson.action(body), body, 0);
        inbox.tick(1, actuator);
        assertEquals("applied", inbox.submit(StrictJson.action(body), body, 600).status());
        inbox.tick(2, actuator);
        assertEquals(List.of("idle"), actuator.effects);
        String changed = action(id, 0, 501, "idle", "{}");
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(changed), changed, 0)).status());
    }
    @Test void finiteQueueAndRetentionRefuseBeforeAcceptanceWithoutEviction() {
        var inbox = inbox(9); var actuator = new FakeActuator();
        List<UUID> ids = new ArrayList<>();
        for (int i = 0; i < 8; i++) ids.add(submit(inbox, 0, 500, "idle", 0));
        assertEquals(429, assertThrows(Rejection.class, () -> submit(inbox, 0, 500, "idle", 0)).status());
        for (int i = 0; i < 8; i++) inbox.tick(i, actuator);
        submit(inbox, 0, 500, "idle", 0);
        assertEquals(503, assertThrows(Rejection.class, () -> submit(inbox, 0, 500, "idle", 0)).status());
        assertNotNull(inbox.find(ids.getFirst()));
    }
    @Test void queuedDeadlineExpiresWithoutWorldEffectAndOrdersFifo() {
        var inbox = inbox(4); var actuator = new FakeActuator();
        UUID expired = submit(inbox, 0, 2, "idle", 0);
        UUID current = submit(inbox, 0, 500, "state", 0);
        inbox.tick(3, actuator);
        assertEquals("expired", inbox.find(expired).status());
        assertEquals("accepted", inbox.find(current).status());
        assertTrue(actuator.effects.isEmpty());
        inbox.tick(4, actuator);
        assertEquals(List.of("state"), actuator.effects);
        assertEquals(4, ((State) inbox.find(current).observation()).timestamp_ms());
        assertEquals(400, assertThrows(Rejection.class, () -> submit(inbox, 0, 60_001, "idle", 0)).status());
    }
    @Test void priorityStopBypassesBothFullBoundsAndPublishesOnlyAfterBarrier() {
        var inbox = inbox(8); var actuator = new FakeActuator();
        List<UUID> pending = new ArrayList<>();
        for (int i = 0; i < 8; i++) pending.add(submit(inbox, 0, 500, "idle", 0));
        UUID id = UUID.randomUUID(); String body = stop(id);
        assertEquals("accepted", inbox.stop(StrictJson.stop(body), body).status());
        assertEquals(1, inbox.generation());
        assertEquals(0, inbox.state().generation());
        for (UUID queued : pending) assertEquals("cancelled", inbox.find(queued).status());
        assertEquals(409, assertThrows(Rejection.class, () -> submit(inbox, 0, 500, "idle", 0)).status());
        assertEquals("accepted", inbox.stop(StrictJson.stop(body), body).status());
        assertEquals(1, inbox.generation());
        inbox.tick(5, actuator);
        assertEquals(List.of("stop"), actuator.effects);
        assertEquals("applied", inbox.find(id).status());
        assertEquals("stopped", ((State) inbox.find(id).observation()).mode());
        assertEquals(1, inbox.state().generation());
    }
    @Test void concurrentStopCannotCrossAnExecutingActionAndNewGenerationRunsAfterBarrier() throws Exception {
        var inbox = inbox(5);
        CountDownLatch entered = new CountDownLatch(1), release = new CountDownLatch(1);
        var actuator = new FakeActuator() {
            public Outcome apply(Action action, long nowMs) {
                entered.countDown();
                try { if (!release.await(2, TimeUnit.SECONDS)) throw new AssertionError("test release timed out"); }
                catch (InterruptedException e) { throw new AssertionError(e); }
                return super.apply(action, nowMs);
            }
        };
        submit(inbox, 0, 500, "idle", 0);
        try (var threads = Executors.newFixedThreadPool(2)) {
            var tick = threads.submit(() -> inbox.tick(1, actuator));
            assertTrue(entered.await(2, TimeUnit.SECONDS));
            UUID stopId = UUID.randomUUID(); String body = stop(stopId);
            CountDownLatch stopEntered = new CountDownLatch(1);
            var stopping = threads.submit(() -> { stopEntered.countDown(); return inbox.stop(StrictJson.stop(body), body); });
            assertTrue(stopEntered.await(2, TimeUnit.SECONDS));
            release.countDown(); tick.get(2, TimeUnit.SECONDS); stopping.get(2, TimeUnit.SECONDS);
            submit(inbox, 1, 500, "state", 2);
            inbox.tick(3, actuator);
            assertEquals(List.of("idle", "stop", "state"), actuator.effects);
            assertEquals("applied", inbox.find(stopId).status());
        }
    }
    @Test void pointMustBeWithinIssuanceDistanceAndConfiguredBox() {
        var initial = new FakeActuator().snapshot(0, 0, 0);
        var inbox = new ActionInbox(BOOT, ACTOR, 4, initial, p -> Math.abs(p.x()) <= 5);
        String distant = action(UUID.randomUUID(), 0, 500, "goto", "{\"x\":17,\"y\":64,\"z\":0}");
        assertEquals(400, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(distant), distant, 0)).status());
        String outsideBox = action(UUID.randomUUID(), 0, 500, "look", "{\"x\":6,\"y\":64,\"z\":0}");
        assertEquals(400, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(outsideBox), outsideBox, 0)).status());
        String allowed = action(UUID.randomUUID(), 0, 500, "look", "{\"x\":5,\"y\":64,\"z\":0}");
        assertEquals("accepted", inbox.submit(StrictJson.action(allowed), allowed, 0).status());
    }
    @Test void historicalStopReplayAndBothKindsOfIdentityCollisionNeverRepeatEffects() {
        var inbox = inbox(2); var actuator = new FakeActuator();
        UUID first = UUID.randomUUID(); String one = stop(first);
        inbox.stop(StrictJson.stop(one), one);
        inbox.tick(1, actuator);
        UUID second = UUID.randomUUID(); String two = stop(second);
        inbox.stop(StrictJson.stop(two), two);
        inbox.tick(2, actuator);
        UUID ordinary = submit(inbox, 2, 500, "idle", 2);
        inbox.tick(3, actuator);

        assertEquals("applied", inbox.stop(StrictJson.stop(one), one).status());
        assertEquals(2, inbox.generation());
        assertEquals(1, inbox.find(first).generation());
        assertEquals("applied", inbox.find(second).status());
        String changed = one.replace(RUN.toString(), UUID.randomUUID().toString());
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(changed), changed)).status());
        String collidingAction = action(first, 2, 500, "idle", "{}");
        assertEquals(409, assertThrows(Rejection.class,
                () -> inbox.submit(StrictJson.action(collidingAction), collidingAction, 3)).status());
        String collidingStop = stop(ordinary);
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(collidingStop), collidingStop)).status());
        inbox.tick(4, actuator);
        assertEquals(List.of("stop", "stop", "idle"), actuator.effects);
        assertEquals("idle", inbox.state().mode());
    }
    @Test void newerPendingStopCancelsAndRetainsEarlierIdentityUntilItsOwnTickBarrier() {
        var inbox = inbox(1); var actuator = new FakeActuator();
        UUID first = UUID.randomUUID(); String one = stop(first);
        UUID second = UUID.randomUUID(); String two = stop(second);
        inbox.stop(StrictJson.stop(one), one);
        assertEquals("accepted", inbox.stop(StrictJson.stop(two), two).status());
        assertEquals("cancelled", inbox.find(first).status());
        assertNull(inbox.find(first).observation());
        assertEquals("cancelled", inbox.stop(StrictJson.stop(one), one).status());
        assertEquals("accepted", inbox.find(second).status());
        assertEquals(2, inbox.generation());
        assertEquals(0, inbox.state().generation());
        assertTrue(actuator.effects.isEmpty());
        inbox.tick(5, actuator);
        assertEquals("cancelled", inbox.find(first).status());
        assertEquals("applied", inbox.find(second).status());
        assertEquals(2, ((State) inbox.find(second).observation()).generation());
        assertEquals(List.of("stop"), actuator.effects);
    }
    @Test void finalStopHistorySlotStillRunsBarrierWithFullOrdinaryRetentionAndKeepsEveryIdentity() {
        var inbox = inbox(8); var actuator = new FakeActuator();
        List<UUID> ordinaryIds = new ArrayList<>();
        List<String> ordinaryBodies = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            UUID id = UUID.randomUUID();
            String body = action(id, 0, 500, "idle", "{}");
            ordinaryIds.add(id); ordinaryBodies.add(body);
            inbox.submit(StrictJson.action(body), body, 0);
        }
        List<UUID> stopIds = new ArrayList<>();
        List<String> stopBodies = new ArrayList<>();
        for (int i = 0; i < 256; i++) {
            UUID id = UUID.randomUUID(); String body = stop(id);
            stopIds.add(id); stopBodies.add(body);
            assertEquals("accepted", inbox.stop(StrictJson.stop(body), body).status());
        }
        assertEquals(256, inbox.generation());
        assertEquals(0, inbox.state().generation());
        assertTrue(actuator.effects.isEmpty());
        for (int i = 0; i < 255; i++) assertEquals("cancelled", inbox.find(stopIds.get(i)).status());
        assertEquals("accepted", inbox.find(stopIds.getLast()).status());
        String exhaustedStop = stop(UUID.randomUUID());
        assertEquals(503, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(exhaustedStop), exhaustedStop)).status());
        assertNull(inbox.find(StrictJson.stop(exhaustedStop).actionId()));
        assertEquals(503, assertThrows(Rejection.class, () -> submit(inbox, 256, 500, "idle", 0)).status());
        for (String body : ordinaryBodies)
            assertEquals("cancelled", inbox.submit(StrictJson.action(body), body, 600).status());
        for (int i = 0; i < 256; i++) {
            String body = stopBodies.get(i);
            assertEquals(i == 255 ? "accepted" : "cancelled", inbox.stop(StrictJson.stop(body), body).status());
        }
        String changedStop = stopBodies.getFirst().replace(RUN.toString(), UUID.randomUUID().toString());
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(changedStop), changedStop)).status());
        String changedAction = ordinaryBodies.getFirst().replace("\"expires_at_ms\":500", "\"expires_at_ms\":501");
        assertEquals(409, assertThrows(Rejection.class,
                () -> inbox.submit(StrictJson.action(changedAction), changedAction, 0)).status());
        String collidingAction = action(stopIds.getFirst(), 256, 500, "idle", "{}");
        assertEquals(409, assertThrows(Rejection.class,
                () -> inbox.submit(StrictJson.action(collidingAction), collidingAction, 0)).status());
        String collidingStop = stop(ordinaryIds.getFirst());
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(collidingStop), collidingStop)).status());

        inbox.tick(5, actuator);
        assertEquals(List.of("stop"), actuator.effects);
        assertEquals("applied", inbox.find(stopIds.getLast()).status());
        assertEquals("stopped", ((State) inbox.find(stopIds.getLast()).observation()).mode());
        assertEquals(256, inbox.state().generation());
        assertEquals("applied", inbox.stop(StrictJson.stop(stopBodies.getLast()), stopBodies.getLast()).status());
        assertEquals(503, assertThrows(Rejection.class, () -> inbox.stop(StrictJson.stop(exhaustedStop), exhaustedStop)).status());
        assertEquals(503, assertThrows(Rejection.class, () -> submit(inbox, 256, 500, "idle", 5)).status());
        for (UUID id : ordinaryIds) assertEquals("cancelled", inbox.find(id).status());
        for (int i = 0; i < 255; i++) assertEquals("cancelled", inbox.find(stopIds.get(i)).status());
        inbox.tick(6, actuator);
        assertEquals(List.of("stop"), actuator.effects);
        assertEquals(256, inbox.generation());
    }
    @Test void finalStopSlotSealsOrdinaryAdmissionEvenWithUnusedOrdinaryCapacity() {
        var inbox = inbox(2); var actuator = new FakeActuator();
        for (int i = 0; i < 255; i++) {
            String body = stop(UUID.randomUUID());
            inbox.stop(StrictJson.stop(body), body);
        }
        UUID ordinary = submit(inbox, 255, 500, "idle", 0);
        inbox.tick(1, actuator);
        assertEquals(List.of("stop", "idle"), actuator.effects);
        String last = stop(UUID.randomUUID());
        assertEquals("accepted", inbox.stop(StrictJson.stop(last), last).status());
        assertEquals(503, assertThrows(Rejection.class, () -> submit(inbox, 256, 500, "state", 1)).status());
        inbox.tick(2, actuator);
        assertEquals("applied", inbox.find(ordinary).status());
        assertEquals("applied", inbox.stop(StrictJson.stop(last), last).status());
        assertEquals(503, assertThrows(Rejection.class, () -> submit(inbox, 256, 500, "state", 2)).status());
        assertEquals(List.of("stop", "idle", "stop"), actuator.effects);
    }
}
