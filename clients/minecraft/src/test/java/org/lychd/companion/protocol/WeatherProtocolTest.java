package org.lychd.companion.protocol;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.lychd.companion.BridgeConfig;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.Protocol.*;
import static org.lychd.companion.protocol.ProtocolTest.*;

/** Wire and mailbox qualification; engine weather is independently checked by WeatherGameTest. */
class WeatherProtocolTest {
    @TempDir Path temporary;
    static String args(String mode) {
        return "{\"revision\":1,\"scope\":\"server_weather\",\"mode\":\"" + mode + "\",\"duration_ticks\":600}";
    }
    static String weather(UUID id, long generation, long expiry, String args) {
        return action(id, generation, expiry, "weather", args);
    }
    @Test void closedWeatherSchemaRequiresOriginalIntegersAndExactEnumValues() {
        for (String mode : List.of("clear", "rain")) {
            Action parsed = StrictJson.action(weather(UUID.randomUUID(), 0, 500, args(mode)));
            assertEquals(new WeatherArgs(1, "server_weather", mode, 600), parsed.weather());
            assertNull(parsed.point()); assertNull(parsed.targetId()); assertNull(parsed.text());
        }
        String good = args("rain");
        for (String invalid : List.of("true", "null", "\"600\"", "600.0", "6e2", "599", "601", "[]", "{}"))
            assertThrows(Rejection.class, () -> StrictJson.action(weather(UUID.randomUUID(), 0, 500,
                    good.replace("\"duration_ticks\":600", "\"duration_ticks\":" + invalid))));
        for (String invalid : List.of("true", "null", "\"1\"", "1.0", "1e0", "0", "2"))
            assertThrows(Rejection.class, () -> StrictJson.action(weather(UUID.randomUUID(), 0, 500,
                    good.replace("\"revision\":1", "\"revision\":" + invalid))));
        for (String invalid : List.of(good.replace("rain", "thunder"), good.replace("rain", "Rain"),
                good.replace("server_weather", "overworld"), good.replace("\"mode\":\"rain\"", "\"mode\":null"),
                good.replace(",\"duration_ticks\":600", ""), good.replace("600}", "600,\"extra\":true}"),
                good.replace("600}", "600,\"mode\":\"rain\"}"), "{}"))
            assertThrows(Rejection.class, () -> StrictJson.action(weather(UUID.randomUUID(), 0, 500, invalid)));
        assertNull(new Action(BOOT, 0, ACTOR, RUN, UUID.randomUUID(), 500, "state", null, null, null).weather());
        assertFalse(new WeatherArgs(1, "server_weather", null, 600).valid());
    }
    @Test void optionalServerCapabilityDefaultsFalseAndAcceptsOnlyBoolean() throws Exception {
        String base = "{\"protocol\":1,\"token\":\"" + "a".repeat(64) + "\",\"port\":18184,"
                + "\"actor_id\":\"" + ACTOR + "\",\"spawn_actor\":false,\"spawn_x\":0,\"spawn_z\":0,"
                + "\"radius\":24,\"max_actions\":8";
        Path file = temporary.resolve("config.json");
        Files.writeString(file, base + "}");
        BridgeConfig legacy = BridgeConfig.read(file);
        assertFalse(legacy.allowWeather());
        assertFalse(new BridgeConfig(legacy.token(), legacy.port(), legacy.actorId(), legacy.spawnActor(),
                0, 0, 24, 8, legacy.followDistance()).allowWeather());
        for (boolean enabled : List.of(false, true)) {
            Files.writeString(file, base + ",\"allow_weather\":" + enabled + "}");
            assertEquals(enabled, BridgeConfig.read(file).allowWeather());
        }
        for (String invalid : List.of("1", "\"true\"", "null", "{}", "[]", "true,\"allow_weather\":false")) {
            Files.writeString(file, base + ",\"allow_weather\":" + invalid + "}");
            assertThrows(java.io.IOException.class, () -> BridgeConfig.read(file));
        }
        Files.writeString(file, base + ",\"allow_weather\":true,\"unexpected\":false}");
        assertThrows(java.io.IOException.class, () -> BridgeConfig.read(file));
    }
    static class WeatherActuator extends ActionInboxTest.FakeActuator {
        @Override public Outcome apply(Action request, long nowMs) {
            if (!request.kind().equals("weather")) return super.apply(request, nowMs);
            effects.add("weather");
            return Outcome.weatherApplied(new WeatherObservation("blockworld.weather@1", BOOT, request.generation(),
                    ACTOR, "server_weather", "minecraft:overworld", request.weather().mode(), 600,
                    0, 600, 600, true, false, true, 321, nowMs));
        }
    }
    @Test void typedWeatherResultIsCorrelatedRetainedAndNeverReplayedByDuplicateOrStop() {
        var actuator = new WeatherActuator(); actuator.mode = "follow";
        var inbox = new ActionInbox(BOOT, ACTOR, 4, actuator.snapshot(0, 0, 0));
        UUID id = UUID.randomUUID(); String body = weather(id, 0, 500, args("rain"));
        inbox.submit(StrictJson.action(body), body, 0);
        inbox.submit(StrictJson.action(body), body, 0); inbox.tick(10, actuator);
        ActionRecord applied = inbox.find(id);
        WeatherObservation observation = assertInstanceOf(WeatherObservation.class, applied.observation());
        assertEquals(id, applied.action_id()); assertEquals(RUN, applied.run_id());
        assertEquals(BOOT, observation.boot_id()); assertEquals(ACTOR, observation.actor_id());
        assertEquals(0, observation.generation()); assertEquals(10, observation.timestamp_ms());
        assertEquals(Set.of("profile", "boot_id", "generation", "actor_id", "scope", "anchor_dimension", "mode",
                "duration_ticks", "clear_time", "rain_time", "thunder_time", "raining", "thundering",
                "weather_advancing", "world_tick", "timestamp_ms"),
                StrictJson.object(StrictJson.GSON.toJson(observation)).keySet());
        assertEquals("follow", inbox.state().mode());
        assertSame(applied, inbox.submit(StrictJson.action(body), body, 600)); inbox.tick(601, actuator);
        assertEquals(List.of("weather"), actuator.effects);
        String changed = body.replace("rain", "clear");
        assertEquals(409, assertThrows(Rejection.class,
                () -> inbox.submit(StrictJson.action(changed), changed, 0)).status());
        UUID queued = UUID.randomUUID(); String pending = weather(queued, 0, 1000, args("clear"));
        inbox.submit(StrictJson.action(pending), pending, 602);
        UUID stopId = UUID.randomUUID(); String stopping = stop(stopId);
        inbox.stop(StrictJson.stop(stopping), stopping); inbox.tick(603, actuator);
        assertEquals("cancelled", inbox.find(queued).status()); assertNull(inbox.find(queued).observation());
        assertSame(applied, inbox.find(id)); assertEquals(List.of("weather", "stop"), actuator.effects);
        assertEquals("owned controller stopped", inbox.find(stopId).detail());
    }
    @Test void staleIdentitiesGenerationAndExpiredQueueProduceNoWeatherObservation() {
        var actuator = new WeatherActuator();
        var inbox = new ActionInbox(BOOT, ACTOR, 3, actuator.snapshot(0, 0, 0));
        String good = weather(UUID.randomUUID(), 0, 500, args("rain"));
        for (String body : List.of(good.replace(BOOT.toString(), UUID.randomUUID().toString()),
                good.replace(ACTOR.toString(), UUID.randomUUID().toString()), good.replace("\"generation\":0", "\"generation\":1")))
            assertEquals(409, assertThrows(Rejection.class,
                    () -> inbox.submit(StrictJson.action(body), body, 0)).status());
        UUID id = UUID.randomUUID(); String expired = weather(id, 0, 1, args("rain"));
        inbox.submit(StrictJson.action(expired), expired, 0); inbox.tick(1, actuator);
        assertEquals("expired", inbox.find(id).status()); assertNull(inbox.find(id).observation());
        assertTrue(actuator.effects.isEmpty());
    }
}
