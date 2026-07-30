import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { OrbRunSnapshot } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/orb/run-a") }
}));
vi.mock("$lib/api/client", () => ({
  getOrbRun: vi.fn()
}));

import { getOrbRun } from "$lib/api/client";
import OrbView from "./OrbView.svelte";

const snapshot: OrbRunSnapshot = {
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.mocked(getOrbRun).mockResolvedValue(snapshot);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Orb evidence focus", () => {
  it("returns focus to the evidence row after its inspector closes", async () => {
    const view = render(OrbView, { runId: "run-a" });
    const opener = await screen.findByRole("button", { name: /Step completed/ });

    await fireEvent.click(opener);
    const close = await screen.findByRole("button", { name: "Close" });
    expect(document.activeElement).not.toBe(opener);
    await fireEvent.click(close);

    expect(document.activeElement).toBe(opener);
    view.unmount();
  });
});
