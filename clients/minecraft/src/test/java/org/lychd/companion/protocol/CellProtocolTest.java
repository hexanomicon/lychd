package org.lychd.companion.protocol;

import com.google.gson.JsonObject;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.Protocol.*;
import static org.lychd.companion.protocol.ProtocolTest.*;

/** Contract checks for inspect@1, independent of engine block-reading implementation. */
class CellProtocolTest {
    static String inspect(UUID id, long generation, long expiry, String args) {
        return action(id, generation, expiry, "inspect", args);
    }
    static String cellArgs(int x, int y, int z) {
        return "{\"revision\":1,\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + "}";
    }
    static void rejected(ActionInbox inbox, String body, int status) {
        UUID id = StrictJson.action(body).actionId();
        assertEquals(status, assertThrows(Rejection.class,
                () -> inbox.submit(StrictJson.action(body), body, 0)).status());
        assertNull(inbox.find(id), "refusal must not retain an accepted action");
    }
    static class CellActuator extends ActionInboxTest.FakeActuator {
        @Override public Outcome apply(Action request, long nowMs) {
            if (!request.kind().equals("inspect")) return super.apply(request, nowMs);
            effects.add("inspect");
            Point p = request.point();
            return Outcome.inspected(new CellObservation("blockworld.cell@1", BOOT, request.generation(), ACTOR,
                    "minecraft:overworld", List.of((int) p.x(), (int) p.y(), (int) p.z()),
                    true, "minecraft:oak_log", Map.of("axis", "x"), 321, nowMs));
        }
    }

    @Test void inspectionRequiresAnExplicitExactRevisionAndOriginalIntegerAxes() {
        for (String axis : List.of("x", "y", "z")) {
            for (String bad : List.of("true", "null", "\"0\"", "0.0", "0e0", "[]", "{}",
                    "30000001", "-30000001", "9223372036854775808")) {
                String args = cellArgs(0, 0, 0).replace("\"" + axis + "\":0", "\"" + axis + "\":" + bad);
                assertEquals(400, assertThrows(Rejection.class,
                        () -> StrictJson.action(inspect(UUID.randomUUID(), 0, 500, args)), axis + "=" + bad).status());
            }
        }
        for (String revision : List.of("0", "2", "true", "\"1\"", "1.0", "1e0", "null")) {
            String args = cellArgs(0, 64, 0).replace("\"revision\":1", "\"revision\":" + revision);
            assertThrows(Rejection.class, () -> StrictJson.action(inspect(UUID.randomUUID(), 0, 500, args)));
        }
        for (String args : List.of("{\"x\":0,\"y\":64,\"z\":0}",
                "{\"revision\":1,\"x\":0,\"y\":64,\"z\":0,\"extra\":true}",
                "{\"revision\":1,\"revision\":1,\"x\":0,\"y\":64,\"z\":0}",
                "{\"revision\":1,\"x\":0,\"x\":0,\"y\":64,\"z\":0}")) {
            assertThrows(Rejection.class, () -> StrictJson.action(inspect(UUID.randomUUID(), 0, 500, args)));
        }
        Action negative = StrictJson.action(inspect(UUID.randomUUID(), 0, 500, cellArgs(-1, 64, -2)));
        assertEquals(new Point(-1, 64, -2), negative.point());
        assertNull(negative.targetId());
        assertNull(negative.text());
        for (int boundary : List.of(-30_000_000, 30_000_000)) {
            Action edge = StrictJson.action(inspect(UUID.randomUUID(), 0, 500, cellArgs(boundary, boundary, boundary)));
            assertEquals(new Point(boundary, boundary, boundary), edge.point());
        }
    }

    @Test void legacyStateAndActionRecordKeepTheirExactJsonShapeThroughTheObservationUnion() {
        State state = new State(1, BOOT, 0, ACTOR, "follow", List.of(0., 64., 0.), 12., -3.,
                2, RUN, List.of(new Player(RUN, "operator", List.of(1., 64., 2.))), 99);
        String expected = "{\"protocol\":1,\"boot_id\":\"" + BOOT + "\",\"generation\":0,\"actor_id\":\"" + ACTOR
                + "\",\"mode\":\"follow\",\"position\":[0.0,64.0,0.0],\"yaw\":12.0,\"pitch\":-3.0,"
                + "\"queue_depth\":2,\"active_action_id\":\"" + RUN + "\",\"players\":[{\"id\":\"" + RUN
                + "\",\"name\":\"operator\",\"position\":[1.0,64.0,2.0]}],\"timestamp_ms\":99}";
        assertEquals(StrictJson.object(expected), StrictJson.object(StrictJson.GSON.toJson(state)));
        UUID id = UUID.randomUUID();
        ActionRecord record = new ActionRecord(1, BOOT, id, RUN, 0, "applied", "cached server observation", state);
        JsonObject wire = StrictJson.object(StrictJson.GSON.toJson(record));
        assertEquals(Set.of("protocol", "boot_id", "action_id", "run_id", "generation", "status", "detail", "observation"),
                wire.keySet());
        assertEquals(StrictJson.object(expected), wire.getAsJsonObject("observation"));
        assertEquals(BOOT.toString(), wire.get("boot_id").getAsString());
        assertEquals(id.toString(), wire.get("action_id").getAsString());
        assertEquals(RUN.toString(), wire.get("run_id").getAsString());
        assertEquals("applied", wire.get("status").getAsString());
        ActionRecord accepted = new ActionRecord(1, BOOT, id, RUN, 0, "accepted", "queued", null);
        JsonObject awaiting = StrictJson.object(StrictJson.GSON.toJson(accepted));
        assertEquals(wire.keySet(), awaiting.keySet());
        assertTrue(awaiting.get("observation").isJsonNull());
    }

    @Test void typedCellResultSurvivesRetentionAndWireSerializationWithoutReplayOrModeReplacement() {
        var actuator = new CellActuator(); actuator.mode = "follow";
        var inbox = new ActionInbox(BOOT, ACTOR, 3, actuator.snapshot(0, 0, 0));
        UUID id = UUID.randomUUID(); String body = inspect(id, 0, 500, cellArgs(-1, 64, 2));
        assertEquals("accepted", inbox.submit(StrictJson.action(body), body, 0).status());
        inbox.submit(StrictJson.action(body), body, 0);
        inbox.tick(10, actuator);
        ActionRecord record = inbox.find(id);
        assertEquals("applied", record.status());
        assertEquals(id, record.action_id()); assertEquals(RUN, record.run_id());
        CellObservation cell = assertInstanceOf(CellObservation.class, record.observation());
        assertEquals("blockworld.cell@1", cell.profile()); assertEquals(BOOT, cell.boot_id());
        assertEquals(ACTOR, cell.actor_id()); assertEquals(0, cell.generation());
        assertEquals("minecraft:overworld", cell.dimension());
        assertEquals(List.of(-1, 64, 2), cell.position());
        assertEquals("minecraft:oak_log", cell.block()); assertEquals(Map.of("axis", "x"), cell.properties());
        assertEquals(321, cell.world_tick()); assertEquals(10, cell.timestamp_ms());
        JsonObject observed = StrictJson.object(StrictJson.GSON.toJson(record)).getAsJsonObject("observation");
        assertEquals(Set.of("profile", "boot_id", "generation", "actor_id", "dimension", "position", "block",
                "available", "properties", "world_tick", "timestamp_ms"), observed.keySet());
        assertEquals("x", observed.getAsJsonObject("properties").get("axis").getAsString());
        assertEquals("follow", inbox.state().mode());
        assertSame(record, inbox.submit(StrictJson.action(body), body, 600));
        inbox.tick(601, actuator);
        assertEquals(List.of("inspect"), actuator.effects);
        assertEquals("follow", inbox.state().mode());
        for (String changed : List.of(body.replace(RUN.toString(), UUID.randomUUID().toString()),
                body.replace("\"x\":-1", "\"x\":0"), body.replace("\"expires_at_ms\":500", "\"expires_at_ms\":501"))) {
            assertEquals(409, assertThrows(Rejection.class,
                    () -> inbox.submit(StrictJson.action(changed), changed, 0)).status());
            assertSame(record, inbox.find(id));
        }
    }

    @Test void staleOrSubstitutedInspectionEnvelopesRefuseBeforeRetention() {
        var actuator = new CellActuator();
        var inbox = new ActionInbox(BOOT, ACTOR, 4, actuator.snapshot(0, 0, 0));
        String original = inspect(UUID.randomUUID(), 0, 500, cellArgs(0, 64, 0));
        rejected(inbox, original.replace(BOOT.toString(), UUID.randomUUID().toString()), 409);
        rejected(inbox, original.replace(ACTOR.toString(), UUID.randomUUID().toString()), 409);
        rejected(inbox, original.replace("\"generation\":0", "\"generation\":1"), 409);
        inbox.tick(1, actuator);
        assertTrue(actuator.effects.isEmpty());
    }

    @Test void wholeCellMustFitEveryBoxAxisWithoutTighteningLegacyPointActions() {
        var actuator = new CellActuator();
        var inbox = new ActionInbox(BOOT, ACTOR, 8, actuator.snapshot(0, 0, 0),
                p -> p.x() >= -1 && p.x() <= 2 && p.y() >= 63 && p.y() <= 66 && p.z() >= -2 && p.z() <= 1);
        for (int[] p : List.of(new int[]{2, 64, 0}, new int[]{0, 66, 0}, new int[]{0, 64, 1},
                new int[]{-2, 64, 0}, new int[]{0, 62, 0}, new int[]{0, 64, -3})) {
            rejected(inbox, inspect(UUID.randomUUID(), 0, 500, cellArgs(p[0], p[1], p[2])), 400);
        }
        for (int[] p : List.of(new int[]{-1, 63, -2}, new int[]{1, 65, 0})) {
            String body = inspect(UUID.randomUUID(), 0, 500, cellArgs(p[0], p[1], p[2]));
            assertEquals("accepted", inbox.submit(StrictJson.action(body), body, 0).status());
        }
        String point = action(UUID.randomUUID(), 0, 500, "look", "{\"x\":2,\"y\":64,\"z\":0}");
        assertEquals("accepted", inbox.submit(StrictJson.action(point), point, 0).status());
        var unrestricted = new ActionInbox(BOOT, ACTOR, 1, actuator.snapshot(0, 0, 0));
        rejected(unrestricted, inspect(UUID.randomUUID(), 0, 500, cellArgs(17, 64, 0)), 400);
    }

    @Test void expiryAndStopSettleInspectionWithoutProducingACellOrRenewingIt() {
        var actuator = new CellActuator();
        var inbox = new ActionInbox(BOOT, ACTOR, 4, actuator.snapshot(0, 0, 0));
        UUID expired = UUID.randomUUID(); String old = inspect(expired, 0, 2, cellArgs(0, 64, 0));
        inbox.submit(StrictJson.action(old), old, 0); inbox.tick(2, actuator);
        assertEquals("expired", inbox.find(expired).status()); assertNull(inbox.find(expired).observation());
        UUID cancelled = UUID.randomUUID(); String pending = inspect(cancelled, 0, 500, cellArgs(1, 64, 0));
        inbox.submit(StrictJson.action(pending), pending, 3);
        UUID stopId = UUID.randomUUID(); String stopBody = stop(stopId);
        inbox.stop(StrictJson.stop(stopBody), stopBody);
        assertEquals("cancelled", inbox.find(cancelled).status()); assertNull(inbox.find(cancelled).observation());
        assertTrue(actuator.effects.isEmpty());
        inbox.tick(4, actuator);
        assertEquals(List.of("stop"), actuator.effects);
        assertEquals("applied", inbox.find(stopId).status());
        assertEquals("expired", inbox.submit(StrictJson.action(old), old, 600).status());
        assertEquals("cancelled", inbox.submit(StrictJson.action(pending), pending, 600).status());
        String fresh = inspect(UUID.randomUUID(), 1, 500, cellArgs(1, 64, 0));
        inbox.submit(StrictJson.action(fresh), fresh, 5); inbox.tick(6, actuator);
        CellObservation cell = assertInstanceOf(CellObservation.class,
                inbox.find(StrictJson.action(fresh).actionId()).observation());
        assertEquals(1, cell.generation());
        assertEquals(List.of("stop", "inspect"), actuator.effects);
    }
}
