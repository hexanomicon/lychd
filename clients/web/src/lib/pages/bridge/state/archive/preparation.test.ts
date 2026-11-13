import { describe, expect, it, vi } from "vitest";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile, ArchiveGeneration, ArchiveGenerationStatus, ArchiveDerivationStatus, NoteRecord } from "$lib/api/models";
import { PublicNotePreparation, initialPreparationState, safePreparationFailure, preparationStatusReason, type PreparationApi, type PreparationState } from "./preparation";
const namespace = "00000000-0000-4000-8000-000000000001", id = "00000000-0000-4000-8000-000000000002", other = "00000000-0000-4000-8000-000000000003";
const profile: ArchiveProfile = { profile: "local-public-notes@1", namespace_id: namespace, owner_subject: { identity: "owner" }, policy_revision: "policy" };
const generation: ArchiveGeneration = { generation_id: other, manifest_digest: "c".repeat(64) };
const record: NoteRecord = { namespace_id: namespace, reference: { record_id: id, revision_digest: "a".repeat(64), lifecycle_version: 2 }, source_key: "<script>key</script>", source_revision: "r1", source_digest: "b".repeat(64), producer: "p", observed_at: "2026-10-19T00:00:00Z", created_at: "2026-10-19T00:00:00Z", lifecycle: "promoted" };
const registration: ArchiveGenerationStatus = { reference: generation, namespace_id: namespace, state: "active", version: 1, created_at: record.created_at, retired_at: null };
const status = (state: ArchiveDerivationStatus["state"] = "complete"): ArchiveDerivationStatus => ({ derivation_id: other, namespace_id: namespace, generation, source: record.reference, source_digest: record.source_digest,
  row_version: 3, attempt_version: 1, state, expires_at: null, observed_at: record.created_at, completed_at: state === "complete" ? record.created_at : null,
  failure_code: null, invalidated_reason: null, vector_digest: state === "complete" ? "d".repeat(64) : null, receipt_digest: null });
