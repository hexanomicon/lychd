package org.lychd.voice;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class VoiceControllerTest {
    static final class Lane implements VoiceController.Lane {
        final ArrayDeque<Runnable> queue = new ArrayDeque<>();
        @Override public boolean offer(Runnable work) { if (queue.size() >= 2) return false; queue.add(work); return true; }
        void run() { assertFalse(queue.isEmpty()); queue.remove().run(); }
    }
    record Sent(String method, String path, byte[] body) { }
    static final class Transport implements ControlTransport {
        final List<Sent> sent = new ArrayList<>();
        String context = "a".repeat(64);
        boolean loseRecord, loseHold, loseRelease, refuseRelease;
        String releaseResult = "pending";
        int holdResponse = 202;
        Runnable onHold;
        @Override public Response request(String method, String path, byte[] body) throws IOException {
            sent.add(new Sent(method, path, body));
            if (path.equals("/v1/state")) return new Response(200, ProtocolTest.bytes(ProtocolTest.state(context, 0)));
            if (method.equals("POST")) {
                if (path.equals("/v1/record") && loseRecord) throw new IOException("synthetic lost acknowledgement");
                if (path.equals("/v1/hold") && onHold != null) onHold.run();
                if (path.equals("/v1/hold") && loseHold) throw new IOException("synthetic lost start acknowledgement");
                if (path.equals("/v1/release") && loseRelease) throw new IOException("synthetic lost finish acknowledgement");
                if (path.equals("/v1/release") && refuseRelease)
                    return new Response(409, ProtocolTest.bytes("{\"protocol\":1,\"status\":\"refused\"}"));
                Map<String, Object> data = Json.object(body, 2048);
                String kind = path.equals("/v1/hold") || path.equals("/v1/release") ? "record" : path.substring(4);
                String view = ProtocolTest.operation((String) data.get("request_id"), kind,
                        path.equals("/v1/release") ? releaseResult : "pending");
                if (path.equals("/v1/release") && releaseResult.equals("known")) {
                    view = view.replace("\"native_evidence_status\":null", "\"native_evidence_status\":\"not_requested\"")
                            .replace("\"reply_status\":null", "\"reply_status\":\"not_attempted\"")
                            .replace("\"playback\":null", "\"playback\":\"not_attempted\"");
                }
                return new Response(path.equals("/v1/hold") ? holdResponse : 202, ProtocolTest.bytes(view));
            }
            return new Response(200, ProtocolTest.bytes(ProtocolTest.operation(path.substring("/v1/operations/".length()), "record", "pending")));
        }
        @Override public void close() { }
        long posts(String operation) { return sent.stream().filter(item -> item.method.equals("POST") && item.path.equals("/v1/" + operation)).count(); }
    }
    static final class Fixture {
        final AtomicLong now = new AtomicLong(1000);
        final Lane ordinary = new Lane(), finish = new Lane(), priority = new Lane();
        final Transport transport = new Transport();
        final Object world = new Object();
        int sequence;
        final VoiceController controller = new VoiceController(transport, ordinary, finish, priority, now::get,
                () -> String.format("00000000-0000-4000-8000-%012d", ++sequence));
        void tick(boolean focused, boolean rec, boolean stop) {
            controller.tick(new EdgeGuard.Input(world, true, focused, true, false, rec, false, stop, true, false, false));
        }
        void held(boolean hold) {
            controller.tick(new EdgeGuard.Input(world, true, true, true, false, false, hold, false, true, false, false));
        }
        void prepare() { tick(true, false, false); ordinary.run(); tick(true, false, false); }
    }
    @Test void requestedIdentityAndOriginalTimesPrecedeWorkerDispatchAndLateWorkIsNotSent() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false);
        VoiceController.Hud requested = f.controller.hud();
        assertEquals("requested", requested.localStage()); assertEquals(0, f.transport.posts("record"));
        f.now.set(4200); f.ordinary.run();
        assertEquals(0, f.transport.posts("record"));
        assertEquals("not_sent", f.controller.hud().localStage());
        assertEquals(requested.requestId(), f.controller.hud().requestId());
    }
    @Test void stopUsesReservedLaneWhileOrdinaryLaneIsOccupiedAndCancelsQueuedRecord() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false);
        assertEquals(1, f.ordinary.queue.size());
        f.now.set(1150); f.tick(true, false, false);
        f.now.set(1200); f.tick(true, false, true);
        assertEquals(1, f.priority.queue.size());
        String stopId = f.controller.hud().requestId();
        f.priority.run();
        assertEquals(1, f.transport.posts("stop")); assertEquals(0, f.transport.posts("record"));
        Map<String, Object> body = Json.object(f.transport.sent.getLast().body, 2048);
        assertEquals(stopId, body.get("request_id")); assertEquals(1200L, body.get("created_at_ms"));
        assertEquals(4200L, body.get("admit_before_ms")); assertFalse(body.containsKey("generation"));
        f.ordinary.run(); assertEquals(0, f.transport.posts("record"));
    }
    @Test void dispatchedRecordKeepsIdentityAndLossOfFocusRequestsExactlyOneStop() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false); String id = f.controller.hud().requestId();
        f.now.set(1300); f.ordinary.run();
        Sent record = f.transport.sent.getLast();
        Map<String, Object> body = Json.object(record.body, 2048);
        assertEquals(id, body.get("request_id")); assertEquals(1100L, body.get("created_at_ms"));
        assertEquals(4100L, body.get("admit_before_ms")); assertEquals(11100L, body.get("expires_at_ms"));
        f.now.set(1400); f.tick(false, true, false);
        f.tick(false, true, false); assertEquals(1, f.priority.queue.size());
        f.priority.run(); assertEquals(1, f.transport.posts("stop"));
        assertNotEquals(id, f.controller.hud().requestId());
        f.tick(true, true, false); assertNull(f.controller.hud());
        f.tick(true, true, false); assertEquals(1, f.transport.posts("record"));
    }
    @Test void lostMutationAcknowledgementOnlyQueriesOriginalIdAndDoesNotReplayHeldPress() {
        Fixture f = new Fixture(); f.prepare(); f.transport.loseRecord = true;
        f.now.set(1100); f.tick(true, true, false); String id = f.controller.hud().requestId();
        f.ordinary.run(); assertEquals("unknown", f.controller.hud().localStage());
        f.now.set(2000); f.tick(true, true, false); f.ordinary.run();
        f.tick(true, true, false); // Adopt the returned context boundary before later polls.
        f.now.set(2500); f.tick(true, true, false); f.ordinary.run();
        assertEquals(1, f.transport.posts("record"));
        assertTrue(f.transport.sent.stream().anyMatch(item -> item.path.equals("/v1/operations/" + id)));
    }
    @Test void changedContextCancelsUnsentPressAndOldCallbackCannotWriteNewEpochHud() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false);
        f.now.set(1200); f.tick(false, true, false);
        f.ordinary.run(); assertEquals(0, f.transport.posts("record"));
        assertNull(f.controller.hud());
        f.tick(true, true, false); f.tick(true, true, false);
        assertEquals(0, f.transport.posts("record"));
    }
    @Test void closeDisablesIngressAndReservesBestEffortStopForOutstandingRecord() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false); f.ordinary.run();
        f.controller.beginClose(); assertEquals(1, f.priority.queue.size()); f.priority.run();
        f.tick(true, false, false); f.tick(true, true, true);
        assertEquals(1, f.transport.posts("record")); assertEquals(1, f.transport.posts("stop"));
    }
    @Test void expiredSessionNeverPollsContextOrRecordsButFreshStopRetiresAlreadyOwnedWork() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.tick(true, true, false); f.ordinary.run();
        long priorStates = f.transport.sent.stream().filter(item -> item.path.equals("/v1/state")).count();
        f.now.set(200001); f.tick(true, false, false);
        f.now.set(200050); f.tick(true, false, true);
        assertEquals(1, f.priority.queue.size());
        assertTrue(f.ordinary.queue.isEmpty());
        f.priority.run();
        assertEquals(1, f.transport.posts("stop")); assertEquals(1, f.transport.posts("record"));
        Map<String, Object> stop = Json.object(f.transport.sent.getLast().body, 2048);
        assertEquals(200050L, stop.get("created_at_ms")); assertEquals(203050L, stop.get("admit_before_ms"));
        assertEquals(ProtocolTest.SESSION, stop.get("session_id"));
        f.now.set(200550); f.tick(true, false, false); f.priority.run();
        assertEquals(priorStates, f.transport.sent.stream().filter(item -> item.path.equals("/v1/state")).count());
        assertTrue(f.transport.sent.getLast().path.startsWith("/v1/operations/"));
    }
    @Test void fullInstructionLifetimeMustFitAtPressAndDispatchWithoutRenewingItsDeadline() {
        for (long late : new long[] {190001, 199000}) {
            Fixture f = new Fixture(); f.prepare();
            f.now.set(late); f.tick(true, false, false); f.ordinary.run();
            f.tick(true, true, false);
            assertNull(f.controller.hud());
            assertTrue(f.ordinary.queue.isEmpty());
            assertEquals(0, f.transport.posts("record"));
        }
        Fixture boundary = new Fixture(); boundary.prepare();
        boundary.now.set(190000); boundary.tick(true, false, false); boundary.ordinary.run();
        boundary.tick(true, true, false); boundary.ordinary.run();
        assertEquals(1, boundary.transport.posts("record"));
        Map<String, Object> original = Json.object(boundary.transport.sent.getLast().body, 2048);
        assertEquals(200000L, original.get("expires_at_ms"));

        Fixture delayed = new Fixture(); delayed.prepare();
        delayed.now.set(190000); delayed.tick(true, false, false); delayed.ordinary.run();
        delayed.tick(true, true, false); String id = delayed.controller.hud().requestId();
        delayed.now.set(190001); delayed.ordinary.run();
        assertEquals(0, delayed.transport.posts("record"));
        assertEquals(id, delayed.controller.hud().requestId());
        assertEquals("not_sent", delayed.controller.hud().localStage());
    }
    @Test void heldReleaseBeforeWorkerDispatchCancelsWithoutEitherMutation() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.held(true);
        assertEquals("hold_requested", f.controller.hud().localStage());
        f.now.set(1200); f.held(false);
        f.ordinary.run();
        assertEquals(0, f.transport.posts("hold")); assertEquals(0, f.transport.posts("release"));
        assertTrue(f.finish.queue.isEmpty()); assertEquals("not_sent", f.controller.hud().localStage());
    }
    @Test void releaseBeforeStartAcknowledgementUsesIndependentLaneAndCannotRegressItsHud() {
        Fixture f = new Fixture(); f.prepare();
        f.now.set(1100); f.held(true); String id = f.controller.hud().requestId();
        f.transport.onHold = () -> {
            f.now.set(1200); f.held(false);
            assertEquals("release_requested", f.controller.hud().localStage());
            f.finish.run();
        };
        f.ordinary.run();
        assertEquals(1, f.transport.posts("hold")); assertEquals(1, f.transport.posts("release"));
        assertEquals("release_requested", f.controller.hud().localStage());
        Sent start = f.transport.sent.stream().filter(item -> item.path.equals("/v1/hold")).findFirst().orElseThrow();
        Sent end = f.transport.sent.stream().filter(item -> item.path.equals("/v1/release")).findFirst().orElseThrow();
        Map<String, Object> original = Json.object(start.body, 2048), release = Json.object(end.body, 2048);
        original.forEach((key, value) -> assertEquals(value, release.get(key), key));
        assertEquals(id, release.get("request_id")); assertEquals(1200L, release.get("released_at_ms"));
        assertEquals(4200L, release.get("release_before_ms"));
        f.held(false); assertTrue(f.finish.queue.isEmpty());
    }
    @Test void finishRejectionLostResponseAndFullLaneContainWithoutRetrying() {
        for (int failure = 0; failure < 3; failure++) {
            Fixture f = new Fixture(); f.prepare();
            f.now.set(1100); f.held(true); f.ordinary.run();
            f.transport.loseRelease = failure == 0; f.transport.refuseRelease = failure == 1;
            if (failure == 2) { f.finish.offer(() -> { }); f.finish.offer(() -> { }); }
            f.now.set(1200); f.held(false);
            if (failure < 2) f.finish.run();
            assertEquals(1, f.priority.queue.size()); f.priority.run();
            assertEquals(1, f.transport.posts("stop"));
            for (int tick = 0; tick < 3; tick++) f.held(false);
            assertEquals(failure < 2 ? 1 : 0, f.transport.posts("release"));
        }
    }
    @Test void everyHeldBoundaryCancelsQueuedFinishAndRequestsOneStop() {
        for (int boundary = 0; boundary < 7; boundary++) {
            Fixture f = new Fixture(); f.prepare();
            f.now.set(1100); f.held(true); f.ordinary.run();
            f.now.set(1200); f.held(false); // Finish has its original physical timestamp before boundary.
            f.now.set(1250);
            f.controller.tick(new EdgeGuard.Input(boundary == 0 ? new Object() : f.world,
                    boundary != 1, boundary != 2, boundary != 3, boundary == 4,
                    false, false, boundary == 5, true, false, false));
            if (boundary == 6) {
                f.transport.context = "b".repeat(64);
                f.now.set(2000); f.held(false); f.ordinary.run(); f.held(false);
            }
            f.finish.run();
            assertEquals(0, f.transport.posts("release"), "boundary " + boundary);
            assertEquals(1, f.priority.queue.size(), "boundary " + boundary); f.priority.run();
            assertEquals(1, f.transport.posts("stop"));
        }
    }
    @Test void delayedFinishNeverRenewsReleaseDeadlineAndTyped200StartIsAccepted() {
        Fixture f = new Fixture(); f.prepare(); f.transport.holdResponse = 200;
        f.now.set(1100); f.held(true); f.ordinary.run();
        assertEquals("hold_requested", f.controller.hud().localStage());
        f.now.set(1200); f.held(false);
        f.now.set(4200); f.finish.run();
        assertEquals(0, f.transport.posts("release")); assertEquals(1, f.priority.queue.size());
        f.priority.run(); assertEquals(1, f.transport.posts("stop"));
    }
    @Test void lostStartAcknowledgementStillFinishesOnlyTheOriginalGesture() {
        Fixture f = new Fixture(); f.prepare(); f.transport.loseHold = true;
        f.now.set(1100); f.held(true); String id = f.controller.hud().requestId(); f.ordinary.run();
        assertEquals("unknown", f.controller.hud().localStage());
        f.now.set(1200); f.held(false); f.finish.run();
        assertEquals(1, f.transport.posts("hold")); assertEquals(1, f.transport.posts("release"));
        Sent end = f.transport.sent.stream().filter(item -> item.path.equals("/v1/release")).findFirst().orElseThrow();
        assertEquals(id, Json.object(end.body, 2048).get("request_id"));
    }
    @Test void typedUnknownOrRefusedFinishAlsoUsesReservedContainment() {
        for (String status : new String[] {"unknown", "refused"}) {
            Fixture f = new Fixture(); f.prepare(); f.transport.releaseResult = status;
            f.now.set(1100); f.held(true); f.ordinary.run();
            f.now.set(1200); f.held(false); f.finish.run();
            assertEquals(1, f.priority.queue.size()); f.priority.run();
            assertEquals(1, f.transport.posts("stop")); assertEquals(1, f.transport.posts("release"));
        }
    }
    @Test void acceptedIndependentFinishSurvivesLateFailedStartExchange() {
        for (String status : new String[] {"pending", "known"}) {
            Fixture f = new Fixture(); f.prepare(); f.transport.loseHold = true;
            f.transport.releaseResult = status;
            VoiceController.Hud[] finishView = new VoiceController.Hud[1];
            f.now.set(1100); f.held(true);
            f.transport.onHold = () -> {
                f.now.set(1200); f.held(false); f.finish.run();
                finishView[0] = f.controller.hud();
                assertEquals(status, finishView[0].result().status());
            };
            f.ordinary.run();
            assertEquals(finishView[0], f.controller.hud(), status);
            assertEquals(1, f.transport.posts("hold")); assertEquals(1, f.transport.posts("release"));
            assertTrue(f.priority.queue.isEmpty());
        }
    }
}
