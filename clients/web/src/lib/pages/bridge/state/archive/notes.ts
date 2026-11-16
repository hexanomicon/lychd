import { z } from "zod";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile, ArchiveBridgeDefault, NoteRecord, NoteProposal, NoteListPage, ArchiveLifecycleIntent } from "$lib/api/models";

const unicode = z.string().refine((v) => [...v].every((c) => { const n = c.codePointAt(0)!; return n < 0xd800 || n > 0xdfff; }));
const label = unicode.refine((v) => [...v].length >= 1 && [...v].length <= 160 && !/[\x00-\x1f\x7f]/.test(v));
const timestamp = z.string().datetime({ offset: true });
const digest = z.string().regex(/^[0-9a-f]{64}$/);
const profileSchema = z.object({ profile: z.literal("local-public-notes@1"), namespace_id: z.uuid(),
  owner_subject: z.object({ identity: label }), policy_revision: label });
const recordSchema = z.object({ namespace_id: z.uuid(), reference: z.object({ record_id: z.uuid(), revision_digest: digest,
  lifecycle_version: z.number().int().positive() }), source_key: label, source_revision: label, source_digest: digest,
  producer: label, observed_at: timestamp, created_at: timestamp, lifecycle: z.enum(["candidate", "promoted", "archived", "revoked"]) });
