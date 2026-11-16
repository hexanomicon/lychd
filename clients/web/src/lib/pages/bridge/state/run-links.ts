import { loomOriginHref, orbReturnHref, selectedOrbHref } from "$lib/navigation/instruments";
import type { LiveTurn } from "./projection";

/** Carries a delegated job selection into Orb and Loom review links. */
export function runSelection(turn?: LiveTurn): string {
  return turn?.delegatedJobId ? new URLSearchParams({ job: turn.delegatedJobId }).toString() : "";
}

/** Orb evidence link, offered only when the served Orb path names this exact Run. */
export function runEvidenceHref(runId: string, turn?: LiveTurn) {
  return !turn || selectedOrbHref(turn.orbPath, "") === orbReturnHref(runId)
    ? orbReturnHref(runId, runSelection(turn))
    : null;
}

/** Loom score link, offered only when the served Loom path matches the declared Pattern revision. */
export function runScoreHref(runId: string, turn?: LiveTurn) {
  if (!turn?.loomPath || !turn.patternId || !turn.patternRevision) return null;
  const selection = runSelection(turn);
  const supplied = loomOriginHref(turn.loomPath, runId, selection);
  const exact = loomOriginHref(`/loom/${encodeURIComponent(turn.patternId)}/${encodeURIComponent(turn.patternRevision)}`, runId, selection);
  return supplied === exact ? supplied : null;
}
