import { createHash, webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "$lib/api/client";
import type { ArchiveProfile } from "$lib/api/models";
import type { SemanticRecallRequest, SemanticRecallReceipt, SemanticRecallProjection } from "$lib/api/models";
import { PublicSourceRecall, emptyRecallDraft, initialRecallState, validateRecallDraft, safeRecallFailure, type RecallState, type SemanticApi } from "./semantic";

const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const hash = (text: string) => createHash("sha256").update(text).digest("hex");
const profile: ArchiveProfile = { profile: "local-public-notes@1", namespace_id: id(1), owner_subject: { identity: "owner" }, policy_revision: "policy" };
const generation = { generation_id: id(2), manifest_digest: "a".repeat(64) };
const draft = { query: " exact é\r\n ", minCosine: "0.25", maxResults: "3", charBudget: "8000" };
const texts = ["<script>source</script>", "second public source"];
function receipt(body: SemanticRecallRequest): SemanticRecallReceipt {
  const queryDigest = hash(body.query);
  return { schema_version: 2, receipt_id: id(3), request_id: body.request_id, namespace_id: body.namespace_id,
    subject: profile.owner_subject, purpose: "archive:answer", profile: profile.profile, retrieval_policy: "postgres-exact-cosine@1",
    policy_revision: profile.policy_revision, query_digest: queryDigest, request_digest: "b".repeat(64), run_id: null,
    max_results: body.max_results, char_budget: body.char_budget, min_cosine: body.min_cosine, generation: body.generation,
    generation_version: 1, coverage: { promoted_notes: 4, eligible_notes: 3 }, omitted_for_budget: 1,
    selected: texts.map((text, i) => ({ reference: { record_id: id(10 + i), revision_digest: "c".repeat(64), lifecycle_version: 1 },
      source_key: `source-${i}`, source_revision: "r1", source_digest: hash(text), score: 0.9 - i / 10,
      projection_digest: hash(text), projected_chars: [...text].length, derivation_id: id(20 + i), row_version: 1, vector_digest: "d".repeat(64) })),
    created_at: "2026-10-19T00:00:00Z", receipt_digest: "e".repeat(64), query_execution: { execution_id: id(30), grant_id: id(31),
      profile_digest: "f".repeat(64), operation: "embed_query", item_id: body.request_id, input_digest: queryDigest,
      rendered_digest: "1".repeat(64), tokens: 4, vector_digest: "2".repeat(64), receipt_digest: "3".repeat(64) } };
}
function projection(value: SemanticRecallReceipt): SemanticRecallProjection {
  return { receipt: value, items: value.selected.map((selection, i) => ({ selection, text: texts[i]! })) };
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function setup(overrides: Partial<SemanticApi> = {}) {
  let selected: SemanticRecallReceipt;
  const api: SemanticApi = { profile: vi.fn().mockResolvedValue(profile), generation: vi.fn().mockResolvedValue(generation),
    recall: vi.fn().mockImplementation(async (body: SemanticRecallRequest) => { selected = receipt(body); return { receipt: selected, current_query_execution: selected.query_execution }; }),
    inspect: vi.fn().mockImplementation(async (body: SemanticRecallRequest) => receipt(body)),
    resolve: vi.fn().mockImplementation(async () => projection(selected)), ...overrides };
  let state: RecallState = initialRecallState(); const changed = vi.fn((next: RecallState) => { state = next; });
  const controller = new PublicSourceRecall(api, changed);
  return { api, controller, changed, get state() { return state; } };
}
beforeEach(() => vi.stubGlobal("crypto", webcrypto));
afterEach(() => vi.unstubAllGlobals());

it("requires a deliberate finite threshold and strict bounds without normalizing raw query", () => {
  expect(emptyRecallDraft().minCosine).toBe("");
  for (const threshold of ["", " ", "NaN", "Infinity", "-1.01", "1.01"]) expect(validateRecallDraft({ ...draft, minCosine: threshold })).not.toEqual([]);
  for (const threshold of ["-1", "0", "1"]) expect(validateRecallDraft({ ...draft, minCosine: threshold })).toEqual([]);
  for (const query of [" ", "\0", "\ud800", "x".repeat(2001)]) expect(validateRecallDraft({ ...draft, query })).not.toEqual([]);
  for (const change of [{ maxResults: "1.5" }, { maxResults: "21" }, { charBudget: "0" }, { charBudget: "32001" }]) expect(validateRecallDraft({ ...draft, ...change })).not.toEqual([]);
});
it("opens and refreshes metadata only; explicit query freezes numbers, raw text and UUID then resolves exact ordered sources", async () => {
  const t = setup(); await t.controller.load(); await t.controller.load();
  expect(t.api.recall).not.toHaveBeenCalled(); expect(t.api.resolve).not.toHaveBeenCalled();
  await t.controller.submit({ ...draft, minCosine: "" }); expect(t.api.recall).not.toHaveBeenCalled();
  await t.controller.submit(draft); const sent = vi.mocked(t.api.recall).mock.calls[0]![0];
  expect(sent).toEqual({ namespace_id: profile.namespace_id, generation, request_id: expect.any(String), query: draft.query, min_cosine: 0.25, max_results: 3, char_budget: 8000, run_id: null });
  expect(t.state.frozen).toEqual(sent); expect(t.state.frozen).not.toBe(sent);
  expect(t.api.resolve).toHaveBeenCalledExactlyOnceWith(id(3), { receipt_digest: "e".repeat(64) }, expect.any(AbortSignal));
  expect(t.state.projection?.items.map((item) => item.text)).toEqual(texts); expect(t.state.receipt?.coverage).toEqual({ promoted_notes: 4, eligible_notes: 3 });
  expect(t.state.receipt?.omitted_for_budget).toBe(1); expect(t.state.resolvedAt).not.toBe(t.state.receipt?.created_at);
  await t.controller.load(); expect(t.state.projection).toBeNull(); expect(t.api.recall).toHaveBeenCalledTimes(1); expect(t.api.resolve).toHaveBeenCalledTimes(1);
});
it("unknown outcome Check uses the exact frozen body; absence stays unknown and recovered metadata never auto-loads sources", async () => {
  const t = setup({ recall: vi.fn().mockRejectedValue(new Error("private detail")), inspect: vi.fn().mockResolvedValueOnce(null).mockImplementation(async (body: SemanticRecallRequest) => receipt(body)) });
  await t.controller.load(); await t.controller.submit(draft); const body = t.state.frozen!;
  expect(t.state.unknown).toBe(true); expect(t.state.message).not.toContain("private detail");
  await t.controller.check(); expect(t.state.unknown).toBe(true); expect(t.state.message).toContain("absence does not prove failure");
  await t.controller.check(); expect(t.state.unknown).toBe(false); expect(t.state.receipt).not.toBeNull(); expect(t.state.projection).toBeNull();
  expect(t.api.resolve).not.toHaveBeenCalled(); expect(vi.mocked(t.api.inspect).mock.calls.map(([input]) => input)).toEqual([body, body]);
  vi.mocked(t.api.resolve).mockResolvedValue(projection(t.state.receipt!)); await t.controller.resolve();
  expect(t.state.projection?.items).toHaveLength(2); expect(t.api.recall).toHaveBeenCalledTimes(1);
});
it.each(["policy", "owner", "generation"] as const)("configuration %s changes clear query/body/sources and late A→B→A query results cannot hydrate", async (change) => {
  const late = deferred<Awaited<ReturnType<SemanticApi["recall"]>>>(); const t = setup({ recall: vi.fn().mockReturnValue(late.promise) });
  await t.controller.load(); const pending = t.controller.submit(draft); const body = t.state.frozen!;
  if (change === "generation") vi.mocked(t.api.generation).mockResolvedValue({ ...generation, manifest_digest: "4".repeat(64) });
  else vi.mocked(t.api.profile).mockResolvedValue(change === "owner" ? { ...profile, owner_subject: { identity: "other" } } : { ...profile, policy_revision: "other" });
  await t.controller.load(); expect(t.state.frozen).toBeNull(); expect(t.state.authorityEpoch).toBe(1); expect(t.state.unknown).toBe(true);
  vi.mocked(t.api.profile).mockResolvedValue(profile); vi.mocked(t.api.generation).mockResolvedValue(generation); await t.controller.load();
  late.resolve({ receipt: receipt(body), current_query_execution: null }); await pending;
  expect(t.state.projection).toBeNull(); expect(t.state.receipt).toBeNull(); expect(t.api.resolve).not.toHaveBeenCalled();
});
it("refusal clears protected material and a later source response cannot repopulate it", async () => {
  const late = deferred<SemanticRecallProjection>(); const t = setup(); await t.controller.load(); await t.controller.submit(draft);
  vi.mocked(t.api.resolve).mockReturnValue(late.promise); const old = t.controller.resolve(); const selected = t.state.receipt!;
  vi.mocked(t.api.profile).mockRejectedValue(new ApiError("private detail", 403)); await t.controller.load();
  expect(t.state.profile).toBeNull(); expect(t.state.frozen).toBeNull(); expect(t.state.receipt).toBeNull(); expect(t.state.projection).toBeNull();
  late.resolve(projection(selected)); await old; expect(t.state.projection).toBeNull(); expect(t.state.message).not.toContain("private detail");
});
it("new configuration requests fence late metadata A→B→A independently of repeated identity", async () => {
  const a = deferred<ArchiveProfile>(), b = deferred<ArchiveProfile>(); const t = setup({ profile: vi.fn().mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise).mockResolvedValue(profile) });
  const first = t.controller.load(), second = t.controller.load(); await t.controller.load();
  b.resolve({ ...profile, policy_revision: "old B" }); a.resolve({ ...profile, policy_revision: "old A" }); await Promise.all([first, second]);
  expect(t.state.profile).toEqual(profile); expect(t.api.generation).toHaveBeenCalledTimes(1); expect(t.api.recall).not.toHaveBeenCalled();
});
it("malformed, swapped or stale source projection never exposes a partial body", async () => {
  for (const failure of ["digest", "order", "receipt"] as const) {
    const t = setup(); await t.controller.load();
    vi.mocked(t.api.resolve).mockImplementation(async () => {
      const value = projection(t.state.receipt!);
      if (failure === "digest") value.items[0]!.text = "different source";
      if (failure === "order") value.items.reverse();
      if (failure === "receipt") value.receipt = { ...value.receipt, receipt_digest: "5".repeat(64) };
      return value;
    });
    await t.controller.submit(draft); expect(t.state.projection).toBeNull(); expect(t.state.resolvedAt).toBeNull(); expect(t.state.receipt).not.toBeNull();
    expect(t.state.message).toContain("no source text is displayed"); t.controller.dispose();
  }
});
it("explicit discard permits a new UUID without pretending the earlier unknown query was cancelled", async () => {
  const t = setup({ recall: vi.fn().mockRejectedValue(new ApiError("private", 409, "embedding_unavailable")) });
  await t.controller.load(); await t.controller.submit(draft); const first = t.state.frozen!.request_id;
  await t.controller.submit(draft); expect(t.api.recall).toHaveBeenCalledTimes(1);
  t.controller.discard(); expect(t.state.unknown).toBe(true); expect(t.state.message).toContain("remains unknown");
  await t.controller.submit(draft); expect(t.state.frozen!.request_id).not.toBe(first); expect(t.api.recall).toHaveBeenCalledTimes(2);
});
it("disposal fences a pending query and never issues source resolution or another notification", async () => {
  const late = deferred<Awaited<ReturnType<SemanticApi["recall"]>>>(); const t = setup({ recall: vi.fn().mockReturnValue(late.promise) });
  await t.controller.load(); const pending = t.controller.submit(draft); const body = t.state.frozen!;
  t.controller.dispose(); const count = t.changed.mock.calls.length;
  late.resolve({ receipt: receipt(body), current_query_execution: null }); await pending;
  expect(t.changed).toHaveBeenCalledTimes(count); expect(t.api.resolve).not.toHaveBeenCalled();
  await t.controller.load(); await t.controller.check(); await t.controller.resolve(); expect(t.api.profile).toHaveBeenCalledTimes(1);
});

it.each([
  ["receipt_stale", "no longer resolves current sources"], ["source_integrity", "failed integrity checks"],
  ["generation_binding", "generation binding changed"], ["generation_missing", "not registered"],
  ["generation_retired", "retired"], ["embedding_unavailable", "embedding capability is unavailable"]
])("presents closed emitted refusal code %s without server detail", (code, expected) => {
  expect(safeRecallFailure(new ApiError("private source and query", 409, code))).toContain(expected);
  expect(safeRecallFailure(new ApiError("private source and query", 409, code))).not.toContain("private");
});
it("keeps unknown refusal codes closed and 404 separate from an empty eligible selection", () => {
  expect(safeRecallFailure(new ApiError("private", 404))).toContain("unavailable (404)");
  expect(safeRecallFailure(new ApiError("private", 409, "untrusted server value"))).toBe("The protected semantic request was refused (409).");
});

it("clears frozen query immediately when changed profile is observed even if generation discovery fails", async () => {
  const query = deferred<Awaited<ReturnType<SemanticApi["recall"]>>>(), metadata = deferred<typeof generation>();
  const t = setup({ recall: vi.fn().mockReturnValue(query.promise) }); await t.controller.load();
  const pending = t.controller.submit(draft); const body = t.state.frozen!;
  vi.mocked(t.api.profile).mockResolvedValue({ ...profile, policy_revision: "new policy" });
  vi.mocked(t.api.generation).mockReturnValue(metadata.promise); const refresh = t.controller.load();
  await Promise.resolve(); await Promise.resolve();
  expect(t.state.frozen).toBeNull(); expect(t.state.receipt).toBeNull(); expect(t.state.authorityEpoch).toBe(1);
  expect(t.state.unknown).toBe(true);
  metadata.reject(new Error("private discovery detail")); await refresh;
  expect(t.state.configuration).toBe("unavailable"); expect(t.state.frozen).toBeNull();
  vi.mocked(t.api.profile).mockResolvedValue(profile); vi.mocked(t.api.generation).mockResolvedValue(generation); await t.controller.load();
  query.resolve({ receipt: receipt(body), current_query_execution: null }); await pending;
  expect(t.state.receipt).toBeNull(); expect(t.state.projection).toBeNull(); expect(t.api.resolve).not.toHaveBeenCalled();
});

it.each([0, 2])("keeps an observed empty selection with %s eligible rows distinct from unavailable configuration", async (eligible) => {
  let selected: SemanticRecallReceipt;
  const t = setup({ recall: vi.fn().mockImplementation(async (body: SemanticRecallRequest) => {
    selected = { ...receipt(body), selected: [], omitted_for_budget: 0, coverage: { promoted_notes: 2, eligible_notes: eligible } };
    return { receipt: selected, current_query_execution: null };
  }), resolve: vi.fn().mockImplementation(async () => ({ receipt: selected, items: [] })) });
  await t.controller.load(); await t.controller.submit(draft);
  expect(t.state.configuration).toBe("configured"); expect(t.state.unknown).toBe(false);
  expect(t.state.receipt?.coverage.eligible_notes).toBe(eligible); expect(t.state.projection?.items).toEqual([]);
});
