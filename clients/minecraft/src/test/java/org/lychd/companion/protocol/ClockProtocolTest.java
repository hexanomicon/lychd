package org.lychd.companion.protocol;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.lychd.companion.BridgeConfig;
import org.lychd.companion.ClockPlacement;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.Protocol.*;
import static org.lychd.companion.protocol.ProtocolTest.*;

class ClockProtocolTest {
    @TempDir Path temporary;
    static String args(String mode) {
        return "{\"revision\":1,\"scope\":\"overworld_clock\",\"mode\":\"" + mode + "\"}";
    }
    static String time(UUID id, long generation, long expiry, String args) {
        return action(id, generation, expiry, "time", args);
    }
    @Test void closedSchemaHasNoNumericAuthorityOrCrossKindArguments() {
        for (String mode : List.of("day", "night", "toggle")) {
            Action parsed = StrictJson.action(time(UUID.randomUUID(), 0, 500, args(mode)));
            assertEquals(new TimeArgs(1, "overworld_clock", mode), parsed.time());
            assertNull(parsed.point()); assertNull(parsed.weather()); assertNull(parsed.targetId()); assertNull(parsed.text());
        }
        String good = args("toggle");
        for (String invalid : List.of("true", "null", "\"1\"", "1.0", "1e0", "0", "2", "[]", "{}"))
            assertThrows(Rejection.class, () -> StrictJson.action(time(UUID.randomUUID(), 0, 500,
                    good.replace("\"revision\":1", "\"revision\":" + invalid))));
        for (String invalid : List.of(good.replace("toggle", "noon"), good.replace("toggle", "Day"),
                good.replace("overworld_clock", "server_weather"), good.replace("\"toggle\"", "null"),
                good.replace("}", ",\"ticks\":1000}"), good.replace("}", ",\"duration_ticks\":600}"),
                good.replace("}", ",\"x\":1}"), good.replace("}", ",\"mode\":\"day\"}"), "{}"))
            assertThrows(Rejection.class, () -> StrictJson.action(time(UUID.randomUUID(), 0, 500, invalid)));
        for (String kind : List.of("state", "idle", "look", "goto", "inspect", "follow", "say", "weather"))
            assertThrows(Rejection.class, () -> StrictJson.action(action(UUID.randomUUID(), 0, 500, kind, good)));
        assertFalse(new TimeArgs(1, "overworld_clock", null).valid());
        assertNull(new Action(BOOT, 0, ACTOR, RUN, UUID.randomUUID(), 500, "state", null, null, null).time());
    }
    @Test void optionalCapabilityDefaultsFalseAndRequiresOriginalBoolean() throws Exception {
        String base = "{\"protocol\":1,\"token\":\"" + "a".repeat(64) + "\",\"port\":18184,"
                + "\"actor_id\":\"" + ACTOR + "\",\"spawn_actor\":false,\"spawn_x\":0,\"spawn_z\":0,"
                + "\"radius\":24,\"max_actions\":8";
        Path file = temporary.resolve("config.json"); Files.writeString(file, base + "}");
        BridgeConfig legacy = BridgeConfig.read(file); assertFalse(legacy.allowTime());
        assertFalse(new BridgeConfig(legacy.token(), 18184, ACTOR, false, 0, 0, 24, 8,
                legacy.followDistance(), true).allowTime());
        for (boolean enabled : List.of(false, true)) {
            Files.writeString(file, base + ",\"allow_time\":" + enabled + "}");
            assertEquals(enabled, BridgeConfig.read(file).allowTime()); assertFalse(BridgeConfig.read(file).allowWeather());
        }
        for (String invalid : List.of("1", "\"true\"", "null", "{}", "[]", "true,\"allow_time\":false")) {
            Files.writeString(file, base + ",\"allow_time\":" + invalid + "}");
            assertThrows(java.io.IOException.class, () -> BridgeConfig.read(file));
        }
    }
    static final class ClockActuator extends ActionInboxTest.FakeActuator {
        long ticks;
        @Override public Outcome apply(Action request, long nowMs) {
            if (!request.kind().equals("time")) return super.apply(request, nowMs);
            effects.add("time"); var p = ClockPlacement.compute(ticks, request.time().mode()); ticks = p.after();
            return Outcome.clockApplied(new ClockObservation("blockworld.clock@1", BOOT, request.generation(), ACTOR,
                    "overworld_clock", "minecraft:overworld", "minecraft:overworld", request.time().mode(), p.mode(),
                    p.before(), p.after(), p.delta(), p.beforePhase(), p.afterPhase(), p.beforeCycle(), p.afterCycle(),
                    p.cycleIncrement(), 0, 0, -1, true, false, 321, nowMs));
        }
    }
    @Test void toggleExecutesOnceAndRetainsExactTypedCorrelatedObservationAcrossStop() {
        var actuator = new ClockActuator(); actuator.mode = "follow";
        var inbox = new ActionInbox(BOOT, ACTOR, 8, actuator.snapshot(0, 0, 0));
        UUID id = UUID.randomUUID(); String body = time(id, 0, 500, args("toggle"));
        inbox.submit(StrictJson.action(body), body, 0); inbox.submit(StrictJson.action(body), body, 0);
        inbox.tick(10, actuator); ActionRecord applied = inbox.find(id);
        ClockObservation o = assertInstanceOf(ClockObservation.class, applied.observation());
        assertEquals(id, applied.action_id()); assertEquals(RUN, applied.run_id());
        assertEquals(BOOT, o.boot_id()); assertEquals(ACTOR, o.actor_id()); assertEquals(0, o.generation());
        assertEquals(10, o.timestamp_ms()); assertEquals(13000, actuator.ticks); assertEquals("follow", inbox.state().mode());
        assertEquals(Set.of("profile", "boot_id", "generation", "actor_id", "scope", "anchor_dimension", "clock",
                "requested_mode", "mode", "before_ticks", "after_ticks", "delta_ticks", "before_phase", "after_phase",
                "before_cycle", "after_cycle", "cycle_increment", "before_partial_tick", "partial_tick", "rate", "paused",
                "time_advancing", "world_tick", "timestamp_ms"), StrictJson.object(StrictJson.GSON.toJson(o)).keySet());
        assertSame(applied, inbox.submit(StrictJson.action(body), body, 600)); inbox.tick(601, actuator);
        assertEquals(13000, actuator.ticks); assertEquals(List.of("time"), actuator.effects);
        String changed = body.replace("toggle", "day");
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(changed), changed, 0)).status());
        UUID queued = UUID.randomUUID(); String pending = time(queued, 0, 1000, args("toggle"));
        inbox.submit(StrictJson.action(pending), pending, 602);
        String stopBody = stop(UUID.randomUUID()); inbox.stop(StrictJson.stop(stopBody), stopBody); inbox.tick(603, actuator);
        assertEquals("cancelled", inbox.find(queued).status()); assertNull(inbox.find(queued).observation());
        assertSame(applied, inbox.find(id)); assertEquals(13000, actuator.ticks); assertEquals(List.of("time", "stop"), actuator.effects);
        String stale = time(UUID.randomUUID(), 0, 1000, args("day"));
        assertEquals(409, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(stale), stale, 604)).status());
    }
    @Test void staleBindingsAndExpiredQueueHaveNoEffectOrClockObservation() {
        var actuator = new ClockActuator(); var inbox = new ActionInbox(BOOT, ACTOR, 8, actuator.snapshot(0, 0, 0));
        String good = time(UUID.randomUUID(), 0, 500, args("day"));
        for (String body : List.of(good.replace(BOOT.toString(), UUID.randomUUID().toString()),
                good.replace(ACTOR.toString(), UUID.randomUUID().toString()), good.replace("\"generation\":0", "\"generation\":1")))
            assertEquals(409, assertThrows(Rejection.class, () -> inbox.submit(StrictJson.action(body), body, 0)).status());
        UUID id = UUID.randomUUID(); String expired = time(id, 0, 1, args("toggle"));
        inbox.submit(StrictJson.action(expired), expired, 0); inbox.tick(1, actuator);
        assertEquals("expired", inbox.find(id).status()); assertNull(inbox.find(id).observation());
        assertTrue(actuator.effects.isEmpty()); assertEquals(0, actuator.ticks);
    }
    @Test void uncertainReadbackRetainsUnknownWithoutDuplicateEffect() {
        var actuator = new ActionInboxTest.FakeActuator() {
            @Override public Outcome apply(Action request, long nowMs) {
                effects.add("attempted-clock");
                return Outcome.unknown("readback uncertain after placement");
            }
        };
        var inbox = new ActionInbox(BOOT, ACTOR, 8, actuator.snapshot(0, 0, 0));
        UUID id = UUID.randomUUID(); String body = time(id, 0, 500, args("toggle"));
        inbox.submit(StrictJson.action(body), body, 0); inbox.tick(10, actuator);
        ActionRecord uncertain = inbox.find(id);
        assertEquals("unknown", uncertain.status()); assertNull(uncertain.observation());
        assertSame(uncertain, inbox.submit(StrictJson.action(body), body, 20)); inbox.tick(21, actuator);
        assertEquals(List.of("attempted-clock"), actuator.effects);
    }
}
