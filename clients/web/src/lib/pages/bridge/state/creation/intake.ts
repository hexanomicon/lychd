import { z } from "zod";
import { ApiError } from "$lib/api/client";
import type { components } from "$lib/api/openapi";

export type InvestigationRequest = components["schemas"]["InvestigationRequest"];
export type CaseView = components["schemas"]["CaseView"];
export interface SourceRow { key: string; name: string; text: string }
export interface CriterionRow { key: string; id: string; predicate: string }
export interface TextRow { key: string; text: string }
export interface InvestigationDraft {
  repository: string; baseRevision: string; digest: string; question: string;
  publicMaterial: boolean; sources: SourceRow[]; criteria: CriterionRow[];
  nonGoals: TextRow[]; omissions: TextRow[];
}
export function emptyDraft(): InvestigationDraft {
  return { repository: "", baseRevision: "", digest: "", question: "", publicMaterial: false,
    sources: [{ key: "source-0", name: "", text: "" }],
    criteria: [{ key: "criterion-0", id: "", predicate: "" }], nonGoals: [], omissions: [] };
}
export const utf8Bytes = (value: string): number => new TextEncoder().encode(value).length;
const unicode = z.string().refine((value) => [...value].every((c) => {
  const point = c.codePointAt(0)!;
  return point < 0xd800 || point > 0xdfff;
}), "Use valid Unicode text.");
const chars = (min: number, max: number) => unicode.refine(
  (value) => [...value].length >= min && [...value].length <= max,
  `Use ${min}–${max} characters.`
);
const boundedText = (max: number) => unicode.refine(
  (value) => value.trim().length > 0 && utf8Bytes(value) <= max,
  `Use nonblank text of at most ${max} UTF-8 bytes.`
);
const sourceSchema = z.object({
  name: unicode.refine((name) => name.length > 0 && utf8Bytes(name) <= 128 &&
    !/[:\\\0]/.test(name) && name.split("/").every((part) => part !== "" && part !== "." && part !== ".."),
  "Use a unique relative source name (128 UTF-8 bytes; no empty, dot or parent segments, backslash, colon or NUL)."),
  text: unicode
});
const criterionSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9_-]{0,31}$/, "Use a lowercase criterion ID, at most 32 characters."),
  predicate: boundedText(192)
});
const requestSchema = z.object({
  request_id: z.uuid(), public_material: z.literal(true, { error: "Confirm all supplied material is public." }),
  repository: chars(1, 256), base_revision: chars(1, 128),
  tree_or_patch_digest: z.string().regex(/^[0-9a-f]{40,64}$/, "Use a declared lowercase hexadecimal digest of 40–64 characters."),
  question: boundedText(512), sources: z.array(sourceSchema).min(1).max(8),
  criteria: z.array(criterionSchema).min(1).max(4),
  non_goals: z.array(boundedText(192)).max(4), omissions: z.array(boundedText(192)).max(4)
}).superRefine((request, context) => {
  if (new Set(request.sources.map((source) => source.name)).size !== request.sources.length)
    context.addIssue({ code: "custom", path: ["sources"], message: "Source names must be unique." });
  if (new Set(request.criteria.map((criterion) => criterion.id)).size !== request.criteria.length)
    context.addIssue({ code: "custom", path: ["criteria"], message: "Criterion IDs must be unique." });
  if (request.sources.reduce((sum, source) => sum + utf8Bytes(source.text), 0) > 4096)
    context.addIssue({ code: "custom", path: ["sources"], message: "All source text together must fit 4096 UTF-8 bytes." });
  if (utf8Bytes(JSON.stringify(request)) > 16384)
    context.addIssue({ code: "custom", message: "The whole request must fit 16384 UTF-8 bytes." });
});
export function prepareRequest(draft: InvestigationDraft, requestId: string):
  { request: InvestigationRequest; errors: [] } | { request: null; errors: string[] } {
  const result = requestSchema.safeParse({ request_id: requestId, public_material: draft.publicMaterial,
    repository: draft.repository, base_revision: draft.baseRevision, tree_or_patch_digest: draft.digest,
    question: draft.question, sources: draft.sources.map(({ name, text }) => ({ name, text })),
    criteria: draft.criteria.map(({ id, predicate }) => ({ id, predicate })),
    non_goals: draft.nonGoals.map(({ text }) => text), omissions: draft.omissions.map(({ text }) => text) });
  if (!result.success) return { request: null, errors: result.error.issues.map((issue) =>
    `${issue.path.join(".") || "Request"}: ${issue.message}`) };
  return { request: result.data, errors: [] };
}