function deferred<T>() { let resolve!: (value: T) => void, reject!: (error: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function setup(overrides: Partial<PreparationApi> = {}) {
  const api: PreparationApi = { generation: vi.fn().mockResolvedValue(generation), register: vi.fn().mockResolvedValue(registration), derive: vi.fn().mockResolvedValue(status()), inspect: vi.fn().mockResolvedValue(status()), ...overrides };
  let state: PreparationState = initialPreparationState(); const busy = vi.fn(), refuse = vi.fn();
  const controller = new PublicNotePreparation(api, (next) => { state = next; }, busy, () => refuse);
  return { api, busy, refuse, controller, get state() { return state; } };
}
async function ready(t: ReturnType<typeof setup>) { t.controller.setContext(profile, id, record, false); await Promise.resolve(); await Promise.resolve(); }
const body = { generation, source: record.reference };
describe("explicit exact-note preparation", () => {
  it("only discovers metadata on context/mount; registration, status and derive require independent gestures", async () => {
    const t = setup(); await ready(t);
    expect(t.state.eligible).toBe(true); expect(t.api.generation).toHaveBeenCalledTimes(1);
    expect(t.api.register).not.toHaveBeenCalled(); expect(t.api.inspect).not.toHaveBeenCalled(); expect(t.api.derive).not.toHaveBeenCalled();
    await t.controller.prepare(); expect(t.api.derive).not.toHaveBeenCalled();
    await t.controller.check(); expect(t.api.inspect).toHaveBeenCalledWith(body, expect.any(AbortSignal));
    expect(t.api.register).not.toHaveBeenCalled(); expect(t.api.derive).not.toHaveBeenCalled();
    await t.controller.register(); expect(t.api.register).toHaveBeenCalledExactlyOnceWith(generation); expect(t.api.derive).not.toHaveBeenCalled();
    t.controller.review(); expect(t.state.review?.profile).toEqual(profile); await t.controller.prepare();
    expect(t.api.derive).toHaveBeenCalledExactlyOnceWith(body); expect(Object.keys(vi.mocked(t.api.derive).mock.calls[0]![0]).sort()).toEqual(["generation", "source"]);
    expect(t.state.status?.state).toBe("complete"); expect(t.busy.mock.calls).toEqual([[true], [false], [true], [false]]);
  });
  it.each(["prepared", "failed", "expired", "complete"] as const)("lost derive remains unknown after latest %s; another same-body attempt needs fresh review", async (state) => {
    const t = setup({ derive: vi.fn().mockRejectedValueOnce(new Error("sensitive")).mockResolvedValue(status()), inspect: vi.fn().mockResolvedValue(status(state)) }); await ready(t);
    t.controller.review(); await t.controller.prepare(); expect(t.state.unknown).toBe(true); expect(t.state.message).not.toContain("sensitive");
    const frozen = JSON.stringify(t.state.frozen); await t.controller.check("frozen");
    expect(t.state.status?.state).toBe(state); expect(t.state.unknown).toBe(true); expect(JSON.stringify(t.state.frozen)).toBe(frozen);
    await t.controller.prepare(); expect(t.api.derive).toHaveBeenCalledTimes(1);
    t.controller.review(); await t.controller.prepare(); expect(t.api.derive).toHaveBeenCalledTimes(2); expect(t.state.unknown).toBe(true);
    expect(vi.mocked(t.api.derive).mock.calls.map(([value]) => value)).toEqual([body, body]);
  });
  it("retains old lifecycle reference for historical Check and never hydrates metadata or guesses it after reload", async () => {
    const t = setup(); await ready(t); t.controller.review(); await t.controller.prepare();
    const revoked = { ...record, lifecycle: "revoked" as const, reference: { ...record.reference, lifecycle_version: 3 } };
    t.controller.setContext(profile, id, null, false); t.controller.setContext(profile, id, revoked, false);
    expect(t.state.eligible).toBe(false); expect(t.state.frozen?.request.source.lifecycle_version).toBe(2);
    await t.controller.check("frozen"); expect(t.state.statusHistorical).toBe(true); expect(t.api.inspect).toHaveBeenLastCalledWith(body, expect.any(AbortSignal));
    t.controller.review(); await t.controller.prepare(); expect(t.api.derive).toHaveBeenCalledTimes(1);
    const fresh = setup(); fresh.controller.setContext(profile, id, revoked, false); await Promise.resolve(); await Promise.resolve();
    await fresh.controller.check(); expect(fresh.api.inspect).toHaveBeenLastCalledWith({ generation, source: revoked.reference }, expect.any(AbortSignal)); expect(fresh.state.frozen).toBeNull();
  });
  it("register repeat is explicit and retired state stays retired without any derive", async () => {
    const retired = { ...registration, state: "retired" as const, version: 2, retired_at: record.created_at };
    const t = setup({ register: vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValue(retired) }); await ready(t);
    await t.controller.register(); expect(t.state.registrationUnknown).toBe(true); await t.controller.check(); expect(t.api.register).toHaveBeenCalledTimes(1);
    await t.controller.register(); expect(t.state.registration?.state).toBe("retired"); expect(t.state.eligible).toBe(false); expect(t.state.registrationUnknown).toBe(false);
    expect(vi.mocked(t.api.register).mock.calls.map(([value]) => value)).toEqual([generation, generation]); expect(t.api.derive).not.toHaveBeenCalled();
  });
  it.each(["candidate", "archived", "revoked"] as const)("%s metadata never authorizes preparation or implicitly registers", async (lifecycle) => {
    const t = setup(); t.controller.setContext(profile, id, { ...record, lifecycle }, false); await Promise.resolve(); await Promise.resolve();
    t.controller.review(); await t.controller.prepare(); expect(t.state.review).toBeNull(); expect(t.api.derive).not.toHaveBeenCalled(); expect(t.api.register).not.toHaveBeenCalled();
  });
  it("blocks duplicate local writes and lifecycle overlap until an ignored earlier response settles", async () => {
    const pending = deferred<ArchiveDerivationStatus>(); const t = setup({ derive: vi.fn().mockReturnValue(pending.promise) }); await ready(t);
    t.controller.review(); const post = t.controller.prepare(); await t.controller.register(); await t.controller.prepare(); await t.controller.check();
    expect(t.api.derive).toHaveBeenCalledTimes(1); expect(t.api.register).not.toHaveBeenCalled(); expect(t.api.inspect).not.toHaveBeenCalled();
    t.controller.setContext(profile, other, { ...record, reference: { ...record.reference, record_id: other } }, false);
    expect(t.busy).toHaveBeenLastCalledWith(true); pending.resolve(status()); await post;
    expect(t.busy).toHaveBeenLastCalledWith(false); expect(t.state.status).toBeNull(); expect(t.state.frozen).toBeNull();
    t.controller.setContext(profile, other, { ...record, reference: { ...record.reference, record_id: other } }, true);
    t.controller.review(); await t.controller.register(); expect(t.state.review).toBeNull(); expect(t.api.register).not.toHaveBeenCalled();
  });
  it("fences A→B→A late errors, lifecycle changes, profile replacement and disposal", async () => {
    const late = deferred<ArchiveDerivationStatus>(); const t = setup({ inspect: vi.fn().mockReturnValue(late.promise) }); await ready(t);
    const check = t.controller.check(); t.controller.setContext(profile, other, null, false); t.controller.setContext(profile, id, record, false);
    late.reject(new ApiError("private", 403)); await check; expect(t.refuse).not.toHaveBeenCalled(); expect(t.state.status).toBeNull();
    await Promise.resolve(); const post = deferred<ArchiveDerivationStatus>(); vi.mocked(t.api.derive).mockReturnValue(post.promise);
    t.controller.review(); const sending = t.controller.prepare(); t.controller.setContext({ ...profile, policy_revision: "new" }, id, record, false);
    post.resolve(status()); await sending; expect(t.state.status).toBeNull(); expect(t.state.frozen).toBeNull();
    const d = setup({ inspect: vi.fn().mockReturnValue(late.promise) }); await ready(d); const reading = d.controller.check(); d.controller.dispose(); await reading; expect(d.refuse).not.toHaveBeenCalled();
  });
  it.each([401, 403])("current %s clears protected preparation and calls the owning manager refusal bridge", async (code) => {
    const t = setup({ inspect: vi.fn().mockRejectedValue(new ApiError("private", code)) }); await ready(t); t.controller.review(); await t.controller.prepare();
    await t.controller.check(); expect(t.refuse).toHaveBeenCalledTimes(1); expect(t.state.generation).toBeNull(); expect(t.state.frozen).toBeNull(); expect(t.state.status).toBeNull(); expect(t.state.message).not.toContain("private");
  });
  it.each(["namespace", "generation", "source", "digest", "shape"])("refuses malformed/cross-boundary %s status without displaying it", async (field) => {
    const value = status(); if (field === "namespace") value.namespace_id = other;
    if (field === "generation") value.generation = { ...generation, manifest_digest: "e".repeat(64) };
    if (field === "source") value.source = { ...record.reference, lifecycle_version: 99 };
    if (field === "digest") value.source_digest = "e".repeat(64); if (field === "shape") value.row_version = -1;
    const t = setup({ inspect: vi.fn().mockResolvedValue(value) }); await ready(t); await t.controller.check(); expect(t.state.status).toBeNull(); expect(t.state.message).toContain("could not be confirmed");
  });
  it("generation replacement invalidates reviewed/frozen bindings and closes arbitrary errors and status codes", async () => {
    const t = setup(); await ready(t); t.controller.review(); await t.controller.prepare();
    vi.mocked(t.api.generation).mockResolvedValue({ ...generation, generation_id: id }); await t.controller.loadGeneration();
    expect(t.state.review).toBeNull(); expect(t.state.frozen).toBeNull(); expect(t.state.status).toBeNull();
    expect(safePreparationFailure(new ApiError("private", 409, "derivation_busy"))).toContain("running");
    expect(safePreparationFailure(new ApiError("private", 409, "secret_code"))).toBe("The protected preparation request failed (409).");
    expect(preparationStatusReason({ ...status("failed"), failure_code: "<script>private</script>" })).not.toContain("private");
  });
});

it("same-note lifecycle refresh keeps pending configuration discovery current, including a current authority refusal", async () => {
  const discovery = deferred<ArchiveGeneration>(); const t = setup({ generation: vi.fn().mockReturnValue(discovery.promise) });
  t.controller.setContext(profile, id, record, false);
  t.controller.setContext(profile, id, null, false);
  t.controller.setContext(profile, id, { ...record, lifecycle: "revoked", reference: { ...record.reference, lifecycle_version: 3 } }, false);
  discovery.reject(new ApiError("private", 403)); await Promise.resolve(); await Promise.resolve();
  expect(t.refuse).toHaveBeenCalledTimes(1); expect(t.state.configuration).toBe("unavailable"); expect(t.state.generation).toBeNull();
});
it("new focus during a write recovers configured metadata only through an enabled explicit refresh after settlement", async () => {
  const pending = deferred<ArchiveDerivationStatus>(); const t = setup({ derive: vi.fn().mockReturnValue(pending.promise) }); await ready(t);
  t.controller.review(); const write = t.controller.prepare();
  const next = { ...record, reference: { ...record.reference, record_id: other } };
  t.controller.setContext(profile, other, next, false); expect(t.api.generation).toHaveBeenCalledTimes(1);
  pending.resolve(status()); await write; expect(t.state.operation).toBe("idle"); expect(t.state.generation).toBeNull();
  await t.controller.loadGeneration(); expect(t.api.generation).toHaveBeenCalledTimes(2); expect(t.state.eligible).toBe(true);
  expect(t.api.derive).toHaveBeenCalledTimes(1); expect(t.api.register).not.toHaveBeenCalled(); expect(t.api.inspect).not.toHaveBeenCalled();
});
it("a failed generation read cannot forget the old binding and retain stale frozen references when the next explicit read observes a replacement", async () => {
  const t = setup(); await ready(t); t.controller.review(); await t.controller.prepare();
  vi.mocked(t.api.generation).mockRejectedValueOnce(new Error()).mockResolvedValueOnce({ ...generation, generation_id: id });
  await t.controller.loadGeneration(); expect(t.state.frozen).not.toBeNull(); await t.controller.loadGeneration();
  expect(t.state.generation?.generation_id).toBe(id); expect(t.state.frozen).toBeNull(); expect(t.state.historical).toBeNull();
});
it("fences and aborts old configuration/status reads through profile and A→B→A replacement", async () => {
  const old = deferred<ArchiveGeneration>(); const t = setup({ generation: vi.fn().mockReturnValueOnce(old.promise).mockResolvedValue(generation) });
  t.controller.setContext(profile, id, record, false); const oldSignal = vi.mocked(t.api.generation).mock.calls[0]![0]!;
  t.controller.setContext(profile, other, null, false); t.controller.setContext(profile, id, record, false);
  old.reject(new ApiError("old private", 403)); await Promise.resolve(); await Promise.resolve();
  expect(oldSignal.aborted).toBe(true); expect(t.refuse).not.toHaveBeenCalled(); expect(t.state.generation).toEqual(generation);
  const pending = deferred<ArchiveDerivationStatus>(); vi.mocked(t.api.inspect).mockReturnValue(pending.promise);
  const reading = t.controller.check(), signal = vi.mocked(t.api.inspect).mock.calls[0]![1]!;
  t.controller.setContext({ ...profile, owner_subject: { identity: "new owner" } }, id, record, false);
  pending.resolve(status()); await reading; expect(signal.aborted).toBe(true); expect(t.state.status).toBeNull(); expect(t.state.frozen).toBeNull();
});

it.each([401, 403])("current preparation %s authority across same-note metadata refresh clears for every operation", async (code) => {
  for (const method of ["register", "derive", "inspect"] as const) {
    const pending = deferred<never>(); const t = setup({ [method]: vi.fn().mockReturnValue(pending.promise) }); await ready(t);
    t.controller.review();
    const request = method === "register" ? t.controller.register() : method === "derive" ? t.controller.prepare() : t.controller.check();
    t.controller.setContext(profile, id, null, false); t.controller.setContext(profile, id, record, false);
    pending.reject(new ApiError("private", code)); await request;
    expect(t.refuse, method).toHaveBeenCalledTimes(1); expect(t.state.generation, method).toBeNull();
    expect(t.state.frozen, method).toBeNull(); expect(t.state.status, method).toBeNull();
  }
});
