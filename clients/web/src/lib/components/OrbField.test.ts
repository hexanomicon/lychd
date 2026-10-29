import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { OrbEventEnvelope, OrbRunPage } from "$lib/api/models";
import { fixtureRun } from "$lib/orb/__fixtures__/snapshot";
vi.mock("$lib/api/client", () => ({ getOrbRun: vi.fn() }));
vi.mock("$lib/orb/live", async (original) => ({ ...await original<typeof import("$lib/orb/live")>(), getOrbCatalogue: vi.fn(), listenToOrb: vi.fn() }));
import { getOrbRun } from "$lib/api/client";
import { getOrbCatalogue, listenToOrb, type OrbLiveCallbacks } from "$lib/orb/live";
import OrbField from "./OrbField.svelte";
const page: OrbRunPage = { schema_version: 1, snapshot_at: "2026-09-22T00:00:00Z", capture: "process_local", next_cursor: null,
  runs: ["run-a", "run-b", "run-c", "run-d"].map((id) => fixtureRun(id).run) };
beforeEach(() => {
  vi.clearAllMocks(); vi.stubGlobal("EventSource", vi.fn());
  vi.mocked(getOrbCatalogue).mockResolvedValue(page);
  vi.mocked(getOrbRun).mockImplementation(async (id) => fixtureRun(id));
  vi.mocked(listenToOrb).mockImplementation(() => vi.fn());
});
afterEach(() => vi.unstubAllGlobals());

async function mountField() {
  const view = render(OrbField);
  await fireEvent.click(view.container.querySelector("details.run-list > summary")!);
  await fireEvent.click(view.container.querySelector("details.view-options > summary")!);
  await fireEvent.click(screen.getByRole("button", { name: "Show evidence" }));
  return view;
}

