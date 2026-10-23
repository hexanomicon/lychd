package org.lychd.companion.protocol;

import java.util.ArrayDeque;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Predicate;
import static org.lychd.companion.protocol.Protocol.*;

/** Admission and tick share one short lock: no old-generation effect can cross an admitted stop. */
public final class ActionInbox {
    private static final int STOP_HISTORY_CAPACITY = 256;
    private static final class Entry {
        final String body;
        final Action action;
        ActionRecord record;
        Entry(String body, Action action, ActionRecord record) {
            this.body = body; this.action = action; this.record = record;
        }
    }
    private final UUID bootId;
    private final UUID actorId;
    private final int maxActions;
    private final Predicate<Point> contains;
    private final Map<UUID, Entry> retained = new LinkedHashMap<>();
    private final Map<UUID, Entry> retainedStops = new LinkedHashMap<>();
    private final ArrayDeque<Entry> queue = new ArrayDeque<>();
    private final AtomicReference<State> cached;
    private Entry stop;
    private boolean stopPending;
    private long generation;

    public ActionInbox(UUID bootId, UUID actorId, int maxActions, State initial) {
        this(bootId, actorId, maxActions, initial, point -> true);
    }
    public ActionInbox(UUID bootId, UUID actorId, int maxActions, State initial, Predicate<Point> contains) {
        if (maxActions < 1 || maxActions > 256) throw new IllegalArgumentException("invalid retention limit");
        this.bootId = bootId; this.actorId = actorId; this.maxActions = maxActions;
        this.cached = new AtomicReference<>(initial);
        this.contains = contains;
    }
    public State state() { return cached.get(); }
    public synchronized long generation() { return generation; }
    public synchronized ActionRecord submit(Action action, String body, long nowMs) {
        Entry previous = retained.get(action.actionId());
        if (previous != null) return duplicate(previous, body);
        if (retainedStops.containsKey(action.actionId())) throw reject(409, "action identity collision");
        bind(action.bootId(), action.actorId());
        // The final retained stop must remain the last possible effect barrier for this boot.
        if (retainedStops.size() >= STOP_HISTORY_CAPACITY) throw reject(503, "stop history full; admission sealed");
        if (action.generation() != generation) throw reject(409, "stale generation");
        long remaining = action.expiresAtMs() - nowMs;
        if (action.expiresAtMs() <= nowMs || remaining <= 0 || remaining > MAX_LEASE_MS)
            throw reject(400, "invalid action deadline");
        if (action.point() != null) {
            State issued = cached.get();
            if (issued.position() == null) throw reject(409, "owned actor unavailable at issuance");
            Point actor = new Point(issued.position().get(0), issued.position().get(1), issued.position().get(2));
            if (!contains.test(action.point()) || actor.distanceSquared(action.point()) > 16 * 16)
                throw reject(400, "point outside issuance bounds");
            if (action.kind().equals("inspect") && !contains.test(new Point(
                    action.point().x() + 1, action.point().y() + 1, action.point().z() + 1)))
                throw reject(400, "cell outside issuance bounds");
        }
        if (retained.size() >= maxActions) throw reject(503, "action retention full");
        if (queue.size() >= QUEUE_CAPACITY) throw reject(429, "action inbox full");
        ActionRecord record = record(action.actionId(), action.runId(), generation, "accepted", "queued", null);
        Entry entry = new Entry(body, action, record);
        retained.put(action.actionId(), entry);
        queue.add(entry);
        return record;
    }
    public synchronized ActionRecord stop(Stop request, String body) {
        Entry previous = retainedStops.get(request.actionId());
        if (previous != null) return duplicate(previous, body);
        if (retained.containsKey(request.actionId())) throw reject(409, "action identity collision");
        bind(request.bootId(), request.actorId());
        if (retainedStops.size() >= STOP_HISTORY_CAPACITY) throw reject(503, "stop history full; admission sealed");
        if (generation == Long.MAX_VALUE) throw reject(503, "generation exhausted");
        if (stopPending) finish(stop, "cancelled", "superseded by newer stop before barrier", null);
        generation++;
        for (Entry entry : queue) finish(entry, "cancelled", "cancelled by stop", null);
        queue.clear();
        stop = new Entry(body, null, record(request.actionId(), request.runId(), generation,
                "accepted", "stop barrier pending", null));
        retainedStops.put(request.actionId(), stop);
        stopPending = true;
        return stop.record;
    }
    public synchronized ActionRecord find(UUID id) {
        Entry entry = retainedStops.get(id);
        if (entry == null) entry = retained.get(id);
        return entry == null ? null : entry.record;
    }
    /** Called once per server tick, exclusively on the Minecraft thread. */
    public synchronized void tick(long nowMs, Actuator actuator) {
        if (stopPending) {
            actuator.stop();
            // Only the server-thread stop barrier may publish an applied stop/new generation.
            cached.set(actuator.snapshot(generation, queue.size(), nowMs));
            finish(stop, "applied", "owned controller stopped", cached.get());
            stopPending = false;
        }
        actuator.tick(nowMs);
        Entry entry = queue.poll();
        if (entry != null) {
            Action action = entry.action;
            if (action.generation() != generation) finish(entry, "cancelled", "stale generation", null);
            else if (action.expiresAtMs() <= nowMs) finish(entry, "expired", "deadline elapsed before execution", null);
            else {
                Outcome outcome = actuator.apply(action, nowMs);
                cached.set(actuator.snapshot(generation, queue.size(), nowMs));
                finish(entry, outcome.uncertain() ? "unknown" : outcome.applied() ? "applied" : "refused", outcome.detail(),
                        outcome.clock() != null ? outcome.clock() : outcome.weather() != null ? outcome.weather()
                                : outcome.cell() != null ? outcome.cell() : outcome.observe() ? cached.get() : null);
            }
        }
        cached.set(actuator.snapshot(generation, queue.size(), nowMs));
    }
    private ActionRecord duplicate(Entry previous, String body) {
        if (!previous.body.equals(body)) throw reject(409, "changed action identity");
        return previous.record;
    }
    private void bind(UUID boot, UUID actor) {
        if (!bootId.equals(boot) || !actorId.equals(actor)) throw reject(409, "server or actor identity mismatch");
    }
    private void finish(Entry entry, String status, String detail, Observation observation) {
        ActionRecord old = entry.record;
        entry.record = record(old.action_id(), old.run_id(), old.generation(), status, detail, observation);
    }
    private ActionRecord record(UUID id, UUID run, long gen, String status, String detail, Observation observation) {
        return new ActionRecord(VERSION, bootId, id, run, gen, status, detail, observation);
    }
    private static Rejection reject(int status, String detail) { return new Rejection(status, detail); }
}
