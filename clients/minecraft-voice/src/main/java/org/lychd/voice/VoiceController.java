package org.lychd.voice;

import java.io.IOException;
import java.util.Objects;
import java.util.UUID;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/** Small synchronized client actor. Tick owns physical input; three bounded lanes own all network IO. */
final class VoiceController {
    interface Lane { boolean offer(Runnable work); }
    record Hud(String requestId, String operation, String localStage, String phase, Protocol.Operation result) { }
    private static final byte[] EMPTY = new byte[0];
    private final ControlTransport transport;
    private final Lane ordinaryLane, finishLane, stopLane;
    private final LongSupplier clock;
    private final Supplier<String> ids;
    private final EdgeGuard edges = new EdgeGuard();
    private Protocol.State state;
    private long stateAt = -1, contextVersion, nextPollAt;
    private EdgeGuard.Input input;
    private Work record, stop;
    private Hud hud;
    private boolean polling, closed, retired, sessionLost, stopSealed;
    private int records, stops;

    private static final class Work {
        final Protocol.Gesture gesture;
        final long pollUntil;
        final boolean held;
        Protocol.Release release;
        boolean releaseDispatched, releaseInFlight, releaseSuppressed, releaseAcknowledged;
        Protocol.Operation observation;
        boolean dispatched, active = true, uncertain, stopRequested;
        Work(Protocol.Gesture gesture, long sessionExpiry, boolean held) {
            this.gesture = gesture; this.held = held;
            pollUntil = gesture.operation().equals("stop") ? gesture.createdAt() + 60000
                    : Math.min(sessionExpiry, gesture.expiresAt() + 60000);
        }
    }

    VoiceController(ControlTransport transport, Lane ordinaryLane, Lane finishLane, Lane stopLane) {
        this(transport, ordinaryLane, finishLane, stopLane, System::currentTimeMillis, () -> UUID.randomUUID().toString());
    }
    VoiceController(ControlTransport transport, Lane ordinaryLane, Lane finishLane, Lane stopLane, LongSupplier clock, Supplier<String> ids) {
        this.transport = transport; this.ordinaryLane = ordinaryLane; this.finishLane = finishLane; this.stopLane = stopLane;
        this.clock = clock; this.ids = ids;
    }

    synchronized void tick(EdgeGuard.Input next) {
        if (closed) return;
        input = next; long now = clock.getAsLong();
        EdgeGuard.Decision decision = edges.update(next, contextVersion);
        if (decision.boundary()) hud = null;
        if (decision.boundary() && record != null && !record.dispatched && record.active) cancelUnsent(record);
        if (decision.boundary() && record != null && record.held) record.releaseSuppressed = true;
        if ((decision.lostWorldOrFocus() || decision.boundary() && record != null && record.held)
                && needsStop(record) && !record.stopRequested) requestStop(now);
        if (decision.action() == EdgeGuard.Action.STOP) requestStop(now);
        else if (decision.action() == EdgeGuard.Action.RELEASE) requestRelease(now);
        else if ((decision.action() == EdgeGuard.Action.RECORD || decision.action() == EdgeGuard.Action.HOLD)
                && recordEligible(now)) requestRecord(now, decision.action() == EdgeGuard.Action.HOLD);
        retireTimedOut(record, now); retireTimedOut(stop, now);
        poll(now);
    }

