package org.lychd.companion.protocol;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Protocol 1 values; these immutable records never expose world objects. */
public final class Protocol {
    private Protocol() {}
    public static final int VERSION = 1;
    public static final int MAX_REQUEST_BYTES = 8192;
    public static final int MAX_RESPONSE_BYTES = 65536;
    public static final int QUEUE_CAPACITY = 8;
    public static final long MAX_LEASE_MS = 60_000;

    public record Point(double x, double y, double z) {
        public double distanceSquared(Point other) {
            double dx = x - other.x, dy = y - other.y, dz = z - other.z;
            return dx * dx + dy * dy + dz * dz;
        }
    }
    public record Player(UUID id, String name, List<Double> position) {
        public Player { position = List.copyOf(position); }
    }
    public sealed interface Observation permits State, CellObservation, WeatherObservation, ClockObservation {}
    public record TimeArgs(int revision, String scope, String mode) {
        public boolean valid() {
            return revision == 1 && "overworld_clock".equals(scope)
                    && ("day".equals(mode) || "night".equals(mode) || "toggle".equals(mode));
        }
    }
    public record ClockObservation(String profile, UUID boot_id, long generation, UUID actor_id,
                                   String scope, String anchor_dimension, String clock,
                                   String requested_mode, String mode, long before_ticks, long after_ticks,
                                   int delta_ticks, int before_phase, int after_phase, long before_cycle,
                                   long after_cycle, int cycle_increment, float before_partial_tick,
                                   float partial_tick, float rate, boolean paused, boolean time_advancing,
                                   long world_tick, long timestamp_ms) implements Observation {}
    public record WeatherArgs(int revision, String scope, String mode, int durationTicks) {
        public boolean valid() {
            return revision == 1 && "server_weather".equals(scope)
                    && ("clear".equals(mode) || "rain".equals(mode)) && durationTicks == 600;
        }
    }
    public record WeatherObservation(String profile, UUID boot_id, long generation, UUID actor_id,
                                     String scope, String anchor_dimension, String mode, int duration_ticks,
                                     int clear_time, int rain_time, int thunder_time, boolean raining,
                                     boolean thundering, boolean weather_advancing, long world_tick,
                                     long timestamp_ms) implements Observation {}
    public record CellObservation(String profile, UUID boot_id, long generation, UUID actor_id,
                                  String dimension, List<Integer> position, boolean available, String block,
                                  Map<String, String> properties, long world_tick, long timestamp_ms)
            implements Observation {
        public CellObservation { position = List.copyOf(position); properties = Map.copyOf(properties); }
    }
    public record State(int protocol, UUID boot_id, long generation, UUID actor_id,
                        String mode, List<Double> position, Double yaw, Double pitch,
                        int queue_depth, UUID active_action_id, List<Player> players,
                        long timestamp_ms) implements Observation {
        public State {
            position = position == null ? null : List.copyOf(position);
            players = List.copyOf(players);
        }
    }
    public record Action(UUID bootId, long generation, UUID actorId, UUID runId,
                         UUID actionId, long expiresAtMs, String kind, Point point,
                         UUID targetId, String text, WeatherArgs weather, TimeArgs time) {
        public Action(UUID bootId, long generation, UUID actorId, UUID runId, UUID actionId,
                      long expiresAtMs, String kind, Point point, UUID targetId, String text, WeatherArgs weather) {
            this(bootId, generation, actorId, runId, actionId, expiresAtMs, kind, point, targetId, text, weather, null);
        }
        public Action(UUID bootId, long generation, UUID actorId, UUID runId, UUID actionId,
                      long expiresAtMs, String kind, Point point, UUID targetId, String text) {
            this(bootId, generation, actorId, runId, actionId, expiresAtMs, kind, point, targetId, text, null);
        }
    }
    public record Stop(UUID bootId, UUID actorId, UUID runId, UUID actionId) {}
    public record ActionRecord(int protocol, UUID boot_id, UUID action_id, UUID run_id,
                               long generation, String status, String detail,
                               Observation observation) {}
    public record Outcome(boolean applied, String detail, boolean observe, CellObservation cell,
                          WeatherObservation weather, ClockObservation clock, boolean uncertain) {
        public Outcome(boolean applied, String detail, boolean observe, CellObservation cell,
                       WeatherObservation weather, ClockObservation clock) {
            this(applied, detail, observe, cell, weather, clock, false);
        }
        public Outcome(boolean applied, String detail, boolean observe, CellObservation cell, WeatherObservation weather) {
            this(applied, detail, observe, cell, weather, null);
        }
        public Outcome(boolean applied, String detail, boolean observe, CellObservation cell) {
            this(applied, detail, observe, cell, null);
        }
        public Outcome(boolean applied, String detail, boolean observe) { this(applied, detail, observe, null); }
        public static Outcome applied(String detail) { return new Outcome(true, detail, false); }
        public static Outcome refused(String detail) { return new Outcome(false, detail, false); }
        public static Outcome unknown(String detail) {
            return new Outcome(false, detail, false, null, null, null, true);
        }
        public static Outcome inspected(CellObservation cell) { return new Outcome(true, "server cell observation", false, cell); }
        public static Outcome clockApplied(ClockObservation clock) {
            return new Outcome(true, "overworld clock placed forward", false, null, null, clock);
        }
        public static Outcome weatherApplied(WeatherObservation weather) {
            return new Outcome(true, "global server weather set for 600 ticks", false, null, weather);
        }
    }
    public interface Actuator {
        void stop();
        default void tick(long nowMs) {}
        Outcome apply(Action action, long nowMs);
        State snapshot(long generation, int queueDepth, long nowMs);
    }
    public static final class Rejection extends RuntimeException {
        private final int status;
        public Rejection(int status, String detail) { super(detail); this.status = status; }
        public int status() { return status; }
    }
}
