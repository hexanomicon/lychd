package org.lychd.companion.gametest;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GameTestListener;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.TicketStorage;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import org.lychd.companion.BridgeConfig;
import org.lychd.companion.CompanionActuator;
import org.lychd.companion.FollowDistancePolicy;
import org.lychd.companion.WolfController;
import org.lychd.companion.WorldWeatherController;
import org.lychd.companion.WorldClockController;
import org.lychd.companion.gametest.mixin.GameTestInfoAccess;
import org.lychd.companion.protocol.ActionInbox;
import org.lychd.companion.protocol.StrictJson;
import static org.lychd.companion.protocol.Protocol.*;

/** One sequential controller per fresh world: the production reservation is world-wide. */
public final class ControllerGameTest implements ModInitializer {
    private static final List<Fixture> OPEN = new ArrayList<>();

    @Override public void onInitialize() {
        // Match LychdBridge's Minecraft-thread ownership and physics ordering.
        ServerTickEvents.START_SERVER_TICK.register(server -> {
            for (Fixture fixture : List.copyOf(OPEN)) fixture.driveController();
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            for (Fixture fixture : List.copyOf(OPEN)) fixture.close("server-stopping");
        });
    }

    @GameTest(maxTicks = 1000, setupTicks = 1)
    public void realFollowController(GameTestHelper helper) {
        Fixture fixture = new Fixture(helper);
        OPEN.add(fixture);
        ((GameTestInfoAccess) helper).lychdTestInfo().addListener(new GameTestListener() {
            @Override public void testStructureLoaded(GameTestInfo info) { }
            @Override public void testPassed(GameTestInfo info, GameTestRunner runner) { fixture.close("passed"); }
            @Override public void testFailed(GameTestInfo info, GameTestRunner runner) { fixture.close("failed-or-timeout"); }
            @Override public void testAddedForRerun(GameTestInfo oldInfo, GameTestInfo newInfo, GameTestRunner runner) {
                fixture.close("rerun");
            }
        });
        try {
            fixture.open();
            helper.onEachTick(() -> {
                if (fixture.closed) return;
                try { fixture.tick(); }
                catch (Throwable error) {
                    fixture.failure = error.toString();
                    fixture.close("assertion-or-exception");
                    helper.fail("Controller qualification: " + error);
                }
            });
        } catch (Throwable error) {
            fixture.failure = error.toString();
            fixture.close("initialization-failed");
            helper.fail("Controller fixture initialization: " + error);
        }
    }

    private enum Phase { SETTLE, NEARBY, PURSUE, STATE, CELL, AIR, CHANGED_CELL, SAY, REFUSE, APPROACH, WAIT,
        RESUME, STOP, STOP_WAIT, FRESH, SHORT_CELL, QUEUED_EXPIRY, QUEUED_CELL_EXPIRY, SHORT_STATE, SHORT_SAY, SHORT_REFUSE,
        LEASE, CORNER, EXCESS, LOST_START, LOST, DEAD_START, DEAD }

    private static final class Fixture {
        private static final long CLOCK_BASE = 1_800_000_000_000L;
        private static final int FLOOR_Y = 80;
        private final GameTestHelper helper;
        private final UUID boot = UUID.randomUUID(), actorId = UUID.randomUUID(), run = UUID.randomUUID();
        private final List<ServerPlayer> players = new ArrayList<>();
        private final JsonArray observations = new JsonArray();
        private final Path report = Path.of("controller-observations.json").toAbsolutePath();
        private WolfController controller;
        private CompanionActuator actuator;
        private ActionInbox inbox;
        private WeatherState originalWeather;
        private boolean originalWeatherAdvance, weatherRestored;
        private UUID weatherActionId;
        private WeatherObservation weatherObservation;
        private TicketStorage ticketStorage;
        private TicketType controllerTicket;
        private ChunkPos home;
        private Wolf wolf;
        private ServerPlayer target;
        private Phase phase = Phase.SETTLE;
        private long phaseTick, leaseDeadline, controllerTicks;
        private int arenaX, arenaZ;
        private UUID followId, pending, stopId;
        private Vec3 reference;
        private double initialSeparation;
        private boolean closed, qualified, cleanup, ticketReleased;
        private String failure;

        Fixture(GameTestHelper helper) { this.helper = helper; }

