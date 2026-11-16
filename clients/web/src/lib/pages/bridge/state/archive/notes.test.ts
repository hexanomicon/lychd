import { webcrypto } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile, NoteProposal, NoteRecord } from "$lib/api/models";
import { PublicNoteManager, initialNotesState, emptyNoteDraft, correctionDraft, prepareNote, validateDraft, safeNoteFailure, type NotesApi, type NotesState } from "./notes";


afterEach(() => vi.unstubAllGlobals());
const namespace = "00000000-0000-4000-8000-000000000001", id = "00000000-0000-4000-8000-000000000002", other = "00000000-0000-4000-8000-000000000003";
const profile: ArchiveProfile = { profile: "local-public-notes@1", namespace_id: namespace, owner_subject: { identity: "operator" }, policy_revision: "policy" };
function record(recordId = id, version = 1, lifecycle: NoteRecord["lifecycle"] = "candidate"): NoteRecord {
  return { namespace_id: namespace, reference: { record_id: recordId, revision_digest: "a".repeat(64), lifecycle_version: version }, source_key: "key", source_revision: "r1", source_digest: "b".repeat(64), producer: "operator", observed_at: "2026-10-19T00:00:00Z", created_at: "2026-10-19T00:00:00Z", lifecycle };
}
const body: NoteProposal = { namespace_id: namespace, request_id: other, source_key: "key", source_revision: "r1", source_digest: "b".repeat(64), producer: "operator", observed_at: "2026-10-19T00:00:00Z", classification: "public", text: "Exact\r\n é " };
function deferred<T>() { let resolve!: (v: T) => void; let reject!: (e: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function setup(overrides: Partial<NotesApi> = {}) {
  const api: NotesApi = { profile: vi.fn().mockResolvedValue(profile), defaults: vi.fn().mockResolvedValue({ current_default: null, requests_profile: null }), list: vi.fn().mockResolvedValue({ records: [], next_cursor: null }), read: vi.fn().mockResolvedValue(record()), admit: vi.fn().mockResolvedValue(record()), promote: vi.fn().mockResolvedValue(record(id, 2, "promoted")), revoke: vi.fn().mockResolvedValue(record(id, 2, "revoked")), ...overrides };
  let state: NotesState = initialNotesState();
  const manager = new PublicNoteManager(api, (next) => { state = next; });
  return { api, manager, get state() { return state; } };
}

describe("public-note exact identity and unknown outcomes", () => {
  it("preserves exact UTF-8 bytes/code-point labels and rejects invalid Unicode, NUL, time and correction revision", async () => {
    const draft = { ...emptyNoteDraft(), sourceKey: "é".repeat(160), revision: "r2", producer: "p", observedAt: "2026-10-19T00:00:00+02:00", text: " é\r\n ", publicMaterial: true };
    vi.stubGlobal("crypto", webcrypto);
    const prepared = await prepareNote(draft, namespace, other);
    expect(prepared.text).toBe(draft.text); expect(prepared.source_key).toBe(draft.sourceKey);
    expect(prepared.source_digest).toBe("e57c8074967d0717b880844245a66037295610bfd3854408453262e228065b36");
    expect(prepared.source_digest).toMatch(/^[0-9a-f]{64}$/);
    for (const text of ["\ud800", "\0", " ", "x".repeat(16001)]) expect(validateDraft({ ...draft, text }).length).toBeGreaterThan(0);
    expect(validateDraft({ ...draft, observedAt: "2026-10-19T00:00:00" }).length).toBeGreaterThan(0);
    const correction = correctionDraft(record()); expect(correction.text).toBe(""); expect(correction.revision).toBe("");
    expect(validateDraft({ ...draft, replacesRevision: "r2" })).toContain("Correction requires a different source revision.");
  });
  it("sends once, preserves frozen body through lost response/conflicting replay and never posts on lookup or Check", async () => {
    const t = setup({ admit: vi.fn().mockRejectedValueOnce(new Error("secret body")).mockRejectedValueOnce(new ApiError("secret", 409, "source_conflict")).mockResolvedValue(record()) });
    await t.manager.load(); t.manager.freeze(body); await t.manager.submit();
    expect(t.state.intakeUnknown).toBe(true); expect(t.state.replayAvailable).toBe(true); expect(t.state.message).not.toContain("secret");
    await t.manager.list(false, "key"); t.manager.select(id); await t.manager.check();
    expect(t.api.admit).toHaveBeenCalledTimes(1); expect(t.state.intakeUnknown).toBe(true);
    await t.manager.replay(); expect(t.state.intakeUnknown).toBe(true);
    await t.manager.replay(); expect(t.state.intakeUnknown).toBe(false);
    expect(vi.mocked(t.api.admit).mock.calls.map(([sent]) => JSON.stringify(sent))).toEqual([JSON.stringify(body), JSON.stringify(body), JSON.stringify(body)]);
    expect(t.api.promote).not.toHaveBeenCalled(); t.manager.dispose();
  });
  it("keeps lifecycle uncertainty after same/newer metadata and failed reads; a new decision uses fresh CAS", async () => {
    const t = setup({ promote: vi.fn().mockRejectedValue(new ApiError("secret", 409, "stale_version")) });
    await t.manager.load(); t.manager.select(id); await t.manager.check();
    await t.manager.transition("promote", t.state.record!);
    expect(t.state.transitionUnknown?.checked).toBe(false); expect(t.state.record).toBeNull();
    await t.manager.check(); expect(t.state.transitionUnknown?.checked).toBe(true); expect(t.state.message).toContain("cannot identify");
    vi.mocked(t.api.read).mockResolvedValue(record(id, 5, "promoted")); await t.manager.check();
    await t.manager.transition("revoke", t.state.record!); expect(t.api.revoke).toHaveBeenCalledWith(id, { expected_version: 5 });
    expect(t.state.transitionUnknown).not.toBeNull(); // malformed revoke response (version 2) cannot settle CAS 5
    vi.mocked(t.api.read).mockRejectedValue(new ApiError("secret", 404)); await t.manager.check();
    expect(t.state.transitionUnknown).not.toBeNull(); expect(t.state.detailError).toContain("does not prove"); expect(t.api.promote).toHaveBeenCalledTimes(1);
  });
  it("late A→B→A reads, foreign rows and teardown cannot disclose stale data or issue POSTs", async () => {
    const a = deferred<NoteRecord>(), b = deferred<NoteRecord>();
    const t = setup({ read: vi.fn().mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise).mockResolvedValue(record(id, 7)) });
    await t.manager.load(); t.manager.select(id); t.manager.select(other); t.manager.select(id);
    await Promise.resolve(); b.resolve(record(other)); a.resolve(record(id, 1)); await Promise.resolve(); await Promise.resolve();
    expect(t.state.record?.reference.lifecycle_version).toBe(7);
    vi.mocked(t.api.list).mockResolvedValue({ records: [{ ...record(), namespace_id: other }] }); await t.manager.list();
    expect(t.state.records).toEqual([]); expect(t.state.listError).toBeTruthy();
    const late = deferred<NoteRecord>(); vi.mocked(t.api.read).mockReturnValue(late.promise); const check = t.manager.check(); t.manager.dispose(); late.resolve(record(id, 9)); await check;
    expect(t.state.record).toBeNull(); expect(t.api.admit).not.toHaveBeenCalled(); expect(t.api.promote).not.toHaveBeenCalled();
  });
  it("refusal clears protected metadata/body and fences an overlapping late write without claiming rollback", async () => {
    const post = deferred<NoteRecord>(); const t = setup({ admit: vi.fn().mockReturnValue(post.promise) });
    await t.manager.load(); t.manager.freeze(body); const pending = t.manager.submit();
    vi.mocked(t.api.list).mockRejectedValue(new ApiError("sensitive", 403)); await t.manager.list();
    expect(t.state.frozen).toBeNull(); expect(t.state.profile).toBeNull(); expect(t.state.intakeUnknown).toBe(true);
    post.resolve(record()); await pending; expect(t.state.record).toBeNull(); expect(t.state.replayAvailable).toBe(false); expect(t.api.admit).toHaveBeenCalledTimes(1);
  });
  it("reload/remount only reads metadata; revoked identical replay refuses without replacing UUID", async () => {
    const t = setup({ admit: vi.fn().mockRejectedValueOnce(new Error()).mockRejectedValueOnce(new ApiError("secret", 409, "revoked")), read: vi.fn().mockResolvedValue(record(id, 3, "revoked")) });
    await t.manager.load(); t.manager.freeze(body); await t.manager.submit(); await t.manager.replay();
    t.manager.select(id); await t.manager.check();
    expect(t.state.intakeUnknown).toBe(true); expect(t.state.record?.lifecycle).toBe("revoked");
    expect(t.state.message).toContain("revoked tombstone"); expect(t.api.promote).not.toHaveBeenCalled();
    expect(vi.mocked(t.api.admit).mock.calls.map(([v]) => v.request_id)).toEqual([other, other]); t.manager.dispose();
    const fresh = setup(); fresh.manager.select(id); await fresh.manager.load(); expect(fresh.state.record?.reference.record_id).toBe(id); expect(fresh.state.replayAvailable).toBe(false); expect(fresh.api.admit).not.toHaveBeenCalled();
  });
  it("resets finite cursor on exact filter, deduplicates identities and rejects stale/foreign pages", async () => {
    const late = deferred<{ records: NoteRecord[]; next_cursor: string | null }>();
    const t = setup({ list: vi.fn().mockResolvedValueOnce({ records: [record()], next_cursor: "next" }).mockReturnValueOnce(late.promise).mockResolvedValueOnce({ records: [record(other)], next_cursor: null }) });
    await t.manager.load(); const old = t.manager.list(true); const current = t.manager.list(false, "key"); await current;
    late.resolve({ records: [record(id, 2)], next_cursor: null }); await old;
    expect(t.state.records.map((r) => r.reference.record_id)).toEqual([other]);
    expect(t.api.list).toHaveBeenLastCalledWith(expect.objectContaining({ sourceKey: "key", cursor: undefined }));
  });
});

it("a full configured-profile change clears the draft/replay binding and cannot retarget an old intake", async () => {
  const t = setup({ admit: vi.fn().mockRejectedValue(new Error()) });
  await t.manager.load(); t.manager.freeze(body); await t.manager.submit();
  vi.mocked(t.api.profile).mockResolvedValue({ ...profile, policy_revision: "changed" });
  await t.manager.load(); expect(t.state.authorityEpoch).toBe(1); expect(t.state.frozen).toBeNull();
  expect(t.state.intakeUnknown).toBe(true); await t.manager.replay(); await t.manager.submit();
  t.manager.freeze({ ...body, request_id: id }); await t.manager.submit(); expect(t.api.admit).toHaveBeenCalledTimes(1);
});

it.each([{ modes: ["manage"] }, { modes: ["manage", "new"] }])("fences a late intake across full mode focus %j without changing selection, applied filter or issuing another POST", async ({ modes }) => {
  const pending = deferred<NoteRecord>(); const t = setup({ admit: vi.fn().mockReturnValue(pending.promise) });
  await t.manager.load(); t.manager.select("new"); t.manager.freeze(body); const posting = t.manager.submit();
  t.manager.select("manage"); await t.manager.list(false, "newer-filter");
  for (const mode of modes.slice(1)) t.manager.select(mode);
  const reads = vi.mocked(t.api.list).mock.calls.length;
  pending.resolve(record()); await posting;
  expect(t.state.selected).toBeNull(); expect(t.state.record).toBeNull(); expect(t.state.records).toEqual([]);
  expect(t.state.filter).toBe("newer-filter"); expect(t.state.frozen).toBeNull(); expect(t.state.intakeUnknown).toBe(false);
  expect(t.state.message).not.toContain(id); expect(t.api.list).toHaveBeenCalledTimes(reads); expect(t.api.admit).toHaveBeenCalledExactlyOnceWith(body);
});
it("a late lifecycle response reconciles its own attempt without changing another focus or applied filter", async () => {
  const pending = deferred<NoteRecord>(); const t = setup({ promote: vi.fn().mockReturnValue(pending.promise) });
  await t.manager.load(); t.manager.select(id); await t.manager.check(); const posting = t.manager.transition("promote", t.state.record!);
  t.manager.select("manage"); await t.manager.list(false, "newer-filter"); const reads = vi.mocked(t.api.list).mock.calls.length;
  pending.resolve(record(id, 2, "promoted")); await posting;
  expect(t.state.selected).toBeNull(); expect(t.state.record).toBeNull(); expect(t.state.filter).toBe("newer-filter");
  expect(t.state.transitionUnknown).toBeNull(); expect(t.api.list).toHaveBeenCalledTimes(reads); expect(t.api.promote).toHaveBeenCalledExactlyOnceWith(id, { expected_version: 1 });
});

it("explains the actual Archive request_conflict code and closes unknown codes/details", () => {
  expect(safeNoteFailure(new ApiError("sensitive detail", 409, "request_conflict"))).toBe("The intake identity conflicts with retained input.");
  expect(safeNoteFailure(new ApiError("sensitive detail", 409, "unrecognized_sensitive_code"))).toBe("The protected request failed (409).");
});

it("routes recall separately while preserving management-only draft departure recognition", async () => {
  const { notesSelection, notesFocusSelection, notesHref } = await import("./notes");
  expect(notesFocusSelection("recall")).toBe("recall"); expect(notesHref("recall")).toBe("/bridge?notes=recall");
  expect(notesSelection("recall")).toBeNull();
  for (const value of ["manage", "new", id]) expect(notesFocusSelection(value)).toBe(notesSelection(value));
  for (const value of ["Recall", "recall ", "unknown", null]) expect(notesFocusSelection(value)).toBeNull();
});

it("serializes preparation with intake/promote/revoke while leaving metadata reads available", async () => {
  const t = setup(); await t.manager.load(); t.manager.select(id); await t.manager.check();
  t.manager.freeze(body); t.manager.setPreparationBusy(true);
  await t.manager.submit(); await t.manager.transition("promote", t.state.record!); await t.manager.transition("revoke", t.state.record!);
  expect(t.api.admit).not.toHaveBeenCalled(); expect(t.api.promote).not.toHaveBeenCalled(); expect(t.api.revoke).not.toHaveBeenCalled();
  await t.manager.list(); await t.manager.check(); expect(t.state.record).toBeTruthy();
  t.manager.setPreparationBusy(false); await t.manager.transition("promote", t.state.record!); expect(t.api.promote).toHaveBeenCalledTimes(1);
});
it("a captured current preparation refusal clears parent management and draft custody, while old focus/profile callbacks are inert", async () => {
  const t = setup(); await t.manager.load(); t.manager.select(id); await t.manager.check(); t.manager.freeze(body);
  const old = t.manager.capturePreparationRefusal(); t.manager.select(other); t.manager.select(id); await t.manager.check();
  old(new ApiError("private", 403)); expect(t.state.profile).not.toBeNull(); expect(t.state.frozen).not.toBeNull();
  const previousProfile = t.manager.capturePreparationRefusal(); vi.mocked(t.api.profile).mockResolvedValue({ ...profile, policy_revision: "new" }); await t.manager.load();
  previousProfile(new ApiError("private", 401)); expect(t.state.profile?.policy_revision).toBe("new");
  t.manager.freeze(body); const current = t.manager.capturePreparationRefusal(); current(new ApiError("private", 403));
  expect(t.state.profile).toBeNull(); expect(t.state.record).toBeNull(); expect(t.state.records).toEqual([]); expect(t.state.frozen).toBeNull(); expect(t.state.message).not.toContain("private");
  t.manager.dispose(); current(new ApiError("late", 401)); expect(t.state.record).toBeNull();
});
it("current preparation configuration authority remains current across same-note metadata and lifecycle reads", async () => {
  const t = setup(); await t.manager.load(); t.manager.select(id); await t.manager.check();
  const refusal = t.manager.capturePreparationRefusal(); vi.mocked(t.api.read).mockResolvedValue(record(id, 3, "revoked")); await t.manager.check();
  refusal(new ApiError("private", 403)); expect(t.state.profile).toBeNull(); expect(t.state.record).toBeNull();
});
