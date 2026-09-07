import { act, render, screen } from "@testing-library/svelte";
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

const runSnapshot: OrbRunSnapshot = {
  schema_version: 1,
  snapshot_at: "2026-07-30T00:00:00Z",
  capture: "process_local",
  ledger_head_seq: 0,
  page_end_seq: 0,
  live_tail: "not_available",
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
    digest: "digest-a",
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

it("does not fetch an invalid Run navigation hint", async () => {
  page.url.href = `http://localhost/loom/bridge_chat/1?run=${"x".repeat(129)}`;
  vi.mocked(getLoomPatternRevision).mockResolvedValue(projection);
  const view = render(LoomView, { patternId: "bridge_chat", revision: "1" });
  expect(await screen.findByText(/Run context unavailable.*invalid/)).toBeTruthy();
  expect(getOrbRun).not.toHaveBeenCalled();
  view.unmount();
});