        void open() throws IOException {
            require(Runtime.getRuntime().availableProcessors() <= 2, "fixture CPU count exceeds two");
            require(Runtime.getRuntime().maxMemory() <= 1536L * 1024 * 1024, "fixture heap exceeds 1536 MiB");
            Path config = Path.of("config");
            if (Files.exists(config)) try (var files = Files.list(config)) {
                require(files.findAny().isEmpty(), "fixture configuration must be empty");
            }
            Path marker = helper.getLevel().getServer().getWorldPath(LevelResource.DATA)
                    .resolve("lychd-companion-created.marker");
            require(!Files.exists(marker), "fixture requires a fresh world reservation");
            // Flat safe floor and all tested positions stay in this single home chunk.
            var world = helper.getLevel();
            originalWeather = WeatherState.read(world.getServer());
            originalWeatherAdvance = world.getGameRules().get(GameRules.ADVANCE_WEATHER);
            BlockPos origin = helper.absolutePos(BlockPos.ZERO);
            arenaX = origin.getX() & ~15; arenaZ = origin.getZ() & ~15;
            world.getChunk(arenaX >> 4, arenaZ >> 4);
            for (int x = 0; x < 16; x++) for (int z = 0; z < 16; z++) {
                world.setBlock(new BlockPos(arenaX + x, FLOOR_Y, arenaZ + z), Blocks.STONE.defaultBlockState(), 3);
                for (int y = FLOOR_Y + 1; y <= FLOOR_Y + 12; y++)
                    world.setBlock(new BlockPos(arenaX + x, y, arenaZ + z), Blocks.AIR.defaultBlockState(), 3);
            }
            // A sealed air cell is truly unreachable. Ground navigation normalizes
            // destinations suspended in air down to the ground, so height is no oracle.
            for (int x = 7; x <= 9; x++) for (int z = 11; z <= 13; z++)
                for (int y = FLOOR_Y + 1; y <= FLOOR_Y + 5; y++)
                    if (x != 8 || z != 12 || y == FLOOR_Y + 5)
                        world.setBlock(new BlockPos(arenaX + x, y, arenaZ + z), Blocks.STONE.defaultBlockState(), 3);
            var configValue = new BridgeConfig("0".repeat(64), 18184, actorId, true,
                    arenaX + 4, arenaZ + 4, 24, 128, FollowDistancePolicy.DEFAULT, true, true);
            home = new ChunkPos(arenaX >> 4, arenaZ >> 4);
            ticketStorage = world.getChunkSource().getDataStorage().computeIfAbsent(TicketStorage.TYPE);
            Set<TicketType> before = ticketTypes();
            controller = new WolfController(world.getServer(), configValue, boot);
            actuator = new CompanionActuator(controller, new WorldWeatherController(world.getServer(), configValue, boot),
                    new WorldClockController(world.getServer(), configValue, boot));
            // Retain the owned body before any later initialization assertion can fail.
            if (world.getEntity(actorId) instanceof Wolf owned) wolf = owned;
            require(wolf != null, "production controller did not spawn wolf");
            Set<TicketType> added = ticketTypes(); added.removeAll(before);
            require(added.size() == 1, "controller did not add exactly one private home ticket type");
            controllerTicket = added.iterator().next();
            require(!wolf.isNoAi(), "real physics and navigation must remain enabled");
            inbox = new ActionInbox(boot, actorId, 128, controller.snapshot(0, 0, now()), configValue::contains);
            target = addTarget(wolf.getX() + 1, wolf.getZ());
            require(world.getServer().getPlayerList().getPlayer(target.getUUID()) == target,
                    "synthetic target absent from actual PlayerList lookup");
            require(controller.snapshot(0, 0, now()).players().stream().anyMatch(p -> p.id().equals(target.getUUID())),
                    "synthetic target absent from controller observation");
            record("opened-real-controller-and-player-list");
        }

        ServerPlayer addTarget(double x, double z) {
            ServerPlayer player = helper.makeMockServerPlayerInLevel();
            players.add(player);
            player.setGameMode(GameType.CREATIVE);
            player.setPos(x, FLOOR_Y + 1, z);
            return player;
        }

        Set<TicketType> ticketTypes() {
            Set<TicketType> result = new HashSet<>();
            for (var ticket : ticketStorage.getTickets(home.pack())) result.add(ticket.getType());
            return result;
        }

        // GameTestServer sprints ticks. Advance the supplied finite lease clock at
        // the same START_SERVER_TICK barrier as the production mailbox, once per tick.
        long now() { return CLOCK_BASE + controllerTicks * 50; }
        long elapsed() { return helper.getTick() - phaseTick; }
        void phase(Phase next) { phase = next; phaseTick = helper.getTick(); record("phase"); }
        double separation() { return wolf.position().distanceTo(target.position()); }
        void require(boolean condition, String detail) {
            if (!condition) throw new IllegalStateException(detail + " [phase=" + phase + ", tick=" + helper.getTick() + "]");
        }
        void boundedWait(long ticks, String detail) { require(elapsed() <= ticks, detail); }

