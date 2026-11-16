import { z } from "zod";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile } from "$lib/api/models";
import type { ArchiveGeneration, ArchiveResolveIntent, SemanticRecallRequest, SemanticRecallResult, SemanticRecallReceipt, SemanticRecallProjection } from "$lib/api/models";

const digest = z.string().regex(/^[0-9a-f]{64}$/);
const label = z.string().min(1).refine((v) => [...v].length <= 160 && !/[\x00-\x1f\x7f\ud800-\udfff]/u.test(v));
const profileSchema = z.object({ profile: z.literal("local-public-notes@1"), namespace_id: z.uuid(), owner_subject: z.object({ identity: label }), policy_revision: label });
const generationSchema = z.object({ generation_id: z.uuid(), manifest_digest: digest });
const unicode = (value: string) => [...value].every((c) => { const n = c.codePointAt(0)!; return n < 0xd800 || n > 0xdfff; });
const integer = (value: number, max: number, min = 1) => Number.isInteger(value) && value >= min && value <= max;
const sameGeneration = (a: ArchiveGeneration, b: ArchiveGeneration) => a.generation_id === b.generation_id && a.manifest_digest === b.manifest_digest;
const exact = (value: unknown) => JSON.stringify(value);
async function textDigest(text: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}
export interface RecallDraft { query: string; minCosine: string; maxResults: string; charBudget: string }
export const emptyRecallDraft = (): RecallDraft => ({ query: "", minCosine: "", maxResults: "5", charBudget: "8000" });
export function validateRecallDraft(draft: RecallDraft): string[] {
  const errors: string[] = [];
  if (!draft.query.trim() || !unicode(draft.query) || draft.query.includes("\0") || [...draft.query].length > 2000)
    errors.push("Query: use nonblank valid Unicode, at most 2,000 code points, without NUL.");
  if (!draft.minCosine.trim() || !Number.isFinite(Number(draft.minCosine)) || Number(draft.minCosine) < -1 || Number(draft.minCosine) > 1)
    errors.push("Minimum similarity: explicitly supply a finite number from −1 to 1.");
  if (!draft.maxResults.trim() || !integer(Number(draft.maxResults), 20)) errors.push("Result limit: supply an integer from 1 to 20.");
  if (!draft.charBudget.trim() || !integer(Number(draft.charBudget), 32000)) errors.push("Source character budget: supply an integer from 1 to 32,000.");
  return errors;
}
export interface SemanticApi {
  profile(signal?: AbortSignal): Promise<ArchiveProfile>;
  generation(signal?: AbortSignal): Promise<ArchiveGeneration>;
  recall(body: SemanticRecallRequest): Promise<SemanticRecallResult>;
  inspect(body: SemanticRecallRequest, signal?: AbortSignal): Promise<SemanticRecallReceipt | null>;
  resolve(id: string, body: ArchiveResolveIntent, signal?: AbortSignal): Promise<SemanticRecallProjection>;
}
export interface RecallState {
  profile: ArchiveProfile | null; generation: ArchiveGeneration | null;
  configuration: "loading" | "configured" | "unavailable";
  operation: "idle" | "querying" | "checking" | "resolving";
  frozen: SemanticRecallRequest | null; receipt: SemanticRecallReceipt | null;
  projection: SemanticRecallProjection | null; resolvedAt: string | null;
  unknown: boolean; message: string; authorityEpoch: number;
  execution: SemanticRecallResult["current_query_execution"];
}
export const initialRecallState = (): RecallState => ({ profile: null, generation: null, configuration: "loading", operation: "idle",
  frozen: null, receipt: null, projection: null, resolvedAt: null, unknown: false, message: "", authorityEpoch: 0, execution: null });
