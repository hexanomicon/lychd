import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { OrbRunSnapshot } from "$lib/api/models";
import { incompleteCreation } from "$lib/pages/orb/state/__fixtures__/creation";
import { coldPreferredRoute } from "$lib/pages/orb/state/__fixtures__/preference";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", async () => {
  const { SvelteURL } = await import("svelte/reactivity");
  return { page: { url: new SvelteURL("http://localhost/orb/run-a") } };
});
vi.mock("$lib/api/client", () => ({
  getAtlasReferences: vi.fn().mockResolvedValue([]),
  getArchiveRunRecall: vi.fn(),
  getOrbRun: vi.fn()
}));

import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { goto } from "$app/navigation";
import { getArchiveRunRecall, getOrbRun } from "$lib/api/client";
import OrbView from "./OrbView.svelte";
import { listenToOrb, type OrbLiveCallbacks } from "$lib/pages/orb/state/live";
vi.mock("$lib/pages/orb/state/live", () => ({ listenToOrb: vi.fn(() => vi.fn()) }));

const snapshot: OrbRunSnapshot = {
  schema_version: 1,
  workflow: null,
  snapshot_at: "2026-07-30T00:00:00Z",
  capture: "process_local",
  ledger_head_seq: 0,
  page_end_seq: 0,
  live_tail: "ledger_poll",
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
  vi.stubGlobal("EventSource", vi.fn());
  page.url.href = "http://localhost/orb/run-a";
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.mocked(getOrbRun).mockResolvedValue(snapshot);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Orb evidence focus", () => {
  it("links only a selected consent record to its exact Bridge request and origin event", async () => {
    page.url.search = "?event=event-consent";
    const record = { ...snapshot.evidence[0]!, event_id: "event-consent", kind: "consent", consent_id: "consent-old", summary: "Consent wait recorded." };
    vi.mocked(getOrbRun).mockResolvedValueOnce({ ...snapshot, evidence: [record] });
    const view = render(OrbView, { runId: "run-a" });
    const link = await screen.findByRole("link", { name: "Open exact consent in Bridge →" });
    expect(link.getAttribute("href")).toBe("/bridge/session-a?run=run-a&consent=consent-old&event=event-consent");
    expect(screen.getByText("Historical reference; current availability is checked in Bridge.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull();
    view.unmount();
  });

  it.each(["node", "consent"])("offers no consent destination for an unbound %s record", async (kind) => {
    page.url.search = "?event=event-a";
    vi.mocked(getOrbRun).mockResolvedValueOnce({ ...snapshot, evidence: [{ ...snapshot.evidence[0]!, kind,
      consent_id: kind === "node" ? "consent-forged" : null }] });
    const view = render(OrbView, { runId: "run-a" });
    await screen.findByRole("heading", { name: "Selected event" });
    expect(screen.queryByRole("link", { name: "Open exact consent in Bridge →" })).toBeNull();
    view.unmount();
  });

  it("discloses a linked job without hiding the Run coverage and ordered evidence", async () => {
    page.url.href = "http://localhost/orb/run-a?job=job-linked";
    const linked: OrbRunSnapshot = {
      ...snapshot,
      known_omissions: ["Older jobs are outside this bounded snapshot."],
      delegated_jobs: [{
        job_id: "job-linked", request_id: "request-linked", runtime: "reference", profile: "read", step_id: "step-a",
        status: "completed", output_present: false, artifact_count: 0, error_present: false,
        events: [], events_truncated: false
      }]
    };
    vi.mocked(getOrbRun).mockResolvedValue(linked);
    const view = render(OrbView, { runId: "run-a" });
    const coverage = await screen.findByRole("region", { name: "Evidence coverage" });
    const limits = screen.getByRole("region", { name: "Evidence limits" });
    const evidence = screen.getByRole("region", { name: "Ordered evidence" });
    const disclosure = view.container.querySelector<HTMLDetailsElement>("details.delegated-jobs")!;
    const job = view.container.querySelector("#delegated-job-job-linked");

    expect(coverage.compareDocumentPosition(limits) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(limits.compareDocumentPosition(evidence) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(evidence.compareDocumentPosition(disclosure) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(disclosure.open).toBe(true);
    await waitFor(() => expect(document.activeElement).toBe(job));
    expect(screen.getByText(/Job lifecycle sequences belong to each AgentJob/)).toBeTruthy();
    const reader = screen.getByRole("button", { name: /Step completed/ });
    reader.focus();
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0,
      snapshot: { ...linked, evidence: [] } }));
    expect(document.activeElement).toBe(reader);
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(getOrbRun).toHaveBeenCalledTimes(2));
    expect(document.activeElement).toBe(reader);
    vi.mocked(getOrbRun).mockResolvedValue({ ...linked, run: { ...linked.run, run_id: "run-b" } });
    await view.rerender({ runId: "run-b" });
    await waitFor(() => expect(document.activeElement).toBe(view.container.querySelector("#delegated-job-job-linked")));
    view.unmount();
  });

  it("keeps unselected job detail closed so its volume cannot precede the evidence", async () => {
    vi.mocked(getOrbRun).mockResolvedValue({
      ...snapshot,
      delegated_jobs: [{
        job_id: "job-visible", request_id: "request-visible", runtime: "reference", profile: "read", step_id: "step-a",
        status: "completed", output_present: false, artifact_count: 0, error_present: false,
        events: [], events_truncated: false
      }]
    });
    const view = render(OrbView, { runId: "run-a" });
    await screen.findByRole("region", { name: "Ordered evidence" });
    expect(view.container.querySelector<HTMLDetailsElement>("details.delegated-jobs")?.open).toBe(false);
    view.unmount();
  });

  it("preserves the historical reader's focus when a previously missing job appears on refresh", async () => {
    page.url.href = "http://localhost/orb/run-a?event=event-a&job=job-later";
    const withJob: OrbRunSnapshot = {...snapshot, delegated_jobs: [{
      job_id: "job-later", request_id: "request-later", runtime: "reference", profile: "read", step_id: "step-a",
      status: "completed", output_present: false, artifact_count: 0, error_present: false,
      events: [], events_truncated: false
    }]};
    vi.mocked(getOrbRun).mockResolvedValueOnce(snapshot).mockResolvedValueOnce(withJob);
    const view = render(OrbView, {runId: "run-a"});
    expect(await screen.findByText("Selected historical evidence")).toBeTruthy();
    expect(screen.getByText(/The linked delegated job is not present/)).toBeTruthy();
    const refresh = screen.getByRole("button", {name: "Refresh"});
    refresh.focus();
    await fireEvent.click(refresh);
    await waitFor(() => expect(view.container.querySelector("#delegated-job-job-later")).toBeTruthy());
    expect(document.activeElement, "Refresh must not move focus to a newly available job").toBe(refresh);
    view.unmount();
  });

  it("keeps focus when pagination replaces and then restores the same linked job", async () => {
    page.url.href = "http://localhost/orb/run-a?event=event-a&job=job-a";
    const job = {
      job_id: "job-a", request_id: "request-a", runtime: "reference", profile: "read", step_id: "step-a",
      status: "completed", output_present: false, artifact_count: 0, error_present: false,
      events: [], events_truncated: false
    };
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce({ ...snapshot, has_more: true, next_after_seq: 0, delegated_jobs: [job] })
      .mockResolvedValueOnce({ ...snapshot, evidence: [], has_more: true, next_after_seq: 1 })
      .mockResolvedValueOnce({ ...snapshot, evidence: [], delegated_jobs: [job] });
    const view = render(OrbView, { runId: "run-a" });
    await waitFor(() => expect(document.activeElement?.id).toBe("delegated-job-job-a"));
    const refresh = screen.getByRole("button", { name: "Refresh" });
    refresh.focus();
    await fireEvent.click(screen.getByRole("button", { name: "Load more retained evidence" }));
    expect(await screen.findByText(/The linked delegated job is not present/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Load more retained evidence" }));
    await waitFor(() => expect(view.container.querySelector("#delegated-job-job-a")).toBeTruthy());
    expect(document.activeElement).toBe(refresh);
    view.unmount();
  });

  it("focuses explicit changed-job and changed-Run navigation after consuming an earlier hint", async () => {
    page.url.href = "http://localhost/orb/run-a?job=job-a";
    const jobs = ["job-a", "job-b"].map((jobId) => ({
      job_id: jobId, request_id: `request-${jobId}`, runtime: "reference", profile: "read", step_id: "step-a",
      status: "completed", output_present: false, artifact_count: 0, error_present: false,
      events: [], events_truncated: false
    }));
    const nextRun = deferred<OrbRunSnapshot>();
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce({ ...snapshot, delegated_jobs: jobs })
      .mockReturnValueOnce(nextRun.promise);
    const view = render(OrbView, { runId: "run-a" });
    await waitFor(() => expect(document.activeElement?.id).toBe("delegated-job-job-a"));
    const refresh = screen.getByRole("button", { name: "Refresh" });
    refresh.focus();
    await act(() => { page.url.searchParams.set("job", "job-b"); });
    expect(document.activeElement?.id).toBe("delegated-job-job-b");
    await act(() => { page.url.searchParams.set("job", "job-a"); });
    expect(document.activeElement?.id).toBe("delegated-job-job-a");
    await act(() => { page.url.searchParams.delete("job"); });
    refresh.focus();
    await act(() => { page.url.searchParams.set("job", "job-a"); });
    expect(document.activeElement?.id).toBe("delegated-job-job-a");
    await view.rerender({ runId: "run-b" });
    await act(() => nextRun.resolve({ ...snapshot, run: { ...snapshot.run, run_id: "run-b" }, delegated_jobs: jobs }));
    expect(document.activeElement?.id).toBe("delegated-job-job-a");
    view.unmount();
  });

  it("reports a linked delegated job absent from the selected Run snapshot", async () => {
    page.url.href = "http://localhost/orb/run-a?job=job-unavailable";
    vi.mocked(getOrbRun).mockResolvedValue({
      ...snapshot,
      delegated_jobs: [{
        job_id: "job-visible", request_id: "request-visible", runtime: "reference", profile: "read", step_id: "step-a",
        status: "completed", output_present: false, artifact_count: 0, error_present: false,
        events: [], events_truncated: false
      }]
    });
    const view = render(OrbView, { runId: "run-a" });
    expect(await screen.findByText(/The linked delegated job is not present in this Run's bounded snapshot/)).toBeTruthy();
    expect(view.container.querySelector(".delegated-job[aria-current='true']")).toBeNull();

    vi.mocked(getOrbRun).mockResolvedValue({
      ...snapshot,
      delegated_jobs: [{
        job_id: "job-unavailable", request_id: "request-selected", runtime: "reference", profile: "read", step_id: "step-a",
        status: "completed", output_present: false, artifact_count: 0, error_present: false,
        events: [], events_truncated: false
      }]
    });
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(view.container.querySelector(".delegated-job[aria-current='true']")?.id)
      .toBe("delegated-job-job-unavailable"));
    expect(screen.queryByText(/The linked delegated job is not present/)).toBeNull();
    view.unmount();
  });

  it("aborts a pending Orb read when its view is destroyed", async () => {
    const pending = deferred<OrbRunSnapshot>();
    let signal: AbortSignal | undefined;
    vi.mocked(getOrbRun).mockImplementationOnce((_runId, options) => {
      signal = options?.signal;
      return pending.promise;
    });
    const view = render(OrbView, { runId: "run-a" });
    await act(async () => {
      await Promise.resolve();
    });

    expect(signal?.aborted).toBe(false);
    view.unmount();

    expect(signal?.aborted).toBe(true);
    await act(() => pending.reject(new DOMException("Aborted", "AbortError")));
  });

  it("aborts a pending Orb read when the selected Run is cleared", async () => {
    const pending = deferred<OrbRunSnapshot>();
    let signal: AbortSignal | undefined;
    vi.mocked(getOrbRun).mockImplementationOnce((_runId, options) => {
      signal = options?.signal;
      return pending.promise;
    });
    const view = render(OrbView, { runId: "run-a" });
    await act(async () => {
      await Promise.resolve();
    });

    await view.rerender({ runId: undefined });

    expect(signal?.aborted).toBe(true);
    expect(screen.getByRole("heading", { name: "Orb" })).toBeTruthy();
    await act(() => pending.reject(new DOMException("Aborted", "AbortError")));
    view.unmount();
  });

  it("returns focus to the evidence row after its inspector closes", async () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })));
    const view = render(OrbView, { runId: "run-a" });
    const opener = await screen.findByRole("button", { name: /Step completed/ });

    await fireEvent.click(opener);
    const close = await screen.findByRole("button", { name: "Close" });
    expect(document.activeElement).toBe(screen.getByRole("region", { name: "Selected event" }));
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
    expect(screen.getByText("Selected historical evidence")).toBeTruthy();

    await view.rerender({ runId: "run-b" });
    expect(screen.queryByText("Selected historical evidence")).toBeNull();
    expect(screen.queryByRole("button", { name: /Step completed/ })).toBeNull();

    await act(() => nextRun.reject(new Error("Run B unavailable")));
    expect(screen.getByRole("alert").textContent).toContain("Run B unavailable");
    expect(screen.queryByText("Selected historical evidence")).toBeNull();
    view.unmount();
  });

  it("retains same-Run evidence when refresh fails", async () => {
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce(snapshot)
      .mockRejectedValueOnce(new Error("Refresh unavailable"));
    const view = render(OrbView, { runId: "run-a" });

    expect(await screen.findByRole("button", { name: /Step completed/ })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect((await screen.findByText("Refresh unavailable")).getAttribute("role")).toBe("alert");
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeTruthy();
    view.unmount();
  });
});

