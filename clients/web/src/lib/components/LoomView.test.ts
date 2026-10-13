import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";

import type { LoomSummary, LoomView as LoomProjection, OrbRunSnapshot } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/loom") }
}));
vi.mock("$lib/api/client", () => ({
  getLoomCatalogue: vi.fn(),
  getLoomPatternRevision: vi.fn(),
  getOrbRun: vi.fn()
}));

import { page } from "$app/state";
import { goto } from "$app/navigation";
import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
import LoomView from "./LoomView.svelte";

const summary: LoomSummary = {
  active: true,
  default: true,
  description: "A test pattern.",
  detail_path: "/loom/bridge_chat/1",
  digest: "sha256:test",
  entry_node: "start",
  implementation_revision: "test",
  pattern_id: "bridge_chat",
  revision: "1",
  route_rank: 0,
  title: "Bridge chat",
  trigger_hint: "test"
};

const projection: LoomProjection = {
  checkpoint_schema: "test@1",
  description: summary.description,
  digest: summary.digest,
  edges: [],
  entry_node: summary.entry_node,
  implementation_revision: summary.implementation_revision,
  mermaid_source: "flowchart TD",
  nodes: [],
  pattern_id: summary.pattern_id,
  publication: "published",
  revision: summary.revision,
  schema_version: 1,
  title: summary.title,
  trigger_hint: summary.trigger_hint
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  page.url.href = "http://localhost/loom";
  vi.mocked(getLoomCatalogue).mockResolvedValue([summary]);
  vi.stubGlobal("matchMedia", vi.fn(() => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn()
  })));
  vi.stubGlobal("ResizeObserver", class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
});

it("does not navigate when a Pattern revision resolves after destroy", async () => {
  const revision = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockReturnValue(revision.promise);
  const view = render(LoomView);
  await act(async () => {
    await Promise.resolve();
  });
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();

  view.unmount();
  await act(() => revision.resolve(projection));

  expect(goto).not.toHaveBeenCalled();
});

it("inspects the exact revision requested by a deep link", async () => {
  const exactRevision = { ...projection, revision: "2", title: "Bridge chat v2" };
  vi.mocked(getLoomPatternRevision).mockResolvedValue(exactRevision);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "2" });

  expect(await screen.findByRole("heading", { name: "Bridge chat v2" })).toBeTruthy();
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  expect(getLoomPatternRevision).toHaveBeenCalledWith("bridge_chat", "2");
  expect(goto).not.toHaveBeenCalled();
  view.unmount();
});

it("explains when a deep-linked Pattern revision is unavailable", async () => {
  vi.mocked(getLoomPatternRevision).mockRejectedValue(
    new Error("No such Pattern revision is woven.")
  );
  const view = render(LoomView, { patternId: "bridge_chat", revision: "retired" });

  expect((await screen.findByRole("alert")).textContent).toContain(
    "No such Pattern revision is woven."
  );
  expect(getLoomPatternRevision).toHaveBeenCalledWith("bridge_chat", "retired");
  expect(goto).not.toHaveBeenCalled();
  view.unmount();
});

const runSnapshot: OrbRunSnapshot = {
  schema_version: 1,
  snapshot_at: "2026-07-30T00:00:00Z",
  capture: "process_local",
  ledger_head_seq: 0,
  page_end_seq: 0,
  live_tail: "ledger_poll",
  workflow: null,
  next_after_seq: null,
  has_more: false,
  known_omissions: [],
  delegated_jobs: [],
  gaps: [],
  evidence: [
    {
      event_id: "event-a",
      seq: 0,
      kind: "node",
      occurred_at: "2026-07-30T00:00:00Z",
      summary: "Step completed",
      capture: "process_local",
      nexus_path: null,
      occurrence_id: "occurrence-a",
      phase: "settled",
      subject_key: "step-a",
      transition_request_id: null
    }
  ],
  pattern: {
    pattern_id: "bridge_chat",
    revision: "1",
    digest: projection.digest,
    exact: true,
    loom_path: "/loom/bridge_chat/1"
  },
  run: {
    run_id: "run-a",
    session_id: "session-a",
    workflow_name: "bridge_chat",
    status: "done",
    created_at: "2026-07-30T00:00:00Z",
    started_at: "2026-07-30T00:00:00Z",
    finished_at: "2026-07-30T00:00:00Z",
    error_present: false,
    bridge_path: "/bridge/session-a"
  }
};


it("returns to the exact originating event after validating the Run and Pattern", async () => {
  page.url.href = "http://localhost/loom/bridge_chat/1?run=run-a&event=event-a";
  vi.mocked(getLoomPatternRevision).mockResolvedValue(projection);
  vi.mocked(getOrbRun).mockResolvedValue(runSnapshot);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect((await screen.findByRole("link", { name: "Return to Run in Orb →" })).getAttribute("href"))
    .toBe("/orb/run-a?event=event-a");
  expect(goto).not.toHaveBeenCalled();
  view.unmount();
});

