import { expect, it, vi } from "vitest";
import { ApiError } from "$lib/api/client";
import { initialObservationState, ObservationWorkspace, type ObservationState, type ObservationTransport } from "./observation";
import { admissionId, otherId, runId, request, field, deferred } from "./observation.fixtures";
import { emptyObservationDraft, prepareObservation } from "./draft";

function harness() {
  let state: ObservationState = initialObservationState;
  const transport = {
    current: vi.fn<ObservationTransport["current"]>().mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: null }),
    read: vi.fn<ObservationTransport["read"]>().mockResolvedValue(field()),
    consent: vi.fn<ObservationTransport["consent"]>().mockResolvedValue(null),
    submit: vi.fn<ObservationTransport["submit"]>().mockResolvedValue({ admission_id: admissionId, run_id: runId, run_status: "queued" }),
    filter: vi.fn<ObservationTransport["filter"]>().mockResolvedValue(field().view!),
    delete: vi.fn<ObservationTransport["delete"]>().mockResolvedValue({ admission_id: admissionId,
      request_digest: field().request_digest, observation_digest: field().observation_digest, status: "deleted" }),
    cancel: vi.fn<ObservationTransport["cancel"]>().mockResolvedValue(undefined)
  };
  const workspace = new ObservationWorkspace(transport, (next) => { state = next; });
  return { workspace, transport, get state() { return state; } };
}

it("does not acquire on open, read, refresh or filter; views stay bound to the complete field", async () => {
  const h = harness(); await h.workspace.open(admissionId);
  const original = h.state.document;
  await h.workspace.filter("é");
  expect(h.state.document).toBe(original);
  expect(h.transport.filter.mock.calls[0]?.slice(0, 2)).toEqual([admissionId, { revision: "literal-casefold@1", query: "é" }]);
  expect(h.transport.submit).not.toHaveBeenCalled();
  h.transport.filter.mockResolvedValue({ ...field().view!, field_digest: "0".repeat(64) });
  await h.workspace.filter("mismatch");
  expect(h.state.document).toBeNull(); expect(h.state.slotAvailable).toBe(false);
});

it("freezes one body after uncertain submission and explicitly replays exactly it", async () => {
  const h = harness(); const body = request(); const expected = structuredClone(body);
  h.transport.submit.mockRejectedValueOnce(new TypeError("network"));
  await h.workspace.submit(body);
  body.seed.need = "Later edited draft";
  expect(h.transport.submit).toHaveBeenCalledTimes(1);
  expect(h.state.unconfirmedId).toBe(admissionId); expect(h.state.canReplay).toBe(true);
  h.transport.read.mockRejectedValueOnce(new ApiError("Not found", 404));
  await h.workspace.refresh();
  expect(h.state.unconfirmedId).toBe(admissionId); expect(h.state.canReplay).toBe(true);
  await h.workspace.submit({ ...request(), request_id: otherId });
  expect(h.transport.submit).toHaveBeenCalledTimes(1);
  await h.workspace.replay();
  expect(h.transport.submit).toHaveBeenCalledTimes(2);
  expect(h.transport.submit.mock.calls.map(([sent]) => sent)).toEqual([expected, expected]);
  expect(h.state.unconfirmedId).toBeNull(); expect(h.state.document?.admission_id).toBe(admissionId);
});

it("clears private content/replay body on current refusal and never treats failure as an empty slot", async () => {
  const h = harness(); await h.workspace.open(admissionId);
  h.transport.read.mockRejectedValue(new ApiError("Denied", 403));
  await h.workspace.refresh();
  expect(h.state.document).toBeNull(); expect(h.state.view).toBeNull(); expect(h.state.consent).toBeNull();
  expect(h.state.accessRefused).toBe(true); expect(h.state.slotAvailable).toBe(false);
  h.transport.submit.mockRejectedValue(new ApiError("Denied after await", 403));
  await h.workspace.submit(request());
  expect(h.state.canReplay).toBe(false); expect(h.state.unconfirmedId).toBe(admissionId);
});

