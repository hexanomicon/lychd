import { act, fireEvent, render, screen } from "@testing-library/svelte";
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

function deferred<T>() {
  let reject!: (reason?: unknown) => void;
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept, decline) => {
    reject = decline;
    resolve = accept;
  });
  return { promise, reject, resolve };
}

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

  it("clears selected evidence when navigation changes Run identity", async () => {
    const nextRun = deferred<OrbRunSnapshot>();
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce(snapshot)
      .mockReturnValueOnce(nextRun.promise);
    const view = render(OrbView, { runId: "run-a" });
    const opener = await screen.findByRole("button", { name: /Step completed/ });

    await fireEvent.click(opener);
    expect(screen.getByText("Selected event")).toBeTruthy();

    await view.rerender({ runId: "run-b" });
    expect(screen.queryByText("Selected event")).toBeNull();
    expect(screen.queryByRole("button", { name: /Step completed/ })).toBeNull();

    await act(() => nextRun.reject(new Error("Run B unavailable")));
    expect(screen.getByRole("alert").textContent).toContain("Run B unavailable");
    expect(screen.queryByText("Selected event")).toBeNull();
    view.unmount();
  });

  it("retains same-Run evidence when refresh fails", async () => {
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce(snapshot)
      .mockRejectedValueOnce(new Error("Refresh unavailable"));
    const view = render(OrbView, { runId: "run-a" });

    expect(await screen.findByRole("button", { name: /Step completed/ })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Refresh unavailable");
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeTruthy();
    view.unmount();
  });
});

describe("Orb evidence pagination", () => {
  it("releases pagination ownership when navigation changes Run identity", async () => {
    const firstPage: OrbRunSnapshot = {
      ...snapshot,
      ledger_head_seq: 1,
      next_after_seq: 0,
      has_more: true
    };
    const stalePage = deferred<OrbRunSnapshot>();
    const runB: OrbRunSnapshot = {
      ...firstPage,
      run: { ...firstPage.run, run_id: "run-b" }
    };
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce(firstPage)
      .mockReturnValueOnce(stalePage.promise)
      .mockResolvedValueOnce(runB);
    const view = render(OrbView, { runId: "run-a" });

    await fireEvent.click(
      await screen.findByRole("button", { name: "Load more retained evidence" })
    );
    expect(screen.getByRole("button", { name: "Reading…" })).toBeTruthy();

    await view.rerender({ runId: "run-b" });

    const runBLoadMore = await screen.findByRole("button", {
      name: "Load more retained evidence"
    });
    expect((runBLoadMore as HTMLButtonElement).disabled).toBe(false);
    await act(() => stalePage.resolve(snapshot));
    expect((runBLoadMore as HTMLButtonElement).disabled).toBe(false);
    view.unmount();
  });

  it("retains loaded evidence and offers a local retry when load more fails", async () => {
    const firstPage: OrbRunSnapshot = {
      ...snapshot,
      ledger_head_seq: 1,
      next_after_seq: 0,
      has_more: true
    };
    const nextPage: OrbRunSnapshot = {
      ...snapshot,
      ledger_head_seq: 1,
      page_end_seq: 1,
      evidence: [
        {
          ...snapshot.evidence[0]!,
          event_id: "event-b",
          seq: 1,
          summary: "Second step completed",
          subject_key: "step-b"
        }
      ]
    };
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce(firstPage)
      .mockRejectedValueOnce(new Error("Next page unavailable"))
      .mockResolvedValueOnce(nextPage);
    const view = render(OrbView, { runId: "run-a" });

    expect(await screen.findByRole("button", { name: /Step completed/ })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Load more retained evidence" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Next page unavailable");
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();

    await fireEvent.click(
      screen.getByRole("button", { name: "Retry loading retained evidence" })
    );

    expect(await screen.findByRole("button", { name: /Second step completed/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    expect(screen.queryByText("Next page unavailable")).toBeNull();
    expect(getOrbRun).toHaveBeenNthCalledWith(2, "run-a", { afterSeq: 0, limit: 100 });
    expect(getOrbRun).toHaveBeenNthCalledWith(3, "run-a", { afterSeq: 0, limit: 100 });
    view.unmount();
  });

  it("refuses to merge a page returned for another Run", async () => {
    const firstPage: OrbRunSnapshot = {
      ...snapshot,
      ledger_head_seq: 1,
      next_after_seq: 0,
      has_more: true
    };
    const wrongPage: OrbRunSnapshot = {
      ...snapshot,
      run: { ...snapshot.run, run_id: "run-b" },
      evidence: [
        {
          ...snapshot.evidence[0]!,
          event_id: "event-b",
          seq: 1,
          summary: "Foreign step",
          subject_key: "step-b"
        }
      ]
    };
    vi.mocked(getOrbRun).mockResolvedValueOnce(firstPage).mockResolvedValueOnce(wrongPage);
    const view = render(OrbView, { runId: "run-a" });

    expect(await screen.findByRole("button", { name: /Step completed/ })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Load more retained evidence" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "The Orb returned evidence for another Run."
    );
    expect(screen.queryByRole("button", { name: /Foreign step/ })).toBeNull();
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    view.unmount();
  });
});
