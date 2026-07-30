import type { BridgeSnapshot, RunProjectionSnapshot } from "$lib/api/models";

export type LiveTurn = {
  sessionId: string;
  runId: string;
  content: string;
  runStatus: string;
  activity: string;
  state: "streaming" | "stale" | "done" | "failed";
  fragments: Array<Record<string, unknown>>;
  patternId: string;
  patternRevision: string;
  loomPath: string | null;
  orbPath: string;
  evidenceCapture: "process_local" | "durable_best_effort";
  occurrenceId: string | null;
  dispatchOccurrenceId: string | null;
  grantId: string | null;
  capabilityKey: string | null;
  transitionOccurrenceId: string | null;
  transitionRequestId: string | null;
  transitionPhase: string | null;
  delegatedJobId: string | null;
  delegatedRuntime: string | null;
  delegatedProfile: string | null;
  delegatedStatus: string | null;
};

export type LiveTurnMerge = {
  liveTurns: LiveTurn[];
  retiredRunIds: string[];
};

export function liveTurnFromSnapshot(snapshot: RunProjectionSnapshot): LiveTurn {
  return {
    sessionId: snapshot.session_id,
    runId: snapshot.run_id,
    content: snapshot.content,
    runStatus: snapshot.run_status,
    activity: snapshot.activity,
    state: snapshot.terminal
      ? snapshot.run_status.includes("fail")
        ? "failed"
        : "done"
      : "streaming",
    fragments: snapshot.fragments.map((fragment) => ({ ...fragment })),
    patternId: snapshot.pattern_id,
    patternRevision: snapshot.pattern_revision,
    loomPath: snapshot.loom_path,
    orbPath: snapshot.orb_path,
    evidenceCapture: snapshot.evidence_capture,
    occurrenceId: snapshot.occurrence_id ?? null,
    dispatchOccurrenceId: snapshot.dispatch_occurrence_id ?? null,
    grantId: snapshot.grant_id ?? null,
    capabilityKey: snapshot.capability_key ?? null,
    transitionOccurrenceId: snapshot.transition_occurrence_id ?? null,
    transitionRequestId: snapshot.transition_request_id ?? null,
    transitionPhase: snapshot.transition_phase ?? null,
    delegatedJobId: snapshot.delegated_job_id ?? null,
    delegatedRuntime: snapshot.delegated_runtime ?? null,
    delegatedProfile: snapshot.delegated_profile ?? null,
    delegatedStatus: snapshot.delegated_status ?? null
  };
}

export function replaceLiveTurnFromSnapshot(
  current: LiveTurn,
  snapshot: RunProjectionSnapshot
): LiveTurn {
  if (current.runId !== snapshot.run_id) {
    throw new Error("A run snapshot cannot replace a different live turn.");
  }
  return liveTurnFromSnapshot(snapshot);
}

/**
 * Merge one authoritative session snapshot into transient run projections.
 *
 * A snapshot retires only live turns whose run identity is now represented by
 * a settled agent turn in that same session. Other live runs — including runs
 * in another session — remain attached to their streams. A process-local active
 * projection reconstructs a missing live turn after a route remount or reload;
 * it does not overwrite a turn whose already-attached stream may be newer than
 * the snapshot request.
 */
export function mergeSnapshotLiveTurns(
  snapshot: BridgeSnapshot,
  current: readonly LiveTurn[]
): LiveTurnMerge {
  const session = snapshot.session;
  if (!session) return { liveTurns: [...current], retiredRunIds: [] };

  const settledRunIds = new Set(
    (session.turns ?? [])
      .filter((turn) => turn.role === "agent" && turn.run_id)
      .map((turn) => turn.run_id as string)
  );
  const retiredRunIds: string[] = [];
  const liveTurns = current.filter((turn) => {
    const retired = turn.sessionId === session.id && settledRunIds.has(turn.runId);
    if (retired) retiredRunIds.push(turn.runId);
    return !retired;
  });
  for (const active of snapshot.active_runs) {
    if (!liveTurns.some((turn) => turn.runId === active.run_id)) {
      liveTurns.push(liveTurnFromSnapshot(active));
    }
  }
  return { liveTurns, retiredRunIds };
}
