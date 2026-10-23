package org.lychd.companion;

import java.util.HashMap;
import java.util.UUID;
import net.minecraft.core.Holder;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.clock.ClockTimeMarker;
import net.minecraft.world.clock.ClockTimeMarkers;
import net.minecraft.world.clock.WorldClock;
import net.minecraft.world.clock.WorldClocks;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.timeline.Timeline;
import net.minecraft.world.timeline.Timelines;
import static org.lychd.companion.protocol.Protocol.*;

/** Minecraft thread only. Immediate selected-clock placement; owns no NPC controller or lease. */
public final class WorldClockController {
    private final MinecraftServer server;
    private final BridgeConfig config;
    private final UUID bootId;
    public WorldClockController(MinecraftServer server, BridgeConfig config, UUID bootId) {
        this.server = server; this.config = config; this.bootId = bootId;
    }
    /** Read-only profile check, exposed for independent engine fixture negative controls. */
    public static boolean compatible(Holder<WorldClock> clock, Holder<Timeline> day,
                                     net.minecraft.world.level.dimension.DimensionType dimension) {
        if (clock == null || !clock.isBound() || day == null || !day.isBound()) return false;
        if (!matchingTimeline(clock, day.value())) return false;
        return dimension.defaultClock().filter(value -> value.isBound() && value.is(clock)).isPresent()
                && dimension.timelines().isBound() && dimension.timelines().contains(day) && !dimension.hasFixedTime();
    }
    public static boolean matchingTimeline(Holder<WorldClock> clock, Timeline timeline) {
        if (clock == null || !clock.isBound()) return false;
        if (!timeline.clock().isBound() || !timeline.clock().is(clock) || timeline.periodTicks().orElse(-1) != 24000) return false;
        var markers = new HashMap<ResourceKey<ClockTimeMarker>, ClockTimeMarker>();
        timeline.registerTimeMarkers(markers::put);
        return marker(markers.get(ClockTimeMarkers.DAY), clock, 1000)
                && marker(markers.get(ClockTimeMarkers.NIGHT), clock, 13000);
    }
    private static boolean marker(ClockTimeMarker marker, Holder<WorldClock> clock, int ticks) {
        return marker != null && marker.clock().isBound() && marker.clock().is(clock)
                && marker.periodTicks().orElse(-1) == 24000 && marker.ticks() == ticks;
    }
    public Outcome apply(Action request, long nowMs) {
        TimeArgs args = request.time();
        if (!"time".equals(request.kind()) || args == null || !args.valid() || request.weather() != null
                || request.point() != null || request.targetId() != null || request.text() != null)
            return Outcome.refused("invalid clock request");
        if (!bootId.equals(request.bootId()) || !config.actorId().equals(request.actorId())
                || request.generation() < 0 || nowMs < 0 || request.expiresAtMs() <= nowMs)
            return Outcome.refused("invalid clock envelope");
        if (!config.allowTime()) return Outcome.refused("server clock capability disabled");
        var world = server.overworld();
        var clock = server.registryAccess().get(WorldClocks.OVERWORLD).orElse(null);
        var day = server.registryAccess().get(Timelines.OVERWORLD_DAY).orElse(null);
        if (!compatible(clock, day, world.dimensionType())) return Outcome.refused("incompatible overworld clock profile");
        final net.minecraft.world.clock.ServerClockManager.ServerClockInstance instance;
        try { instance = server.clockManager().getInstance(clock); }
        catch (IllegalStateException unavailable) { return Outcome.refused("overworld clock instance unavailable"); }
        long before = instance.totalTicks();
        float fraction = instance.partialTick(), rate = instance.rate();
        boolean paused = instance.isPaused(), advancing = server.getGlobalGameRules().get(GameRules.ADVANCE_TIME);
        if (!Float.isFinite(fraction) || !Float.isFinite(rate)) return Outcome.refused("nonfinite clock settings");
        final ClockPlacement.Placement placement;
        try { placement = ClockPlacement.compute(before, args.mode()); }
        catch (IllegalArgumentException invalid) { return Outcome.refused("invalid cumulative clock placement"); }
        if (placement.delta() > 0) server.clockManager().setTotalTicks(clock, placement.after());
        float expectedFraction = placement.delta() == 0 ? fraction : 0F;
        if (instance.totalTicks() != placement.after() || Float.compare(instance.partialTick(), expectedFraction) != 0
                || Float.compare(instance.rate(), rate) != 0 || instance.isPaused() != paused
                || server.getGlobalGameRules().get(GameRules.ADVANCE_TIME) != advancing)
            return Outcome.unknown("clock readback mismatch; outcome uncertain");
        return Outcome.clockApplied(new ClockObservation("blockworld.clock@1", bootId, request.generation(),
                config.actorId(), "overworld_clock", "minecraft:overworld", "minecraft:overworld", args.mode(),
                placement.mode(), before, instance.totalTicks(), placement.delta(), placement.beforePhase(),
                placement.afterPhase(), placement.beforeCycle(), placement.afterCycle(), placement.cycleIncrement(),
                fraction, instance.partialTick(), instance.rate(), instance.isPaused(), advancing, world.getGameTime(), nowMs));
    }
}