describe("Orb parallel Run field", () => {
  it("does not overwrite newer streamed metadata with an older in-flight catalogue read", async () => {
    const initial = fixtureRun();
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    let release!: (value: OrbRunPage) => void;
    vi.mocked(getOrbCatalogue).mockReturnValueOnce(new Promise((accept) => release = accept));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Runs" }));
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0,
      snapshot: { ...initial, run: { ...initial.run, status: "done" }, evidence: [] } }));
    const feed = screen.getByRole("complementary", { name: "Run evidence" });
    expect(within(feed).getByText("done")).toBeTruthy();
    await act(() => release({ ...page, runs: [initial.run] }));
    expect(within(feed).getByText("done")).toBeTruthy();
    expect(within(feed).queryByText("running")).toBeNull();
    view.unmount();
  });
  it("holds the observed graph during incoming metadata and evidence, then resumes LIVE", async () => {
    const initial = fixtureRun();
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    const feed = screen.getByRole("complementary", { name: "Run evidence" });
    await fireEvent.click(screen.getByRole("button", { name: "Pause live field" }));
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    const latest = { ...initial, run: { ...initial.run, status: "done" }, ledger_head_seq: 1,
      evidence: [{ ...initial.evidence[0]!, seq: 1, event_id: "new-event", summary: "Newly finished step", phase: "done" }] };
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 1, snapshot: latest }));
    expect(within(feed).getByText("done")).toBeTruthy();
    expect(within(feed).getByText("running")).toBeTruthy();
    expect(within(feed).queryByText("Newly finished step")).toBeNull();
    expect(within(feed).getByText("Inspect entered")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "LIVE" }));
    expect(within(feed).getByText("Newly finished step")).toBeTruthy();
    expect(within(feed).queryByText("Status at capture")).toBeNull();
    view.unmount();
  });
  it("separates historical evidence from an explicitly closed current subscription", async () => {
    const initial = fixtureRun();
    const stop = vi.fn();
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    vi.mocked(listenToOrb).mockReturnValue(stop);
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await fireEvent.click(screen.getByRole("button", { name: "Pause live field" }));
    await fireEvent.click(screen.getByRole("button", { name: "Close live lens" }));
    expect(stop).toHaveBeenCalledOnce();
    const feed = screen.getByRole("complementary", { name: "Run evidence" });
    expect(within(feed).getByText("Inspect entered")).toBeTruthy();
    expect(within(feed).getByText("lens closed")).toBeTruthy();
    expect(within(feed).getByRole("button", { name: "Open live lens" })).toBeTruthy();
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0, snapshot: initial }));
    expect(listenToOrb).toHaveBeenCalledOnce();
    await fireEvent.click(screen.getByRole("button", { name: "LIVE" }));
    expect(screen.queryByRole("list", { name: "Selected Run live records" })).toBeNull();
    view.unmount();
  });
  it("scrubs refused evidence from current, retained and pinned captures and fences late frames", async () => {
    const initial = fixtureRun();
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await fireEvent.click(screen.getByRole("button", { name: "Pause live field" }));
    vi.mocked(getOrbRun).mockRejectedValueOnce(Object.assign(new Error("Evidence refused"), { status: 403 }));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh lens" }));
    await screen.findByText("Evidence refused");
    expect(screen.queryByText("Inspect entered")).toBeNull();
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0, snapshot: initial }));
    await fireEvent.click(screen.getByRole("button", { name: "LIVE" }));
    expect(screen.queryByText("Inspect entered")).toBeNull();
    view.unmount();
  });
  it("fences an older catalogue response after a concurrent Run read refuses authority", async () => {
    const initial = fixtureRun();
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    let release!: (value: OrbRunPage) => void;
    vi.mocked(getOrbCatalogue).mockReturnValueOnce(new Promise((accept) => release = accept));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Runs" }));
    vi.mocked(getOrbRun).mockRejectedValueOnce(Object.assign(new Error("Authority expired"), { status: 401 }));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh lens" }));
    await screen.findByText("Authority expired");
    await act(() => release({ ...page, runs: [fixtureRun("stale-private-run").run] }));
    expect(screen.queryByText("stale-private-run")).toBeNull();
    expect(screen.queryByText("Inspect entered")).toBeNull();
    expect(screen.getByRole("button", { name: "Refresh Runs" }).hasAttribute("disabled")).toBe(false);
    view.unmount();
  });
  it("groups native waiting states without dropping their exact status", async () => {
    const initial = fixtureRun();
    initial.run.status = "awaiting_consent";
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    vi.mocked(getOrbRun).mockResolvedValue(initial);
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    await fireEvent.change(screen.getByRole("combobox", { name: "Run status filter" }), { target: { value: "waiting" } });
    const list = within(view.container.querySelector("details.run-list")!);
    expect(list.getByText("run-a")).toBeTruthy();
    expect(list.getByText("awaiting_consent")).toBeTruthy();
    view.unmount();
  });
  it("waits for initial lenses before mounting the graph, then retains it across refresh", async () => {
    let release!: (value: ReturnType<typeof fixtureRun>) => void;
    const pending = new Promise<ReturnType<typeof fixtureRun>>((accept) => release = accept);
    vi.mocked(getOrbRun).mockImplementation((id) => id === "run-a" ? pending : Promise.resolve(fixtureRun(id)));
    const view = await mountField();
    await waitFor(() => expect(getOrbRun).toHaveBeenCalledTimes(3));
    expect(screen.queryByRole("region", { name: "Parallel Run workflow field" })).toBeNull();
    await act(() => release(fixtureRun()));
    const graph = await screen.findByRole("region", { name: "Parallel Run workflow field" });
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Runs" }));
    await waitFor(() => expect(getOrbCatalogue).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("region", { name: "Parallel Run workflow field" })).toBe(graph);
    view.unmount();
  });
  it("opens three exact live lenses and requires an explicit close before another", async () => {
    const stops = new Map<string, ReturnType<typeof vi.fn>>();
    vi.mocked(listenToOrb).mockImplementation((id) => { const stop = vi.fn(); stops.set(id, stop); return stop; });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    expect(vi.mocked(listenToOrb).mock.calls.map(([id]) => id)).toEqual(["run-a", "run-b", "run-c"]);
    await fireEvent.click(screen.getByRole("button", { name: "Unfold Run" }));
    expect(screen.getByText(/Three live Run lenses are open/)).toBeTruthy();
    expect(getOrbRun).toHaveBeenCalledTimes(3);
    await fireEvent.click(screen.getAllByRole("button", { name: "Close lens" })[0]!);
    expect(stops.get("run-a")).toHaveBeenCalledOnce();
    const rowD = screen.getAllByText("run-d").find((element) => element.tagName === "CODE")!.closest("li")!;
    await fireEvent.click(within(rowD).getByRole("button", { name: "Unfold Run" }));
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(4));
    view.unmount();
    expect(stops.get("run-b")).toHaveBeenCalledOnce(); expect(stops.get("run-c")).toHaveBeenCalledOnce(); expect(stops.get("run-d")).toHaveBeenCalledOnce();
  });
  it("keeps all lenses closed after an explicit close and catalogue refresh", async () => {
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    for (const button of screen.getAllByRole("button", { name: "Close lens" })) await fireEvent.click(button);
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Runs" }));
    await waitFor(() => expect(getOrbCatalogue).toHaveBeenCalledTimes(2));
    expect(listenToOrb).toHaveBeenCalledTimes(3);
    expect(screen.queryAllByRole("button", { name: "Close lens" })).toHaveLength(0);
    view.unmount();
  });
  it("keeps an open older lens when refreshing the newest catalogue page", async () => {
    const close = vi.fn();
    vi.mocked(listenToOrb).mockReturnValue(close);
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [fixtureRun("run-new").run] });
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Runs" }));
    await within(view.container.querySelector("details.run-list")!).findByText("run-new");
    expect(close).not.toHaveBeenCalled();
    expect(screen.getAllByRole("button", { name: "Close lens" })).toHaveLength(3);
    expect(listenToOrb).toHaveBeenCalledTimes(3);
    view.unmount();
  });
  it("marks a retained lens closed after a failed refresh and reconnects on retry", async () => {
    const stop = vi.fn();
    vi.mocked(listenToOrb).mockImplementation((_id, _cursor, callbacks) => {
      callbacks.onConnection("connected");
      return stop;
    });
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    const feed = screen.getByRole("complementary", { name: "Run evidence" });
    expect(within(feed).getByText("connected")).toBeTruthy();
    vi.mocked(getOrbRun).mockRejectedValueOnce(new Error("Lens refresh failed"));
    await fireEvent.click(within(feed).getByRole("button", { name: "Refresh lens" }));
    await within(feed).findByText("Lens refresh failed");
    expect(stop).toHaveBeenCalledOnce();
    expect(within(feed).getByText("closed")).toBeTruthy();
    expect(within(feed).getByText("Inspect entered")).toBeTruthy();
    await fireEvent.click(within(feed).getByRole("button", { name: "Refresh lens" }));
    await within(feed).findByText("connected");
    expect(within(feed).queryByText("Lens refresh failed")).toBeNull();
    view.unmount();
  });
  it("preserves unloaded retained history through a metadata-only live frame", async () => {
    const initial = fixtureRun();
    initial.evidence = Array.from({ length: 100 }, (_, seq) => ({ ...initial.evidence[0]!, seq, event_id: `event-${seq}` }));
    Object.assign(initial, { ledger_head_seq: 149, page_end_seq: 99, next_after_seq: 99, has_more: true });
    vi.mocked(getOrbCatalogue).mockResolvedValue({ ...page, runs: [initial.run] });
    vi.mocked(getOrbRun).mockResolvedValue(initial);
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    expect(screen.getByText(/More retained history exists outside this lens/)).toBeTruthy();
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 149, cursor: 149,
      snapshot: { ...initial, evidence: [], page_end_seq: null, next_after_seq: null, has_more: false } }));
    expect(screen.getByText(/More retained history exists outside this lens/)).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "Selected Run live records" })).getAllByRole("listitem")).toHaveLength(100);
    view.unmount();
  });
  it("keeps a fresh continuation cursor when automatic refresh discovers a new page", async () => {
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    const original = page.runs.slice(0, 3);
    vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, runs: original });
    const view = await mountField();
    try {
      await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
      expect(screen.queryByRole("button", { name: "Load more retained Runs" })).toBeNull();
      vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, next_cursor: "older-new-runs",
        runs: Array.from({ length: 20 }, (_, index) => fixtureRun(`new-${index}`).run) });
      await act(() => document.dispatchEvent(new Event("visibilitychange")));
      const more = await screen.findByRole("button", { name: "Load more retained Runs" });
      vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, runs: [fixtureRun("new-missed").run, ...original] });
      await fireEvent.click(more);
      await waitFor(() => expect(getOrbCatalogue).toHaveBeenLastCalledWith("older-new-runs", expect.any(AbortSignal)));
      const list = within(view.container.querySelector<HTMLDetailsElement>("details.run-list")!);
      await list.findByText("new-missed");
      expect(list.getAllByRole("listitem")).toHaveLength(24);
      expect(listenToOrb).toHaveBeenCalledTimes(3);
    } finally { view.unmount(); visibility.mockRestore(); }
  });
  it("preserves pagination progress when the refreshed page overlaps the loaded catalogue", async () => {
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, next_cursor: "page-two" });
    const view = await mountField();
    try {
      await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
      vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, runs: [fixtureRun("older").run], next_cursor: "page-three" });
      await fireEvent.click(screen.getByRole("button", { name: "Load more retained Runs" }));
      await within(view.container.querySelector("details.run-list")!).findByText("older");
      vi.mocked(getOrbCatalogue).mockResolvedValueOnce({ ...page, next_cursor: "page-two" });
      await act(() => document.dispatchEvent(new Event("visibilitychange")));
      await waitFor(() => expect(getOrbCatalogue).toHaveBeenCalledTimes(3));
      await fireEvent.click(screen.getByRole("button", { name: "Load more retained Runs" }));
      await waitFor(() => expect(getOrbCatalogue).toHaveBeenLastCalledWith("page-three", expect.any(AbortSignal)));
    } finally { view.unmount(); visibility.mockRestore(); }
  });
  it("offers each semantic depth without fabricating a nested workflow", async () => {
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    expect(screen.getByRole("button", { name: "Follow selected Run" }).getAttribute("aria-pressed")).toBe("false");
    for (const name of ["Run groups", "Stations", "Occurrences", "Records"]) {
      const button = screen.getByRole("button", { name });
      await fireEvent.click(button); expect(button.getAttribute("aria-pressed")).toBe("true");
    }
    expect(screen.getByText(/Deeper subworkflow structure is unavailable/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Pause live field" }));
    await fireEvent.click(screen.getByRole("button", { name: "Follow selected Run" }));
    expect(screen.getByRole("button", { name: "LIVE" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Pause following" }).getAttribute("aria-pressed")).toBe("true");
    view.unmount();
  });
  it("bounds a selected live lens and fences callbacks after closing it", async () => {
    const view = await mountField();
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(3));
    const cb = vi.mocked(listenToOrb).mock.calls[0]![2] as OrbLiveCallbacks;
    const snapshot = fixtureRun();
    const frame: OrbEventEnvelope = { schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 100,
      snapshot: { ...snapshot, ledger_head_seq: 100, evidence: Array.from({ length: 100 }, (_, i) => ({ ...snapshot.evidence[0]!, event_id: `live-${i + 1}`, seq: i + 1, summary: `New record ${i + 1}` })) } };
    await act(() => cb.onFrame(frame));
    const records = screen.getByRole("list", { name: "Selected Run live records" });
    expect(within(records).getAllByRole("listitem")).toHaveLength(100);
    expect(screen.getByText(/More retained history exists outside this lens/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Close live lens" }));
    await act(() => cb.onFrame(frame));
    expect(screen.queryByRole("list", { name: "Selected Run live records" })).toBeNull();
    view.unmount();
  });
});

it("polls only while visible, never overlaps catalogue reads, and stops on teardown", async () => {
  const warning = vi.spyOn(console, "warn");
  let duplicateUnmountWarning = false;
  let mounted = true;
  vi.useFakeTimers();
  const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  const empty = { ...page, runs: [] };
  let release!: (value: OrbRunPage) => void;
  const pending = new Promise<OrbRunPage>((accept) => release = accept);
  vi.mocked(getOrbCatalogue).mockResolvedValueOnce(empty).mockReturnValueOnce(pending).mockResolvedValue(empty);
  const view = await mountField();
  try {
    await act(() => Promise.resolve());
    expect(getOrbCatalogue).toHaveBeenCalledOnce();
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(getOrbCatalogue).toHaveBeenCalledTimes(2);
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(getOrbCatalogue).toHaveBeenCalledTimes(2);
    visibility.mockReturnValue("hidden");
    await act(() => release(empty));
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(getOrbCatalogue).toHaveBeenCalledTimes(2);
    visibility.mockReturnValue("visible");
    await act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(getOrbCatalogue).toHaveBeenCalledTimes(3);
    view.unmount(); mounted = false;
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(getOrbCatalogue).toHaveBeenCalledTimes(3);
  } finally {
    if (mounted) view.unmount();
    duplicateUnmountWarning = warning.mock.calls.some((args) => args.some((value) => String(value).includes("lifecycle_double_unmount")));
    warning.mockRestore(); visibility.mockRestore(); vi.useRealTimers();
  }
  expect(duplicateUnmountWarning).toBe(false);
});