it("fences stale selection, non-cooperative reads, invalid selection and teardown", async () => {
  const h = harness(); const old = deferred<ReturnType<typeof field>>();
  h.transport.read.mockReturnValueOnce(old.promise);
  const opening = h.workspace.open(admissionId); const signal = h.transport.read.mock.calls[0]![1];
  await h.workspace.open(otherId); expect(signal.aborted).toBe(true);
  // A wrong-identity response is refused rather than becoming the new selection.
  expect(h.state.document).toBeNull();
  old.resolve(field()); await opening; expect(h.state.document).toBeNull();
  h.transport.read.mockResolvedValue(field()); await h.workspace.open(admissionId);
  h.workspace.clearSelection(); expect(h.state.document).toBeNull();
  const late = deferred<ReturnType<typeof field>>(); h.transport.read.mockReturnValueOnce(late.promise);
  const reading = h.workspace.open(admissionId); h.workspace.dispose(); late.resolve(field()); await reading;
  expect(h.state.document).toBeNull();
});

it("fences a late successful mutation after a route change while preserving its unconfirmed UUID", async () => {
  const h = harness(); const pending = deferred<Awaited<ReturnType<ObservationTransport["submit"]>>>();
  h.transport.submit.mockReturnValue(pending.promise);
  const sending = h.workspace.submit(request());
  await h.workspace.open(otherId);
  pending.resolve({ admission_id: admissionId, run_id: runId, run_status: "queued" }); await sending;
  expect(h.state.selectedId).toBe(otherId); expect(h.state.document).toBeNull();
  expect(h.state.unconfirmedId).toBe(admissionId); expect(h.state.mutationPending).toBe(false);
  expect(h.transport.submit).toHaveBeenCalledTimes(1);
});

it("unknown custody forbids deletion; exact terminal deletion is distinct from empty and uncertainty survives leaving", async () => {
  const h = harness(); h.transport.read.mockResolvedValue({ ...field(), status: "unknown", terminal_disposition: "unknown" });
  await h.workspace.open(admissionId); await h.workspace.delete(); expect(h.transport.delete).not.toHaveBeenCalled();
  h.transport.read.mockResolvedValue(field()); await h.workspace.refresh();
  h.transport.delete.mockRejectedValueOnce(new TypeError("lost acknowledgement"));
  await h.workspace.delete(); expect(h.state.document).toBeNull(); expect(h.state.unconfirmedDeletion?.admissionId).toBe(admissionId);
  expect(h.workspace.needsUnloadWarning).toBe(true); expect(h.state.slotAvailable).toBe(false);
  await h.workspace.refresh(); await h.workspace.delete();
  expect(h.transport.delete.mock.calls[1]).toEqual([admissionId,
    { request_digest: field().request_digest, observation_digest: field().observation_digest }]);
  expect(h.state.deleted?.status).toBe("deleted"); expect(h.state.document).toBeNull();
  expect(h.state.unconfirmedDeletion).toBeNull(); expect(h.transport.submit).not.toHaveBeenCalled();
});

it("requires complete explicit seed facts and preserves empty lists/unknowns without inventing assessments", () => {
  const draft = emptyObservationDraft(); expect(prepareObservation(draft, admissionId).request).toBeNull();
  Object.assign(draft, { subject: "Technology@1", need: "Need é", evidence: "Title only", delivery: "Not assessed", deadline: "2099-01-01T12:00" });
  const prepared = prepareObservation(draft, admissionId);
  expect(prepared.errors).toEqual([]); expect(prepared.request?.seed).toMatchObject({ inventory: [], hard_criteria: [],
    preferences: [], budget_minor: null, region: null, operating_mode: "Watch", learning_mode: "none" });
  draft.budget = "12.34"; expect(prepareObservation(draft, admissionId).request?.seed.budget_minor).toBe(1234);
  draft.budget = "0.001"; expect(prepareObservation(draft, admissionId).request).toBeNull();
  draft.budget = ""; draft.need = "é".repeat(1025); expect(prepareObservation(draft, admissionId).request).toBeNull();
});