it("reports mismatched Run context without offering a different Run", async () => {
  page.url.href = "http://localhost/loom/bridge_chat/1?run=run-b&event=event-a";
  vi.mocked(getLoomPatternRevision).mockResolvedValue(projection);
  vi.mocked(getOrbRun).mockResolvedValue(runSnapshot);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect(await screen.findByText(/Run context unavailable/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Return to Run in Orb →" })).toBeNull();
  expect(goto).not.toHaveBeenCalled();
  view.unmount();
});

it("refuses Run context when the displayed revision changed between reads", async () => {
  page.url.href = "http://localhost/loom/bridge_chat/1?run=run-a&event=event-a";
  vi.mocked(getLoomPatternRevision).mockResolvedValue({ ...projection, digest: "changed-digest" });
  vi.mocked(getOrbRun).mockResolvedValue(runSnapshot);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });

  expect(await screen.findByText(/Run context unavailable/)).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Bridge chat" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Return to Run in Orb →" })).toBeNull();
  expect(goto).not.toHaveBeenCalled();
  view.unmount();
});

it("does not fetch an invalid Run navigation hint", async () => {
  page.url.href = `http://localhost/loom/bridge_chat/1?run=${"x".repeat(129)}`;
  vi.mocked(getLoomPatternRevision).mockResolvedValue(projection);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect(await screen.findByText(/Run context unavailable.*invalid/)).toBeTruthy();
  expect(getOrbRun).not.toHaveBeenCalled();
  view.unmount();
});

const score: LoomProjection = {
  ...projection,
  nodes: [
    { key: "start", label: "Start", kind: "step" },
    { key: "compose", label: "Compose reply", kind: "step" },
    { key: "wait", label: "Await input", kind: "gate" },
    { key: "close", label: "Close", kind: "terminal" }
  ],
  edges: [
    { key: "start-compose", source: "start", target: "compose", relation: "permits" },
    { key: "compose-wait", source: "compose", target: "wait", relation: "permits" },
    { key: "wait-wait", source: "wait", target: "wait", relation: "permits" },
    { key: "wait-compose", source: "wait", target: "compose", relation: "permits" },
    { key: "compose-close", source: "compose", target: "close", relation: "permits" }
  ]
};

it("inspects declared successors and self-loops and returns focus to the selected station", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  await fireEvent.click(await screen.findByText("Graph outline", { exact: false, selector: "summary" }));
  const stations = screen.getByRole("list", { name: "Declared stations" });
  const opener = within(stations).getByRole("button", { name: "Inspect Await input (wait)" });
  await fireEvent.click(opener);

  const inspector = screen.getByRole("complementary", { name: "Selected station" });
  expect(document.activeElement).toBe(within(inspector).getByRole("heading", { name: "Await input" }));
  expect(opener.getAttribute("aria-pressed")).toBe("true");
  const incoming = within(inspector).getByRole("list", { name: "Incoming permissions" });
  const outgoing = within(inspector).getByRole("list", { name: "Outgoing permissions" });
  expect(within(incoming).getAllByRole("listitem")).toHaveLength(2);
  expect(within(outgoing).getAllByRole("listitem")).toHaveLength(2);
  expect(within(outgoing).getByText("Self-loop")).toBeTruthy();
  expect(within(outgoing).getByText("wait → compose")).toBeTruthy();
  expect(within(outgoing).getByText("wait → wait")).toBeTruthy();

  await fireEvent.click(within(outgoing).getByRole("button", { name: "Inspect Compose reply (compose)" }));
  expect(document.activeElement).toBe(within(inspector).getByRole("heading", { name: "Compose reply" }));
  await fireEvent.click(within(inspector).getByRole("button", { name: "← Back to selected station" }));
  expect(document.activeElement).toBe(within(stations).getByRole("button", { name: "Inspect Compose reply (compose)" }));
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  view.unmount();
});