describe("Orb evidence pagination", () => {
  it("keeps a linked event outside the loaded page distinct from a gap and selects it after loading", async () => {
    page.url.href = "http://localhost/orb/run-a?event=event-b";
    vi.mocked(getOrbRun)
      .mockResolvedValueOnce({
        ...snapshot,
        ledger_head_seq: 4,
        page_end_seq: 2,
        next_after_seq: 2,
        has_more: true,
        gaps: [{ start_seq: 1, end_seq: 2, classification: "unknown_or_omitted" }]
      })
      .mockResolvedValueOnce({
        ...snapshot,
        ledger_head_seq: 4,
        page_end_seq: 4,
        evidence: [{ ...snapshot.evidence[0]!, event_id: "event-b", seq: 4, summary: "Linked event" }]
      });
    const view = render(OrbView, { runId: "run-a" });
    expect(await screen.findByText(/outside this loaded page/)).toBeTruthy();
    expect(screen.getByText("Unknown or omitted interval")).toBeTruthy();
    expect(screen.getByText(/Sequence is order, not elapsed time or causality/)).toBeTruthy();

    await fireEvent.click(screen.getByRole("button", { name: "Load more retained evidence" }));

    const linkedRow = await screen.findByRole("button", { name: /Linked event/ });
    expect(linkedRow.getAttribute("aria-current")).toBe("true");
    expect(screen.getByRole("region", { name: "Selected event" })).toBeTruthy();
    expect(screen.queryByText(/outside this loaded page/)).toBeNull();
    expect(screen.getByText("Unknown or omitted interval")).toBeTruthy();
    view.unmount();
  });

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

    expect((await screen.findByText("Next page unavailable")).getAttribute("role")).toBe("alert");
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();

    await fireEvent.click(
      screen.getByRole("button", { name: "Retry loading retained evidence" })
    );

    expect(await screen.findByRole("button", { name: /Second step completed/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    expect(screen.queryByText("Next page unavailable")).toBeNull();
    expect(getOrbRun).toHaveBeenNthCalledWith(
      2,
      "run-a",
      expect.objectContaining({ afterSeq: 0, limit: 100 })
    );
    expect(getOrbRun).toHaveBeenNthCalledWith(
      3,
      "run-a",
      expect.objectContaining({ afterSeq: 0, limit: 100 })
    );
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

    expect((await screen.findByText("The Orb returned evidence for another Run.")).getAttribute("role")).toBe("alert");
    expect(screen.queryByRole("button", { name: /Foreign step/ })).toBeNull();
    expect(screen.getByRole("button", { name: /Step completed/ })).toBeTruthy();
    view.unmount();
  });
});


it("hands exact Run and event context to Bridge and the pinned Pattern", async () => {
  page.url.href = "http://localhost/orb/run-a?event=event-a&job=job-a";
  const view = render(OrbView, { runId: "run-a" });
  expect((await screen.findByRole("link", { name: "Bridge" })).getAttribute("href"))
    .toBe("/bridge/session-a?run=run-a");
  expect(screen.getByRole("link", { name: "Exact Pattern →" }).getAttribute("href"))
    .toBe("/loom/bridge_chat/1?run=run-a&event=event-a&job=job-a");
  view.unmount();
});


describe("Orb selected-Run live ownership", () => {
  it("freezes historical Animator evidence across live-window eviction and resumes on Follow latest", async () => {
    const view = render(OrbView, { runId: "run-a" });
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    const grant = { ...snapshot.evidence[0]!, event_id: "grant-live", seq: 1, kind: "dispatch", summary: "Grant selected", animator_name: "historical-reasoner", model_id: "model-at-one" };
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 1,
      snapshot: { ...snapshot, ledger_head_seq: 1, evidence: [grant] } }));
    const rail = screen.getByRole("complementary", { name: "Recorded Animators" });
    await fireEvent.click(within(rail).getByRole("button", { name: /historical-reasoner/ }));
    const slider = screen.getByRole("slider", { name: "Record cursor" });
    expect(slider.getAttribute("aria-valuetext")).toBe("Record #1");
    expect(screen.getByRole("button", { name: "LIVE" }).getAttribute("aria-pressed")).toBe("false");
    await act(() => {
      for (let seq = 2; seq <= 103; seq++) callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: seq - 1, cursor: seq,
        snapshot: { ...snapshot, ledger_head_seq: seq, evidence: [{ ...grant, event_id: `future-${seq}`, seq, animator_name: "future-animator" }] } });
    });
    expect(slider.getAttribute("aria-valuetext")).toBe("Record #1");
    expect(within(rail).getByText("historical-reasoner")).toBeTruthy();
    expect(within(rail).queryByText("future-animator")).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: "Follow latest" }));
    expect(screen.getByRole("button", { name: "LIVE" }).getAttribute("aria-pressed")).toBe("true");
    expect(slider.getAttribute("aria-valuetext")).toBe("Record #103");
    expect(within(rail).queryByText("historical-reasoner")).toBeNull();
    expect(within(rail).getByText("future-animator")).toBeTruthy();
    view.unmount();
  });

  it("closes the prior feed and fences callbacks after a Run change and unmount", async () => {
    const closeA = vi.fn(), closeB = vi.fn();
    vi.mocked(listenToOrb).mockReturnValueOnce(closeA).mockReturnValueOnce(closeB);
    const view = render(OrbView, { runId: "run-a" });
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2] as OrbLiveCallbacks;
    vi.mocked(getOrbRun).mockResolvedValue({ ...snapshot, run: { ...snapshot.run, run_id: "run-b" } });
    await view.rerender({ runId: "run-b" });
    await waitFor(() => expect(listenToOrb).toHaveBeenCalledTimes(2));
    expect(closeA).toHaveBeenCalledOnce();
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 1,
      snapshot: { ...snapshot, ledger_head_seq: 1, evidence: [{ ...snapshot.evidence[0]!, event_id: "late-a", seq: 1, summary: "Late foreign callback" }] } }));
    expect(screen.queryByText("Late foreign callback")).toBeNull();
    expect(screen.getByText("run-b")).toBeTruthy();
    view.unmount();
    expect(closeB).toHaveBeenCalledOnce();
  });

  it("appends real records while preserving selected evidence and paused follow", async () => {
    page.url.href = "http://localhost/orb/run-a?event=event-a";
    const view = render(OrbView, { runId: "run-a" });
    const opener = await screen.findByRole("button", { name: /Step completed/ });
    await fireEvent.click(opener);
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 1,
      snapshot: { ...snapshot, ledger_head_seq: 1, evidence: [{ ...snapshot.evidence[0]!, event_id: "event-live", seq: 1, summary: "Fresh ledger record" }] } }));
    expect(screen.getByRole("button", { name: /Fresh ledger record/ })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Selected event" }).textContent).toContain("event-a");
    expect(screen.getByRole("button", { name: "Follow latest" }).getAttribute("aria-pressed")).toBe("false");
    view.unmount();
  });
});

