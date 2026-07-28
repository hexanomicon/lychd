import type { BridgeSnapshot, RunProjectionSnapshot } from "$lib/api/models";

export type LiveTurn = {
  sessionId: string;
  runId: string;
  content: string;
  status: string;
  state: "streaming" | "done" | "failed";
  fragments: Array<Record<string, unknown>>;
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
    status: snapshot.status,
    state: snapshot.terminal
      ? snapshot.status.includes("fail")
        ? "failed"
        : "done"
      : "streaming",
    fragments: snapshot.fragments.map((fragment) => ({ ...fragment }))
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
