import { describe, expect, it } from "vitest";

import type { BridgeSnapshot, RunProjectionSnapshot } from "$lib/api/models";
import {
  mergeSnapshotLiveTurns,
  replaceLiveTurnFromSnapshot,
  type LiveTurn
} from "./projection";

function snapshot(
  sessionId: string,
  settledRunIds: string[],
  activeRuns: RunProjectionSnapshot[] = []
): BridgeSnapshot {
  return {
    sessions: [],
    session: {
      id: sessionId,
      title: "Séance",
      created_at: "2026-07-28T00:00:00Z",
      turns: settledRunIds.map((runId) => ({
        role: "agent",
        content: `${runId} settled`,
        run_id: runId,
        state: "settled",
        fragments: [],
        created_at: "2026-07-28T00:00:00Z"
      }))
    },
    active_runs: activeRuns,
    pending_consents: [],
    pending_count: 0
  };
}

function live(sessionId: string, runId: string): LiveTurn {
  return {
    sessionId,
    runId,
    content: "",
    status: "running",
    state: "streaming",
    fragments: []
  };
}

describe("Bridge snapshot/live merge", () => {
  it("retires only the completed run during concurrent completion", () => {
    const result = mergeSnapshotLiveTurns(
      snapshot("session-a", ["run-a"]),
      [live("session-a", "run-a"), live("session-a", "run-b")]
    );

    expect(result.retiredRunIds).toEqual(["run-a"]);
    expect(result.liveTurns.map((turn) => turn.runId)).toEqual(["run-b"]);
  });

  it("preserves every active run during a consent-only refresh", () => {
    const current = [live("session-a", "run-a"), live("session-a", "run-b")];
    const result = mergeSnapshotLiveTurns(snapshot("session-a", []), current);

    expect(result.retiredRunIds).toEqual([]);
    expect(result.liveTurns).toEqual(current);
  });

  it("never retires a live stream owned by another session", () => {
    const result = mergeSnapshotLiveTurns(
      snapshot("session-a", ["run-shared"]),
      [live("session-b", "run-shared")]
    );

    expect(result.retiredRunIds).toEqual([]);
    expect(result.liveTurns).toHaveLength(1);
  });

  it("replaces an active run only with its cursor-bound projection", () => {
    const current = live("session-a", "run-a");
    current.content = "partial";
    const projection: RunProjectionSnapshot = {
      schema_version: 1,
      session_id: "session-a",
      run_id: "run-a",
      cursor: 17,
      content: "authoritative",
      status: "weaving",
      fragments: [{ kind: "genui.plan_checklist" }],
      terminal: false
    };

    expect(replaceLiveTurnFromSnapshot(current, projection)).toEqual({
      ...current,
      content: "authoritative",
      status: "weaving",
      state: "streaming",
      fragments: [{ kind: "genui.plan_checklist" }]
    });
    expect(current.content).toBe("partial");
  });

  it("keeps terminal projection visible until the session ledger contains it", () => {
    const current = live("session-a", "run-a");
    const projection: RunProjectionSnapshot = {
      schema_version: 1,
      session_id: "session-a",
      run_id: "run-a",
      cursor: 18,
      content: "settled answer",
      status: "done",
      fragments: [],
      terminal: true
    };

    const terminal = replaceLiveTurnFromSnapshot(current, projection);
    const merge = mergeSnapshotLiveTurns(snapshot("session-a", []), [terminal]);

    expect(terminal.state).toBe("done");
    expect(merge.liveTurns).toEqual([terminal]);
    expect(merge.retiredRunIds).toEqual([]);
  });

  it("reconstructs a process-local active run missing after a remount", () => {
    const projection: RunProjectionSnapshot = {
      schema_version: 1,
      session_id: "session-a",
      run_id: "run-a",
      cursor: 17,
      content: "authoritative partial",
      status: "weaving",
      fragments: [{ kind: "genui.plan_checklist" }],
      terminal: false
    };

    const merge = mergeSnapshotLiveTurns(snapshot("session-a", [], [projection]), []);

    expect(merge.liveTurns).toEqual([
      {
        sessionId: "session-a",
        runId: "run-a",
        content: "authoritative partial",
        status: "weaving",
        state: "streaming",
        fragments: [{ kind: "genui.plan_checklist" }]
      }
    ]);
  });

  it("does not regress a projection whose stream remained attached", () => {
    const current = live("session-a", "run-a");
    current.content = "newer stream content";
    const projection: RunProjectionSnapshot = {
      schema_version: 1,
      session_id: "session-a",
      run_id: "run-a",
      cursor: 3,
      content: "older snapshot content",
      status: "weaving",
      fragments: [],
      terminal: false
    };

    const merge = mergeSnapshotLiveTurns(
      snapshot("session-a", [], [projection]),
      [current]
    );

    expect(merge.liveTurns).toEqual([current]);
  });
});
