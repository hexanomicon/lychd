import { createContext } from "svelte";
import { getBridgeSnapshot, getOrbRun } from "$lib/api/client";
import type { BridgeTurnView, LoomView, OrbRunSnapshot } from "$lib/api/models";
import { canonical, characterLimit, contractError, digest, immutable, judgmentError, limitations, matchingTurns, reviewLimit, scoreKey, validateRun, type Criterion, type Judgment, type ReviewContract, type ReviewRecord, type ReviewSource } from "./review";

export interface ReviewDraft {
  id: string; revision: number; parentId: string | null; score: LoomView;
  goal: string; reviewer: string; criteria: readonly Criterion[]; contract: ReviewContract | null;
  runId: string; run: OrbRunSnapshot | null; turns: readonly BridgeTurnView[]; selectedTurn: number | null;
  source: ReviewSource | null; judgments: readonly Judgment[]; record: ReviewRecord | null;
  loading: boolean; error: string;
}
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const now = () => new Date().toISOString();
const initialJudgments = (criteria: readonly Criterion[]): Judgment[] => criteria.map(item => ({ criterionId: item.id, verdict: "UNKNOWN", rationale: "", quotation: "", limitation: "" }));
// Payload admission reserves bounded room for errors and control-state settlement.
const payloadCharacterLimit = characterLimit - reviewLimit * 4_096;

