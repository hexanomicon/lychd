package org.lychd.companion;

import java.util.Objects;
import static org.lychd.companion.protocol.Protocol.*;

/** Routes the finite mailbox without granting world effects ownership of the NPC lease. */
public final class CompanionActuator implements Actuator {
    private final Actuator npc;
    private final WorldWeatherController weather;
    private final WorldClockController clock;

    public CompanionActuator(Actuator npc, WorldWeatherController weather, WorldClockController clock) {
        this.npc = Objects.requireNonNull(npc); this.weather = Objects.requireNonNull(weather);
        this.clock = Objects.requireNonNull(clock);
    }
    @Override public void tick(long nowMs) { npc.tick(nowMs); }
    @Override public void stop() { npc.stop(); }
    @Override public State snapshot(long generation, int queueDepth, long nowMs) {
        return npc.snapshot(generation, queueDepth, nowMs);
    }
    @Override public Outcome apply(Action action, long nowMs) {
        if ("time".equals(action.kind())) return clock.apply(action, nowMs);
        if ("weather".equals(action.kind())) return weather.apply(action, nowMs);
        if (action.time() != null || action.weather() != null) return Outcome.refused("cross-kind arguments");
        return npc.apply(action, nowMs);
    }
}
