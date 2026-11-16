import { z } from "zod";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile, ArchiveGeneration, ArchiveGenerationStatus, ArchiveDerivationRequest, ArchiveDerivationStatus, NoteRecord } from "$lib/api/models";

const digest = z.string().regex(/^[0-9a-f]{64}$/);
const label = z.string().min(1).refine((v) => [...v].length <= 160 && !/[\x00-\x1f\x7f\ud800-\udfff]/u.test(v));
const timestamp = z.string().datetime({ offset: true });
const profileSchema = z.object({ profile: z.literal("local-public-notes@1"), namespace_id: z.uuid(), owner_subject: z.object({ identity: label }), policy_revision: label });
const generationSchema = z.object({ generation_id: z.uuid(), manifest_digest: digest });
const sourceSchema = z.object({ record_id: z.uuid(), revision_digest: digest, lifecycle_version: z.number().int().positive() });
const recordSchema = z.object({ namespace_id: z.uuid(), reference: sourceSchema, source_key: label, source_revision: label,
  source_digest: digest, producer: label, observed_at: timestamp, created_at: timestamp, lifecycle: z.enum(["candidate", "promoted", "archived", "revoked"]) });
const generationStatusSchema = z.object({ reference: generationSchema, namespace_id: z.uuid(), state: z.enum(["active", "retired"]),
  version: z.number().int().positive(), created_at: timestamp, retired_at: timestamp.nullable() });
const statusSchema = z.object({ derivation_id: z.uuid(), namespace_id: z.uuid(), generation: generationSchema, source: sourceSchema, source_digest: digest,
  row_version: z.number().int().positive(), attempt_version: z.number().int().nonnegative(), state: z.enum(["prepared", "running", "expired", "complete", "failed", "invalidated"]),
  expires_at: timestamp.nullable(), observed_at: timestamp, completed_at: timestamp.nullable(), failure_code: z.string().nullable(),
  invalidated_reason: z.string().nullable(), vector_digest: digest.nullable(), receipt_digest: digest.nullable() });
const exact = (value: unknown) => JSON.stringify(value);
const copy = <T>(value: T): T => JSON.parse(exact(value)) as T;
export interface PreparationTarget { profile: ArchiveProfile; request: ArchiveDerivationRequest; sourceKey: string; sourceRevision: string; sourceDigest: string }
export interface PreparationState {
  contextVersion: number;
  generation: ArchiveGeneration | null; configuration: "unavailable" | "loading" | "configured";
  registration: ArchiveGenerationStatus | null; registrationUnknown: boolean;
  operation: "idle" | "registering" | "preparing" | "checking";
  review: PreparationTarget | null; frozen: PreparationTarget | null; historical: PreparationTarget | null;
  status: ArchiveDerivationStatus | null; statusHistorical: boolean; statusTarget: PreparationTarget | null;
  unknown: boolean; message: string; eligible: boolean;
}
export const initialPreparationState = (): PreparationState => ({ contextVersion: 0, generation: null, configuration: "unavailable", registration: null,
  registrationUnknown: false, operation: "idle", review: null, frozen: null, historical: null, status: null, statusHistorical: false, statusTarget: null, unknown: false, message: "", eligible: false });