    private boolean fresh(long now) {
        return state != null && stateAt >= 0 && now >= stateAt && now - stateAt <= 1500 && now < state.sessionExpiresAt();
    }
    private boolean recordLifetimeFits(long now) {
        return state != null && now <= state.sessionExpiresAt() - state.instructionTimeout();
    }
    private boolean recordEligible(long now) {
        return !retired && records < 128 && input != null && input.matched() && input.focused()
                && input.menuFree() && !input.paused() && fresh(now) && recordLifetimeFits(now) && state.canRecord()
                && !state.stopping() && !state.audioBlocked() && !active(record)
                && (record == null || !record.releaseInFlight)
                && (stop == null || stop.observation != null && stop.observation.status().equals("known")
                && stateAt >= stop.gesture.createdAt() && state.lastStop() != null
                && state.lastStop().requestId().equals(stop.gesture.requestId())
                && state.lastStop().status().equals("known"));
    }
    private void requestRecord(long now, boolean held) {
        Work work = new Work(Protocol.gesture("record", state, now, edges.epoch(), ids.get()), state.sessionExpiresAt(), held);
        record = work; records++;
        hud = new Hud(work.gesture.requestId(), "record", held ? "hold_requested" : "requested", null, null);
        if (!ordinaryLane.offer(() -> mutate(work))) cancelUnsent(work);
    }
    private void requestRelease(long now) {
        Work work = record;
        if (work == null || !work.held || !work.active || work.release != null
                || work.releaseSuppressed || work.stopRequested) return;
        if (!work.dispatched) { cancelUnsent(work); return; }
        try { work.release = Protocol.release(work.gesture, now); }
        catch (IllegalArgumentException | ArithmeticException exception) { failRelease(work, now); return; }
        local(work, "release_requested");
        work.releaseInFlight = true;
        if (!finishLane.offer(() -> finish(work))) {
            work.releaseInFlight = false; failRelease(work, now);
        }
    }
    private void failRelease(Work work, long now) {
        work.releaseSuppressed = true; unknown(work);
        if (!work.stopRequested) requestStop(now);
    }
    private void finish(Work work) {
        synchronized (this) {
            long now = clock.getAsLong();
            if (work.releaseSuppressed || work.stopRequested || closed) { work.releaseInFlight = false; return; }
            if (work.release == null || work.releaseDispatched || now < work.release.releasedAt()
                    || now >= work.release.releaseBefore() || work.gesture.epoch() != edges.epoch()
                    || input == null || !input.matched() || !input.focused() || !input.menuFree() || input.paused()
                    || state == null || !state.sessionId().equals(work.gesture.sessionId())
                    || !state.contextId().equals(work.gesture.contextId()) || state.generation() != work.gesture.generation()) {
                work.releaseInFlight = false; failRelease(work, now); return;
            }
            work.releaseDispatched = true;
        }
        try {
            ControlTransport.Response response = transport.request("POST", "/v1/release", work.release.bytes());
            synchronized (this) {
                if (response.status() == 200 || response.status() == 202) {
                    Protocol.Operation observation = Protocol.operation(response.body());
                    if (matches(work, observation) && !observation.status().equals("refused")
                            && !observation.status().equals("unknown")) {
                        work.releaseAcknowledged = true; accept(work, observation);
                    }
                    else failRelease(work, clock.getAsLong());
                } else failRelease(work, clock.getAsLong());
            }
        } catch (IOException | RuntimeException exception) {
            synchronized (this) { failRelease(work, clock.getAsLong()); }
        } finally { synchronized (this) { work.releaseInFlight = false; } }
    }
    private void requestStop(long now) {
        if (record != null) record.releaseSuppressed = true;
        // Session expiry fences recording and context polling, never the reserved retirement stop.
        if (state == null || sessionLost || stopSealed || stops >= 64 || active(stop)) return;
        if (record != null && !record.dispatched && record.active) cancelUnsent(record);
        Work work = new Work(Protocol.gesture("stop", state, now, edges.epoch(), ids.get()), state.sessionExpiresAt(), false);
        stop = work; stops++;
        if (record != null) record.stopRequested = true;
        hud = new Hud(work.gesture.requestId(), "stop", "requested", null, null);
        if (!stopLane.offer(() -> mutate(work))) { work.active = false; work.uncertain = true; local(work, "unknown"); }
    }
    private static boolean active(Work work) { return work != null && work.active; }
    private static boolean needsStop(Work work) { return work != null && work.dispatched && (work.active || work.uncertain); }
    private void cancelUnsent(Work work) { work.active = false; local(work, "not_sent"); }

    private void mutate(Work work) {
        synchronized (this) {
            long now = clock.getAsLong();
            if (!work.active) return;
            if (now < work.gesture.createdAt() || now >= work.gesture.admitBefore()) {
                work.active = false; local(work, "not_sent"); return;
            }
            if (work.gesture.operation().equals("record") && (closed || work.gesture.epoch() != edges.epoch()
                    || !recordEligibleForDispatch(work, now))) { cancelUnsent(work); return; }
            work.dispatched = true;
        }
        try {
            ControlTransport.Response response = transport.request("POST", work.held ? "/v1/hold" : "/v1/" + work.gesture.operation(), work.gesture.bytes());
            synchronized (this) {
                // The independent finish response supersedes every older start response or failure.
                if (work.held && work.releaseAcknowledged) return;
                if (response.status() == 200 || response.status() == 202) accept(work, Protocol.operation(response.body()));
                else if (isRefusal(response)) { work.active = false; local(work, "refused"); }
                else unknown(work);
            }
        } catch (IOException | RuntimeException exception) {
            synchronized (this) { if (!work.held || !work.releaseAcknowledged) unknown(work); }
        }
    }
    private boolean recordEligibleForDispatch(Work work, long now) {
        return !retired && fresh(now) && recordLifetimeFits(now)
                && work.gesture.expiresAt() <= state.sessionExpiresAt() && now < work.gesture.expiresAt()
                && input != null && input.matched() && input.focused()
                && input.menuFree() && !input.paused() && state.canRecord() && !state.stopping() && !state.audioBlocked()
                && state.sessionId().equals(work.gesture.sessionId()) && state.contextId().equals(work.gesture.contextId())
                && state.generation() == work.gesture.generation() && !active(stop);
    }