export function safeRecallFailure(error: unknown): string {
  if (!(error instanceof ApiError)) return "The response could not be confirmed or safely displayed.";
  if (error.status === 401 || error.status === 403) return "Current Archive authority was refused. Protected material was cleared.";
  if (error.status === 404) return "This exact configured semantic service or source is unavailable (404).";
  const messages: Record<string, string> = {
    embedding_unavailable: "The exact embedding capability is unavailable; runtime preparation is separate.",
    generation_missing: "The configured generation is not registered.", generation_retired: "The exact generation is retired.",
    generation_binding: "The configured generation binding changed.", request_conflict: "This request identity conflicts with retained input.",
    receipt_stale: "The exact selection no longer resolves current sources.", source_integrity: "A selected source failed integrity checks; exact resolution was refused.",
    receipt_binding: "The exact receipt binding was refused.", receipt_integrity: "The selection receipt failed integrity checks.",
    receipt_missing: "The exact retained selection is unavailable.", embedding_input_size: "The query exceeds the exact embedding profile input limit.",
    storage: "The Archive storage request failed."
  };
  return error.code && Object.hasOwn(messages, error.code) ? messages[error.code]! : `The protected semantic request was refused${error.status ? ` (${error.status})` : ""}.`;
}

export class PublicSourceRecall {
  private state = initialRecallState();
  private alive = true;
  private epoch = 0;
  private operation = 0;
  private profileBinding: string | null = null;
  private generationBinding: string | null = null;
  private original: string | null = null;
  private metadataAbort: AbortController | null = null;
  private sourceAbort: AbortController | null = null;
  constructor(private api: SemanticApi, private changed: (state: RecallState) => void) {}
  private publish(update: Partial<RecallState>) {
    if (this.alive) { this.state = { ...this.state, ...update }; this.changed(this.state); }
  }
  private current(epoch: number, operation?: number) { return this.alive && this.epoch === epoch && (operation === undefined || this.operation === operation); }
  private refused(error: unknown) {
    if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) return false;
    ++this.epoch; ++this.operation; this.metadataAbort?.abort(); this.sourceAbort?.abort(); this.original = null; this.profileBinding = null; this.generationBinding = null;
    this.publish({ ...initialRecallState(), configuration: "unavailable", unknown: this.state.unknown,
      authorityEpoch: this.state.authorityEpoch + 1, message: safeRecallFailure(error) });
    return true;
  }
  async load() {
    if (!this.alive) return;
    const epoch = ++this.epoch; ++this.operation;
    this.metadataAbort?.abort(); this.sourceAbort?.abort();
    const request = new AbortController(); this.metadataAbort = request;
    this.publish({ profile: null, generation: null, configuration: "loading", operation: "idle", projection: null, resolvedAt: null, execution: null,
      message: this.state.unknown ? "The earlier query remains unknown. Metadata refresh performs no retry or source load." : "" });
    try {
      const profile = profileSchema.parse(await this.api.profile(request.signal));
      if (!this.current(epoch)) return;
      const profileBinding = exact(profile);
      if (this.profileBinding !== null && this.profileBinding !== profileBinding) this.clearBinding();
      this.profileBinding = profileBinding;
      const generation = generationSchema.parse(await this.api.generation(request.signal));
      if (!this.current(epoch)) return;
      const generationBinding = exact(generation);
      if (this.generationBinding !== null && this.generationBinding !== generationBinding) this.clearBinding();
      this.generationBinding = generationBinding;
      this.publish({ profile, generation, configuration: "configured" });
    } catch (error) {
      if (!this.current(epoch) || this.refused(error)) return;
      this.publish({ configuration: "unavailable", profile: null, generation: null, receipt: null, message: safeRecallFailure(error) });
    }
  }
  private clearBinding() {
    this.original = null;
    this.publish({ frozen: null, receipt: null, projection: null, resolvedAt: null, execution: null,
      authorityEpoch: this.state.authorityEpoch + 1,
      message: "Configured authority or generation changed. Query bodies and selected sources were cleared; earlier unknown work remains unknown." });
  }
  private async checkedReceipt(receipt: SemanticRecallReceipt, body: SemanticRecallRequest, profile: ArchiveProfile): Promise<SemanticRecallReceipt> {
    const copy: SemanticRecallReceipt = JSON.parse(exact(receipt));
    if (copy.schema_version !== 2 || copy.profile !== profile.profile || copy.retrieval_policy !== "postgres-exact-cosine@1" ||
      copy.namespace_id !== body.namespace_id || copy.request_id !== body.request_id || !sameGeneration(copy.generation, body.generation) ||
      copy.policy_revision !== profile.policy_revision || copy.subject.identity !== profile.owner_subject.identity || copy.purpose !== "archive:answer" ||
      copy.run_id !== null || copy.min_cosine !== body.min_cosine || copy.max_results !== body.max_results || copy.char_budget !== body.char_budget ||
      !z.uuid().safeParse(copy.receipt_id).success || !digest.safeParse(copy.receipt_digest).success || !digest.safeParse(copy.request_digest).success ||
      !z.string().datetime({ offset: true }).safeParse(copy.created_at).success || !integer(copy.generation_version, Number.MAX_SAFE_INTEGER) ||
      !integer(copy.coverage.promoted_notes, Number.MAX_SAFE_INTEGER, 0) || !integer(copy.coverage.eligible_notes, copy.coverage.promoted_notes, 0) ||
      !Array.isArray(copy.selected) || !integer(copy.omitted_for_budget, body.max_results, 0) ||
      copy.selected.length + copy.omitted_for_budget > Math.min(body.max_results, copy.coverage.eligible_notes)) throw new Error("foreign_receipt");
    let chars = 0;
    const identities = new Set<string>(), sources = new Set<string>(), derivations = new Set<string>();
    for (const [index, item] of copy.selected.entries()) {
      const previous = copy.selected[index - 1];
      if (!z.uuid().safeParse(item.reference.record_id).success || !z.uuid().safeParse(item.derivation_id).success ||
        !integer(item.reference.lifecycle_version, Number.MAX_SAFE_INTEGER) || !integer(item.row_version, Number.MAX_SAFE_INTEGER) ||
        !label.safeParse(item.source_key).success || !label.safeParse(item.source_revision).success ||
        ![item.reference.revision_digest, item.source_digest, item.projection_digest, item.vector_digest].every((v) => digest.safeParse(v).success) ||
        item.projection_digest !== item.source_digest || !integer(item.projected_chars, 16000) ||
        !Number.isFinite(item.score) || item.score < body.min_cosine || item.score > 1 || item.score < -1 ||
        identities.has(item.reference.record_id) || sources.has(item.source_key) || derivations.has(item.derivation_id) ||
        (previous && (previous.score < item.score || (previous.score === item.score && previous.reference.record_id >= item.reference.record_id)))) throw new Error("invalid_selection");
      identities.add(item.reference.record_id); sources.add(item.source_key); derivations.add(item.derivation_id); chars += item.projected_chars;
    }
    if (chars > body.char_budget || copy.query_execution.item_id !== body.request_id || copy.query_execution.operation !== "embed_query" ||
      copy.query_digest !== await textDigest(body.query) || copy.query_execution.input_digest !== copy.query_digest) throw new Error("invalid_binding");
    return copy;
  }
  async submit(draft: RecallDraft) {
    const profile = this.state.profile, generation = this.state.generation;
    if (!this.alive || !profile || !generation || this.state.configuration !== "configured" || this.state.operation !== "idle" || this.original || validateRecallDraft(draft).length) return;
    let requestId: string;
    try { requestId = crypto.randomUUID(); }
    catch { this.publish({ message: "A fresh query identity could not be created. No request was sent." }); return; }
    const body: SemanticRecallRequest = { namespace_id: profile.namespace_id, request_id: requestId, generation: { ...generation },
      query: draft.query, min_cosine: Number(draft.minCosine), max_results: Number(draft.maxResults), char_budget: Number(draft.charBudget), run_id: null };
    this.original = exact(body);
    const epoch = this.epoch, operation = ++this.operation;
    this.publish({ frozen: JSON.parse(this.original) as SemanticRecallRequest, receipt: null, projection: null, resolvedAt: null,
      execution: null, operation: "querying", unknown: true, message: "One explicit query is waiting. No automatic retry; leaving does not cancel server work." });
    try {
      const result = await this.api.recall(body);
      if (!this.current(epoch, operation)) return;
      const receipt = await this.checkedReceipt(result.receipt, body, profile);
      if (!this.current(epoch, operation)) return;
      this.publish({ receipt, unknown: false, execution: result.current_query_execution, operation: "idle", message: "Selection retained. Checking exact current sources…" });
      await this.resolve();
    } catch (error) {
      if (!this.current(epoch, operation) || this.refused(error)) return;
      this.publish({ operation: "idle", unknown: true, projection: null, resolvedAt: null,
        message: `${safeRecallFailure(error)} Query outcome unknown. Check the identical frozen request; no retry was sent.` });
    }
  }
  async check() {
    const profile = this.state.profile;
    if (!this.alive || !this.original || !profile || !this.state.generation || this.state.configuration !== "configured" || this.state.operation !== "idle") return;
    const body = JSON.parse(this.original) as SemanticRecallRequest;
    const epoch = this.epoch, operation = ++this.operation;
    this.sourceAbort?.abort(); const request = new AbortController(); this.sourceAbort = request;
    this.publish({ operation: "checking", receipt: null, projection: null, resolvedAt: null, execution: null, message: "Checking exact historical metadata only…" });
    try {
      const value = await this.api.inspect(body, request.signal);
      if (!this.current(epoch, operation)) return;
      const receipt = value === null ? null : await this.checkedReceipt(value, body, profile);
      if (!this.current(epoch, operation)) return;
      this.publish({ receipt, operation: "idle", unknown: receipt === null, message: receipt ?
        "Historical selection recovered. Load exact current sources explicitly; no inference or source load occurred during Check." :
        "No receipt was observed. The earlier query may still be in flight; absence does not prove failure. No retry was sent." });
    } catch (error) {
      if (!this.current(epoch, operation) || this.refused(error)) return;
      this.publish({ operation: "idle", unknown: true, message: `${safeRecallFailure(error)} The earlier query remains unknown. No retry was sent.` });
    }
  }
  async resolve() {
    const receipt = this.state.receipt, profile = this.state.profile;
    if (!this.alive || !receipt || !profile || !this.original || !this.state.generation || this.state.configuration !== "configured" || this.state.operation !== "idle") return;
    const epoch = this.epoch, operation = ++this.operation;
    this.sourceAbort?.abort(); const request = new AbortController(); this.sourceAbort = request;
    this.publish({ operation: "resolving", projection: null, resolvedAt: null, message: "Loading the entire exact selection under current source authority…" });
    try {
      const value = await this.api.resolve(receipt.receipt_id, { receipt_digest: receipt.receipt_digest }, request.signal);
      if (!this.current(epoch, operation)) return;
      const projection: SemanticRecallProjection = JSON.parse(exact(value));
      if (exact(projection.receipt) !== exact(receipt) || !Array.isArray(projection.items) || projection.items.length !== receipt.selected.length) throw new Error("foreign_projection");
      for (const [index, item] of projection.items.entries()) {
        if (exact(item.selection) !== exact(receipt.selected[index]) || typeof item.text !== "string" || !item.text.trim() || !unicode(item.text) || item.text.includes("\0") ||
          [...item.text].length !== item.selection.projected_chars || await textDigest(item.text) !== item.selection.projection_digest) throw new Error("foreign_source");
        if (!this.current(epoch, operation)) return;
      }
      if (!this.current(epoch, operation)) return;
      this.publish({ projection, resolvedAt: new Date().toISOString(), operation: "idle", message: "Exact sources resolved. Authorization was checked for this handoff; later source changes require a new explicit load." });
    } catch (error) {
      if (!this.current(epoch, operation) || this.refused(error)) return;
      this.publish({ operation: "idle", projection: null, resolvedAt: null, message: `${safeRecallFailure(error)} Selection metadata is historical; no source text is displayed.` });
    }
  }
  discard() {
    if (!this.alive || this.state.operation !== "idle") return;
    ++this.operation; this.sourceAbort?.abort(); this.original = null;
    this.publish({ frozen: null, receipt: null, projection: null, resolvedAt: null, execution: null,
      message: this.state.unknown ? "Frozen body discarded. The earlier query remains unknown; starting a new query is a separate explicit operation." : "Transient query and sources cleared." });
  }
  dispose() {
    if (!this.alive) return;
    this.alive = false; ++this.epoch; ++this.operation; this.metadataAbort?.abort(); this.sourceAbort?.abort();
    this.original = null; this.profileBinding = null; this.generationBinding = null; this.state = initialRecallState(); this.changed = () => {};
  }
}