        UUID submit(String label, String kind, Point point, UUID targetId, long duration) {
            UUID id = UUID.nameUUIDFromBytes(label.getBytes(StandardCharsets.UTF_8));
            Action action = new Action(boot, inbox.generation(), actorId, run, id, now() + duration,
                    kind, point, targetId, kind.equals("say") ? "synthetic controller qualification" : null);
            require(inbox.submit(action, label, now()).status().equals("accepted"), "action admission failed");
            pending = id;
            return id;
        }
        void applied() {
            require(inbox.find(pending).status().equals("applied"), "action was not applied: " + inbox.find(pending));
        }
        void following() {
            State state = inbox.state();
            require(state.mode().equals("follow") && followId.equals(state.active_action_id()),
                    "follow identity was replaced or lost");
        }
        void stopped(String mode) {
            State state = inbox.state();
            require(state.mode().equals(mode) && state.active_action_id() == null && wolf.getNavigation().isDone(),
                    "controller or navigation remains active");
        }
        void moveTarget(double x, double z) {
            require(x >= 0.5 && x <= 15.5 && z >= 0.5 && z <= 15.5, "target left home arena");
            target.setPos(arenaX + x, FLOOR_Y + 1, arenaZ + z);
            reference = wolf.position();
            initialSeparation = separation();
            record("target-moved-only");
        }
        boolean movedTowardTarget() {
            following();
            return wolf.position().distanceTo(reference) > 0.5 && separation() < initialSeparation - 0.5
                    && !wolf.getNavigation().isDone();
        }