const defaultSchema = z.object({ current_default: z.object({ pattern_id: z.string(), pattern_revision: z.string(), guidance: z.string().nullable() }).nullable(), requests_profile: z.boolean().nullable() }).refine((v) => (v.current_default === null) === (v.requests_profile === null));
export const notesHref = (selection: string) => `/bridge?notes=${encodeURIComponent(selection)}`;
export function notesSelection(value: string | null): string | null {
  if (value === "new" || value === "manage") return value;
  return value !== null && z.uuid().safeParse(value).success ? value.toLowerCase() : null;
}
export function notesFocusSelection(value: string | null): string | null {
  return value === "recall" ? value : notesSelection(value);
}
export interface NoteDraft { sourceKey: string; revision: string; text: string; producer: string; observedAt: string; publicMaterial: boolean; replacesRevision: string | null }
export function emptyNoteDraft(): NoteDraft { return { sourceKey: "", revision: "", text: "", producer: "", observedAt: "", publicMaterial: false, replacesRevision: null }; }
export function correctionDraft(record: NoteRecord): NoteDraft {
  return { ...emptyNoteDraft(), sourceKey: record.source_key, producer: record.producer, observedAt: record.observed_at, replacesRevision: record.source_revision };
}
export function validateDraft(draft: NoteDraft): string[] {
  const errors: string[] = [];
  for (const [name, value] of [["Source key", draft.sourceKey], ["Source revision", draft.revision], ["Producer", draft.producer]] as const)
    if (!label.safeParse(value).success) errors.push(`${name}: use 1–160 Unicode characters without control characters.`);
  if (!unicode.safeParse(draft.text).success || [...draft.text].length > 16000 || !draft.text.trim() || draft.text.includes("\0"))
    errors.push("Replacement text: use nonblank valid Unicode, at most 16,000 code points, without NUL.");
  if (!timestamp.safeParse(draft.observedAt).success) errors.push("Observation time: supply an ISO timestamp with timezone (Z or an explicit offset).");
  if (draft.replacesRevision !== null && draft.revision === draft.replacesRevision) errors.push("Correction requires a different source revision.");
  if (!draft.publicMaterial) errors.push("Confirm the supplied material is public.");
  return errors;
}
export async function prepareNote(draft: NoteDraft, namespace: string, requestId: string): Promise<NoteProposal> {
  if (validateDraft(draft).length || !z.uuid().safeParse(namespace).success || !z.uuid().safeParse(requestId).success) throw new Error("invalid_draft");
  const bytes = new TextEncoder().encode(draft.text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return { namespace_id: namespace, request_id: requestId, source_key: draft.sourceKey, source_revision: draft.revision,
    text: draft.text, producer: draft.producer, observed_at: draft.observedAt, classification: "public",
    source_digest: Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("") };
}
export function safeNoteFailure(error: unknown): string {
  if (!(error instanceof ApiError)) return "The response could not be confirmed or safely displayed.";
  if (error.status === 401 || error.status === 403) return "Current management authority was refused.";
  if (error.status === 404) return "The configured profile or exact record is unavailable (404).";
  const codes: Record<string, string> = { source_conflict: "This source revision is already bound to different material.",
    stale_version: "The lifecycle version changed; Check the exact record before deciding again.",
    request_conflict: "The intake identity conflicts with retained input.",
    record_missing: "The exact record is unavailable under this profile.", storage: "The public-note storage request failed.", revoked: "This revision is a retained revoked tombstone." };
  return error.code && Object.hasOwn(codes, error.code) ? codes[error.code]! : `The protected request failed${error.status ? ` (${error.status})` : ""}.`;
}
export interface NotesApi {
  profile(signal?: AbortSignal): Promise<ArchiveProfile>; defaults(signal?: AbortSignal): Promise<ArchiveBridgeDefault>;
  list(options: { sourceKey?: string; cursor?: string; signal?: AbortSignal }): Promise<NoteListPage>;
  read(id: string, signal?: AbortSignal): Promise<NoteRecord>; admit(body: NoteProposal): Promise<NoteRecord>;
  promote(id: string, body: ArchiveLifecycleIntent): Promise<NoteRecord>; revoke(id: string, body: ArchiveLifecycleIntent): Promise<NoteRecord>;
}
type UnknownTransition = Readonly<{ recordId: string; namespace: string; version: number; target: "promote" | "revoke"; checked: boolean }>;
export interface NotesState {
  profile: ArchiveProfile | null; profilePhase: "loading" | "ready" | "unavailable";
  defaults: ArchiveBridgeDefault | null; defaultError: string; records: readonly NoteRecord[]; cursor: string | null;
  filter: string; listBusy: boolean; listError: string; selected: string | null; record: NoteRecord | null;
  detailBusy: boolean; detailError: string; writing: boolean; message: string;
  intakeUnknown: boolean; replayAvailable: boolean; frozen: NoteProposal | null; transitionUnknown: UnknownTransition | null;
  authorityEpoch: number;
}
export function initialNotesState(): NotesState { return { profile: null, profilePhase: "loading", defaults: null, defaultError: "", records: [], cursor: null,
  filter: "", listBusy: false, listError: "", selected: null, record: null, detailBusy: false, detailError: "", writing: false,
  message: "", intakeUnknown: false, replayAvailable: false, frozen: null, transitionUnknown: null, authorityEpoch: 0 }; }
export class PublicNoteManager {
  private state = initialNotesState();
  private alive = true;
  private epoch = 0;
  private selection = 0;
  private focus: string | null = null;
  private focusEpoch = 0;
  private preparationBusy = false;
  private listing = 0;
  private readAbort: AbortController | null = null;
  private listAbort: AbortController | null = null;
  private profileAbort: AbortController | null = null;
  private original: string | null = null;
  private profileBinding: string | null = null;
  constructor(private api: NotesApi, private changed: (state: NotesState) => void) {}
  private publish(update: Partial<NotesState>) {
    if (!this.alive) return;
    this.state = { ...this.state, ...update };
    this.changed(this.state);
  }
  private current(epoch: number) { return this.alive && this.epoch === epoch; }
  private refused(error: unknown) {
    if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) return false;
    ++this.epoch; ++this.selection; ++this.listing;
    this.readAbort?.abort(); this.listAbort?.abort(); this.profileAbort?.abort(); this.original = null;
    this.publish({ ...initialNotesState(), selected: this.state.selected, profilePhase: "unavailable", message: safeNoteFailure(error),
      intakeUnknown: this.state.intakeUnknown, transitionUnknown: this.state.transitionUnknown,
      authorityEpoch: this.state.authorityEpoch + 1 });
    return true;
  }
  setPreparationBusy(busy: boolean) { this.preparationBusy = busy; }
  capturePreparationRefusal(): (error: unknown) => void {
    const epoch = this.epoch, focusEpoch = this.focusEpoch, profile = JSON.stringify(this.state.profile);
    return (error) => {
      if (this.current(epoch) && focusEpoch === this.focusEpoch && profile === JSON.stringify(this.state.profile)) this.refused(error);
    };
  }
  async load() {
    if (!this.alive || this.state.writing) return;
    const epoch = ++this.epoch;
    ++this.listing; ++this.selection; this.listAbort?.abort(); this.readAbort?.abort(); this.profileAbort?.abort();
    const request = new AbortController(); this.profileAbort = request;
    this.publish({ profile: null, profilePhase: "loading", defaults: null, defaultError: "", records: [], cursor: null, record: null, listError: "", detailError: "" });
    try {
      const profile = profileSchema.parse(await this.api.profile(request.signal));
      if (!this.current(epoch)) return;
      const binding = JSON.stringify(profile);
      if (this.profileBinding !== null && this.profileBinding !== binding) {
        this.original = null;
        this.publish({ frozen: null, replayAvailable: false, filter: "", authorityEpoch: this.state.authorityEpoch + 1,
          message: "The configured profile changed. Transient source and replay bodies were cleared; earlier unknown writes remain unknown." });
      }
      this.profileBinding = binding;
      this.publish({ profile, profilePhase: "ready" });
      await Promise.all([this.loadDefaults(epoch, request.signal), this.list(false), this.state.selected ? this.check() : Promise.resolve()]);
    } catch (error) {
      if (!this.current(epoch) || this.refused(error)) return;
      this.publish({ profilePhase: "unavailable", message: safeNoteFailure(error) });
    }
  }
  private async loadDefaults(epoch: number, signal: AbortSignal) {
    try { const defaults = defaultSchema.parse(await this.api.defaults(signal)); if (this.current(epoch)) this.publish({ defaults }); }
    catch (error) { if (this.current(epoch) && !this.refused(error)) this.publish({ defaults: null, defaultError: safeNoteFailure(error) }); }
  }
  async list(more = false, filter = this.state.filter) {
    const profile = this.state.profile;
    if (!profile || !this.alive) return;
    if (filter && !label.safeParse(filter).success) { this.publish({ listError: "Exact source key must contain 1–160 valid characters without controls." }); return; }
    const epoch = this.epoch, generation = ++this.listing;
    this.listAbort?.abort(); const request = new AbortController(); this.listAbort = request;
    const cursor = more && filter === this.state.filter ? this.state.cursor : null;
    if (more && !cursor) return;
    this.publish({ filter, listBusy: true, listError: "", ...(cursor ? {} : { records: [], cursor: null }) });
    try {
      const page = await this.api.list({ sourceKey: filter || undefined, cursor: cursor || undefined, signal: request.signal });
      const rows = z.array(recordSchema).max(50).parse(page.records);
      const next = z.string().min(1).max(2048).nullable().parse(page.next_cursor ?? null);
      if (rows.some((row) => row.namespace_id !== profile.namespace_id || (filter && row.source_key !== filter)) || (next && next === cursor)) throw new Error("foreign_page");
      if (!this.current(epoch) || generation !== this.listing) return;
      const merged = new Map((cursor ? this.state.records : []).map((row) => [row.reference.record_id, row]));
      rows.forEach((row) => merged.set(row.reference.record_id, row));
      this.publish({ records: [...merged.values()], cursor: next, listBusy: false });
    } catch (error) {
      if (!this.current(epoch) || generation !== this.listing || this.refused(error)) return;
      this.publish({ listBusy: false, listError: safeNoteFailure(error) });
    }
  }
  select(focus: string | null) {
    if (!this.alive || this.focus === focus) return;
    this.focus = focus; ++this.focusEpoch;
    const id = focus === "new" || focus === "manage" ? null : focus;
    ++this.selection; this.readAbort?.abort();
    this.publish({ selected: id, record: null, detailBusy: false, detailError: "" });
    if (id && this.state.profile) void this.check();
  }
  private record(value: NoteRecord, namespace: string, id?: string): NoteRecord {
    const record = recordSchema.parse(value);
    if (record.namespace_id !== namespace || (id && record.reference.record_id !== id)) throw new Error("foreign_record");
    return record;
  }
  async check() {
    const id = this.state.selected, profile = this.state.profile;
    if (!id || !profile || !this.alive || this.state.writing) return;
    const epoch = this.epoch, selection = ++this.selection;
    this.readAbort?.abort(); const request = new AbortController(); this.readAbort = request;
    this.publish({ detailBusy: true, record: null, detailError: "" });
    try {
      const record = this.record(await this.api.read(id, request.signal), profile.namespace_id, id);
      if (!this.current(epoch) || selection !== this.selection || this.state.selected !== id) return;
      const unknown = this.state.transitionUnknown;
      const sameAttempt = unknown?.recordId === id && unknown.namespace === profile.namespace_id;
      this.publish({ record, detailBusy: false, transitionUnknown: sameAttempt ? { ...unknown, checked: true } : unknown,
        message: sameAttempt ? `Current lifecycle version ${record.reference.lifecycle_version} observed. Unchanged or newer metadata cannot identify which attempted occurrence committed; missing metadata cannot prove rollback. Make a new explicit decision from this state.` : this.state.message });
    } catch (error) {
      if (!this.current(epoch) || selection !== this.selection || this.refused(error)) return;
      this.publish({ detailBusy: false, record: null, detailError: `${safeNoteFailure(error)} A failed or missing read does not prove that a pending write rolled back.` });
    }
  }
  freeze(proposal: NoteProposal) {
    if (this.original || this.state.intakeUnknown || this.state.writing || this.preparationBusy || proposal.namespace_id !== this.state.profile?.namespace_id) return;
    this.original = JSON.stringify(proposal);
    this.publish({ frozen: JSON.parse(this.original) as NoteProposal, replayAvailable: false });
  }
  async submit() { if (this.original && !this.state.intakeUnknown) await this.postOriginal(); }
  async replay() { if (this.state.replayAvailable) await this.postOriginal(); }
  private async postOriginal() {
    if (!this.original || !this.alive || this.state.writing || this.preparationBusy || !this.state.profile || this.state.frozen?.namespace_id !== this.state.profile.namespace_id) return;
    const body = JSON.parse(this.original) as NoteProposal, epoch = this.epoch, selection = ++this.selection;
    this.readAbort?.abort();
    this.publish({ writing: true, intakeUnknown: true, replayAvailable: false, message: "Submitting frozen public intake once; no automatic retry." });
    try {
      const record = this.record(await this.api.admit(body), body.namespace_id);
      if (record.source_key !== body.source_key || record.source_revision !== body.source_revision ||
        record.source_digest !== body.source_digest || record.producer !== body.producer ||
        Date.parse(record.observed_at) !== Date.parse(body.observed_at)) throw new Error("foreign_intake");
      if (!this.current(epoch)) return;
      this.original = null;
      const selected = selection === this.selection;
      this.publish({ writing: false, frozen: null, intakeUnknown: false, replayAvailable: false,
        ...(selected ? { selected: record.reference.record_id, record } : {}),
        message: selected ? `Retained identity ${record.reference.record_id} returned. Intake creates a candidate; promotion is separate. An identical replay does not attribute an earlier occurrence.` :
          "The earlier intake response was reconciled. Refresh authorized metadata explicitly to inspect retained identities." });
      if (selected) await this.list(false, body.source_key);
    } catch (error) {
      if (!this.current(epoch) || this.refused(error)) return;
      this.publish({ writing: false, intakeUnknown: true, replayAvailable: true, message: `${safeNoteFailure(error)} Intake outcome unknown. Look up this exact source key or explicitly replay the identical frozen body. Later refusal or conflict cannot prove an earlier write rolled back.` });
    }
  }
  async transition(target: "promote" | "revoke", expected: NoteRecord) {
    const record = this.state.record, profile = this.state.profile;
    if (!record || !profile || !this.alive || this.state.writing || this.preparationBusy || record.reference.record_id !== expected.reference.record_id ||
      record.reference.lifecycle_version !== expected.reference.lifecycle_version || record.namespace_id !== expected.namespace_id ||
      (target === "promote" ? record.lifecycle !== "candidate" : record.lifecycle === "revoked") ||
      (this.state.transitionUnknown?.recordId === record.reference.record_id && !this.state.transitionUnknown.checked)) return;
    const earlierUnknown = this.state.transitionUnknown !== null;
    const command = { recordId: record.reference.record_id, namespace: profile.namespace_id, version: record.reference.lifecycle_version, target, checked: false };
    const epoch = this.epoch, selection = ++this.selection; this.readAbort?.abort();
    this.publish({ writing: true, record: null, transitionUnknown: command, message: `Sending explicit ${target} at version ${command.version}. No automatic replay.` });
    try {
      const result = this.record(await this.api[target](command.recordId, { expected_version: command.version }), command.namespace, command.recordId);
      if (result.lifecycle !== (target === "promote" ? "promoted" : "revoked") || result.reference.lifecycle_version <= command.version || result.reference.revision_digest !== record.reference.revision_digest) throw new Error("invalid_transition");
      if (!this.current(epoch)) return;
      const selected = selection === this.selection && this.state.selected === command.recordId;
      this.publish({ writing: false, ...(selected ? { record: result } : {}), transitionUnknown: null,
        message: selected ? `The explicit ${target} response returned ${result.lifecycle} at version ${result.reference.lifecycle_version}.${earlierUnknown ? " Earlier unconfirmed occurrences remain unattributed." : ""}` :
          `The earlier ${target} response was reconciled. Refresh authorized metadata explicitly; earlier unconfirmed occurrences remain unattributed.` });
      if (selected) await this.list(false, record.source_key);
    } catch (error) {
      if (!this.current(epoch) || this.refused(error)) return;
      this.publish({ writing: false, ...(selection === this.selection ? { record: null } : {}), message: `${safeNoteFailure(error)} Lifecycle outcome unknown. Check this exact record before making a new decision; no lifecycle retry was sent.` });
    }
  }
  discardIntake() { if (!this.state.writing) { this.original = null; this.publish({ frozen: null, replayAvailable: false }); } }
  dispose() {
    this.alive = false; ++this.epoch;
    this.profileAbort?.abort(); this.listAbort?.abort(); this.readAbort?.abort();
    this.profileAbort = null; this.listAbort = null; this.readAbort = null;
    this.original = null; this.state = initialNotesState(); this.changed = () => {};
  }
}
