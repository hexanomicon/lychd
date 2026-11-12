import { ApiError } from "$lib/api/client";
import type { components } from "$lib/api/openapi";

export type ObservationRequest = components["schemas"]["ObserveMarketRequest"];
export type ObservationDocument = components["schemas"]["ObservationDocument"];
export type ObservationView = components["schemas"]["ObservationView"];
type Consent = components["schemas"]["ConsentCard"];
type Deleted = components["schemas"]["ObservationDeleted"];
export type ObservationTransport = {
  current: (signal: AbortSignal) => Promise<components["schemas"]["ScavengerState"]>;
  read: (id: string, signal: AbortSignal) => Promise<ObservationDocument>;
  consent: (id: string, signal: AbortSignal) => Promise<Consent | null>;
  submit: (body: ObservationRequest) => Promise<components["schemas"]["ObservationAdmission"]>;
  filter: (id: string, body: components["schemas"]["LiteralFilter"], signal: AbortSignal) => Promise<ObservationView>;
  delete: (id: string, body: components["schemas"]["DeleteObservationRequest"]) => Promise<Deleted>;
  cancel: (runId: string) => Promise<void>;
};
export type ObservationState = Readonly<{
  configured: boolean | null;
  accessRefused: boolean;
  slotAvailable: boolean;
  mutationPending: boolean;
  unconfirmedDeletion: Readonly<{ admissionId: string; requestDigest: string; observationDigest: string | null }> | null;
  selectedId: string | null;
  document: ObservationDocument | null;
  view: ObservationView | null;
  consent: Consent | null;
  deleted: Deleted | null;
  phase: "idle" | "reading" | "submitting" | "filtering" | "deleting" | "cancelling";
  message: string;
  unconfirmedId: string | null;
  unconfirmedCancel: Readonly<{ admissionId: string; runId: string }> | null;
  canReplay: boolean;
}>;

export function observationId(value: string | null): string | null {
  return value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) ? value : null;
}

export const initialObservationState: ObservationState = Object.freeze({
  configured: null, accessRefused: false, slotAvailable: false, mutationPending: false, unconfirmedDeletion: null, selectedId: null, document: null, view: null, consent: null,
  deleted: null, phase: "idle", message: "", unconfirmedId: null, unconfirmedCancel: null, canReplay: false
});

/** Document-local action identity; only protected server reads establish retained state. */
export class ObservationWorkspace {
  private state: ObservationState = initialObservationState;
  private version = 0;
  private disposed = false;
  private reader: AbortController | null = null;
  private pending: ObservationRequest | null = null;

  constructor(private transport: ObservationTransport, private changed: (state: ObservationState) => void) {
    this.emit({});
  }

  private emit(patch: Partial<ObservationState>) {
    this.state = { ...this.state, ...patch, canReplay: this.pending !== null };
    if (!this.disposed) this.changed(this.state);
  }

  private begin(phase: ObservationState["phase"]): number {
    this.reader?.abort();
    this.reader = new AbortController();
    this.emit({ phase, message: "", accessRefused: false });
    return ++this.version;
  }

  private current(version: number): boolean { return !this.disposed && this.version === version; }