describe("Orb loaded evidence browsing", () => {
  const records: OrbRunSnapshot["evidence"] = [
    { ...snapshot.evidence[0]!, event_id: "node-a1", seq: 8, subject_key: "review", occurrence_id: "a1", summary: "Review entered", phase: "entered", occurred_at: "2026-07-30T10:02:00Z" },
    { ...snapshot.evidence[0]!, event_id: "dispatch-review", seq: 9, kind: "dispatch", subject_key: "review", occurrence_id: null, summary: "Review capability granted", occurred_at: "2026-07-30T10:01:00Z" },
    { ...snapshot.evidence[0]!, event_id: "node-a2", seq: 10, subject_key: "review", occurrence_id: "a2", summary: "Review repeated", occurred_at: "2026-07-30T10:01:00Z" },
    { ...snapshot.evidence[0]!, event_id: "node-unknown", seq: 20, subject_key: "review", occurrence_id: null, summary: "Review unassigned" }
  ];
  const account = { ...snapshot, evidence: records, page_end_seq: 20, ledger_head_seq: 21, has_more: true, next_after_seq: 20, gaps: [{ start_seq: 11, end_seq: 19, classification: "unknown_or_omitted" as const }] };

  it("keeps typed subjects, exact attempts and unknown membership separate without inventing gaps", async () => {
    vi.mocked(getOrbRun).mockResolvedValue(account);
    const view = render(OrbView, { runId: "run-a" });
    const subjects = await screen.findByLabelText("Recorded subject");
    const station = screen.getByRole("option", { name: "Station observations · review · 3 loaded records" }) as HTMLOptionElement;
    const capability = screen.getByRole("option", { name: "Capability dispatches · review · 1 loaded records" }) as HTMLOptionElement;
    await fireEvent.change(subjects, { target: { value: station.value } });
    expect(view.container.querySelectorAll(".evidence-row")).toHaveLength(3);
    expect(screen.queryByRole("button", { name: /Review capability granted/ })).toBeNull();
    expect(view.container.querySelectorAll(".evidence-gap")).toHaveLength(1);
    expect(screen.getByText("#11–19")).toBeTruthy();
    expect(screen.getByText(/sequence jumps alone are not evidence gaps/)).toBeTruthy();
    const attempts = screen.getByLabelText("Station attempt");
    const a2 = screen.getByRole("option", { name: "Station attempt a2 · 1 loaded records" }) as HTMLOptionElement;
    await fireEvent.change(attempts, { target: { value: a2.value } });
    expect(view.container.querySelectorAll(".evidence-row")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /Review repeated/ })).toBeTruthy();
    const unknown = screen.getByRole("option", { name: "No recorded attempt · 1 loaded records" }) as HTMLOptionElement;
    await fireEvent.change(attempts, { target: { value: unknown.value } });
    expect(screen.getByRole("button", { name: /Review unassigned/ })).toBeTruthy();
    expect(view.container.querySelectorAll(".evidence-row")).toHaveLength(1);
    await fireEvent.change(subjects, { target: { value: capability.value } });
    expect(screen.queryByLabelText("Station attempt")).toBeNull();
    expect(screen.getByRole("button", { name: /Review capability granted/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Load more retained evidence" })).toBeTruthy();
    view.unmount();
  });

  it("steps through all loaded Run records in sequence and preserves exact event and job hints", async () => {
    page.url.href = "http://localhost/orb/run-a?job=job-a";
    vi.mocked(getOrbRun).mockResolvedValue(account);
    const view = render(OrbView, { runId: "run-a" });
    const subjects = await screen.findByLabelText("Recorded subject");
    const station = screen.getByRole("option", { name: /Station observations/ }) as HTMLOptionElement;
    await fireEvent.change(subjects, { target: { value: station.value } });
    await fireEvent.click(screen.getByRole("button", { name: /Review entered/ }));
    expect((screen.getByRole("button", { name: "Previous loaded record" }) as HTMLButtonElement).disabled).toBe(true);
    expect(document.activeElement).toBe(view.container.querySelector(".selected-evidence"));
    await fireEvent.click(screen.getByRole("button", { name: "Next loaded record" }));
    expect(goto).toHaveBeenLastCalledWith("/orb/run-a?job=job-a&event=dispatch-review", expect.objectContaining({ reset: false }));
    expect((subjects as HTMLSelectElement).value).toBe("");
    expect(within(view.container.querySelector(".selected-evidence") as HTMLElement).getByText("Review capability granted")).toBeTruthy();
    expect(view.container.querySelector(".run-status")?.textContent).toBe("done");
    expect(screen.getByText("Latest fetched Run status")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Next loaded record" }));
    expect(goto).toHaveBeenLastCalledWith("/orb/run-a?job=job-a&event=node-a2", expect.anything());
    await fireEvent.click(screen.getByRole("button", { name: "Next loaded record" }));
    expect((screen.getByRole("button", { name: "Next loaded record" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/End of loaded evidence; load more retained evidence to continue/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Previous loaded record" }));
    expect(goto).toHaveBeenLastCalledWith("/orb/run-a?job=job-a&event=node-a2", expect.anything());
    await fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(document.activeElement).toBe(screen.getByRole("button", { name: /Review repeated/ }));
    view.unmount();
  });

  it("keeps selection while filtering and returns focus to the account when the opener is filtered out", async () => {
    vi.mocked(getOrbRun).mockResolvedValue(account);
    const view = render(OrbView, { runId: "run-a" });
    await fireEvent.click(await screen.findByRole("button", { name: /Review entered/ }));
    const capability = screen.getByRole("option", { name: /Capability dispatches/ }) as HTMLOptionElement;
    await fireEvent.change(screen.getByLabelText("Recorded subject"), { target: { value: capability.value } });
    expect(screen.getByText(/selected record is outside the current subject/)).toBeTruthy();
    expect(within(view.container.querySelector(".selected-evidence") as HTMLElement).getByText("node-a1")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Ordered evidence" }));
    view.unmount();
  });

  it("keeps a historical identity through refresh and reports its loss without selecting a neighbor", async () => {
    page.url.href = "http://localhost/orb/run-a?event=node-a1";
    vi.mocked(getOrbRun).mockResolvedValueOnce(account).mockResolvedValueOnce({ ...account, snapshot_at: "2026-07-31T10:00:00Z" }).mockResolvedValueOnce({ ...account, evidence: records.slice(1), has_more: false });
    const view = render(OrbView, { runId: "run-a" });
    expect(await screen.findByText("Selected historical evidence")).toBeTruthy();
    const refresh = screen.getByRole("button", { name: "Refresh" });
    refresh.focus();
    await fireEvent.click(refresh);
    await waitFor(() => expect(view.container.querySelector('.coverage-strip time')?.getAttribute("datetime")).toBe("2026-07-31T10:00:00Z"));
    expect(document.activeElement).toBe(refresh);
    expect(within(view.container.querySelector(".selected-evidence") as HTMLElement).getByText("node-a1")).toBeTruthy();
    await fireEvent.click(refresh);
    expect(await screen.findByText(/linked event was not found in retained evidence at this read/)).toBeTruthy();
    expect(screen.queryByText("Selected historical evidence")).toBeNull();
    expect(page.url.searchParams.get("event")).toBe("node-a1");
    view.unmount();
  });

  it("exposes conflicting attempt correlations while keeping station subjects separate", async () => {
    vi.mocked(getOrbRun).mockResolvedValue({ ...account, evidence: [...records, { ...records[0]!, event_id: "other-station", seq: 21, subject_key: "publish" }] });
    const view = render(OrbView, { runId: "run-a" });
    expect(await screen.findByText(/Station attempt IDs appear under multiple station subjects/)).toBeTruthy();
    expect(screen.getByRole("option", { name: /Station observations · publish/ })).toBeTruthy();
    expect(screen.getByRole("option", { name: /Station observations · review/ })).toBeTruthy();
    view.unmount();
  });
});

describe("Creation evidence in the selected Run", () => {
  it("keeps DONE separate from incomplete custody, applies metadata-only updates and clears revoked details", async () => {
    vi.mocked(getOrbRun).mockResolvedValue({ ...snapshot, creation: incompleteCreation });
    const view = render(OrbView, { runId: "run-a" });
    await screen.findByRole("region", { name: "Creation outcome" });
    expect(view.container.querySelector(".run-status")?.textContent).toBe("done");
    expect(screen.getByText("incomplete")).toBeTruthy();
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0,
      snapshot: { ...snapshot, evidence: [], creation: { ...incompleteCreation, native_status: "accepted", native_disposition: "accepted",
        external_disposition: "partial", feedback_status: "hold", current_decision_id: "43a159ef-e563-485f-a5f9-772b52bf59d7" } }
    }));
    expect(screen.getByText("partial")).toBeTruthy();
    expect(screen.getByText("hold")).toBeTruthy();
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "settled", after_seq: 0, cursor: 0,
      snapshot: { ...snapshot, evidence: [], creation: null }
    }));
    expect(screen.queryByRole("region", { name: "Creation outcome" })).toBeNull();
    expect(screen.queryByText(incompleteCreation.case_id)).toBeNull();
    view.unmount();
  });

  it("refreshes later feedback after settlement and does not display a foreign Run summary", async () => {
    vi.mocked(getOrbRun).mockResolvedValueOnce({ ...snapshot, creation: incompleteCreation })
      .mockResolvedValueOnce({ ...snapshot, creation: { ...incompleteCreation, feedback_status: "review_required" } })
      .mockResolvedValueOnce({ ...snapshot, creation: { ...incompleteCreation, run_id: "another-run" } });
    const view = render(OrbView, { runId: "run-a" });
    await screen.findByRole("region", { name: "Creation outcome" });
    await act(() => vi.mocked(listenToOrb).mock.calls[0]![2].onConnection("settled"));
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByText(/Feedback: review required/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Creation outcome" })).toBeNull());
    expect(screen.queryByText(incompleteCreation.case_id)).toBeNull();
    view.unmount();
  });
});

describe("Routing preference in the Run inspector", () => {
  it("retains supplied preference metadata at the same cursor and hides legacy absence", async () => {
    const view = render(OrbView, { runId: "run-a" });
    await screen.findByRole("heading", { name: "Inspect a record" });
    expect(screen.queryByRole("region", { name: "Routing preference" })).toBeNull();
    const callbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0,
      snapshot: { ...snapshot, evidence: [], bridge_preference: coldPreferredRoute }
    }));
    const preference = screen.getByRole("region", { name: "Routing preference" });
    expect(within(preference).getByRole("table")).toBeTruthy();
    expect(preference.closest("aside.orb-inspector")).toBeTruthy();
    expect(within(preference).getByText(coldPreferredRoute.policy_digest)).toBeTruthy();
    await act(() => callbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "settled", after_seq: 0, cursor: 0,
      snapshot: { ...snapshot, evidence: [], bridge_preference: null }
    }));
    expect(screen.queryByRole("region", { name: "Routing preference" })).toBeNull();
    expect(screen.queryByText(coldPreferredRoute.policy_digest)).toBeNull();
    view.unmount();
  });
});

