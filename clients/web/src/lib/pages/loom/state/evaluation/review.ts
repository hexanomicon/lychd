import type { BridgeSnapshot, BridgeTurnView, LoomView, OrbRunSnapshot } from "$lib/api/models";
import { sameInspectionBinding } from "$lib/api/inspection";
import { matchesOrbPattern } from "$lib/graph/model";

export const verdicts = ["PASS", "PARTIAL", "FAIL", "CONTRADICTED", "UNKNOWN", "DISPUTED"] as const;
export type Verdict = typeof verdicts[number];
export const reviewLimit = 4;
export const characterLimit = 256_000;
export const criterionLimit = 8;
export interface Criterion { id: string; statement: string; evidence: string; missing: string }
export interface ReviewContract { goal: string; reviewer: string; criteria: readonly Criterion[]; frozenAt: string; digest: string }
export interface Judgment { criterionId: string; verdict: Verdict; rationale: string; quotation: string; limitation: string }
export interface ReviewSource {
  content: string; digest: string; role: "agent"; createdAt: string; runId: string; sessionId: string;
  turnState: string; capturedAt: string; run: OrbRunSnapshot["run"]; pattern: OrbRunSnapshot["pattern"];
  score: LoomView; capture: OrbRunSnapshot["capture"]; snapshotAt: string; limitations: readonly string[];
}
export interface ReviewRecord {
  schema: "LoomManualOutputReview@1"; id: string; revision: number; parentId: string | null;
  kind: "retrospective_retained_output"; savedToVessel: false; newExecution: false;
  contract: ReviewContract; source: ReviewSource; judgments: readonly Judgment[]; completedAt: string;
}
export const limitations = [
  "Retrospective review: the historical execution predates these criteria; they were not predeclared trial criteria.",
  "Retained output only. No new execution; no complete trajectory, tool receipts, cost or latency measurement is established.",
  "Reviewer identity is self-declared and is not authenticated attribution or independent evaluation.",
  "No durable turn ID is supplied. The source is bound by supplied Session, Run, role, timestamp and exact content bytes.",
  "Document-local record, not saved to Vessel or localStorage; not a durable Drift Outcome or a promotion decision.",
  "This review cannot establish workflow improvement or reproduction by another score revision."
] as const;

export function canonical(value: unknown): string {
  if (value === undefined) return "null";
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.entries(value).filter(([, item]) => item !== undefined).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
}

export async function digest(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return `sha256:${Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("")}`;
}

export function scoreKey(score: LoomView): string { return canonical(score); }

/** Orb supplies workflow only when the entire valid pinned manifest equals its registry owner. */
export function validateRun(runId: string, run: OrbRunSnapshot, score: LoomView): void {
  if (run.run.run_id !== runId || !run.run.session_id || !run.workflow || !run.pattern.loom_path ||
      !matchesOrbPattern(run, score) || !matchesOrbPattern(run, run.workflow) ||
      !sameInspectionBinding(run.workflow.binding, score.binding) || scoreKey(run.workflow) !== scoreKey(score)) {
    throw new Error("Source unavailable: the full pinned Run manifest and inspection binding must match this exact score. No substitute Run was loaded.");
  }
}

export function matchingTurns(snapshot: BridgeSnapshot, run: OrbRunSnapshot): readonly BridgeTurnView[] {
  if (snapshot.session?.id !== run.run.session_id) throw new Error("Source unavailable: the returned Session does not match the Run's exact Session.");
  const turns = (snapshot.session.turns ?? []).filter(turn => turn.role === "agent" && turn.run_id === run.run.run_id);
  if (!turns.length) throw new Error("No supplied agent turn matches this Run. Resolve the missing retained output and explicitly load the Run again; no latest-answer fallback is used.");
  return turns.map(turn => ({ role: turn.role, content: turn.content, created_at: turn.created_at, run_id: turn.run_id, state: turn.state }));
}

export function contractError(goal: string, reviewer: string, criteria: readonly Criterion[]): string | null {
  if (!goal.trim() || !reviewer.trim()) return "Declare the goal and self-declared reviewer before freezing criteria.";
  if (!criteria.length || criteria.length > criterionLimit) return "Declare between one and eight criteria.";
  if (goal.length > 4_000 || reviewer.length > 256) return "Goal limit is 4,000 characters; reviewer limit is 256. Nothing was truncated.";
  if (criteria.some(item => !item.statement.trim() || !item.evidence.trim() || !item.missing.trim())) return "Every criterion requires expected behavior, evidence requirements and a missing-evidence policy.";
  if (criteria.some(item => [item.statement, item.evidence, item.missing].some(text => text.length > 2_000))) return "Each criterion field is limited to 2,000 characters. Nothing was truncated.";
  return null;
}

export function judgmentError(judgments: readonly Judgment[], source: ReviewSource): string | null {
  for (const judgment of judgments) {
    if (!verdicts.includes(judgment.verdict) || !judgment.rationale.trim()) return "Every criterion requires a verdict and rationale.";
    if (!judgment.quotation.trim() && !judgment.limitation.trim()) return "Every criterion requires an exact supporting quotation or an explicit missing-evidence limitation.";
    if (judgment.quotation && !source.content.includes(judgment.quotation)) return "A supporting quotation must occur exactly in the frozen output, including whitespace.";
  }
  return null;
}

export function immutable<T>(value: T): T {
  if (value && typeof value === "object") { Object.freeze(value); for (const item of Object.values(value)) immutable(item); }
  return value;
}

export function exportJson(record: ReviewRecord): string { return JSON.stringify(record, null, 2); }
export function exportMarkdown(record: ReviewRecord): string {
  // A longer fence keeps arbitrary retained Markdown and HTML inside literal text.
  const quote = (text: string) => { const fence = "~".repeat(Math.max(3, ...Array.from(text.matchAll(/~+/g), match => match[0].length + 1))); return `${fence}text\n${text}\n${fence}`; };
  const contract = record.contract;
  return ["# Manual output review", "Retrospective · Retained output · No new execution · Not saved to Vessel",
    `Local record: ${record.id}, revision ${record.revision}; parent: ${record.parentId ?? "none"}`,
    `Criteria frozen: ${contract.frozenAt}; completed: ${record.completedAt}`, "## Self-declared reviewer", quote(contract.reviewer),
    "## Goal", quote(contract.goal), `Criteria digest: ${contract.digest}`, "## Exact source",
    `Run: ${record.source.runId}; Session: ${record.source.sessionId}; role: ${record.source.role}`,
    `Supplied timestamp: ${record.source.createdAt}; captured: ${record.source.capturedAt}`,
    `Run status (not a quality verdict): ${record.source.run.status}; turn state: ${record.source.turnState}`,
    `Output UTF-8 SHA-256: ${record.source.digest}`, "### Exact output", quote(record.source.content),
    "### Pinned score, manifest resolution and inspection binding", quote(canonical({ pattern: record.source.pattern, score: record.source.score, capture: record.source.capture, snapshotAt: record.source.snapshotAt })),
    "## Criteria and judgments", ...contract.criteria.flatMap(criterion => {
      const judgment = record.judgments.find(item => item.criterionId === criterion.id)!;
      return [`### ${criterion.id} · ${judgment.verdict}`, quote(criterion.statement), "Evidence required:", quote(criterion.evidence), "Missing-evidence policy:", quote(criterion.missing), "Rationale:", quote(judgment.rationale), "Supporting quotation:", quote(judgment.quotation || "None supplied"), "Missing-evidence limitation:", quote(judgment.limitation || "None declared")];
    }), "## Limitations", ...record.source.limitations.map(quote), ""].join("\n\n");
}
