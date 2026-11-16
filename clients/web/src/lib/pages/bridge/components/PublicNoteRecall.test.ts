import { createHash, webcrypto } from "node:crypto";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { SemanticRecallRequest, SemanticRecallReceipt, SemanticRecallProjection } from "$lib/api/models";
const hooks = vi.hoisted(() => ({ before: [] as ((event: unknown) => void)[] }));
vi.mock("$app/navigation", () => ({ beforeNavigate: (fn: (event: unknown) => void) => { hooks.before.push(fn); } }));
vi.mock("$lib/api/client", () => ({ ApiError: class ApiError extends Error { constructor(message: string, public status?: number, public code?: string) { super(message); } },
  getArchiveProfile: vi.fn(), discoverArchiveGeneration: vi.fn(), recallArchiveSemanticNotes: vi.fn(), inspectArchiveSemanticRecall: vi.fn(), resolveArchiveSemanticRecall: vi.fn() }));
import * as api from "$lib/api/client";
import PublicNoteRecall from "./PublicNoteRecall.svelte";

const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const hash = (text: string) => createHash("sha256").update(text).digest("hex");
const profile = { profile: "local-public-notes@1" as const, namespace_id: id(1), owner_subject: { identity: "owner" }, policy_revision: "policy" };
const generation = { generation_id: id(2), manifest_digest: "a".repeat(64) };
const text = "<script>source</script>\nExact public source";
function receipt(body: SemanticRecallRequest): SemanticRecallReceipt {
  const queryDigest = hash(body.query);
  return { schema_version: 2, receipt_id: id(3), request_id: body.request_id, namespace_id: body.namespace_id,
    subject: profile.owner_subject, purpose: "archive:answer", profile: profile.profile, retrieval_policy: "postgres-exact-cosine@1",
    policy_revision: profile.policy_revision, query_digest: queryDigest, request_digest: "b".repeat(64), run_id: null,
    max_results: body.max_results, char_budget: body.char_budget, min_cosine: body.min_cosine, generation: body.generation,
    generation_version: 1, coverage: { promoted_notes: 3, eligible_notes: 2 }, omitted_for_budget: 1,
    selected: [{ reference: { record_id: id(10), revision_digest: "c".repeat(64), lifecycle_version: 1 },
      source_key: "public-source", source_revision: "r1", source_digest: hash(text), score: 0.8,
      projection_digest: hash(text), projected_chars: [...text].length, derivation_id: id(20), row_version: 1, vector_digest: "d".repeat(64) }],
    created_at: "2026-10-19T00:00:00Z", receipt_digest: "e".repeat(64), query_execution: { execution_id: id(30), grant_id: id(31),
      profile_digest: "f".repeat(64), operation: "embed_query", item_id: body.request_id, input_digest: queryDigest,
      rendered_digest: "1".repeat(64), tokens: 4, vector_digest: "2".repeat(64), receipt_digest: "3".repeat(64) } };
}
function projection(selected: SemanticRecallReceipt): SemanticRecallProjection { return { receipt: selected, items: [{ selection: selected.selected[0]!, text }] }; }
let selected: SemanticRecallReceipt;
beforeEach(() => {
  vi.clearAllMocks(); hooks.before = []; vi.stubGlobal("crypto", webcrypto);
  vi.mocked(api.getArchiveProfile).mockResolvedValue(profile); vi.mocked(api.discoverArchiveGeneration).mockResolvedValue(generation);
  vi.mocked(api.recallArchiveSemanticNotes).mockImplementation(async (body) => { selected = receipt(body); return { receipt: selected, current_query_execution: selected.query_execution }; });
  vi.mocked(api.inspectArchiveSemanticRecall).mockImplementation(async (body) => receipt(body));
  vi.mocked(api.resolveArchiveSemanticRecall).mockImplementation(async () => projection(selected));
});
afterEach(() => vi.unstubAllGlobals());
async function fill(query = " exact é\n ") {
  await fireEvent.input(screen.getByLabelText(/^Exact public query/), { target: { value: query } });
  await fireEvent.input(screen.getByLabelText(/^Minimum cosine similarity/), { target: { value: "0.25" } });
}
it("opening, typing and metadata refresh perform no semantic operation; threshold starts empty and errors receive focus", async () => {
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation");
  expect((screen.getByLabelText(/^Minimum cosine similarity/) as HTMLInputElement).value).toBe("");
  const query = screen.getByLabelText(/^Exact public query/); query.focus();
  await fireEvent.input(query, { target: { value: "private in-document draft" } });
  await fireEvent.click(screen.getByRole("button", { name: "Refresh metadata only" }));
  await screen.findByText("Configured profile and generation");
  expect((query as HTMLTextAreaElement).value).toBe("private in-document draft");
  expect(api.recallArchiveSemanticNotes).not.toHaveBeenCalled(); expect(api.inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(api.resolveArchiveSemanticRecall).not.toHaveBeenCalled();
  await fireEvent.submit(screen.getByRole("form", { name: "Semantic source query" }));
  expect(screen.getByRole("heading", { name: "Check source query" })).toBe(document.activeElement);
  expect(api.recallArchiveSemanticNotes).not.toHaveBeenCalled(); view.unmount();
});
it("one explicit form gesture loads escaped attributed sources, coverage and distinct times and focuses the result", async () => {
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation");
  await fill(); await fireEvent.submit(screen.getByRole("form", { name: "Semantic source query" }));
  await screen.findByText(text, { selector: "pre", normalizer: (value) => value });
  await waitFor(() => expect(screen.getByRole("heading", { name: "Selection and current sources" })).toBe(document.activeElement));
  expect(document.querySelector("script")).toBeNull(); expect(screen.getByRole("heading", { name: "public-source · r1" })).toBeTruthy();
  expect(screen.getByText(/Coverage at selection: 2 eligible \/ 3 promoted notes/)).toBeTruthy();
  expect(screen.getByText(/1 selected; 1 omitted/)).toBeTruthy(); expect(screen.getByText(/Partial derivation coverage/)).toBeTruthy();
  expect(screen.getByText(/Selection time \(server\): 2026-10-19T00:00:00Z/)).toBeTruthy();
  expect(api.recallArchiveSemanticNotes).toHaveBeenCalledTimes(1); expect(api.resolveArchiveSemanticRecall).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.recallArchiveSemanticNotes).mock.calls[0]![0].query).toBe(" exact é\n "); view.unmount();
});
it("lost query response needs explicit metadata Check and then a separate source-load gesture", async () => {
  vi.mocked(api.recallArchiveSemanticNotes).mockRejectedValue(new Error("private detail"));
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation");
  await fill("public question"); await fireEvent.submit(screen.getByRole("form", { name: "Semantic source query" }));
  await screen.findByText(/Query outcome unknown/);
  expect(api.inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(api.resolveArchiveSemanticRecall).not.toHaveBeenCalled();
  vi.mocked(api.inspectArchiveSemanticRecall).mockResolvedValueOnce(null);
  await fireEvent.click(screen.getByRole("button", { name: "Check exact request metadata only" })); await screen.findByText(/No receipt was observed/);
  expect(api.recallArchiveSemanticNotes).toHaveBeenCalledTimes(1);
  await fireEvent.click(screen.getByRole("button", { name: "Check exact request metadata only" })); await screen.findByText(/Historical selection recovered/);
  expect(screen.queryByText(text, { selector: "pre", normalizer: (value) => value })).toBeNull(); expect(api.resolveArchiveSemanticRecall).not.toHaveBeenCalled();
  const body = vi.mocked(api.recallArchiveSemanticNotes).mock.calls[0]![0]; selected = receipt(body);
  expect(vi.mocked(api.inspectArchiveSemanticRecall).mock.calls.every(([input]) => JSON.stringify(input) === JSON.stringify(body))).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Load exact current sources" })); await screen.findByText(text, { selector: "pre", normalizer: (value) => value });
  expect(api.recallArchiveSemanticNotes).toHaveBeenCalledTimes(1); expect(screen.queryByText("private detail")).toBeNull(); view.unmount();
});
it("authority refusal clears query and sources, closes controls and does not display server detail", async () => {
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation");
  await fill(); await fireEvent.submit(screen.getByRole("form", { name: "Semantic source query" })); await screen.findByText(text, { selector: "pre", normalizer: (value) => value });
  vi.mocked(api.resolveArchiveSemanticRecall).mockRejectedValue(new api.ApiError("private detail", 403));
  await fireEvent.click(screen.getByRole("button", { name: "Load exact current sources" })); await screen.findByText(/Current Archive authority was refused/);
  expect(screen.queryByText(text, { selector: "pre", normalizer: (value) => value })).toBeNull(); expect(screen.queryByRole("button", { name: "Load exact current sources" })).toBeNull();
  expect((screen.getByLabelText(/^Exact public query/) as HTMLTextAreaElement).value).toBe(""); expect(screen.queryByText("private detail")).toBeNull(); view.unmount();
});
it("draft departure and clear review keep keyboard focus and never claim server cancellation", async () => {
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation"); await fill("public question");
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false); const cancel = vi.fn();
  await act(() => hooks.before.forEach((hook) => hook({ willUnload: false, to: { url: new URL("http://localhost/bridge?notes=manage") }, cancel })));
  expect(cancel).toHaveBeenCalledTimes(1); expect(confirm).toHaveBeenCalledWith(expect.stringContaining("does not cancel model work")); confirm.mockRestore();
  await fireEvent.click(screen.getByRole("button", { name: "Review clearing query and sources" }));
  expect(screen.getByRole("heading", { name: "Clear transient query and sources?" })).toBe(document.activeElement);
  expect(api.recallArchiveSemanticNotes).not.toHaveBeenCalled(); await fireEvent.click(screen.getByRole("button", { name: "Keep query" }));
  expect(screen.getByRole("heading", { name: "Selection and current sources" })).toBe(document.activeElement); view.unmount();
});
it("a late query after unmount neither resolves sources nor steals a newer element's focus", async () => {
  let finish!: (value: Awaited<ReturnType<typeof api.recallArchiveSemanticNotes>>) => void;
  vi.mocked(api.recallArchiveSemanticNotes).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  const view = render(PublicNoteRecall); await screen.findByText("Configured profile and generation"); await fill("public question");
  await fireEvent.submit(screen.getByRole("form", { name: "Semantic source query" }));
  const body = vi.mocked(api.recallArchiveSemanticNotes).mock.calls[0]![0]; view.unmount();
  const button = document.createElement("button"); document.body.append(button); button.focus();
  await act(() => finish({ receipt: receipt(body), current_query_execution: null }));
  expect(api.resolveArchiveSemanticRecall).not.toHaveBeenCalled(); expect(document.activeElement).toBe(button); button.remove();
});

it.each([
  { name: "result limit", label: /^Maximum results/, value: "3", original: "5" },
  { name: "character budget", label: /^Source character budget/, value: "4000", original: "8000" }
])("warns before leaving or reloading a bounds-only draft: $name", async ({ label, value, original }) => {
  const view = render(PublicNoteRecall);
  await screen.findByText("Configured profile and generation");
  await fireEvent.input(screen.getByLabelText(label), { target: { value } });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const cancel = vi.fn();
  await act(() => hooks.before.forEach((hook) => hook({ willUnload: false,
    to: { url: new URL("http://localhost/bridge?notes=manage") }, cancel })));
  expect(cancel).toHaveBeenCalledOnce();
  const unload = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Review clearing query and sources" }));
  await fireEvent.click(screen.getByRole("button", { name: "Confirm clear" }));
  expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe(original);
  const clearedUnload = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(clearedUnload);
  expect(clearedUnload.defaultPrevented).toBe(false);
  expect(api.recallArchiveSemanticNotes).not.toHaveBeenCalled();
  expect(api.inspectArchiveSemanticRecall).not.toHaveBeenCalled();
  expect(api.resolveArchiveSemanticRecall).not.toHaveBeenCalled();
  confirm.mockRestore();
  view.unmount();
});