        void tick() {
            require(wolf.isAlive() && !wolf.isRemoved(), "owned wolf unavailable");
            require(wolf.getX() >= arenaX && wolf.getX() < arenaX + 16 && wolf.getZ() >= arenaZ && wolf.getZ() < arenaZ + 16,
                    "wolf left the single-chunk arena");
            if (helper.getTick() % 10 == 0) record("sample");
            switch (phase) {
                case SETTLE -> {
                    if (elapsed() < 20) return;
                    require(wolf.tickCount > 0 && wolf.onGround()
                            && Math.abs(wolf.getY() - FLOOR_Y - 1) < 0.05, "wolf did not tick and settle on floor");
                    reference = wolf.position();
                    followId = submit("nearby-follow", "follow", null, target.getUUID(), 60_000);
                    phase(Phase.NEARBY);
                }
                case NEARBY -> {
                    applied(); following();
                    require(wolf.getNavigation().isDone(), "nearby follow started navigation");
                    require(wolf.position().distanceTo(reference) < 0.1, "nearby follow moved wolf");
                    if (elapsed() < 20) return;
                    record("nearby-retained-without-movement");
                    moveTarget(12.5, 4.5); phase(Phase.PURSUE);
                }
                case PURSUE -> {
                    boundedWait(100, "real navigation did not move toward target");
                    if (!movedTowardTarget()) return;
                    record("real-displacement-and-decreasing-separation");
                    submit("state-during-follow", "state", null, null, 30_000); phase(Phase.STATE);
                }
                case STATE -> {
                    applied(); following();
                    require(((State) inbox.find(pending).observation()).active_action_id().equals(followId), "state correlation lost follow");
                    helper.getLevel().setBlock(new BlockPos(arenaX + 4, FLOOR_Y, arenaZ + 4),
                            Blocks.OAK_LOG.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.Z), 3);
                    submit("inspect-log-during-follow", "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, 30_000);
                    phase(Phase.CELL);
                }
                case CELL -> {
                    applied(); following();
                    require(inbox.find(pending).observation() instanceof CellObservation, "inspection returned no typed cell");
                    CellObservation cell = (CellObservation) inbox.find(pending).observation();
                    require(cell.profile().equals("blockworld.cell@1") && cell.boot_id().equals(boot)
                            && cell.actor_id().equals(actorId) && cell.generation() == inbox.generation()
                            && cell.dimension().equals("minecraft:overworld") && cell.world_tick() > 0
                            && cell.timestamp_ms() == now() && cell.position().equals(List.of(arenaX + 4, FLOOR_Y, arenaZ + 4))
                            && cell.block().equals("minecraft:oak_log") && cell.properties().equals(java.util.Map.of("axis", "z")),
                            "real non-default block state/provenance differs");
                    record("real-log-axis-z-observed-with-follow-preserved");
                    ActionRecord retained = inbox.find(pending);
                    Action duplicate = new Action(boot, inbox.generation(), actorId, run, pending, now() + 30_000,
                            "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, null);
                    require(inbox.submit(duplicate, "inspect-log-during-follow", now()) == retained,
                            "duplicate inspection did not return original retained result");
                    submit("inspect-air-during-follow", "inspect", new Point(arenaX + 4, FLOOR_Y + 8, arenaZ + 4), null, 30_000);
                    phase(Phase.AIR);
                }
                case AIR -> {
                    applied(); following();
                    CellObservation cell = (CellObservation) inbox.find(pending).observation();
                    require(cell.block().equals("minecraft:air") && cell.properties().isEmpty(), "air was not observed as successful empty state");
                    record("real-air-observed-with-follow-preserved");
                    helper.getLevel().setBlock(new BlockPos(arenaX + 4, FLOOR_Y, arenaZ + 4), Blocks.STONE.defaultBlockState(), 3);
                    submit("inspect-changed-cell", "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, 30_000);
                    phase(Phase.CHANGED_CELL);
                }
                case CHANGED_CELL -> {
                    applied(); following();
                    CellObservation cell = (CellObservation) inbox.find(pending).observation();
                    require(cell.block().equals("minecraft:stone") && cell.properties().isEmpty(), "inspection reused an old cell snapshot");
                    int loaded = helper.getLevel().getChunkSource().getLoadedChunksCount();
                    Outcome refused = controller.apply(new Action(boot, inbox.generation(), actorId, run, UUID.randomUUID(),
                            now() + 1000, "inspect", new Point(arenaX + 4000, FLOOR_Y, arenaZ), null, null), now());
                    require(!refused.applied() && refused.cell() == null && loaded == helper.getLevel().getChunkSource().getLoadedChunksCount(),
                            "refused far inspection loaded a chunk or returned cell evidence");
                    following(); record("changed-cell-fresh-and-outside-refusal-without-load");
                    submit("say-during-follow", "say", null, null, 30_000); phase(Phase.SAY);
                }
                case SAY -> {
                    applied(); following();
                    submit("unreachable-goto", "goto", new Point(arenaX + 8.5, FLOOR_Y + 1, arenaZ + 12.5), null, 30_000);
                    phase(Phase.REFUSE);
                }
                case REFUSE -> {
                    require(inbox.find(pending).status().equals("refused")
                            && inbox.find(pending).detail().equals("bounded navigation unavailable"),
                            "unreachable navigation was not refused by the real pathfinder");
                    following(); require(!wolf.getNavigation().isDone(), "refusal stopped prior navigation");
                    record("refusal-preserved-follow"); phase(Phase.APPROACH);
                }
                case APPROACH -> {
                    following(); boundedWait(150, "follow never approached and stopped");
                    if (separation() > 2.05 || !wolf.getNavigation().isDone()) return;
                    require(!wolf.getBoundingBox().intersects(target.getBoundingBox()), "approach left no room beside target");
                    reference = wolf.position(); record("approached-and-navigation-stopped"); phase(Phase.WAIT);
                }
                case WAIT -> {
                    following(); require(wolf.getNavigation().isDone(), "waiting follow restarted navigation");
                    require(!wolf.getBoundingBox().intersects(target.getBoundingBox()), "waiting wolf overlaps target");
                    require(wolf.position().distanceTo(reference) < 0.15, "waiting follow drifted");
                    if (elapsed() < 20) return;
                    moveTarget(4.5, 4.5); phase(Phase.RESUME);
                }
                case RESUME -> {
                    boundedWait(100, "waiting follow did not resume pursuit");
                    if (!movedTowardTarget()) return;
                    record("resumed-real-pursuit");
                    UUID queued = submit("stale-queued-idle", "idle", null, null, 30_000);
                    UUID second = submit("stale-queued-state", "state", null, null, 30_000);
                    UUID cell = submit("stale-queued-cell", "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, 30_000);
                    long oldGeneration = inbox.generation();
                    stopId = UUID.nameUUIDFromBytes("priority-stop".getBytes(StandardCharsets.UTF_8));
                    inbox.stop(new Stop(boot, actorId, run, stopId), "priority-stop");
                    require(inbox.find(queued).status().equals("cancelled") && inbox.find(second).status().equals("cancelled")
                            && inbox.find(cell).status().equals("cancelled"),
                            "priority stop did not cancel queued work");
                    require(inbox.find(stopId).status().equals("accepted"), "stop acknowledged before tick barrier");
                    try {
                        inbox.submit(new Action(boot, oldGeneration, actorId, run, UUID.randomUUID(), now() + 1000,
                                "idle", null, null, null), "stale-generation", now());
                        throw new IllegalStateException("stale generation admitted");
                    } catch (Rejection rejected) { require(rejected.status() == 409, "wrong stale-generation refusal"); }
                    phase(Phase.STOP);
                }
                case STOP -> {
                    ActionRecord ack = inbox.find(stopId);
                    require(ack.status().equals("applied") && ack.action_id().equals(stopId) && ack.run_id().equals(run)
                            && ack.generation() == inbox.generation() && ack.observation() != null
                            && ((State) ack.observation()).mode().equals("stopped") && ((State) ack.observation()).active_action_id() == null,
                            "stop acknowledgement lacks correlated stopped observation");
                    stopped("stopped"); record("correlated-stop-after-navigation-clear"); phase(Phase.STOP_WAIT);
                }
                case STOP_WAIT -> {
                    stopped("stopped");
                    if (elapsed() == 10) reference = wolf.position();
                    if (elapsed() < 20) return;
                    require(wolf.position().distanceTo(reference) < 0.05, "stopped wolf continued moving");
                    reference = wolf.position(); initialSeparation = separation();
                    followId = submit("fresh-generation-short-follow", "follow", null, target.getUUID(), 1000);
                    leaseDeadline = now() + 1000;
                    phase(Phase.FRESH);
                }
                case FRESH -> {
                    applied(); following();
                    require(inbox.find(followId).generation() == inbox.generation(), "fresh generation not retained");
                    submit("short-follow-successful-cell", "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, 30_000);
                    phase(Phase.SHORT_CELL);
                }
                case SHORT_CELL -> {
                    applied(); following();
                    CellObservation cell = (CellObservation) inbox.find(pending).observation();
                    require(cell.available() && cell.block().equals("minecraft:stone"), "short-lease inspection did not read the actual cell");
                    record("successful-cell-preserved-short-follow-before-original-deadline");
                    weatherDuringShortFollow();
                    clockDuringShortFollow();
                    submit("queued-expiry", "idle", null, null, 1); phase(Phase.QUEUED_EXPIRY);
                }
                case QUEUED_EXPIRY -> {
                    require(inbox.find(pending).status().equals("expired"), "queued deadline crossed into execution");
                    following();
                    submit("queued-cell-expiry", "inspect", new Point(arenaX + 4, FLOOR_Y, arenaZ + 4), null, 1);
                    phase(Phase.QUEUED_CELL_EXPIRY);
                }
                case QUEUED_CELL_EXPIRY -> {
                    require(inbox.find(pending).status().equals("expired") && inbox.find(pending).observation() == null,
                            "expired queued inspection produced evidence");
                    following();
                    submit("short-follow-state", "state", null, null, 30_000); phase(Phase.SHORT_STATE);
                }
                case SHORT_STATE -> {
                    applied(); following();
                    submit("short-follow-say", "say", null, null, 30_000); phase(Phase.SHORT_SAY);
                }
                case SHORT_SAY -> {
                    applied(); following();
                    submit("short-follow-unreachable-goto", "goto",
                            new Point(arenaX + 8.5, FLOOR_Y + 1, arenaZ + 12.5), null, 30_000);
                    phase(Phase.SHORT_REFUSE);
                }
                case SHORT_REFUSE -> {
                    require(inbox.find(pending).status().equals("refused")
                            && inbox.find(pending).detail().equals("bounded navigation unavailable"),
                            "short-lease real navigation refusal did not occur");
                    following(); record("state-say-refusal-and-queued-expiry-preserved-lease"); phase(Phase.LEASE);
                }
                case LEASE -> {
                    if (now() < leaseDeadline) { following(); return; }
                    stopped("idle");
                    require(wolf.position().distanceTo(reference) > 0.5 && separation() < initialSeparation - 0.5,
                            "fresh-generation follow did not cause real displacement");
                    record("fresh-generation-displacement-and-original-lease-expiry");
                    moveTarget(1.5, 1.5);
                    followId = submit("corner-follow", "follow", null, target.getUUID(), 60_000); phase(Phase.CORNER);
                }
                case CORNER -> {
                    following(); boundedWait(150, "follow did not reach arena corner");
                    if (separation() > 2.05 || !wolf.getNavigation().isDone()) return;
                    moveTarget(14.5, 14.5);
                    require(separation() > 16, "excess-distance negative control was not constructed");
                    phase(Phase.EXCESS);
                }
                case EXCESS -> {
                    stopped("idle"); record("excess-target-distance-stopped");
                    moveTarget(wolf.getX() - arenaX + 1, wolf.getZ() - arenaZ);
                    followId = submit("target-loss-follow", "follow", null, target.getUUID(), 60_000); phase(Phase.LOST_START);
                }
                case LOST_START -> {
                    applied(); following();
                    target.connection.disconnect(Component.literal("synthetic target loss"));
                    require(helper.getLevel().getServer().getPlayerList().getPlayer(target.getUUID()) == null,
                            "target loss did not remove real PlayerList entry");
                    phase(Phase.LOST);
                }
                case LOST -> {
                    stopped("idle"); record("actual-player-list-target-loss-stopped");
                    target = addTarget(wolf.getX() + 1, wolf.getZ());
                    followId = submit("target-death-follow", "follow", null, target.getUUID(), 60_000); phase(Phase.DEAD_START);
                }
                case DEAD_START -> { applied(); following(); target.setHealth(0); phase(Phase.DEAD); }
                case DEAD -> {
                    stopped("idle"); record("dead-target-stopped"); qualified = true;
                    close("qualified"); require(cleanup, "terminal cleanup failed"); helper.succeed();
                }
            }
        }

        void driveController() {
            if (!closed && inbox != null) { controllerTicks++; inbox.tick(now(), actuator); }
        }

        /** Direct production composite dispatch isolates continuity without delaying old queue/lease oracles. */
        void weatherDuringShortFollow() {
            require(now() < leaseDeadline, "weather continuity probe missed original short follow lease");
            var world = helper.getLevel();
            if (!world.getGameRules().get(GameRules.ADVANCE_WEATHER))
                world.getGameRules().set(GameRules.ADVANCE_WEATHER, true, world.getServer());
            State before = actuator.snapshot(inbox.generation(), inbox.state().queue_depth(), now());
            require(before.mode().equals("follow") && followId.equals(before.active_action_id()),
                    "real short follow unavailable before weather dispatch");
            weatherActionId = UUID.nameUUIDFromBytes("weather-during-real-short-follow".getBytes(StandardCharsets.UTF_8));
            Action request = new Action(boot, inbox.generation(), actorId, run, weatherActionId, now() + 30_000,
                    "weather", null, null, null, new WeatherArgs(1, "server_weather", "clear", 600));
            Outcome outcome = actuator.apply(request, now());
            weatherObservation = outcome.weather();
            require(outcome.applied() && weatherObservation != null && outcome.cell() == null && !outcome.observe(),
                    "direct composite weather dispatch returned no dedicated weather observation");
            var data = world.getServer().getWeatherData();
            require(weatherObservation.profile().equals("blockworld.weather@1") && weatherObservation.boot_id().equals(boot)
                    && weatherObservation.generation() == request.generation() && weatherObservation.actor_id().equals(actorId)
                    && weatherObservation.scope().equals("server_weather")
                    && weatherObservation.anchor_dimension().equals("minecraft:overworld")
                    && weatherObservation.mode().equals("clear") && weatherObservation.duration_ticks() == 600
                    && weatherObservation.clear_time() == 600 && weatherObservation.rain_time() == 0
                    && weatherObservation.thunder_time() == 0 && !weatherObservation.raining() && !weatherObservation.thundering()
                    && weatherObservation.weather_advancing() && weatherObservation.world_tick() == world.getGameTime()
                    && weatherObservation.timestamp_ms() == now() && data.getClearWeatherTime() == 600
                    && data.getRainTime() == 0 && data.getThunderTime() == 0 && !data.isRaining() && !data.isThundering(),
                    "weather observation does not match request or immediate engine readback");
            State after = actuator.snapshot(inbox.generation(), inbox.state().queue_depth(), now());
            require(after.mode().equals(before.mode()) && followId.equals(after.active_action_id()),
                    "weather replaced the real NPC follow controller");
            following();
            // The unchanged LEASE phase below proves expiry at the preexisting leaseDeadline.
            record("direct-composite-weather-preserved-real-short-follow-before-original-deadline");
        }

        /** Direct immediate placement preserves the original real-follow expiry oracle below. */
        void clockDuringShortFollow() {
            require(now() < leaseDeadline, "clock continuity probe missed original short follow lease");
            var server = helper.getLevel().getServer();
            var clock = server.registryAccess().get(net.minecraft.world.clock.WorldClocks.OVERWORLD).orElseThrow();
            var instance = server.clockManager().getInstance(clock);
            var saved = instance.packState();
            boolean advancing = server.getGlobalGameRules().get(GameRules.ADVANCE_TIME);
            State before = actuator.snapshot(inbox.generation(), inbox.state().queue_depth(), now());
            long gameTime = helper.getLevel().getGameTime();
            WeatherState weather = WeatherState.read(server);
            try {
                Action request = new Action(boot, inbox.generation(), actorId, run, UUID.randomUUID(), now() + 30_000,
                        "time", null, null, null, null, new TimeArgs(1, "overworld_clock", "toggle"));
                Outcome outcome = actuator.apply(request, now());
                require(outcome.applied() && outcome.clock() != null && outcome.weather() == null && outcome.cell() == null,
                        "direct composite clock dispatch returned no dedicated clock observation");
                var o = outcome.clock();
                require(o.before_ticks() == saved.totalTicks() && o.after_ticks() == instance.totalTicks()
                        && o.before_partial_tick() == saved.partialTick() && o.partial_tick() == instance.partialTick()
                        && o.rate() == saved.rate() && o.paused() == saved.paused() && o.time_advancing() == advancing
                        && o.after_ticks() >= o.before_ticks() && o.delta_ticks() == o.after_ticks() - o.before_ticks()
                        && o.world_tick() == gameTime && o.timestamp_ms() == now(), "clock engine readback differs");
                State after = actuator.snapshot(inbox.generation(), inbox.state().queue_depth(), now());
                require(before.mode().equals("follow") && followId.equals(before.active_action_id())
                        && after.mode().equals(before.mode()) && followId.equals(after.active_action_id())
                        && weather.equals(WeatherState.read(server)) && helper.getLevel().getGameTime() == gameTime,
                        "clock changed follow, simulation ticks or weather");
                following(); record("direct-composite-clock-preserved-real-short-follow-before-original-deadline");
            } finally {
                // Fixture-only public snapshot restoration includes fractional state; production never uses loadFrom.
                instance.loadFrom(saved);
                require(instance.packState().equals(saved), "clock continuity fixture failed exact restoration");
            }
        }

        private record WeatherState(int clear, int rain, int thunder, boolean raining, boolean thundering) {
            static WeatherState read(MinecraftServer server) {
                var data = server.getWeatherData();
                return new WeatherState(data.getClearWeatherTime(), data.getRainTime(), data.getThunderTime(),
                        data.isRaining(), data.isThundering());
            }
            void restore(MinecraftServer server) {
                var data = server.getWeatherData();
                data.setClearWeatherTime(clear); data.setRainTime(rain); data.setThunderTime(thunder);
                data.setRaining(raining); data.setThundering(thundering);
            }
        }

        void record(String event) {
            JsonObject value = new JsonObject();
            value.addProperty("event", event); value.addProperty("phase", phase.name());
            value.addProperty("test_tick", helper.getTick()); value.addProperty("clock_ms", now());
            value.addProperty("world_tick", helper.getLevel().getGameTime());
            if (inbox != null) {
                State state = inbox.state();
                value.addProperty("generation", state.generation()); value.addProperty("mode", state.mode());
                value.addProperty("active_action_id", state.active_action_id() == null ? "none" : state.active_action_id().toString());
                value.addProperty("queue_depth", state.queue_depth());
                if (pending != null) {
                    ActionRecord action = inbox.find(pending);
                    value.addProperty("latest_action_id", action.action_id().toString());
                    value.addProperty("latest_run_id", action.run_id().toString());
                    value.addProperty("latest_action_status", action.status());
                    value.addProperty("latest_action_generation", action.generation());
                }
                if (stopId != null) {
                    ActionRecord stop = inbox.find(stopId);
                    value.addProperty("stop_id", stop.action_id().toString());
                    value.addProperty("stop_run_id", stop.run_id().toString());
                    value.addProperty("stop_status", stop.status());
                    value.addProperty("stop_generation", stop.generation());
                    if (stop.observation() != null) {
                        value.addProperty("stop_observed_mode", ((State) stop.observation()).mode());
                        value.addProperty("stop_observed_active_action", ((State) stop.observation()).active_action_id() == null
                                ? "none" : ((State) stop.observation()).active_action_id().toString());
                    }
                }
            }
            if (leaseDeadline != 0) value.addProperty("short_follow_deadline_ms", leaseDeadline);
            if (weatherObservation != null) {
                value.addProperty("weather_dispatch", "direct-production-composite-continuity-probe");
                value.addProperty("weather_action_id", weatherActionId.toString());
                value.add("weather_observation", StrictJson.GSON.toJsonTree(weatherObservation));
            }
            if (wolf != null) {
                value.addProperty("actor_id", wolf.getUUID().toString());
                value.add("wolf_position", vector(wolf.position()));
                value.addProperty("navigation_done", wolf.getNavigation().isDone());
                value.addProperty("wolf_on_ground", wolf.onGround());
                value.addProperty("wolf_entity_ticks", wolf.tickCount);
                value.addProperty("home_entities_loaded_and_ticking", helper.getLevel().areEntitiesActuallyLoadedAndTicking(home));
                value.addProperty("wolf_position_entity_ticking", helper.getLevel().isPositionEntityTicking(wolf.blockPosition()));
            }
            if (target != null) {
                value.addProperty("target_id", target.getUUID().toString()); value.add("target_position", vector(target.position()));
                value.addProperty("separation", separation());
                value.addProperty("target_alive", target.isAlive());
                value.addProperty("target_in_overworld", target.level() == helper.getLevel().getServer().overworld());
                value.addProperty("target_in_player_list", helper.getLevel().getServer().getPlayerList().getPlayer(target.getUUID()) == target);
            }
            observations.add(value);
            writeReport();
        }
        JsonArray vector(Vec3 position) {
            require(Double.isFinite(position.x) && Double.isFinite(position.y) && Double.isFinite(position.z), "non-finite observation");
            JsonArray result = new JsonArray(); result.add(position.x); result.add(position.y); result.add(position.z); return result;
        }
        void writeReport() {
            JsonObject root = new JsonObject();
            root.addProperty("profile", "synthetic-server-controller-gametest@1");
            root.addProperty("controller_tick_phase", "START_SERVER_TICK");
            root.addProperty("lease_clock", "synthetic-50ms-per-start-server-tick");
            root.addProperty("arena_min_x", arenaX); root.addProperty("arena_min_z", arenaZ);
            root.addProperty("qualified", qualified); root.addProperty("closed", closed); root.addProperty("cleanup", cleanup);
            root.addProperty("failure", failure);
            root.addProperty("max_heap_bytes", Runtime.getRuntime().maxMemory());
            root.addProperty("available_processors", Runtime.getRuntime().availableProcessors());
            root.addProperty("private_bridge_config_absent", Files.notExists(Path.of("config/lychd-bridge.json")));
            root.addProperty("controller_ticket_released", ticketReleased);
            root.addProperty("weather_and_rule_restored", weatherRestored);
            root.addProperty("world_data", helper.getLevel().getServer().getWorldPath(LevelResource.DATA).toAbsolutePath().toString());
            root.add("observations", observations);
            try { Files.writeString(report, new GsonBuilder().setPrettyPrinting().create().toJson(root) + "\n"); }
            catch (IOException error) { throw new IllegalStateException("fixture report could not be written", error); }
        }
        void close(String reason) {
            if (closed) return;
            closed = true;
            boolean clean = true;
            try { if (controller != null) controller.close(); }
            catch (Throwable error) { clean = false; failure = "controller cleanup: " + error; }
            ticketReleased = controllerTicket == null || !ticketTypes().contains(controllerTicket);
            clean &= ticketReleased;
            for (ServerPlayer player : players) {
                try {
                    if (helper.getLevel().getServer().getPlayerList().getPlayer(player.getUUID()) == player)
                        player.connection.disconnect(Component.literal("synthetic controller fixture closed"));
                    clean &= helper.getLevel().getServer().getPlayerList().getPlayer(player.getUUID()) == null;
                } catch (Throwable error) { clean = false; failure = "player cleanup: " + error; }
            }
            if (wolf != null) {
                clean &= wolf.getNavigation().isDone();
                wolf.discard(); clean &= wolf.isRemoved();
            }
            if (originalWeather != null) {
                try {
                    var world = helper.getLevel();
                    originalWeather.restore(world.getServer());
                    world.getGameRules().set(GameRules.ADVANCE_WEATHER, originalWeatherAdvance, world.getServer());
                    weatherRestored = originalWeather.equals(WeatherState.read(world.getServer()))
                            && originalWeatherAdvance == world.getGameRules().get(GameRules.ADVANCE_WEATHER);
                    clean &= weatherRestored;
                } catch (Throwable error) { clean = false; failure = "weather cleanup: " + error; }
            }
            cleanup = clean;
            qualified &= cleanup;
            OPEN.remove(this);
            record("cleanup-" + reason);
        }
    }
}