  private failure(error: unknown, message: string) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      this.pending = null;
      this.emit({ configured: null, slotAvailable: false, accessRefused: true, document: null, view: null, consent: null, deleted: null,
        message: "Current access was refused. Protected content and replay body were cleared." });
    } else this.emit({ slotAvailable: false, document: null, view: null, consent: null, deleted: null, message });
  }

  clearSelection(): void {
    this.reader?.abort(); this.version++;
    this.emit({ phase: "idle", selectedId: null, slotAvailable: false, document: null, view: null, consent: null, deleted: null });
  }

  async open(id: string | null): Promise<void> {
    if (this.disposed) return;
    this.clearSelection();
    this.emit({ selectedId: id });
    await this.refresh();
  }

  async refresh(): Promise<void> {
    if (this.disposed || this.state.phase === "submitting" || this.state.phase === "deleting") return;
    const id = this.state.selectedId;
    const version = this.begin("reading");
    const signal = this.reader!.signal;
    this.emit({ slotAvailable: false, document: null, view: null, consent: null, deleted: null });
    try {
      let document: ObservationDocument | null;
      if (id) document = await this.transport.read(id, signal);
      else {
        const status = await this.transport.current(signal);
        if (!this.current(version)) return;
        this.emit({ configured: status.configured, slotAvailable: status.configured && status.current === null });
        document = status.current;
      }
      if (!this.current(version)) return;
      if (document && id && document.admission_id !== id) throw new Error("selection");
      if (document && this.state.unconfirmedId === document.admission_id) {
        this.pending = null;
        this.emit({ unconfirmedId: null });
      }
      if (document?.admission_id === this.state.unconfirmedCancel?.admissionId &&
          document?.run_id === this.state.unconfirmedCancel?.runId &&
          ["cancelling", "cancelled", "done", "failed"].includes(document?.run_status ?? "")) {
        this.emit({ unconfirmedCancel: null });
      }
      const deletion = this.state.unconfirmedDeletion;
      if (deletion && document?.status === "deleted" && document.admission_id === deletion.admissionId &&
          document.request_digest === deletion.requestDigest && document.observation_digest === deletion.observationDigest) {
        this.emit({ unconfirmedDeletion: null });
      }
      this.emit({ configured: document ? true : this.state.configured, selectedId: document?.admission_id ?? id, document, view: document?.view ?? null });
      if (document?.status === "awaiting_consent") {
        const consent = await this.transport.consent(document.admission_id, signal);
        if (!this.current(version)) return;
        if (consent && consent.run_id !== document.run_id) throw new Error("consent selection");
        this.emit({ consent });
      }
    } catch (error) {
      if (this.current(version)) this.failure(error,
        this.state.unconfirmedId ? "Admission remains unconfirmed. A failed read, including 404, does not prove refusal." :
          "The current field is unavailable. Refresh explicitly; no source acquisition was requested.");
    } finally { if (this.current(version)) this.emit({ phase: "idle" }); }
  }

  async submit(body: ObservationRequest): Promise<void> {
    if (this.disposed || this.state.phase !== "idle" || this.state.mutationPending || this.state.unconfirmedId ||
        this.state.unconfirmedCancel || this.state.unconfirmedDeletion) return;
    // No reactive proxy or subsequently editable draft becomes the retry envelope.
    this.pending = JSON.parse(JSON.stringify(body)) as ObservationRequest;
    await this.send();
  }

  async replay(): Promise<void> {
    if (!this.disposed && this.state.phase === "idle" && !this.state.mutationPending &&
        !this.state.unconfirmedCancel && !this.state.unconfirmedDeletion && this.pending) await this.send();
  }

  private async send(): Promise<void> {
    const request = this.pending;
    if (!request) return;
    const version = this.begin("submitting");
    this.emit({ mutationPending: true });
    this.emit({ slotAvailable: false, selectedId: request.request_id, unconfirmedId: request.request_id,
      document: null, view: null, consent: null, deleted: null });
    try {
      const result = await this.transport.submit(request);
      if (!this.current(version)) return;
      if (result.admission_id !== request.request_id) throw new Error("admission identity");
      this.pending = null;
      this.emit({ unconfirmedId: null, phase: "idle" });
      await this.refresh();
    } catch (error) {
      // A superseded mutation still owns its replay body, never the new selection.
      if (error instanceof ApiError && (error.status === 401 || error.status === 403) && this.pending === request) {
        this.pending = null;
        this.emit({});
      }
      if (this.current(version)) this.failure(error,
        "Submission unconfirmed. Keep this UUID. Check the same request or explicitly replay its identical body; no automatic retry was sent.");
    } finally { this.emit({ mutationPending: false }); if (this.current(version)) this.emit({ phase: "idle" }); }
  }

  async filter(query: string): Promise<void> {
    const document = this.state.document;
    if (this.disposed || this.state.phase !== "idle" || this.state.mutationPending || !document?.observation) return;
    const version = this.begin("filtering");
    try {
      const view = await this.transport.filter(document.admission_id,
        { revision: "literal-casefold@1", query }, this.reader!.signal);
      if (!this.current(version)) return;
      if (view.observation_id !== document.observation.observation_id ||
          view.observation_digest !== document.observation_digest ||
          (document.view && view.field_digest !== document.view.field_digest)) throw new Error("field identity");
      this.emit({ view });
    } catch (error) {
      if (this.current(version)) this.failure(error, "The local view was refused or unavailable. No acquisition was requested.");
    } finally { if (this.current(version)) this.emit({ phase: "idle" }); }
  }

  async delete(): Promise<void> {
    const document = this.state.document;
    if (this.disposed || this.state.phase !== "idle" || this.state.mutationPending || !document || document.status === "deleted" ||
        document.terminal_disposition !== "terminal" || this.state.unconfirmedId || this.state.unconfirmedCancel ||
        (this.state.unconfirmedDeletion && this.state.unconfirmedDeletion.admissionId !== document.admission_id)) return;
    const version = this.begin("deleting");
    this.emit({ unconfirmedDeletion: { admissionId: document.admission_id, requestDigest: document.request_digest,
      observationDigest: document.observation_digest }, mutationPending: true });
    try {
      const result = await this.transport.delete(document.admission_id,
        { request_digest: document.request_digest, observation_digest: document.observation_digest });
      if (!this.current(version)) return;
      if (result.admission_id !== document.admission_id || result.request_digest !== document.request_digest ||
          result.observation_digest !== document.observation_digest || result.status !== "deleted") throw new Error("delete identity");
      this.pending = null;
      this.emit({ unconfirmedDeletion: null, document: null, view: null, consent: null, deleted: result,
        message: "Deleted: the application seed and item payload were removed. Immutable execution/contact receipts and backups are outside this acknowledgement." });
    } catch (error) {
      if (this.current(version)) this.failure(error, "Deletion unconfirmed. Refresh this exact UUID; no deletion retry or new acquisition was sent.");
    } finally { this.emit({ mutationPending: false }); if (this.current(version)) this.emit({ phase: "idle" }); }
  }

  async cancel(): Promise<void> {
    const document = this.state.document;
    if (this.disposed || this.state.phase !== "idle" || this.state.mutationPending || !document?.run_id ||
        this.state.unconfirmedId || this.state.unconfirmedDeletion ||
        !document.run_status || ["done", "failed", "cancelled"].includes(document.run_status) ||
        (this.state.unconfirmedCancel && this.state.unconfirmedCancel.runId !== document.run_id)) return;
    const version = this.begin("cancelling");
    this.emit({ mutationPending: true, consent: null,
      unconfirmedCancel: { admissionId: document.admission_id, runId: document.run_id } });
    try {
      await this.transport.cancel(document.run_id);
      if (!this.current(version)) return;
      this.emit({ unconfirmedCancel: null, phase: "idle" });
      await this.refresh();
    } catch (error) {
      if (this.current(version)) this.failure(error,
        "Cancellation unconfirmed. Check this same observation or retry cancellation of the same Run explicitly. Cancellation does not delete or settle unknown acquisition.");
    } finally { this.emit({ mutationPending: false }); if (this.current(version)) this.emit({ phase: "idle" }); }
  }

  /** Fence old reads before an explicit native consent action. */
  invalidate(): number { this.reader?.abort(); return ++this.version; }
  isCurrent(version: number): boolean { return this.current(version); }
  get needsUnloadWarning(): boolean { return this.state.unconfirmedId !== null || this.state.unconfirmedDeletion !== null ||
    this.state.unconfirmedCancel !== null || this.state.phase === "submitting" || this.state.phase === "deleting"; }
  dispose(): void { this.disposed = true; this.version++; this.reader?.abort(); this.pending = null; this.state = initialObservationState; }
}