// Runtime guards consume only the existing generic CaseView fields used by this text disclosure.
const citationSchema = z.object({ source: z.string(), first_line: z.number().int().positive(), last_line: z.number().int().positive() });
const findingSchema = z.object({ criterion: z.string(), claim: chars(1, 512),
  citations: z.array(citationSchema).max(4), unknown: chars(0, 192) });
const findingsSchema = z.array(findingSchema).min(1).max(4);
const caseSchema = z.object({
  case_id: z.uuid(), request: requestSchema, status: z.enum(["reserved", "candidate", "accepted", "rejected", "partial", "incomplete", "unknown", "cancelled"]),
  deadline: z.string().datetime({ offset: true }), slot_encumbered: z.boolean(), reason: z.string().nullable(),
  admissions: z.array(z.object({ case_id: z.uuid(), admission_id: z.uuid(), run_id: z.uuid().nullable() })),
  candidate: z.object({ summary: chars(1, 512), findings: findingsSchema }).nullable(),
  verdict: z.object({ disposition: z.enum(["accepted", "rejected", "partial", "incomplete"]),
    findings: findingsSchema, contradictions: z.array(z.string()).max(4) }).nullable()
});
export type InvestigationReport = z.infer<typeof caseSchema>;
export function retainedReport(value: CaseView, caseId: string): InvestigationReport {
  const result = caseSchema.parse(value);
  if (new Set(result.admissions.map((admission) => admission.admission_id)).size !== result.admissions.length)
    throw new Error("admission_identity");
  for (const output of [result.candidate, result.verdict]) {
    if (output === null) continue;
    const expected = new Set(result.request.criteria.map((criterion) => criterion.id));
    if (utf8Bytes(JSON.stringify(output)) > 1536 || output.findings.length !== expected.size ||
      new Set(output.findings.map((finding) => finding.criterion)).size !== expected.size ||
      output.findings.some((finding) => !expected.has(finding.criterion) || finding.citations.some((citation) =>
        citation.last_line < citation.first_line || !result.request.sources.some((source) => source.name === citation.source))))
      throw new Error("report_structure");
  }
  if (result.case_id !== caseId || result.request.request_id !== caseId ||
    result.admissions.some((admission) => admission.case_id !== caseId)) throw new Error("case_identity");
  return result;
}
export function investigationHref(caseId: string): string {
  return `/bridge?investigation=${encodeURIComponent(caseId)}`;
}
export function investigationSelection(value: string | null): "new" | string | null {
  return value === "new" || (value !== null && z.uuid().safeParse(value).success) ? value : null;
}
const safeCodes: Record<string, string> = {
  capability_not_warm: "The configured capability is not warm. This form cannot start it.",
  slot_busy: "The investigation slot is occupied.", conflicting_replay: "This UUID is already bound to different retained input.",
  local_authority: "Current local operator authority is required.", unknown_case: "This case is unavailable.",
  profile_changed: "The retained investigation profile differs from the configured profile."
};
function failure(error: unknown): string {
  if (error instanceof ApiError) {
    const code = error.code && Object.hasOwn(safeCodes, error.code) ? safeCodes[error.code] : undefined;
    return code ?? (error.status ? `The protected request failed (${error.status}).` : "The protected request failed.");
  }
  return "The response could not be confirmed or safely displayed.";
}
export interface IntakeState {
  caseId: string | null; phase: "idle" | "submitting" | "checking" | "retained" | "unconfirmed" | "unavailable";
  report: InvestigationReport | null; message: string; unconfirmedIds: readonly string[]; canReplay: boolean;
}
export function initialIntakeState(): IntakeState {
  return { caseId: null, phase: "idle", report: null, message: "", unconfirmedIds: [], canReplay: false };
}
interface InvestigationApi {
  submit: (request: InvestigationRequest) => Promise<CaseView>;
  read: (caseId: string, signal?: AbortSignal) => Promise<CaseView>;
}
export class InvestigationIntake {
  private state = initialIntakeState();
  private original: Readonly<{ caseId: string; body: string }> | null = null;
  private generation = 0;
  private readRequest: AbortController | null = null;
  private destroyed = false;
  constructor(private api: InvestigationApi, private changed: (state: IntakeState) => void) {}
  private publish(update: Partial<IntakeState>) {
    if (this.destroyed) return;
    this.state = { ...this.state, ...update };
    this.state = { ...this.state, canReplay: !!this.original && this.original.caseId === this.state.caseId &&
      this.state.unconfirmedIds.includes(this.original.caseId) && !this.busy };
    this.changed(this.state);
  }
  get busy(): boolean { return this.state.phase === "submitting" || this.state.phase === "checking"; }
  select(caseId: string | null) {
    if (this.state.caseId === caseId) return;
    ++this.generation;
    this.readRequest?.abort(); this.readRequest = null;
    this.publish({ caseId, phase: "idle", report: null, message: "" });
  }
  startDifferent() {
    ++this.generation;
    this.readRequest?.abort(); this.readRequest = null;
    this.original = null;
    this.publish({ caseId: null, phase: "idle", report: null, message: "" });
  }
  private resolved(caseId: string) {
    if (this.original?.caseId === caseId) this.original = null;
    this.publish({ unconfirmedIds: this.state.unconfirmedIds.filter((id) => id !== caseId) });
  }
  async submit(request: InvestigationRequest): Promise<void> {
    if (this.busy || this.destroyed || this.original) return;
    // Own literal JSON bytes; each Fetch receives a new plain value from this unchanged body.
    this.original = { caseId: request.request_id, body: JSON.stringify(request) };
    this.select(request.request_id);
    this.publish({ unconfirmedIds: [...new Set([...this.state.unconfirmedIds, request.request_id])] });
    await this.postOriginal();
  }
  async replay(): Promise<void> { if (this.state.canReplay) await this.postOriginal(); }
  private async postOriginal(): Promise<void> {
    const original = this.original;
    if (!original || this.busy || this.destroyed) return;
    const version = ++this.generation;
    const caseId = original.caseId;
    this.publish({ phase: "submitting", report: null, message: "" });
    try {
      const result = retainedReport(await this.api.submit(JSON.parse(original.body) as InvestigationRequest), caseId);
      if (this.destroyed || version !== this.generation || this.state.caseId !== caseId) return;
      this.resolved(caseId);
      this.publish({ phase: "retained", report: result, message: "Retained case read from the submission response." });
    } catch (error) {
      if (this.destroyed || version !== this.generation || this.state.caseId !== caseId) return;
      this.publish({ phase: "unconfirmed", report: null,
        message: `${failure(error)} Admission unconfirmed. Check this exact case under current authority; no retry was sent.` });
    }
  }
  async check(): Promise<void> {
    const caseId = this.state.caseId;
    if (!caseId || this.busy || this.destroyed) return;
    const version = ++this.generation;
    const request = new AbortController();
    this.readRequest?.abort(); this.readRequest = request;
    this.publish({ phase: "checking", report: null, message: "" });
    try {
      const result = retainedReport(await this.api.read(caseId, request.signal), caseId);
      if (this.destroyed || version !== this.generation || this.state.caseId !== caseId) return;
      this.resolved(caseId);
      this.publish({ phase: "retained", report: result, message: "Retained case read under current authority." });
    } catch (error) {
      if (this.destroyed || version !== this.generation || this.state.caseId !== caseId) return;
      this.publish({ phase: "unavailable", report: null,
        message: `${failure(error)} No protected report is displayed. A failed check, including 404, does not resolve an unconfirmed submission.` });
    } finally { if (this.readRequest === request) this.readRequest = null; }
  }
  dispose() { this.destroyed = true; ++this.generation; this.readRequest?.abort(); this.original = null; }
}
