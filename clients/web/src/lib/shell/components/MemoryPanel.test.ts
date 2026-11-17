import { webcrypto } from "node:crypto";
import { act, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createMemoryPanel } from "$lib/memory/panel.svelte";
import { createSeancesWorkspace } from "$lib/seances/workspace.svelte";
import type { BridgeTurnView } from "$lib/api/models";

const hooks = vi.hoisted(() => ({ before: [] as Array<(event: unknown) => void>, after: [] as Array<() => void> }));
vi.mock("$app/navigation", () => ({ beforeNavigate: (fn: (event: unknown) => void) => hooks.before.push(fn), afterNavigate: (fn: () => void) => hooks.after.push(fn) }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status?: number) { super(message); } },
  getArchiveProfile: vi.fn(), getArchiveBridgeDefault: vi.fn(), listArchiveNotes: vi.fn(), getArchiveNote: vi.fn(),
  admitArchiveNote: vi.fn(), promoteArchiveNote: vi.fn(), revokeArchiveNote: vi.fn(), discoverArchiveGeneration: vi.fn(),
  registerArchiveGeneration: vi.fn(), deriveArchiveNote: vi.fn(), inspectArchiveDerivation: vi.fn(),
  recallArchiveSemanticNotes: vi.fn(), inspectArchiveSemanticRecall: vi.fn(), resolveArchiveSemanticRecall: vi.fn(), getBridgeSnapshot: vi.fn()
}));
import * as api from "$lib/api/client";
import MemoryPanel from "./MemoryPanel.svelte";
const namespace = "00000000-0000-4000-8000-000000000001";
const turn: BridgeTurnView = { role: "user", content: "Exact private quotation\n é ", created_at: "2026-11-10T10:00:00Z", run_id: "run-a", state: "settled" };
function setup() {
  const state = createMemoryPanel();
  const work = createSeancesWorkspace(vi.fn());
  const opener = document.createElement("button"); opener.textContent = "Memory opener"; document.body.append(opener); opener.focus();
  state.open("working", opener);
  const component = render(MemoryPanel, { state, work, liveSession: "live-a" });
  return { state, work, opener, component };
}
beforeEach(() => {
  vi.clearAllMocks(); hooks.before = []; hooks.after = []; localStorage.clear(); vi.stubGlobal("crypto", webcrypto);
  vi.mocked(api.getArchiveProfile).mockResolvedValue({ profile: "local-public-notes@1", namespace_id: namespace, owner_subject: { identity: "owner" }, policy_revision: "policy" });
  vi.mocked(api.getArchiveBridgeDefault).mockResolvedValue({ current_default: null, requests_profile: null });
  vi.mocked(api.listArchiveNotes).mockResolvedValue({ records: [], next_cursor: null });
  vi.mocked(api.discoverArchiveGeneration).mockResolvedValue({ generation_id: "00000000-0000-4000-8000-000000000002", manifest_digest: "a".repeat(64) });
});
afterEach(() => { vi.unstubAllGlobals(); document.querySelectorAll("body > button").forEach((node) => node.remove()); });
it("opens tab-local material with no Archive request, groups exact sessions and keeps edits across close", async () => {
  const { state, work, opener, component } = setup();
  await act(() => { work.add("source-b", turn); work.add("source-c", { ...turn, content: "Another source" }); });
  const panel = screen.getByRole("dialog", { name: "Memory" });
  expect(within(panel).getByRole("region", { name: "Material from Session source-b" })).toBeTruthy();
  expect(within(panel).getByRole("region", { name: "Material from Session source-c" })).toBeTruthy();
  await fireEvent.input(screen.getAllByLabelText("Your note")[0]!, { target: { value: "Attributed working annotation" } });
  await fireEvent.click(screen.getByRole("button", { name: "Close Memory" }));
  expect(state.isOpen).toBe(false); expect(document.activeElement).toBe(opener);
  await act(() => state.open("working", opener));
  expect((screen.getAllByLabelText("Your note")[0] as HTMLTextAreaElement).value).toBe("Attributed working annotation");
  expect(work.continueInBridge).not.toHaveBeenCalled();
  expect(api.getArchiveProfile).not.toHaveBeenCalled(); expect(api.getBridgeSnapshot).not.toHaveBeenCalled();
  expect(localStorage.length).toBe(0); component.unmount();
});
it("mounts each Archive section once and retains hidden query/intake drafts without navigation interception", async () => {
  const { state, component } = setup();
  await fireEvent.click(screen.getByRole("button", { name: "Public notes" }));
  await screen.findByRole("heading", { name: "Configured profile" });
  await fireEvent.click(screen.getByRole("link", { name: "New public note" }));
  const text = screen.getByLabelText(/^Complete replacement text/);
  await fireEvent.input(text, { target: { value: "Explicit public source" } });
  await fireEvent.click(screen.getByRole("button", { name: "Recall" }));
  await screen.findByText("Configured profile and generation");
  await fireEvent.input(screen.getByLabelText(/^Exact public query/), { target: { value: "Public question" } });
  await act(() => { state.close(); hooks.after.forEach((fn) => fn()); });
  const confirm = vi.spyOn(window, "confirm"), cancel = vi.fn();
  await act(() => hooks.before.forEach((fn) => fn({ willUnload: false, to: { url: new URL("http://localhost/loom") }, cancel })));
  expect(confirm).not.toHaveBeenCalled(); expect(cancel).not.toHaveBeenCalled();
  await act(() => state.open("notes"));
  expect(screen.getByLabelText(/^Complete replacement text/)).toBe(text);
  expect((text as HTMLTextAreaElement).value).toBe("Explicit public source");
  await fireEvent.click(screen.getByRole("button", { name: "Recall" }));
  expect((screen.getByLabelText(/^Exact public query/) as HTMLTextAreaElement).value).toBe("Public question");
  expect(api.getArchiveProfile).toHaveBeenCalledTimes(2); expect(api.listArchiveNotes).toHaveBeenCalledTimes(1);
  expect(api.recallArchiveSemanticNotes).not.toHaveBeenCalled(); expect(api.admitArchiveNote).not.toHaveBeenCalled();
  const exit = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(exit); expect(exit.defaultPrevented).toBe(true);
  confirm.mockRestore(); component.unmount();
});
it("preserves an uncertain intake across presentation close and section changes without replay or focus theft", async () => {
  const { state, component, opener } = setup();
  await act(() => state.selectNotes("new"));
  await screen.findByRole("heading", { name: "Configured profile" });
  for (const [label, value] of [["Source key", "public-key"], ["Source revision", "r1"], ["Producer", "author"], ["Observation time with timezone", "2026-11-10T10:00:00Z"], ["Complete replacement text", "Public bytes"]]) await fireEvent.input(screen.getByLabelText(new RegExp(`^${label}`)), { target: { value } });
  await fireEvent.click(screen.getByLabelText("I confirm this is public material."));
  await fireEvent.submit(screen.getByRole("form", { name: "Public note intake" }));
  await screen.findByRole("heading", { name: "Frozen public intake" });
  let reject!: (cause: unknown) => void;
  vi.mocked(api.admitArchiveNote).mockReturnValue(new Promise((_, no) => { reject = no; }));
  await fireEvent.click(screen.getByRole("button", { name: "Submit candidate once" }));
  await act(() => state.close()); opener.focus();
  await act(() => reject(new Error("Connection lost")));
  expect(state.isOpen).toBe(false); expect(document.activeElement).toBe(opener);
  await act(() => state.open("working")); await act(() => state.open("notes"));
  expect(screen.getByRole("heading", { name: "Intake outcome unknown" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Replay identical intake" })).toBeTruthy();
  expect(api.admitArchiveNote).toHaveBeenCalledTimes(1); component.unmount();
});
it("dismisses with Escape, traps focus and returns to the exact opener", async () => {
  const { state, opener, component } = setup();
  await act(() => Promise.resolve());
  const close = screen.getByRole("button", { name: "Close Memory" }); expect(document.activeElement).toBe(close);
  await fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Recall" }));
  await fireEvent.keyDown(window, { key: "Escape" }); expect(state.isOpen).toBe(false); expect(document.activeElement).toBe(opener);
  component.unmount();
});

it.each(["new", "manage"])("preserves exact unknown preparation references when Recall tries %s without reviewed departure", async (next) => {
  const recordId = "00000000-0000-4000-8000-000000000003";
  const record = { namespace_id: namespace, reference: { record_id: recordId, revision_digest: "b".repeat(64), lifecycle_version: 2 }, source_key: "source-key", source_revision: "r1", source_digest: "c".repeat(64), producer: "author", observed_at: turn.created_at, created_at: turn.created_at, lifecycle: "promoted" as const };
  vi.mocked(api.getArchiveNote).mockResolvedValue(record);
  vi.mocked(api.deriveArchiveNote).mockRejectedValue(new Error("Lost preparation response"));
  const { state, component } = setup();
  await act(() => state.selectNotes(recordId));
  await screen.findByText("Configured generation");
  await fireEvent.click(screen.getByRole("button", { name: "Review preparation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Prepare this promoted revision" }));
  await screen.findByText(/Earlier preparation outcome remains unknown/);
  const frozen = screen.getByRole("button", { name: "Check frozen preparation reference" });
  await fireEvent.click(screen.getByRole("button", { name: "Recall" }));
  await screen.findByText("Configured profile and generation");
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  await fireEvent.click(screen.getByRole("link", { name: next === "new" ? "New public note" : "Manage public notes" }));
  expect(confirm).toHaveBeenCalledTimes(1); expect(state.notesSelection).toBe(recordId);
  expect(screen.getByRole("button", { name: "Check frozen preparation reference" })).toBe(frozen);
  expect(screen.getByText(/Earlier preparation outcome remains unknown/)).toBeTruthy();
  await act(() => { state.close(); });
  // The shell's legacy URL handler uses this same centralized selection entry.
  await act(() => { state.selectNotes(next); });
  expect(confirm).toHaveBeenCalledTimes(2); expect(state.notesSelection).toBe(recordId);
  expect(screen.getByRole("button", { name: "Check frozen preparation reference" })).toBe(frozen);
  expect(api.deriveArchiveNote).toHaveBeenCalledTimes(1);
  confirm.mockRestore(); component.unmount();
});

it("keeps Bridge quotations separate from an Archive authority refusal", async () => {
  const { state, work, component } = setup();
  await act(() => { work.add("source-b", turn); });
  vi.mocked(api.getArchiveProfile).mockRejectedValueOnce(new api.ApiError("Archive denied", 403));
  await act(() => state.selectNotes("manage"));
  await screen.findByText(/Public-note configuration is unavailable/);
  expect(work.materials.get("source-b")![0]!.source.content).toBe(turn.content);
  component.unmount();
});
