package org.lychd.companion.gametest;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GameTestListener;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.gamerules.GameRules;
import org.lychd.companion.BridgeConfig;
import org.lychd.companion.CompanionActuator;
import org.lychd.companion.FollowDistancePolicy;
import org.lychd.companion.WorldWeatherController;
import org.lychd.companion.WorldClockController;
import org.lychd.companion.gametest.mixin.GameTestInfoAccess;
import org.lychd.companion.protocol.ActionInbox;
import org.lychd.companion.protocol.StrictJson;
import static org.lychd.companion.protocol.Protocol.*;

/** Run separately from ControllerGameTest: this fixture owns the server's global weather/rule.
 * Real engine weather plus a deliberately fake finite NPC; no claim of real NPC physics here. */
public final class WeatherGameTest implements ModInitializer {
    private static final List<Fixture> OPEN = new ArrayList<>();
    @Override public void onInitialize() {
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            for (Fixture fixture : List.copyOf(OPEN)) fixture.close();
        });
    }

    @GameTest(maxTicks = 1250, setupTicks = 1)
    public void realServerWeather(GameTestHelper helper) {
        Fixture fixture = new Fixture(helper);
        OPEN.add(fixture);
        ((GameTestInfoAccess) helper).lychdTestInfo().addListener(new GameTestListener() {
            @Override public void testStructureLoaded(GameTestInfo info) { }
            @Override public void testPassed(GameTestInfo info, GameTestRunner runner) { fixture.close(); }
            @Override public void testFailed(GameTestInfo info, GameTestRunner runner) { fixture.close(); }
            @Override public void testAddedForRerun(GameTestInfo oldInfo, GameTestInfo newInfo, GameTestRunner runner) {
                fixture.close();
            }
        });
        try {
            fixture.open();
            helper.onEachTick(() -> {
                if (fixture.closed) return;
                try { fixture.tick(); }
                catch (Throwable error) { fixture.close(); helper.fail("Weather qualification: " + error); }
            });
        } catch (Throwable error) { fixture.close(); helper.fail("Weather fixture initialization: " + error); }
    }

    private record Weather(int clear, int rain, int thunder, boolean raining, boolean thundering) {
        static Weather read(MinecraftServer server) {
            var data = server.getWeatherData();
            return new Weather(data.getClearWeatherTime(), data.getRainTime(), data.getThunderTime(),
                    data.isRaining(), data.isThundering());
        }
        void restore(MinecraftServer server) {
            var data = server.getWeatherData();
            data.setClearWeatherTime(clear); data.setRainTime(rain); data.setThunderTime(thunder);
            data.setRaining(raining); data.setThundering(thundering);
        }
    }
    private static final class Fixture {
        final GameTestHelper helper;
        final MinecraftServer server;
        final UUID boot = UUID.randomUUID(), actor = UUID.randomUUID(), run = UUID.randomUUID();
        final FakeNpc npc = new FakeNpc();
        final List<String> receipts = new ArrayList<>();
        Weather original;
        boolean originalAdvance, closed, qualified;
        CompanionActuator composite;
        ActionInbox inbox;
        Action clearAction, rainAction;
        ActionRecord clearRecord, rainRecord;
        long startTick, rainTick = -1, npcDeadline;
        boolean stopped;

        Fixture(GameTestHelper helper) { this.helper = helper; server = helper.getLevel().getServer(); }
        long now() { return 1_800_000_000_000L + server.overworld().getGameTime() * 50; }
        BridgeConfig config(boolean allow) {
            return new BridgeConfig("0".repeat(64), 18184, actor, false, 0, 0, 1, 16,
                    FollowDistancePolicy.DEFAULT, allow);
        }
        Action weather(String mode) {
            return new Action(boot, inbox == null ? 0 : inbox.generation(), actor, run, UUID.randomUUID(), now() + 1000,
                    "weather", null, null, null, new WeatherArgs(1, "server_weather", mode, 600));
        }
        void require(boolean value, String message) {
            if (!value) throw new IllegalStateException(message + " at world tick " + server.overworld().getGameTime());
        }
        void receipt(String event) { receipts.add(event + ": " + Weather.read(server)); }
        void open() {
            require(Files.notExists(Path.of("config/lychd-bridge.json")), "private bridge must remain absent");
            original = Weather.read(server);
            originalAdvance = server.overworld().getGameRules().get(GameRules.ADVANCE_WEATHER);
            server.overworld().getGameRules().set(GameRules.ADVANCE_WEATHER, false, server);
            server.setWeatherParameters(77, 88, true, false);
            Weather before = Weather.read(server);
            var enabled = new WorldWeatherController(server, config(true), boot);
            Outcome disabled = new WorldWeatherController(server, config(false), boot).apply(weather("clear"), now());
            require(!disabled.applied() && disabled.weather() == null && before.equals(Weather.read(server)),
                    "default-deny capability mutated weather");
            Outcome paused = enabled.apply(weather("clear"), now());
            require(!paused.applied() && paused.weather() == null && before.equals(Weather.read(server))
                    && !server.overworld().getGameRules().get(GameRules.ADVANCE_WEATHER),
                    "disabled advancement was changed or bypassed");
            server.overworld().getGameRules().set(GameRules.ADVANCE_WEATHER, true, server);
            Action valid = weather("clear");
            for (WeatherArgs invalid : List.of(new WeatherArgs(2, "server_weather", "clear", 600),
                    new WeatherArgs(1, "overworld", "clear", 600), new WeatherArgs(1, "server_weather", "thunder", 600),
                    new WeatherArgs(1, "server_weather", "rain", 601))) {
                Outcome refused = enabled.apply(new Action(boot, 0, actor, run, UUID.randomUUID(), now() + 1000,
                        "weather", null, null, null, invalid), now());
                require(!refused.applied() && refused.weather() == null && before.equals(Weather.read(server)),
                        "direct malformed weather request had an effect");
            }
            require(!enabled.apply(new Action(boot, 0, actor, run, UUID.randomUUID(), now() + 1000,
                    "weather", null, null, null), now()).applied(), "missing direct weather args accepted");
            composite = new CompanionActuator(npc, enabled, new WorldClockController(server, config(false), boot));
            inbox = new ActionInbox(boot, actor, 16, npc.snapshot(0, 0, now()));
            npcDeadline = now() + 5000;
            Action follow = new Action(boot, 0, actor, run, UUID.randomUUID(), npcDeadline,
                    "follow", null, UUID.randomUUID(), null);
            inbox.submit(follow, "finite-fake-follow", now()); inbox.tick(now(), composite);
            require(npc.mode.equals("follow") && npc.active.equals(follow.actionId()), "fake follow setup failed");
            clearAction = valid;
            inbox.submit(clearAction, "clear", now()); inbox.tick(now(), composite);
            clearRecord = inbox.find(clearAction.actionId());
            readback(clearRecord, "clear", new Weather(600, 0, 0, false, false));
            require(npc.applies == 1 && npc.deadline == npcDeadline && npc.active.equals(follow.actionId()),
                    "weather replaced or renewed fake NPC controller");
            startTick = server.overworld().getGameTime(); receipt("clear-applied-immediate-readback");
        }
        void readback(ActionRecord record, String mode, Weather expected) {
            require(record.status().equals("applied") && record.boot_id().equals(boot) && record.run_id().equals(run)
                    && record.observation() instanceof WeatherObservation, "missing correlated weather result");
            WeatherObservation observation = (WeatherObservation) record.observation();
            require(observation.profile().equals("blockworld.weather@1") && observation.boot_id().equals(boot)
                    && observation.actor_id().equals(actor) && observation.generation() == record.generation()
                    && observation.scope().equals("server_weather") && observation.anchor_dimension().equals("minecraft:overworld")
                    && observation.mode().equals(mode) && observation.duration_ticks() == 600 && observation.weather_advancing()
                    && observation.world_tick() == server.overworld().getGameTime() && observation.timestamp_ms() == now()
                    && new Weather(observation.clear_time(), observation.rain_time(), observation.thunder_time(),
                            observation.raining(), observation.thundering()).equals(expected)
                    && Weather.read(server).equals(expected), "immediate engine readback differs from wire observation");
        }
        void tick() {
            inbox.tick(now(), composite);
            long elapsed = server.overworld().getGameTime() - (rainTick < 0 ? startTick : rainTick);
            Weather actual = Weather.read(server);
            require(elapsed >= 0 && elapsed <= 601, "unexpected engine elapsed ticks");
            if (rainTick < 0) {
                if (elapsed <= 600) require(actual.clear == 600 - elapsed && !actual.raining && !actual.thundering,
                        "clear timer did not advance exactly once per actual engine tick");
                if (now() < npcDeadline) require(npc.mode.equals("follow") && npc.deadline == npcDeadline,
                        "fake NPC lease changed before its original deadline");
                else if (!stopped) require(npc.mode.equals("idle") && npc.active == null,
                        "weather renewed fake NPC lease past its original deadline");
                if (elapsed >= 150 && !stopped) {
                    Action queued = weather("rain"); inbox.submit(queued, "queued-rain", now());
                    UUID stopId = UUID.randomUUID(); inbox.stop(new Stop(boot, actor, run, stopId), "priority-stop");
                    require(inbox.find(queued.actionId()).status().equals("cancelled")
                            && inbox.find(queued.actionId()).observation() == null, "stop did not cancel queued weather");
                    inbox.tick(now(), composite); stopped = true;
                    require(inbox.find(stopId).status().equals("applied") && npc.stops == 1
                            && inbox.find(clearAction.actionId()) == clearRecord && actual.equals(Weather.read(server)),
                            "stop rolled back or changed applied weather");
                    receipt("original-fake-lease-expired-queued-weather-cancelled-applied-weather-retained");
                }
                require(inbox.submit(clearAction, "clear", now()) == clearRecord, "clear duplicate lost retained result");
                if (elapsed == 600) receipt("clear-exactly-600-engine-ticks-timer-zero");
                if (elapsed == 601) {
                    require(actual.clear == 0 && actual.raining && actual.thundering, "normal clear-expiry transition absent");
                    receipt("normal-engine-transition-after-clear-timer");
                    rainAction = weather("rain"); inbox.submit(rainAction, "rain", now()); inbox.tick(now(), composite);
                    rainRecord = inbox.find(rainAction.actionId());
                    readback(rainRecord, "rain", new Weather(0, 600, 600, true, false));
                    rainTick = server.overworld().getGameTime(); receipt("rain-applied-immediate-readback");
                }
            } else {
                require(inbox.submit(rainAction, "rain", now()) == rainRecord, "rain duplicate replayed");
                require(npc.applies == 1 && npc.stops == 1 && npc.active == null, "weather forwarded to fake NPC");
                require(actual.clear == 0 && actual.rain == 600 - elapsed && actual.thunder == 600 - elapsed,
                        "rain/thunder timers did not count down actual engine ticks");
                if (elapsed < 600) require(actual.raining && !actual.thundering, "rain flags changed before timer expiry");
                if (elapsed == 600) {
                    require(!actual.raining && actual.thundering, "natural rain timer transition absent");
                    receipt("rain-exactly-600-engine-ticks-and-natural-transition");
                    qualified = true; close(); helper.succeed();
                }
            }
        }
        void close() {
            if (closed) return;
            closed = true; OPEN.remove(this);
            if (original != null) {
                original.restore(server);
                server.overworld().getGameRules().set(GameRules.ADVANCE_WEATHER, originalAdvance, server);
            }
            try {
                Files.writeString(Path.of("weather-observations.json"), StrictJson.GSON.toJson(java.util.Map.of(
                        "profile", "synthetic-server-weather-gametest@1", "qualified", qualified,
                        "npc", "fake finite actuator; real NPC physics qualified separately", "closed", true,
                        "restored_weather", original == null || original.equals(Weather.read(server)),
                        "restored_rule", original == null || originalAdvance == server.overworld().getGameRules().get(GameRules.ADVANCE_WEATHER),
                        "observations", receipts)) + "\n");
            } catch (java.io.IOException error) { throw new IllegalStateException("weather report failed", error); }
        }
        final class FakeNpc implements Actuator {
            String mode = "idle";
            UUID active;
            long deadline;
            int applies, stops;
            @Override public void stop() { stops++; mode = "stopped"; active = null; }
            @Override public void tick(long nowMs) {
                if (active != null && nowMs >= deadline) { mode = "idle"; active = null; }
            }
            @Override public Outcome apply(Action action, long nowMs) {
                applies++; mode = action.kind(); active = action.actionId(); deadline = action.expiresAtMs();
                return Outcome.applied("fake finite NPC controller");
            }
            @Override public State snapshot(long generation, int queueDepth, long nowMs) {
                return new State(1, boot, generation, actor, mode, List.of(0., 64., 0.), 0., 0., queueDepth,
                        active, List.of(), nowMs);
            }
        }
    }
}
