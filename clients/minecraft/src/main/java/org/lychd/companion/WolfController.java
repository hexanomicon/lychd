package org.lychd.companion;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.TreeMap;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ChunkLevel;
import net.minecraft.server.level.FullChunkStatus;
import net.minecraft.server.level.Ticket;
import net.minecraft.server.level.TicketType;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.pathfinder.Node;
import net.minecraft.world.level.storage.LevelResource;
import org.lychd.companion.mixin.MobGoalAccess;
import static org.lychd.companion.protocol.Protocol.*;

/** Minecraft thread only. One owned vanilla Wolf, no teleport, combat, commands or client renderer. */
public final class WolfController implements Actuator, AutoCloseable {
    private final MinecraftServer server;
    private final ServerLevel world;
    private final BridgeConfig config;
    private final UUID bootId;
    // TicketStorage matches types by identity. This private type cannot remove another owner's ticket.
    private final TicketType homeTicketType = new TicketType(TicketType.NO_TIMEOUT,
            TicketType.FLAG_LOADING | TicketType.FLAG_SIMULATION | TicketType.FLAG_KEEP_DIMENSION_ACTIVE);
    private final ChunkPos home;
    private boolean homeTicketHeld;
    private Wolf actor;
    private String mode = "idle";
    private UUID activeAction;
    private UUID followTarget;
    private boolean followPursuing;
    private Point lookPoint;
    private long leaseEnd;
    private int ticks;