    private static boolean isRefusal(ControlTransport.Response response) {
        return switch (response.status()) {
            case 400, 401, 408, 409, 429 -> Protocol.fixedStatus(response.body(), "refused");
            default -> false;
        };
    }
    private void unknown(Work work) { work.uncertain = true; local(work, "unknown"); }
    private void local(Work work, String stage) {
        if (!closed && work.gesture.epoch() == edges.epoch() && hud != null
                && hud.requestId().equals(work.gesture.requestId())) {
            hud = new Hud(work.gesture.requestId(), work.gesture.operation(), stage, null, work.observation);
        }
    }
    private static boolean matches(Work work, Protocol.Operation observation) {
        return observation.requestId().equals(work.gesture.requestId())
                && observation.operation().equals(work.gesture.operation());
    }
    private void accept(Work work, Protocol.Operation observation) {
        if (!matches(work, observation)) { unknown(work); return; }
        if (work.observation != null && work.observation.terminal() && !observation.terminal()) return;
        work.observation = observation; work.uncertain = false;
        work.active = !(observation.operation().equals("stop") ? observation.terminal() : observation.settled());
        if (observation.status().equals("unknown")) {
            retired = true; work.active = false;
            if (work.gesture.operation().equals("stop")) stopSealed = true;
        }
        if (!closed && work.gesture.epoch() == edges.epoch() && hud != null
                && hud.requestId().equals(work.gesture.requestId())) {
            project(work, observation.status(), observation.phase(), observation);
        }
    }
    private void project(Work work, String stage, String phase, Protocol.Operation observation) {
        if (work.held && stage.equals("pending")) {
            stage = work.release != null ? "release_requested" : "hold_requested";
            if (work.release != null && ("recording".equals(phase) || "recording_pending".equals(phase)
                    || "waiting_audio".equals(phase))) phase = null;
        }
        hud = new Hud(work.gesture.requestId(), work.gesture.operation(), stage, phase, observation);
    }
    private void retireTimedOut(Work work, long now) {
        if (active(work) && now >= work.pollUntil) {
            work.active = false; work.uncertain = true; retired = true; local(work, "unknown");
            if (work.gesture.operation().equals("stop")) stopSealed = true;
        }
    }

    private void poll(long now) {
        boolean sessionExpired = state != null && now >= state.sessionExpiresAt();
        if (polling || now < nextPollAt || (retired || sessionExpired) && !active(stop)) return;
        if (!(input.matched() && input.focused()) && !active(record) && !active(stop)) return;
        Work lookup = active(stop) && stop.dispatched ? stop : active(record) && record.dispatched ? record : null;
        if ((sessionExpired || retired) && lookup == null) return;
        // Alternate state and own-operation reads. One poll in flight across the query lanes, at most 2 Hz.
        boolean operationRead = lookup != null && (sessionExpired || retired || state == null || now - stateAt < 1000);
        Work selected = operationRead ? lookup : null;
        String path = selected == null ? "/v1/state" : "/v1/operations/" + selected.gesture.requestId();
        long queryEpoch = edges.epoch();
        Lane lane = selected != null && selected.gesture.operation().equals("stop") ? stopLane : ordinaryLane;
        polling = true; nextPollAt = now + 500;
        if (!lane.offer(() -> query(path, selected, queryEpoch))) polling = false;
    }
    private void query(String path, Work selected, long queryEpoch) {
        try {
            ControlTransport.Response response = transport.request("GET", path, EMPTY);
            synchronized (this) {
                if (closed) return;
                if (response.status() == 200) {
                    if (selected != null) accept(selected, Protocol.operation(response.body()));
                    else updateState(Protocol.state(response.body()), queryEpoch);
                } else if (selected != null) {
                    if (response.status() == 404 && Protocol.fixedStatus(response.body(), "not_found")) {
                        selected.active = false; unknown(selected); retired = true;
                        if (selected.gesture.operation().equals("stop")) stopSealed = true;
                    } else unknown(selected);
                } else stateAt = -1;
            }
        } catch (IOException | RuntimeException exception) {
            synchronized (this) { if (selected != null) unknown(selected); else stateAt = -1; }
        } finally {
            synchronized (this) {
                polling = false;
                nextPollAt = Math.max(nextPollAt, clock.getAsLong() + 500);
            }
        }
    }
    private void updateState(Protocol.State next, long queryEpoch) {
        if (state != null && !state.sessionId().equals(next.sessionId())) {
            retired = true; sessionLost = true; contextVersion++; stateAt = -1;
            if (record != null) unknown(record); if (stop != null) unknown(stop);
            return;
        }
        if (state == null || !Objects.equals(state.contextId(), next.contextId()) || state.generation() != next.generation()) contextVersion++;
        state = next; stateAt = clock.getAsLong();
        if (record != null && next.lastRecord() != null && next.lastRecord().requestId().equals(record.gesture.requestId())) accept(record, next.lastRecord());
        if (stop != null && next.lastStop() != null && next.lastStop().requestId().equals(stop.gesture.requestId())) accept(stop, next.lastStop());
        if (queryEpoch == edges.epoch() && record != null && record.gesture.epoch() == edges.epoch()
                && next.voiceRequestId() != null && next.voiceRequestId().equals(record.gesture.requestId())
                && hud != null && hud.requestId().equals(record.gesture.requestId()) && record.observation == null) {
            project(record, "pending", next.voicePhase(), null);
        }
    }

    synchronized Hud hud() { return hud; }
    /** Close ingress first. The owner then drains the reserved stop lane and closes all IO. */
    synchronized void beginClose() {
        if (closed) return;
        if (needsStop(record) && !record.stopRequested) requestStop(clock.getAsLong());
        closed = true;
        if (record != null && !record.dispatched) record.active = false;
    }
}
