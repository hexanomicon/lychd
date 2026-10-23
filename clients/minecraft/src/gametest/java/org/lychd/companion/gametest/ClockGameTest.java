package org.lychd.companion.gametest;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.clock.ClockState;
import net.minecraft.world.clock.ClockTimeMarkers;
import net.minecraft.world.clock.WorldClocks;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.timeline.Timeline;
import net.minecraft.world.timeline.Timelines;
import org.lychd.companion.BridgeConfig;
import org.lychd.companion.CompanionActuator;
import org.lychd.companion.FollowDistancePolicy;
import org.lychd.companion.WorldClockController;
import org.lychd.companion.WorldWeatherController;
import org.lychd.companion.protocol.ActionInbox;
import org.lychd.companion.protocol.StrictJson;
import static org.lychd.companion.protocol.Protocol.*;

/** Sole synchronous fixture in a fresh clock profile world. Engine clocks are real; NPC is fake.
 * All fixture-owned clock/rule states, including partial ticks, restore in a same-thread finally. */
public final class ClockGameTest implements ModInitializer {
    @Override public void onInitialize() { }
    @GameTest(maxTicks = 100, setupTicks = 1)
    public void realOverworldClock(GameTestHelper helper) {
        var fixture = new Fixture(helper.getLevel().getServer());
        try { fixture.run(); }
        catch (Throwable error) { helper.fail("Clock qualification: " + error); return; }
        helper.succeed();
    }
    private static final class Fixture {
        final MinecraftServer server;
        final UUID boot = UUID.randomUUID(), actor = UUID.randomUUID(), run = UUID.randomUUID();
        final List<ClockObservation> observations = new ArrayList<>();
        final long now = 1_800_000_000_000L;
        Fixture(MinecraftServer server) { this.server = server; }
        void require(boolean condition, String message) {
            if (!condition) throw new IllegalStateException(message);
        }
        BridgeConfig config(boolean enabled) {
            return new BridgeConfig("0".repeat(64), 18184, actor, false, 0, 0, 1, 32,
                    FollowDistancePolicy.DEFAULT, false, enabled);
        }
        Action request(String mode, long generation) {
            return new Action(boot, generation, actor, run, UUID.randomUUID(), now + 1000,
                    "time", null, null, null, null, new TimeArgs(1, "overworld_clock", mode));
        }
        void run() throws Exception {
            require(Files.notExists(Path.of("config/lychd-bridge.json")), "private bridge must remain absent");
            var clock = server.registryAccess().get(WorldClocks.OVERWORLD).orElseThrow();
            var other = server.registryAccess().get(WorldClocks.THE_END).orElseThrow();
            var day = server.registryAccess().get(Timelines.OVERWORLD_DAY).orElseThrow();
            var instance = server.clockManager().getInstance(clock);
            var otherInstance = server.clockManager().getInstance(other);
            ClockState saved = instance.packState(), otherSaved = otherInstance.packState();
            boolean advance = server.getGlobalGameRules().get(GameRules.ADVANCE_TIME);
            var weather = Weather.read(server); long simulation = server.overworld().getGameTime();
            boolean qualified = false, restored = false;
            try {
                var owner = new WorldClockController(server, config(true), boot);
                var disabled = new WorldClockController(server, config(false), boot);
                require(WorldClockController.compatible(clock, day, server.overworld().dimensionType()), "vanilla profile refused");
                require(WorldClockController.matchingTimeline(clock, day.value()), "vanilla markers refused");
                require(!WorldClockController.compatible(null, day, server.overworld().dimensionType())
                        && !WorldClockController.compatible(clock, null, server.overworld().dimensionType()), "missing profile accepted");
                for (Timeline bad : List.of(
                        Timeline.builder(clock).setPeriodTicks(23999).addTimeMarker(ClockTimeMarkers.DAY, 1000)
                                .addTimeMarker(ClockTimeMarkers.NIGHT, 13000).build(),
                        Timeline.builder(clock).setPeriodTicks(24000).addTimeMarker(ClockTimeMarkers.DAY, 1000).build(),
                        Timeline.builder(clock).setPeriodTicks(24000).addTimeMarker(ClockTimeMarkers.DAY, 1001)
                                .addTimeMarker(ClockTimeMarkers.NIGHT, 13000).build(),
                        Timeline.builder(clock).setPeriodTicks(24000).addTimeMarker(ClockTimeMarkers.DAY, 1000)
                                .addTimeMarker(ClockTimeMarkers.NIGHT, 13001).build(),
                        Timeline.builder(other).setPeriodTicks(24000).addTimeMarker(ClockTimeMarkers.DAY, 1000)
                                .addTimeMarker(ClockTimeMarkers.NIGHT, 13000).build()))
                    require(!WorldClockController.matchingTimeline(clock, bad), "incompatible timeline accepted");
                var dimension = server.overworld().dimensionType();
                require(!WorldClockController.compatible(clock, day, dimension(dimension, true, dimension.timelines(), dimension.defaultClock()))
                        && !WorldClockController.compatible(clock, day, dimension(dimension, false, HolderSet.empty(), dimension.defaultClock()))
                        && !WorldClockController.compatible(clock, day, dimension(dimension, false, dimension.timelines(), Optional.empty()))
                        && !WorldClockController.compatible(clock, day, dimension(dimension, false, dimension.timelines(), Optional.of(other))),
                        "incompatible dimension profile accepted");
                require(instance.packState().equals(saved), "read-only profile checks mutated clock");
                require(!disabled.apply(request("day", 0), now).applied() && instance.packState().equals(saved), "disabled clock mutated");
                for (Action bad : List.of(
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", new Point(0,0,0), null, null, null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, UUID.randomUUID(), null, null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, "stray", null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, new WeatherArgs(1,"server_weather","rain",600), new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(2,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(1,"server_weather","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(1,"overworld_clock","noon")),
                        new Action(UUID.randomUUID(), 0, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, UUID.randomUUID(), run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, -1, actor, run, UUID.randomUUID(), now + 1000, "time", null, null, null, null, new TimeArgs(1,"overworld_clock","day")),
                        new Action(boot, 0, actor, run, UUID.randomUUID(), now, "time", null, null, null, null, new TimeArgs(1,"overworld_clock","day")))) {
                    Outcome refused = owner.apply(bad, now);
                    require(!refused.applied() && refused.clock() == null && instance.packState().equals(saved), "malformed clock changed engine");
                }
                for (ClockState bad : List.of(new ClockState(-1,.5F,1,false), new ClockState(Long.MAX_VALUE,.5F,1,false),
                        new ClockState(1000,Float.NaN,1,false), new ClockState(1000,.5F,Float.POSITIVE_INFINITY,false))) {
                    instance.loadFrom(bad); var before = instance.packState();
                    Outcome refused = owner.apply(request("day", 0), now);
                    require(!refused.applied() && refused.clock() == null && instance.packState().equals(before), "invalid clock state mutated");
                }
                // Explicit expected placements include both toggle boundaries and wrapping/no-op markers.
                long[][] cases = {{0,1000,13000},{1000,1000,13000},{1001,25000,13000},
                        {11999,25000,13000},{12000,25000,13000},{13000,25000,13000},{23999,25000,37000}};
                for (float rate : new float[]{1F,0F,-.5F}) for (boolean paused : new boolean[]{false,true})
                    for (boolean advancing : new boolean[]{false,true}) for (long[] c : cases)
                        for (String mode : new String[]{"day","night","toggle"}) {
                            instance.loadFrom(new ClockState(c[0],.375F,rate,paused));
                            server.getGlobalGameRules().set(GameRules.ADVANCE_TIME, advancing, server);
                            Action action = request(mode, 0); Outcome outcome = owner.apply(action, now);
                            require(outcome.applied() && outcome.clock() != null, "valid clock placement refused");
                            var o = outcome.clock();
                            String resolved = mode.equals("toggle") ? (c[0] % 24000 < 12000 ? "night" : "day") : mode;
                            long expected = resolved.equals("day") ? c[1] : c[2];
                            require(o.profile().equals("blockworld.clock@1") && o.boot_id().equals(boot) && o.actor_id().equals(actor)
                                    && o.generation() == 0 && o.scope().equals("overworld_clock")
                                    && o.anchor_dimension().equals("minecraft:overworld") && o.clock().equals("minecraft:overworld")
                                    && o.requested_mode().equals(mode) && o.mode().equals(resolved) && o.before_ticks() == c[0]
                                    && o.after_ticks() == expected && instance.totalTicks() == expected
                                    && o.delta_ticks() == expected-c[0] && o.before_phase() == c[0]%24000
                                    && o.after_phase() == expected%24000 && o.before_cycle() == c[0]/24000
                                    && o.after_cycle() == expected/24000 && o.cycle_increment() == expected/24000-c[0]/24000
                                    && o.before_partial_tick() == .375F && o.partial_tick() == (expected==c[0] ? .375F : 0F)
                                    && instance.partialTick() == o.partial_tick() && o.rate() == rate && instance.rate() == rate
                                    && o.paused() == paused && instance.isPaused() == paused && o.time_advancing() == advancing
                                    && server.getGlobalGameRules().get(GameRules.ADVANCE_TIME) == advancing
                                    && o.world_tick() == simulation && o.timestamp_ms() == now, "engine/wire placement mismatch");
                            observations.add(o);
                        }
                instance.loadFrom(new ClockState(0,.375F,-.5F,true));
                var npc = new FakeNpc();
                var composite = new CompanionActuator(npc, new WorldWeatherController(server, config(true), boot), owner);
                var inbox = new ActionInbox(boot, actor, 32, npc.snapshot(0,0,now));
                Action follow = new Action(boot, 0, actor, run, UUID.randomUUID(), now+500,
                        "follow", null, UUID.randomUUID(), null);
                inbox.submit(follow,"follow",now); inbox.tick(now,composite);
                Action toggle = request("toggle",0); inbox.submit(toggle,"toggle",now); inbox.submit(toggle,"toggle",now);
                inbox.tick(now,composite); ActionRecord applied = inbox.find(toggle.actionId());
                require(applied.status().equals("applied") && applied.observation() instanceof ClockObservation
                        && applied.run_id().equals(run) && applied.action_id().equals(toggle.actionId())
                        && instance.totalTicks()==13000 && npc.applies==1 && npc.active.equals(follow.actionId())
                        && npc.deadline==follow.expiresAtMs(), "mailbox clock replaced fake finite follow");
                require(inbox.submit(toggle,"toggle",now+2000)==applied, "duplicate did not retain applied result");
                try { inbox.submit(toggle,"changed",now); throw new IllegalStateException("changed identity accepted"); }
                catch (Rejection expected) { require(expected.status()==409,"wrong changed-body status"); }
                Action queued = request("toggle",0); inbox.submit(queued,"queued",now);
                UUID stop = UUID.randomUUID(); inbox.stop(new Stop(boot,actor,run,stop),"stop"); inbox.tick(now,composite);
                require(inbox.find(queued.actionId()).status().equals("cancelled") && inbox.find(queued.actionId()).observation()==null
                        && inbox.find(stop).status().equals("applied") && inbox.find(toggle.actionId())==applied
                        && instance.totalTicks()==13000 && npc.stops==1, "stop replayed or undid clock");
                try { inbox.submit(request("day",0),"stale",now); throw new IllegalStateException("stale generation accepted"); }
                catch (Rejection expected) { require(expected.status()==409,"wrong stale-generation status"); }
                Action expired = request("toggle",inbox.generation()); inbox.submit(expired,"expired",now);
                inbox.tick(expired.expiresAtMs(),composite);
                require(inbox.find(expired.actionId()).status().equals("expired") && inbox.find(expired.actionId()).observation()==null
                        && instance.totalTicks()==13000 && npc.applies==1, "expired clock had an effect");
                require(otherInstance.packState().equals(otherSaved) && weather.equals(Weather.read(server))
                        && simulation==server.overworld().getGameTime(), "clock changed another clock, weather or simulation");
                qualified=true;
            } finally {
                instance.loadFrom(saved);
                server.getGlobalGameRules().set(GameRules.ADVANCE_TIME,advance,server);
                restored=instance.packState().equals(saved) && otherInstance.packState().equals(otherSaved)
                        && server.getGlobalGameRules().get(GameRules.ADVANCE_TIME)==advance && weather.equals(Weather.read(server));
                Files.writeString(Path.of("clock-observations.json"),StrictJson.GSON.toJson(Map.of(
                        "profile","synthetic-server-clock-gametest@1","qualified",qualified,"restored_clock_fraction_settings_rule",restored,
                        "npc","fake finite actuator; real follow separately checked in ControllerGameTest", "observations",observations))+"\n");
                require(restored,"clock fixture exact restoration failed");
            }
        }
        DimensionType dimension(DimensionType d, boolean fixed, HolderSet<net.minecraft.world.timeline.Timeline> timelines,
                                Optional<Holder<net.minecraft.world.clock.WorldClock>> clock) {
            return new DimensionType(fixed,d.hasSkyLight(),d.hasCeiling(),d.hasEnderDragonFight(),d.coordinateScale(),
                    d.minY(),d.height(),d.logicalHeight(),d.infiniburn(),d.ambientLight(),d.monsterSettings(),d.skybox(),
                    d.cardinalLightType(),d.attributes(),timelines,clock);
        }
        final class FakeNpc implements Actuator {
            UUID active; long deadline; int applies,stops;
            @Override public void stop() { stops++; active=null; }
            @Override public Outcome apply(Action action,long time) {
                applies++; active=action.actionId(); deadline=action.expiresAtMs(); return Outcome.applied("fake follow");
            }
            @Override public State snapshot(long gen,int depth,long time) {
                return new State(1,boot,gen,actor,active==null?"idle":"follow",List.of(0.,64.,0.),0.,0.,depth,active,List.of(),time);
            }
        }
    }
    private record Weather(int clear,int rain,int thunder,boolean raining,boolean thundering) {
        static Weather read(MinecraftServer server) {
            var d=server.getWeatherData(); return new Weather(d.getClearWeatherTime(),d.getRainTime(),d.getThunderTime(),d.isRaining(),d.isThundering());
        }
    }
}