    public WolfController(MinecraftServer server, BridgeConfig config, UUID bootId) throws IOException {
        this.server = server; this.world = server.overworld(); this.config = config; this.bootId = bootId;
        home = new ChunkPos(config.spawnX() >> 4, config.spawnZ() >> 4);
        try {
            // One fixed home anchor; vanilla loads its bounded supporting halo for entity ticking.
            // No PERSIST flag: the ticket is neither a saved forced chunk nor a restart reservation.
            homeTicketHeld = true;
            world.getChunkSource().addTicket(new Ticket(homeTicketType,
                    ChunkLevel.byStatus(FullChunkStatus.ENTITY_TICKING)), home);
            world.getChunk(config.spawnX() >> 4, config.spawnZ() >> 4);
            Path directory = server.getWorldPath(LevelResource.DATA);
            Path marker = directory.resolve("lychd-companion-created.marker");
            boolean previouslyCreated = Files.exists(marker);
            if (previouslyCreated && (Files.size(marker) > 64
                    || !Files.readString(marker, StandardCharsets.US_ASCII).equals(config.actorId().toString())))
                throw new IOException("Companion created marker does not match configured actor");
            refreshActor();
            if (actor != null && !previouslyCreated) reserveMarker(directory, marker);
            if (actor == null && config.spawnActor() && !previouslyCreated) {
                reserveMarker(directory, marker);
                Wolf wolf = EntityTypes.WOLF.create(world, EntitySpawnReason.COMMAND);
                if (wolf == null) throw new IOException("Companion actor creation refused");
                int y = world.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, config.spawnX(), config.spawnZ());
                wolf.setUUID(config.actorId());
                wolf.setPos(config.spawnX() + 0.5, y, config.spawnZ() + 0.5);
                prepare(wolf);
                if (!world.addFreshEntity(wolf)) throw new IOException("Companion actor insertion refused");
                actor = wolf;
                mode = "idle";
            }
        } catch (IOException | RuntimeException | Error error) {
            releaseHomeTicket();
            throw error;
        }
    }
    private void releaseHomeTicket() {
        if (homeTicketHeld) {
            int radius = ChunkLevel.byStatus(FullChunkStatus.FULL)
                    - ChunkLevel.byStatus(FullChunkStatus.ENTITY_TICKING);
            world.getChunkSource().removeTicketWithRadius(homeTicketType, home, radius);
            homeTicketHeld = false;
        }
    }
    @Override public void close() {
        try { stop(); }
        finally { releaseHomeTicket(); }
    }
    private void reserveMarker(Path directory, Path marker) throws IOException {
        Files.createDirectories(directory);
        // Reserve before spawning and force to disk. A crash can lose availability, never permit duplication.
        try (FileChannel out = FileChannel.open(marker, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            ByteBuffer value = ByteBuffer.wrap(config.actorId().toString().getBytes(StandardCharsets.US_ASCII));
            while (value.hasRemaining()) out.write(value);
            out.force(true);
        }
        try (FileChannel dir = FileChannel.open(directory, StandardOpenOption.READ)) { dir.force(true); }
    }
    private void prepare(Wolf wolf) {
        wolf.setPersistenceRequired();
        wolf.setNoAi(false);
        wolf.setCustomName(Component.literal("LychD companion"));
        wolf.removeAllGoals(goal -> true);
        ((MobGoalAccess) wolf).lychdTargetSelector().removeAllGoals(goal -> true);
        wolf.setOwnerReference(null);
        wolf.setTame(false, false);
        wolf.setOrderedToSit(false);
        wolf.setTarget(null);
        wolf.setPersistentAngerEndTime(0);
        wolf.setPersistentAngerTarget(null);
        wolf.getNavigation().stop();
        wolf.setSpeed(0);
    }
    private boolean refreshActor() {
        var found = world.getEntity(config.actorId());
        if (!(found instanceof Wolf wolf) || !wolf.isAlive() || wolf.isRemoved() || wolf.level() != world) {
            if (actor != null) clearController("unavailable");
            actor = null;
            mode = "unavailable";
            return false;
        }
        if (actor != wolf) {
            actor = wolf;
            prepare(wolf);
            clearController("idle");
        }
        // Prevent taming from granting a competing owner-teleport controller.
        wolf.setOwnerReference(null);
        wolf.setOrderedToSit(false);
        wolf.setTarget(null);
        wolf.setPersistentAngerEndTime(0);
        wolf.setPersistentAngerTarget(null);
        return true;
    }
    @Override public void stop() {
        refreshActor();
        clearController(actor == null ? "unavailable" : "stopped");
    }
    private void stopMovement() {
        if (actor != null) {
            actor.getNavigation().stop();
            actor.getMoveControl().setWantedPosition(actor.getX(), actor.getY(), actor.getZ(), 0);
            actor.setSpeed(0);
            actor.xxa = 0; actor.yya = 0; actor.zza = 0;
            actor.getJumpControl().tick();
            actor.setJumping(false);
        }
    }
    private void clearController(String nextMode) {
        stopMovement();
        if (actor != null) {
            actor.getLookControl().setLookAt(actor.getX(), actor.getEyeY(), actor.getZ());
            actor.setTarget(null);
        }
        mode = nextMode;
        activeAction = null; followTarget = null; followPursuing = false; lookPoint = null; leaseEnd = 0;
    }
    @Override public void tick(long nowMs) {
        ticks++;
        if (!refreshActor()) return;
        if (!config.contains(position())) { clearController("stopped"); return; }
        if (activeAction != null && nowMs >= leaseEnd) { clearController("idle"); return; }
        switch (mode) {
            case "goto" -> {
                if (actor.getNavigation().isDone()) clearController("idle");
            }
            case "follow" -> {
                ServerPlayer target = target(followTarget);
                if (target == null) clearController("idle");
                else switch (config.followDistance().decide(followPursuing,
                        point(target).distanceSquared(position()), ticks % 10 == 0)) {
                    case STOP -> { stopMovement(); followPursuing = false; }
                    case NAVIGATE -> {
                        if (navigate(point(target), 1.0)) followPursuing = true;
                        else clearController("idle");
                    }
                    case WAIT, CONTINUE -> { }
                }
            }
            case "look" -> actor.getLookControl().setLookAt(lookPoint.x(), lookPoint.y(), lookPoint.z());
            case "idle" -> {
                if (activeAction != null) {
                    double angle = (ticks % 160) * Math.PI / 80;
                    actor.getLookControl().setLookAt(actor.getX() + Math.cos(angle) * 2,
                            actor.getEyeY(), actor.getZ() + Math.sin(angle) * 2);
                }
            }
            default -> { }
        }
    }
    @Override public Outcome apply(Action request, long nowMs) {
        if (request.kind().equals("state")) return new Outcome(true, "cached server observation", true);
        if (!refreshActor()) return Outcome.refused("owned actor unavailable");
        if (!config.contains(position())) return Outcome.refused("owned actor outside control box");
        if (request.point() != null && (!config.contains(request.point())
                || request.point().distanceSquared(position()) > 16 * 16)) return Outcome.refused("point outside admitted bounds");
        if (request.kind().equals("inspect")) return inspect(request, nowMs);
        if (request.kind().equals("say")) {
            server.getPlayerList().broadcastSystemMessage(Component.literal("<LychD companion> " + request.text()), false);
            return Outcome.applied("ordinary chat broadcast");
        }
        ServerPlayer target = null;
        if (request.kind().equals("follow")) {
            target = target(request.targetId());
            if (target == null) return Outcome.refused("follow target unavailable or outside admitted bounds");
        }
        boolean pursueFollow = target != null && config.followDistance().decide(false,
                point(target).distanceSquared(position()), false) == FollowDistancePolicy.Decision.NAVIGATE;
        // Validate navigation before replacing the previous controller: refused means no controller effect.
        net.minecraft.world.level.pathfinder.Path path = null;
        if (request.kind().equals("goto") || pursueFollow) {
            Point destination = target == null ? request.point() : point(target);
            path = boundedPath(destination);
            if (path == null) return Outcome.refused("bounded navigation unavailable");
        }
        clearController("idle");
        mode = request.kind(); activeAction = request.actionId(); leaseEnd = request.expiresAtMs();
        switch (mode) {
            case "look" -> {
                lookPoint = request.point();
                actor.getLookControl().setLookAt(lookPoint.x(), lookPoint.y(), lookPoint.z());
            }
            case "goto", "follow" -> {
                followTarget = request.targetId();
                followPursuing = pursueFollow;
                if (path != null && !actor.getNavigation().moveTo(path, 1.0)) {
                    clearController("idle");
                    return Outcome.applied("bounded controller applied; navigation inactive");
                }
            }
            case "idle" -> { }
            default -> throw new IllegalStateException("unsupported controller");
        }
        if (mode.equals("follow") && !followPursuing)
            return Outcome.applied("finite follow controller activated; waiting within distance band");
        return Outcome.applied(mode.equals("goto") || mode.equals("follow")
                ? "bounded navigation activated; destination completion unconfirmed" : "bounded controller activated");
    }
    private Outcome inspect(Action request, long nowMs) {
        Point point = request.point();
        if (point == null || point.x() != Math.rint(point.x()) || point.y() != Math.rint(point.y())
                || point.z() != Math.rint(point.z()) || Math.abs(point.x()) > 30_000_000
                || Math.abs(point.y()) > 30_000_000 || Math.abs(point.z()) > 30_000_000
                || !config.contains(new Point(point.x() + 1, point.y() + 1, point.z() + 1)))
            return Outcome.refused("invalid or unbounded cell");
        BlockPos cell = new BlockPos((int) point.x(), (int) point.y(), (int) point.z());
        if (world.isOutsideBuildHeight(cell) || !world.getWorldBorder().isWithinBounds(cell))
            return Outcome.refused("cell outside world bounds");
        // getChunkNow never requests a load; read the returned chunk rather than Level.getBlockState.
        var chunk = world.getChunkSource().getChunkNow(cell.getX() >> 4, cell.getZ() >> 4);
        if (chunk == null) return new Outcome(false, "cell not loaded", false,
                new CellObservation("blockworld.cell@1", bootId, request.generation(), config.actorId(),
                        world.dimension().identifier().toString(), List.of(cell.getX(), cell.getY(), cell.getZ()),
                        false, null, java.util.Map.of(), world.getGameTime(), nowMs));
        BlockState state = chunk.getBlockState(cell);
        var properties = new TreeMap<String, String>();
        for (Property<?> property : state.getProperties()) properties.put(property.getName(), propertyValue(state, property));
        return Outcome.inspected(new CellObservation("blockworld.cell@1", bootId, request.generation(),
                config.actorId(), world.dimension().identifier().toString(),
                List.of(cell.getX(), cell.getY(), cell.getZ()), true, BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString(),
                properties, world.getGameTime(), nowMs));
    }
    private static <T extends Comparable<T>> String propertyValue(BlockState state, Property<T> property) {
        return property.getName(state.getValue(property));
    }
    private ServerPlayer target(UUID id) {
        ServerPlayer player = server.getPlayerList().getPlayer(id);
        return player != null && player.isAlive() && player.level() == world && !player.getName().getString().isBlank()
                && config.contains(point(player)) && point(player).distanceSquared(position()) <= 16 * 16 ? player : null;
    }
    private net.minecraft.world.level.pathfinder.Path boundedPath(Point destination) {
        var path = actor.getNavigation().createPath(destination.x(), destination.y(), destination.z(), 0);
        if (path == null || !path.canReach()) return null;
        for (int i = 0; i < path.getNodeCount(); i++) {
            Node node = path.getNode(i);
            if (!config.contains(new Point(node.x + 0.5, node.y, node.z + 0.5))) return null;
        }
        return path;
    }
    private boolean navigate(Point destination, double speed) {
        var path = boundedPath(destination);
        return path != null && actor.getNavigation().moveTo(path, speed);
    }
    private Point position() { return new Point(actor.getX(), actor.getY(), actor.getZ()); }
    private static Point point(net.minecraft.world.entity.Entity entity) { return new Point(entity.getX(), entity.getY(), entity.getZ()); }
    private static List<Double> coordinates(net.minecraft.world.entity.Entity entity) { return List.of(entity.getX(), entity.getY(), entity.getZ()); }
    @Override public State snapshot(long generation, int queueDepth, long nowMs) {
        boolean available = refreshActor();
        List<Player> players = server.getPlayerList().getPlayers().stream().limit(16)
                .map(player -> new Player(player.getUUID(), player.getName().getString(), coordinates(player))).toList();
        return new State(VERSION, bootId, generation, config.actorId(), mode,
                available ? coordinates(actor) : null, available ? (double) actor.getYHeadRot() : null,
                available ? (double) actor.getXRot() : null, queueDepth, activeAction, players, nowMs);
    }
}