it("returns an app-owned Run to Scavenger without exposing a nonexistent Bridge session", async () => {
  const path = "/scavenger?observation=00000000-0000-4000-8000-000000000001";
  vi.mocked(getOrbRun).mockResolvedValue({ ...snapshot, run: { ...snapshot.run, bridge_path: null,
    application_path: path, workflow_name: "scavenger.observe_market", session_id: "scavenger:opaque-reference" } });
  render(OrbView, { runId: "run-a" });
  const link = await screen.findByRole("link", { name: "Scavenger market" });
  expect(link.getAttribute("href")).toBe(path);
  expect(screen.queryByRole("link", { name: "Bridge" })).toBeNull();
});


it("mounts an explicit Archive read by supplied Run and aborts it on navigation without restarting Orb ownership", async () => {
  const pending = deferred<import("$lib/api/models").ArchiveRunRecall>();
  vi.mocked(getArchiveRunRecall).mockReturnValueOnce(pending.promise);
  const view = render(OrbView, { runId: "run-a" });
  await screen.findByRole("region", { name: "Archive selection" });
  expect(getArchiveRunRecall).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Read Archive selection" }));
  expect(getArchiveRunRecall).toHaveBeenCalledWith("run-a", expect.any(AbortSignal));
  const signal = vi.mocked(getArchiveRunRecall).mock.calls[0]![1]!;
  const firstCallbacks = vi.mocked(listenToOrb).mock.calls[0]![2];
  await act(() => firstCallbacks.onFrame({ schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 0, snapshot: { ...snapshot, evidence: [] } }));
  expect(signal.aborted).toBe(false);
  expect(getArchiveRunRecall).toHaveBeenCalledTimes(1);
  vi.mocked(getOrbRun).mockResolvedValue({ ...snapshot, run: { ...snapshot.run, run_id: "run-b" } });
  await view.rerender({ runId: "run-b" });
  expect(signal.aborted).toBe(true);
  expect(screen.getByRole("region", { name: "Archive selection" }).textContent).toContain("Exact Run · run-b");
  expect(screen.getByRole("button", { name: "Read Archive selection" })).toBeTruthy();
  await act(() => pending.resolve({ run_id: "run-a", capture: "matching_retained_request", status: "not_recorded", receipt: null }));
  expect(screen.queryByText(/Not recorded: no matching retained request/)).toBeNull();
  expect(getArchiveRunRecall).toHaveBeenCalledTimes(1);
  vi.mocked(getArchiveRunRecall).mockResolvedValueOnce({ run_id: "run-b", capture: "matching_retained_request", status: "not_applicable", receipt: null });
  await fireEvent.click(screen.getByRole("button", { name: "Read Archive selection" }));
  await screen.findByText(/Not applicable: this Run's pinned Pattern/);
  expect(vi.mocked(getArchiveRunRecall).mock.calls[1]![0]).toBe("run-b");
  view.unmount();
});