it("cancels the exact Run through its owner and re-reads disposition rather than treating cancellation as deletion", async () => {
  const h = harness(); h.transport.read.mockResolvedValue({ ...field(), status: "pending", run_status: "running", terminal_disposition: "pending" });
  await h.workspace.open(admissionId);
  h.transport.read.mockResolvedValue({ ...field(), status: "unknown", run_status: "cancelled", terminal_disposition: "unknown" });
  await h.workspace.cancel();
  expect(h.transport.cancel).toHaveBeenCalledWith(runId);
  expect(h.state.document?.terminal_disposition).toBe("unknown");
  await h.workspace.delete(); expect(h.transport.delete).not.toHaveBeenCalled(); expect(h.transport.submit).not.toHaveBeenCalled();
});

it("retains an uncertain cancellation identity without an automatic retry and reconciles its native terminal read", async () => {
  const h = harness(); h.transport.read.mockResolvedValue({ ...field(), status: "pending", run_status: "running", terminal_disposition: "pending" });
  await h.workspace.open(admissionId); h.transport.cancel.mockRejectedValue(new TypeError("lost acknowledgement"));
  await h.workspace.cancel();
  expect(h.transport.cancel).toHaveBeenCalledTimes(1); expect(h.workspace.needsUnloadWarning).toBe(true);
  expect(h.state.unconfirmedCancel).toEqual({ admissionId, runId }); expect(h.state.document).toBeNull();
  h.transport.read.mockResolvedValue({ ...field(), status: "unavailable", run_status: "cancelled", terminal_disposition: "terminal" });
  await h.workspace.refresh(); expect(h.state.unconfirmedCancel).toBeNull(); expect(h.transport.cancel).toHaveBeenCalledTimes(1);
});

it("settles uncertain deletion only from the exact tombstone and keeps other mutations fenced", async () => {
  const h = harness(); await h.workspace.open(admissionId);
  h.transport.delete.mockRejectedValueOnce(new TypeError("lost acknowledgement"));
  await h.workspace.delete();
  const uncertain = h.state.unconfirmedDeletion;
  h.transport.read.mockResolvedValue({ ...field(), admission_id: otherId, status: "deleted", seed: null,
    seed_document: null, observation: null, view: null });
  await h.workspace.open(otherId);
  expect(h.state.unconfirmedDeletion).toBe(uncertain);
  expect(h.workspace.needsUnloadWarning).toBe(true);
  await h.workspace.submit({ ...request(), request_id: otherId });
  expect(h.transport.submit).not.toHaveBeenCalled();
  h.transport.read.mockResolvedValue({ ...field(), status: "deleted", seed: null, seed_document: null, observation: null, view: null });
  await h.workspace.open(admissionId);
  expect(h.state.unconfirmedDeletion).toBeNull(); expect(h.workspace.needsUnloadWarning).toBe(false);
});

it("clears a refused superseded submission body without replacing the new selection", async () => {
  const h = harness(); const pending = deferred<Awaited<ReturnType<ObservationTransport["submit"]>>>();
  h.transport.submit.mockReturnValueOnce(pending.promise);
  const sending = h.workspace.submit(request());
  h.transport.read.mockResolvedValue({ ...field(), admission_id: otherId });
  await h.workspace.open(otherId); expect(h.state.document?.admission_id).toBe(otherId);
  pending.reject(new ApiError("Refused old request", 403)); await sending;
  expect(h.state.canReplay).toBe(false); expect(h.state.unconfirmedId).toBe(admissionId);
  expect(h.state.document?.admission_id).toBe(otherId);
  await h.workspace.replay(); expect(h.transport.submit).toHaveBeenCalledTimes(1);
});

it("cannot discard an uncertain submission's immutable replay body by deleting another selected field", async () => {
  const h = harness(); h.transport.submit.mockRejectedValueOnce(new TypeError("lost admission acknowledgement"));
  await h.workspace.submit(request());
  h.transport.read.mockResolvedValue({ ...field(), admission_id: otherId });
  await h.workspace.open(otherId); await h.workspace.delete();
  expect(h.transport.delete).not.toHaveBeenCalled(); expect(h.state.canReplay).toBe(true);
  expect(h.state.unconfirmedId).toBe(admissionId);
  h.transport.read.mockResolvedValue(field()); await h.workspace.replay();
  expect(h.transport.submit.mock.calls.map(([body]) => body)).toEqual([request(), request()]);
});