export interface PreparationApi {
  generation(signal?: AbortSignal): Promise<ArchiveGeneration>;
  register(body: ArchiveGeneration): Promise<ArchiveGenerationStatus>;
  derive(body: ArchiveDerivationRequest): Promise<ArchiveDerivationStatus>;
  inspect(body: ArchiveDerivationRequest, signal?: AbortSignal): Promise<ArchiveDerivationStatus>;
}
export function safePreparationFailure(error: unknown): string {
  if (!(error instanceof ApiError)) return "The response could not be confirmed or safely displayed.";
  if (error.status === 401 || error.status === 403) return "Current Archive authority was refused. Protected management and preparation material was cleared.";
  if (error.status === 404) return "The configured derivation service is unavailable (404).";
  const messages: Record<string, string> = {
    generation_missing: "The configured generation is not registered.", generation_retired: "The exact generation is retired; registration cannot reactivate it.",
    generation_binding: "The configured generation binding changed.", generation_conflict: "The generation identity conflicts with the retained manifest.",
    derivation_missing: "No retained derivation row was observed for this exact reference. This does not prove that pending work failed.",
    derivation_binding: "The retained derivation has a different exact source binding. Use the original frozen reference for historical Check.",
    derivation_busy: "The latest attempt is running. No replacement was started automatically.", derivation_invalidated: "This exact derivation is invalidated.",
    source_stale: "The source is no longer this exact promoted revision. Check current note metadata before deciding again.",
    attempt_stale: "A different attempt won the durable fence. No replacement was started automatically.",
    embedding_unavailable: "The exact embedding capability is unavailable; runtime preparation is separate.",
    embedding_input_size: "The whole note exceeds the exact embedding input limit; it was not truncated or split.",
    source_integrity: "Source integrity validation refused preparation.", embedding_result: "Embedding result validation refused publication.",
    embedding_receipt: "Embedding receipt validation refused publication.", vector_storage_integrity: "Vector storage validation refused publication.",
    storage: "The Archive storage request failed."
  };
  return error.code && Object.hasOwn(messages, error.code) ? messages[error.code]! : `The protected preparation request failed${error.status ? ` (${error.status})` : ""}.`;
}
export function preparationStatusReason(status: ArchiveDerivationStatus): string {
  if (status.failure_code === "execution_failed") return "Execution failed; inference may already have been consumed.";
  const reasons: Record<string, string> = { archived: "Source archived.", revoked: "Source revoked.", promoted: "Source superseded by another promoted revision.", generation_retired: "Generation retired." };
  return status.invalidated_reason && Object.hasOwn(reasons, status.invalidated_reason) ? reasons[status.invalidated_reason]! :
    status.failure_code || status.invalidated_reason ? "The server supplied a bounded failure or invalidation reason." : "";
}