it("makes the graph primary and preserves selection while folding the Pattern", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  const summary = await screen.findByText("Graph outline", { exact: false, selector: "summary" });
  expect(summary.parentElement?.hasAttribute("open")).toBe(false);
  expect(screen.getByRole("heading", { name: "Pattern graph" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Stations" }).getAttribute("aria-pressed")).toBe("true");
  await fireEvent.click(summary);
  const stations = screen.getByRole("list", { name: "Declared stations" });
  const opener = within(stations).getByRole("button", { name: "Inspect Await input (wait)" });
  await fireEvent.click(opener);
  await fireEvent.click(screen.getByRole("button", { name: "Whole Pattern" }));
  expect(screen.getByRole("button", { name: "Whole Pattern" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByText("Zoom in to reveal stations")).toBeTruthy();
  expect(opener.getAttribute("aria-pressed")).toBe("true");
  expect(within(screen.getByRole("complementary", { name: "Selected station" })).getByRole("heading", { name: "Await input" })).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Stations" }));
  expect(opener.getAttribute("aria-pressed")).toBe("true");
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  view.unmount();
});

it("selects stations on the canvas and returns focus to their canvas opener", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  const canvas = await screen.findByRole("region", { name: "Bridge chat Pattern graph" });
  const opener = await within(canvas).findByRole("button", { name: "Inspect Await input" });
  await fireEvent.click(opener);
  const inspector = screen.getByRole("complementary", { name: "Selected station" });
  expect(document.activeElement).toBe(within(inspector).getByRole("heading", { name: "Await input" }));
  expect(opener.getAttribute("aria-pressed")).toBe("true");
  await fireEvent.click(within(inspector).getByRole("button", { name: "← Back to selected station" }));
  expect(document.activeElement).toBe(opener);
  view.unmount();
});

it("opens the same graph outline by default on a narrow viewport", async () => {
  vi.mocked(window.matchMedia).mockReturnValue({
    matches: true,
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    addListener: vi.fn(), removeListener: vi.fn(),
    media: "(max-width: 48rem)", onchange: null, dispatchEvent: vi.fn()
  });
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  const stations = await screen.findByRole("list", { name: "Declared stations" });
  expect(stations.closest("details")?.open).toBe(true);
  expect(within(stations).getAllByRole("listitem").length).toBeGreaterThanOrEqual(score.nodes.length);
  view.unmount();
});

it("states absent outgoing permissions without inferring execution termination", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  await fireEvent.click(await screen.findByText("Graph outline", { exact: false, selector: "summary" }));
  const stations = screen.getByRole("list", { name: "Declared stations" });
  await fireEvent.click(within(stations).getByRole("button", { name: "Inspect Close (close)" }));
  const inspector = screen.getByRole("complementary", { name: "Selected station" });
  expect(within(inspector).getByText("No outgoing permission declared")).toBeTruthy();
  expect(within(inspector).queryByText(/completed|finished|execution ended/i)).toBeNull();
  view.unmount();
});

it("keeps loading, failed reads, and retry distinct", async () => {
  const pending = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockRejectedValueOnce(new Error("Registry unavailable")).mockReturnValueOnce(pending.promise);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect(screen.getByRole("status").textContent).toContain("Loading Pattern revision");
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Registry unavailable");
  await fireEvent.click(screen.getByRole("button", { name: "Retry reading Pattern" }));
  expect(screen.getByRole("status").textContent).toContain("Loading Pattern revision");
  await act(() => pending.resolve(score));
  expect(await screen.findByRole("heading", { name: "Bridge chat" })).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
  view.unmount();
});

it("distinguishes an empty registry from a revision with no declared stations", async () => {
  vi.mocked(getLoomCatalogue).mockResolvedValue([]);
  const empty = render(LoomView);
  expect(await screen.findByRole("heading", { name: "No Pattern revisions are registered" })).toBeTruthy();
  expect(getLoomPatternRevision).not.toHaveBeenCalled();
  empty.unmount();

  vi.mocked(getLoomCatalogue).mockResolvedValue([summary]);
  vi.mocked(getLoomPatternRevision).mockResolvedValue(projection);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect(await screen.findByText("No stations declared in this Pattern revision.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Bridge chat" })).toBeTruthy();
  view.unmount();
});

it("clears the previous station inspector while another exact revision is being read", async () => {
  const replacement = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockResolvedValueOnce(score).mockReturnValueOnce(replacement.promise);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  await fireEvent.click(await screen.findByText("Graph outline", { exact: false, selector: "summary" }));
  const stations = screen.getByRole("list", { name: "Declared stations" });
  await fireEvent.click(within(stations).getByRole("button", { name: "Inspect Await input (wait)" }));
  await view.rerender({ patternId: "bridge_chat", revision: "2" });
  expect(screen.queryByRole("complementary", { name: "Selected station" })).toBeNull();
  await act(() => replacement.resolve({ ...score, revision: "2" }));
  await waitFor(() => expect(screen.getByRole("complementary", { name: "Selected station" }).textContent).toContain("Start"));
  expect(screen.getByRole("button", { name: "Inspect Await input (wait)" }).getAttribute("aria-pressed")).toBe("false");
  view.unmount();
});

it("previews node meaning on hover and keyboard focus without changing the selected station", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  const node = await screen.findByRole("button", { name: "Inspect Await input" });
  const selectedBefore = screen.getByRole("complementary", { name: "Selected station" }).textContent;
  await fireEvent.pointerEnter(node);
  expect(await screen.findByRole("tooltip")).toHaveProperty("textContent", expect.stringContaining("Await input"));
  expect(screen.getByRole("complementary", { name: "Selected station" }).textContent).toBe(selectedBefore);
  await fireEvent.keyDown(node, { key: "Escape" });
  expect(screen.queryByRole("tooltip")).toBeNull();
  await fireEvent.focus(node);
  expect(await screen.findByRole("tooltip")).toBeTruthy();
  expect(node.getAttribute("aria-pressed")).toBe("false");
  view.unmount();
});
