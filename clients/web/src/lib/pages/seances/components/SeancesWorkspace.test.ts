import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BridgeSnapshot } from "$lib/api/models";
vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status: number) { super(message); } },
  getBridgeSessions: vi.fn(), getBridgeSnapshot: vi.fn()
}));
import { ApiError, getBridgeSessions, getBridgeSnapshot } from "$lib/api/client";
import { createSeancesWorkspace, setSeancesWorkspace, materialCharacterLimit, materialLimit } from "$lib/pages/seances/state/workspace.svelte";
import SeancesWorkspace from "./SeancesWorkspace.svelte";

const created = "2026-11-06T10:00:00Z";
const summaries = [{ id: "a", title: "Alpha", created_at: created, pending_count: 0 }, { id: "b", title: "Beta", created_at: created, pending_count: 0 }];
function snapshot(id: string): BridgeSnapshot {
  return { sessions: summaries, session: { ...summaries.find((item) => item.id === id)!, turns: [{ role: "user", content: `Question ${id}`, run_id: `run-${id}`, state: "settled", created_at: created }] }, active_runs: [], pending_consents: [], pending_count: 0 };
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function setup(sessionId?: string) {
  const continueInBridge = vi.fn();
  const work = createSeancesWorkspace(continueInBridge);
  function Wrapper(...args: Parameters<typeof SeancesWorkspace>) { setSeancesWorkspace(work); return SeancesWorkspace(...args); }
  return { work, continueInBridge, component: render(Wrapper, { sessionId }) };
}
beforeEach(() => {
  vi.clearAllMocks(); localStorage.clear();
  vi.mocked(getBridgeSessions).mockResolvedValue({ sessions: summaries, next_cursor: null });
  vi.mocked(getBridgeSnapshot).mockImplementation(async (id) => snapshot(id!));
});

describe("Séances workspace", () => {
  it("reads only metadata for the catalogue and searches only loaded identities", async () => {
    setup();
    await screen.findByRole("link", { name: /Alpha/ });
    expect(getBridgeSnapshot).not.toHaveBeenCalled();
    await fireEvent.input(screen.getByLabelText("Find in loaded séances"), { target: { value: "Beta" } });
    expect(screen.queryByRole("link", { name: /Alpha/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Beta/ }).getAttribute("href")).toBe("/seances/b");
  });
  it("requires explicit continuation and stages source quotations without browser storage", async () => {
    const { work, continueInBridge } = setup("b");
    await screen.findByText("Question b");
    expect(continueInBridge).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
    expect(work.needsUnloadWarning).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Working material (1)" }));
    await fireEvent.change(screen.getByLabelText("Use as"), { target: { value: "Open question" } });
    await fireEvent.input(screen.getByLabelText("Your note"), { target: { value: "Follow this thread" } });
    expect(work.materials.get("b")?.[0]).toMatchObject({ kind: "Open question", note: "Follow this thread", source: { run_id: "run-b", content: "Question b" } });
    expect(localStorage.length).toBe(0);
    await fireEvent.click(screen.getByRole("button", { name: "Inspect source" }));
    expect(document.activeElement?.getAttribute("data-seance-source")).toContain("Question b");
    await fireEvent.click(screen.getByRole("button", { name: "Continue in Bridge" }));
    expect(continueInBridge).toHaveBeenCalledExactlyOnceWith("b");
  });
  it("rejects foreign snapshots without falling back or allowing continuation", async () => {
    vi.mocked(getBridgeSnapshot).mockResolvedValue(snapshot("a"));
    setup("b");
    await screen.findByRole("heading", { name: "Séance unavailable" });
    expect(screen.queryByText("Question a")).toBeNull();
    expect(screen.queryByRole("button", { name: "Continue in Bridge" })).toBeNull();
  });
  it("fences an old read after inspection changes and ignores its later refusal", async () => {
    const old = deferred<BridgeSnapshot>();
    vi.mocked(getBridgeSnapshot).mockImplementation((id) => id === "a" ? old.promise : Promise.resolve(snapshot("b")));
    const { component } = setup("a");
    await waitFor(() => expect(getBridgeSnapshot).toHaveBeenCalledWith("a"));
    await component.rerender({ sessionId: "b" });
    await screen.findByText("Question b");
    await act(() => old.reject(new Error("Old read denied")));
    expect(screen.getByText("Question b")).toBeTruthy();
    expect(screen.queryByText("Old read denied")).toBeNull();
  });
  it("clears protected quotation staging on a current refused refresh", async () => {
    const { work } = setup("b");
    await screen.findByText("Question b");
    await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
    vi.mocked(getBridgeSnapshot).mockRejectedValue(new ApiError("Access refused", 403));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh transcript" }));
    await screen.findByText("Access refused");
    expect(work.materials.has("b")).toBe(false);
    expect(screen.queryByText("Question b")).toBeNull();
    expect(screen.queryByRole("button", { name: "Export Markdown" })).toBeNull();
  });
  it("keeps absent source quotations distinguishable after a fresh authorized read", async () => {
    setup("b");
    await screen.findByText("Question b");
    await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
    const next = snapshot("b"); next.session!.turns = [];
    vi.mocked(getBridgeSnapshot).mockResolvedValue(next);
    await fireEvent.click(screen.getByRole("button", { name: "Refresh transcript" }));
    await screen.findByText("No retained turns yet");
    await fireEvent.click(screen.getByRole("button", { name: "Working material (1)" }));
    await fireEvent.click(screen.getByRole("button", { name: "Inspect source" }));
    expect(screen.getByText(/quotation is not present in this retained read/)).toBeTruthy();
  });
});

it("refuses oversized and excess document-local material without truncating it", () => {
  const work = createSeancesWorkspace(vi.fn());
  const turn = snapshot("a").session!.turns![0]!;
  expect(work.add("a", { ...turn, content: "x".repeat(materialCharacterLimit + 1) })).toContain("Nothing was added");
  expect(work.materials.size).toBe(0);
  for (let i = 0; i < materialLimit; i++) expect(work.add("a", { ...turn, content: `Quotation ${i}` })).toBeNull();
  expect(work.add("b", turn)).toContain("32 selections");
  const item = work.materials.get("a")![0]!;
  expect(work.update("a", item.id, { note: "x".repeat(materialCharacterLimit) })).toContain("note was not changed");
  expect(work.materials.get("a")![0]!.note).toBe("");
});

it("revokes catalogue metadata, inspected text and staging after a denied page read", async () => {
  vi.mocked(getBridgeSessions).mockResolvedValueOnce({ sessions: summaries, next_cursor: "older" }).mockRejectedValueOnce(new ApiError("Catalogue access refused", 403));
  const { work } = setup("b");
  await screen.findByText("Question b");
  await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Load more séances" }));
  await screen.findByText("Catalogue access refused");
  expect(screen.queryByRole("link", { name: /Alpha/ })).toBeNull();
  expect(screen.queryByText("Question b")).toBeNull();
  expect(work.materials.size).toBe(0);
});

it("fences an older successful catalogue page after an exact-session access refusal", async () => {
  const older = deferred<Awaited<ReturnType<typeof getBridgeSessions>>>();
  vi.mocked(getBridgeSessions).mockResolvedValueOnce({ sessions: summaries, next_cursor: "older" }).mockReturnValueOnce(older.promise);
  setup("b");
  await screen.findByText("Question b");
  await fireEvent.click(screen.getByRole("button", { name: "Load more séances" }));
  vi.mocked(getBridgeSnapshot).mockRejectedValue(new ApiError("Session access refused", 403));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh transcript" }));
  await screen.findByText("Session access refused");
  await act(() => older.resolve({ sessions: summaries, next_cursor: null }));
  expect(screen.queryByRole("link", { name: /Alpha/ })).toBeNull();
  expect(screen.queryByText("Question b")).toBeNull();
});

it.each([404, 500])("preserves user staging on a %i refresh while disabling source export until reread", async (status) => {
  const { work } = setup("b");
  await screen.findByText("Question b");
  await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
  vi.mocked(getBridgeSnapshot).mockRejectedValueOnce(new ApiError("Read unavailable", status));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh transcript" }));
  await screen.findByText("Read unavailable");
  expect(work.materials.get("b")).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Export Markdown" })).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry read" }));
  await screen.findByText("Question b");
  await fireEvent.click(screen.getByRole("button", { name: "Working material (1)" }));
  expect(screen.getByRole("button", { name: "Export Markdown" })).toBeTruthy();
});

it("copies reviewed material with exact source provenance", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  setup("b");
  await screen.findByText("Question b");
  await fireEvent.click(screen.getByRole("button", { name: "Select quotation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Working material (1)" }));
  await fireEvent.click(screen.getByRole("button", { name: "Copy material" }));
  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("/bridge/b?run=run-b"));
  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("> Question b"));
  expect(localStorage.length).toBe(0);
});

it("offers catalogue recovery after exact-session access denial and a successful retry", async () => {
  setup("b");
  await screen.findByText("Question b");
  vi.mocked(getBridgeSnapshot).mockRejectedValueOnce(new ApiError("Session access refused", 403));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh transcript" }));
  await screen.findByText("Session access refused");
  await fireEvent.click(screen.getByRole("button", { name: "Retry read" }));
  await screen.findByText("Question b");
  expect(screen.queryByRole("link", { name: /Alpha/ })).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry catalogue" }));
  expect(await screen.findByRole("link", { name: /Alpha/ })).toBeTruthy();
  expect(getBridgeSessions).toHaveBeenCalledTimes(2);
  expect(vi.mocked(getBridgeSessions).mock.calls[1]?.[0]).toBeUndefined();
});