/** Document-local presentation only; Archive owns every durable decision. */
export class PublicNotePreparation {
  private state = initialPreparationState();
  private alive = true;
  private epoch = 0;
  private configurationEpoch = 0;
  private operation = 0;
  private profile: ArchiveProfile | null = null;
  private generationBinding: ArchiveGeneration | null = null;
  private selected: string | null = null;
  private record: NoteRecord | null = null;
  private blocked = false;
  private pendingWrite = false;
  private generationAbort: AbortController | null = null;
  private statusAbort: AbortController | null = null;
  constructor(private api: PreparationApi, private changed: (state: PreparationState) => void,
    private writing: (busy: boolean) => void, private captureRefusal: () => (error: unknown) => void) {}
  get contextVersion() { return this.epoch; }
  private publish(update: Partial<PreparationState>) { if (this.alive) { this.state = { ...this.state, ...update, contextVersion: this.epoch }; this.changed(this.state); } }
  private current(epoch: number, operation: number) { return this.alive && epoch === this.epoch && operation === this.operation; }
  setContext(profile: ArchiveProfile | null, selected: string | null, record: NoteRecord | null, blocked: boolean) {
    if (!this.alive) return;
    const parsedProfile = profileSchema.safeParse(profile), parsedRecord = recordSchema.safeParse(record);
    const nextProfile = parsedProfile.success ? parsedProfile.data : null;
    const nextRecord = parsedRecord.success && parsedRecord.data.namespace_id === nextProfile?.namespace_id && parsedRecord.data.reference.record_id === selected ? parsedRecord.data : null;
    const boundary = exact(nextProfile) !== exact(this.profile) || selected !== this.selected;
    const revision = exact(nextRecord) !== exact(this.record);
    this.profile = nextProfile; this.selected = selected; this.record = nextRecord; this.blocked = blocked;
    if (boundary || revision || blocked) {
      ++this.epoch; ++this.operation; this.statusAbort?.abort();
      this.publish({ review: null, status: null, statusTarget: null, eligible: false,
        ...(!this.pendingWrite ? { operation: "idle" as const } : {}) });
    }
    if (boundary) {
      ++this.configurationEpoch; this.generationAbort?.abort(); this.generationBinding = null;
      this.publish({ ...initialPreparationState(), operation: this.pendingWrite ? this.state.operation : "idle",
        unknown: this.state.unknown, message: this.state.unknown ? "An earlier preparation response remains unknown. Navigation does not cancel model work; its frozen reference is no longer retained in this focus." : "" });
      if (nextProfile && selected) void this.loadGeneration();
    }
    this.publish({ eligible: !!this.target() && !blocked && !this.pendingWrite });
  }
  private target(): PreparationTarget | null {
    const { profile, record } = this;
    if (!profile || !record || !this.state.generation || this.state.registration?.state === "retired" || record.lifecycle !== "promoted") return null;
    return { profile: copy(profile), request: { generation: copy(this.state.generation), source: copy(record.reference) },
      sourceKey: record.source_key, sourceRevision: record.source_revision, sourceDigest: record.source_digest };
  }
  private inspectTarget(): PreparationTarget | null {
    if (!this.profile || !this.record || !this.state.generation) return null;
    return { profile: copy(this.profile), request: { generation: copy(this.state.generation), source: copy(this.record.reference) },
      sourceKey: this.record.source_key, sourceRevision: this.record.source_revision, sourceDigest: this.record.source_digest };
  }
  async loadGeneration() {
    if (!this.alive || !this.profile || !this.selected || this.pendingWrite) return;
    const configuration = ++this.configurationEpoch, refusal = this.captureRefusal();
    ++this.epoch; ++this.operation; this.statusAbort?.abort(); this.generationAbort?.abort();
    const request = new AbortController(); this.generationAbort = request;
    const previous = this.generationBinding;
    this.publish({ configuration: "loading", generation: null, registration: null, review: null, status: null, statusTarget: null, eligible: false, operation: "idle" });
    try {
      const generation = generationSchema.parse(await this.api.generation(request.signal));
      if (!this.alive || configuration !== this.configurationEpoch) return;
      const changed = previous !== null && exact(generation) !== exact(previous);
      this.generationBinding = copy(generation);
      this.publish({ generation, configuration: "configured", ...(changed ? { frozen: null, historical: null, registrationUnknown: false,
        message: "Configured generation changed. Earlier unknown occurrences remain unknown; old frozen references were cleared." } : {}) });
      this.publish({ eligible: !!this.target() && !this.blocked });
    } catch (error) {
      if (!this.alive || configuration !== this.configurationEpoch) return;
      if (this.refused(error, refusal)) return;
      this.publish({ configuration: "unavailable", message: safePreparationFailure(error) });
    }
  }
  private refused(error: unknown, refusal: (error: unknown) => void) {
    if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) return false;
    ++this.epoch; ++this.operation; ++this.configurationEpoch; this.generationAbort?.abort(); this.statusAbort?.abort(); this.generationBinding = null;
    this.publish({ ...initialPreparationState(), unknown: this.state.unknown, message: safePreparationFailure(error) });
    refusal(error); return true;
  }
  private refusedInConfiguration(error: unknown, configuration: number, refusal: (error: unknown) => void) {
    return this.alive && configuration === this.configurationEpoch && this.refused(error, refusal);
  }
  review() {
    if (!this.alive || this.blocked || this.pendingWrite || this.state.operation !== "idle" || this.state.configuration !== "configured") return;
    const target = this.target(); if (target) this.publish({ review: target, message: "Review this exact preparation decision before sending." });
  }
  cancelReview() { this.publish({ review: null }); }
  async register() {
    if (!this.alive || this.blocked || this.pendingWrite || this.state.operation !== "idle" || !this.profile || !this.state.generation) return;
    const generation = copy(this.state.generation), namespace = this.profile.namespace_id;
    const epoch = this.epoch, configuration = this.configurationEpoch, operation = ++this.operation, refusal = this.captureRefusal();
    this.pendingWrite = true; this.writing(true);
    this.publish({ operation: "registering", registrationUnknown: true, eligible: false, review: null, message: "Waiting for explicit registration response; no embedding or reactivation is requested." });
    try {
      const result = generationStatusSchema.parse(await this.api.register(generation));
      if (result.namespace_id !== namespace || exact(result.reference) !== exact(generation) || (result.state === "retired") !== (result.retired_at !== null)) throw new Error("foreign_generation");
      if (!this.current(epoch, operation)) return;
      this.publish({ registration: result, registrationUnknown: false, message: "Exact shared-generation state observed. This response does not attribute an earlier registration occurrence or prove runtime readiness." });
    } catch (error) {
      if (this.refusedInConfiguration(error, configuration, refusal) || !this.current(epoch, operation)) return;
      this.publish({ registration: null, message: `${safePreparationFailure(error)} Registration outcome unknown. An explicit exact registration repeat reads retained state without embedding and cannot reactivate retirement.` });
    } finally { this.finishWrite(); }
  }
  async prepare() {
    const target = this.state.review;
    if (!this.alive || this.blocked || this.pendingWrite || this.state.operation !== "idle" || !target || exact(target) !== exact(this.target())) return;
    const epoch = this.epoch, configuration = this.configurationEpoch, operation = ++this.operation, refusal = this.captureRefusal(), earlierUnknown = this.state.unknown;
    const historical = this.state.frozen && exact(this.state.frozen.request) !== exact(target.request) ? this.state.frozen : this.state.historical;
    this.pendingWrite = true; this.writing(true);
    this.publish({ frozen: copy(target), historical, review: null, status: null, statusTarget: null, unknown: true, operation: "preparing", eligible: false,
      message: "Waiting for preparation response. Leaving does not cancel work or establish rollback." });
    try {
      const status = this.validateStatus(await this.api.derive(copy(target.request)), target);
      if (!this.current(epoch, operation)) return;
      this.publish({ status, statusHistorical: this.historicalStatus(status), statusTarget: target, unknown: earlierUnknown, message: "Preparation response observed for this exact reference. Latest row state is not invocation authorship or an all-attempt cost ledger." });
    } catch (error) {
      if (this.refusedInConfiguration(error, configuration, refusal) || !this.current(epoch, operation)) return;
      this.publish({ message: `${safePreparationFailure(error)} Preparation outcome unknown. Check metadata explicitly; no automatic retry was sent.` });
    } finally { this.finishWrite(); }
  }
  private finishWrite() {
    this.pendingWrite = false; this.writing(false);
    this.publish({ operation: "idle", eligible: !!this.target() && !this.blocked });
  }
  async check(which: "current" | "frozen" | "historical" = "current") {
    const target = which === "current" ? this.inspectTarget() : this.state[which];
    if (!this.alive || this.blocked || this.pendingWrite || this.state.operation !== "idle" || !target || !this.profile ||
      exact(target.profile) !== exact(this.profile) || exact(target.request.generation) !== exact(this.state.generation)) return;
    const epoch = this.epoch, configuration = this.configurationEpoch, operation = ++this.operation, refusal = this.captureRefusal();
    this.statusAbort?.abort(); const request = new AbortController(); this.statusAbort = request;
    this.publish({ operation: "checking", review: null, status: null, statusTarget: target, message: "Checking latest retained metadata only; this does not resolve an unknown invocation." });
    try {
      const status = this.validateStatus(await this.api.inspect(copy(target.request), request.signal), target);
      if (this.current(epoch, operation)) this.publish({ status, statusHistorical: this.historicalStatus(status), message: "Latest row observed. Any earlier lost preparation response remains unknown, including after complete or expired status." });
    } catch (error) {
      if (this.refusedInConfiguration(error, configuration, refusal) || !this.current(epoch, operation)) return;
      this.publish({ message: safePreparationFailure(error) });
    } finally { if (this.current(epoch, operation)) this.publish({ operation: "idle" }); }
  }
  private historicalStatus(status: ArchiveDerivationStatus) {
    const record = this.record;
    return status.state === "invalidated" || !record || record.lifecycle !== "promoted" || exact(status.source) !== exact(record.reference);
  }
  private validateStatus(value: ArchiveDerivationStatus, target: PreparationTarget): ArchiveDerivationStatus {
    const result = statusSchema.parse(value);
    if (result.namespace_id !== target.profile.namespace_id || exact(result.generation) !== exact(target.request.generation) ||
      exact(result.source) !== exact(target.request.source) || result.source_digest !== target.sourceDigest) throw new Error("foreign_status");
    return result;
  }
  dispose() {
    this.alive = false; ++this.epoch; ++this.operation; ++this.configurationEpoch;
    this.generationAbort?.abort(); this.statusAbort?.abort();
    this.state = initialPreparationState(); this.changed = () => {}; this.writing = () => {};
  }
}