/** A bounded shell-lifetime document. No persistence, model calls or mutation transport. */
export function createEvaluationWorkspace() {
  let entries = $state.raw<readonly ReviewDraft[]>([]);
  let activeId = $state<string | null>(null);
  let notice = $state("");
  let sequence = 0;
  let authorityEpoch = 0;
  // Request tokens are not presentation state; reads must not subscribe to cancellation.
  const versions = new Map<string, number>();
  const find = (id: string) => entries.find(item => item.id === id);
  const token = (id: string) => { const next = (versions.get(id) ?? 0) + 1; versions.set(id, next); return next; };
  function put(entry: ReviewDraft): boolean {
    const next = entries.some(item => item.id === entry.id) ? entries.map(item => item.id === entry.id ? entry : item) : [...entries, entry];
    const payloadCharacters = canonical(next.map(({ loading: _loading, error: _error, ...payload }) => payload)).length;
    if (next.length > reviewLimit || payloadCharacters > payloadCharacterLimit) {
      notice = `This tab is limited to ${reviewLimit} reviews and ${characterLimit.toLocaleString("en")} characters across all drafts, captures and records. Nothing was changed or truncated. Export or discard a review first.`;
      return false;
    }
    entries = immutable(next);
    return true;
  }
  function failure(id: string, error: string) {
    const entry = find(id);
    if (entry) put({ ...entry, loading: false, error: error.length > 2_048 ? "The operation failed with an oversized error message. Its details were not retained. The source was not changed or truncated; retry the explicit action." : error });
  }
  function clearProtected() {
    authorityEpoch++;
    for (const entry of entries) { if (entry.record) versions.delete(entry.id); else token(entry.id); }
    entries = immutable(entries.filter(entry => !entry.record).map(entry => ({ ...entry, source: null, run: null, turns: [], selectedTurn: null, judgments: initialJudgments(entry.contract?.criteria ?? []), loading: false, error: "Authorization refused. Protected captures and completed records were cleared. Explicitly load the source again after access is restored." })));
    if (!entries.some(entry => entry.id === activeId)) activeId = null;
    notice = "Authorization refused. Protected captures and completed records were cleared.";
  }
  function catchFailure(id: string, cause: unknown) {
    if (typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403)) clearProtected();
    else failure(id, cause instanceof Error ? cause.message : "The exact retained output could not be read.");
  }
  return {
    get entries() { return entries; },
    get activeId() { return activeId; },
    get active() { return entries.find(entry => entry.id === activeId) ?? null; },
    get notice() { return notice; },
    get needsUnloadWarning() { return entries.length > 0; },
    select(id: string) { if (find(id)) activeId = id; },
    start(score: LoomView) {
      const id = `review-${++sequence}`;
      if (put({ id, revision: 1, parentId: null, score: clone(score), goal: "", reviewer: "", criteria: [{ id: "criterion-1", statement: "", evidence: "", missing: "Missing evidence remains UNKNOWN." }], contract: null, runId: "", run: null, turns: [], selectedTurn: null, source: null, judgments: [], record: null, loading: false, error: "" })) { activeId = id; notice = ""; }
    },
    discard(id: string) { versions.delete(id); entries = entries.filter(entry => entry.id !== id); if (activeId === id) activeId = null; notice = "Review discarded from this tab."; },
    cancelRead(id: string) { token(id); const entry = find(id); if (entry?.loading) put({ ...entry, loading: false, error: "Read interrupted. Explicitly load the exact source again." }); },
    editContract(id: string, change: Partial<Pick<ReviewDraft, "goal" | "reviewer" | "criteria">>) {
      const entry = find(id);
      if (!entry || entry.contract || entry.record || entry.loading) return;
      const next = { ...entry, ...clone(change), error: "" };
      if (next.goal.length > 4_000 || next.reviewer.length > 256 || next.criteria.length > 8 || next.criteria.some(item => [item.statement, item.evidence, item.missing].some(text => text.length > 2_000))) { notice = "Input exceeds its field limit (goal 4,000; reviewer 256; up to 8 criteria, 2,000 per field). Nothing was changed or truncated."; return; }
      put(next);
    },
    async freezeContract(id: string) {
      const entry = find(id); if (!entry || entry.contract || entry.record || entry.loading) return;
      const error = contractError(entry.goal, entry.reviewer, entry.criteria); if (error) { failure(id, error); return; }
      const version = token(id), epoch = authorityEpoch;
      if (!put({ ...entry, loading: true, error: "" })) return;
      try {
        const body = { goal: entry.goal, reviewer: entry.reviewer, criteria: entry.criteria, frozenAt: now() };
        const hash = await digest(canonical(body));
        if (epoch !== authorityEpoch || versions.get(id) !== version) return;
        const current = find(id);
        if (current && !put({ ...current, loading: false, contract: { ...body, digest: hash }, judgments: initialJudgments(entry.criteria) })) {
          failure(id, "Frozen criteria exceed this tab's character limit. The original draft is retained; export or discard another review before retrying.");
        }
      } catch (cause) { if (epoch === authorityEpoch && versions.get(id) === version) catchFailure(id, cause); }
    },
    editRun(id: string, runId: string) {
      const entry = find(id); if (!entry?.contract || entry.source || entry.record) return;
      if (runId.length > 128) { notice = "Run identity is limited to 128 characters. Nothing was changed or truncated."; return; }
      token(id); put({ ...entry, runId, run: null, turns: [], selectedTurn: null, loading: false, error: "" });
    },
    async loadSource(id: string, displayedScore: LoomView) {
      const entry = find(id); if (!entry?.contract || entry.record || entry.source || entry.loading) return;
      if (scoreKey(entry.score) !== scoreKey(displayedScore)) { failure(id, "This review belongs to another exact score. Return to that score to load source, or start a new review here."); return; }
      if (!/^[A-Za-z0-9_-]{1,128}$/.test(entry.runId)) { failure(id, "Supply one exact, valid Run identity."); return; }
      const version = token(id), epoch = authorityEpoch;
      const current = () => epoch === authorityEpoch && versions.get(id) === version && !!find(id);
      if (!put({ ...entry, loading: true, error: "", run: null, turns: [], selectedTurn: null })) return;
      try {
        const run = await getOrbRun(entry.runId, { limit: 1 });
        if (!current()) return;
        validateRun(entry.runId, run, entry.score);
        const session = await getBridgeSnapshot(run.run.session_id);
        if (!current()) return;
        const turns = matchingTurns(session, run);
        // Retain only matching supplied turns, never the rest of a private Session.
        const latest = find(id)!;
        if (!put({ ...latest, loading: false, run: clone({ ...run, evidence: [], delegated_jobs: [] }), turns: clone(turns), selectedTurn: null })) failure(id, "Source exceeds this tab's character limit. Nothing was captured or truncated.");
      } catch (cause) { if (current()) catchFailure(id, cause); }
    },
    selectTurn(id: string, index: number) {
      const entry = find(id); if (entry && !entry.loading && !entry.source && entry.turns[index]) put({ ...entry, selectedTurn: index, error: "" });
    },
    async freezeSource(id: string) {
      const entry = find(id); if (!entry?.contract || !entry.run || entry.record || entry.source || entry.loading) return;
      const turn = entry.selectedTurn === null ? null : entry.turns[entry.selectedTurn];
      if (!turn) { failure(id, "Explicitly select a supplied matching agent turn before freezing output."); return; }
      const version = token(id), epoch = authorityEpoch;
      if (!put({ ...entry, loading: true, error: "" })) return;
      try {
        const hash = await digest(turn.content);
        if (epoch !== authorityEpoch || versions.get(id) !== version || !find(id)) return;
        const source: ReviewSource = { content: turn.content, digest: hash, role: "agent", createdAt: turn.created_at, runId: entry.run.run.run_id, sessionId: entry.run.run.session_id, turnState: turn.state, capturedAt: now(), run: entry.run.run, pattern: entry.run.pattern, score: entry.score, capture: entry.run.capture, snapshotAt: entry.run.snapshot_at, limitations: [...limitations, `Run evidence capture: ${entry.run.capture}.`, ...entry.run.known_omissions, ...(entry.run.has_more ? ["Additional Run evidence exists outside the requested snapshot."] : []), ...(entry.run.gaps.length ? ["The supplied Run snapshot contains evidence gaps."] : []), ...(entry.turns.length > 1 ? ["Multiple supplied agent turns matched this Run; the reviewer explicitly selected this output."] : [])] };
        if (!put({ ...entry, loading: false, source, run: null, turns: [], selectedTurn: null })) failure(id, "Frozen source exceeds this tab's character limit. Nothing was frozen or truncated.");
      } catch (cause) { if (epoch === authorityEpoch && versions.get(id) === version) catchFailure(id, cause); }
    },
    editJudgment(id: string, criterionId: string, change: Partial<Omit<Judgment, "criterionId">>) {
      const entry = find(id); if (!entry?.source || entry.record) return;
      if (Object.values(change).some(value => typeof value === "string" && value.length > 8_000)) { notice = "Judgment fields are limited to 8,000 characters. Nothing was changed or truncated."; return; }
      put({ ...entry, error: "", judgments: entry.judgments.map(item => item.criterionId === criterionId ? { ...item, ...change } : item) });
    },
    finish(id: string) {
      const entry = find(id); if (!entry?.contract || !entry.source || entry.record) return;
      if (entry.judgments.length !== entry.contract.criteria.length || entry.contract.criteria.some(criterion => entry.judgments.filter(item => item.criterionId === criterion.id).length !== 1)) { failure(id, "Every frozen criterion requires exactly one judgment."); return; }
      const error = judgmentError(entry.judgments, entry.source); if (error) { failure(id, error); return; }
      const record: ReviewRecord = { schema: "LoomManualOutputReview@1", id: entry.id, revision: entry.revision, parentId: entry.parentId, kind: "retrospective_retained_output", savedToVessel: false, newExecution: false, contract: entry.contract, source: entry.source, judgments: entry.judgments, completedAt: now() };
      // Completed bytes are kept once, rather than duplicating the exact output in the draft.
      put({ ...entry, goal: "", reviewer: "", criteria: [], contract: null, source: null, judgments: [], record, error: "" });
    },
    revise(id: string) {
      const entry = find(id), record = entry?.record; if (!entry || !record) return;
      const nextId = `review-${++sequence}`;
      if (put({ ...entry, id: nextId, revision: record.revision + 1, parentId: record.id, goal: record.contract.goal, reviewer: record.contract.reviewer, criteria: record.contract.criteria, contract: record.contract, source: record.source, judgments: record.judgments.map(item => ({ ...item })), record: null, error: "" })) { activeId = nextId; notice = "New retrospective review revision. The completed record remains immutable; the same frozen criteria and output are reused."; }
    },
    clearProtected
  };
}
export type EvaluationWorkspace = ReturnType<typeof createEvaluationWorkspace>;
export const [getEvaluationWorkspace, setEvaluationWorkspace, hasEvaluationWorkspace] = createContext<EvaluationWorkspace>();
