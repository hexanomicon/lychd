import { act, cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BridgeSnapshot, OrbRunSnapshot, RunProjectionSnapshot } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn(), goto: vi.fn(), replaceState: vi.fn() }));
vi.mock("$app/state", async () => {
  const { SvelteURL } = await import("svelte/reactivity");
  return { page: { url: new SvelteURL("http://localhost/bridge/session-b"), state: {} } };
});
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error { status?: number; },
  cancelBridgeRun: vi.fn(),
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getAtlasProject: vi.fn(),
  getAtlasReferences: vi.fn().mockResolvedValue([]),
  getBridgeSnapshot: vi.fn(),
  getBridgeSessions: vi.fn(),
  getDictationDiscovery: vi.fn().mockResolvedValue({ status: "unavailable", reason: "unconfigured", languages: [], profile_digest: null }),
  getOrbRun: vi.fn(),
  getRunSnapshot: vi.fn(),
  listenToRun: vi.fn(),
  sendBridgeMessage: vi.fn()
}));

import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { goto, replaceState } from "$app/navigation";
import {
  cancelBridgeRun, createBridgeSession, decideConsent, getAtlasReferences,
  getBridgeSnapshot, getOrbRun, getRunSnapshot, listenToRun, sendBridgeMessage
} from "$lib/api/client";
import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/shell/state/bridge-workspace.svelte";
import BridgeView from "$lib/pages/bridge/components/BridgeView.svelte";
import OrbView from "$lib/pages/orb/components/OrbView.svelte";

const at = "2026-10-10T12:00:00Z";
const bridgeRead = vi.mocked(getBridgeSnapshot);
const orbRead = vi.mocked(getOrbRun);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => { resolve = accept; });
  return { promise, resolve };
}

function bridgeSnapshot(sessionId: string, activeRuns: RunProjectionSnapshot[] = []): BridgeSnapshot {
  const sessions = ["session-a", "session-b", "session-c"].map((id) => ({
    id, title: `Conversation ${id}`, created_at: at, pending_count: 0
  }));
  const session = sessions.find((item) => item.id === sessionId)!;
  return {
    sessions,
    session: { ...session, turns: [{
      role: "agent", content: `Retained reply in ${sessionId}`, run_id: `run-${sessionId.at(-1)}`,
      state: "settled", fragments: [], created_at: at
    }] },
    active_runs: activeRuns, pending_consents: [], pending_count: 0
  };
}

function activeRun(): RunProjectionSnapshot {
  return {
    schema_version: 1, session_id: "session-b", run_id: "run-live-b", cursor: 17,
    content: "Late live B", run_status: "running", activity: "weaving",
    pattern_id: "bridge_chat", pattern_revision: "1", loom_path: "/loom/bridge_chat/1",
    orb_path: "/orb/run-live-b", evidence_capture: "process_local", fragments: [],
    occurrence_id: null, dispatch_occurrence_id: null, grant_id: null, capability_key: null,
    transition_occurrence_id: null, transition_request_id: null, transition_phase: null,
    delegated_job_id: null, delegated_runtime: null, delegated_profile: null,
    delegated_status: null, terminal: false
  };
}

function orbSnapshot(runId = "run-b"): OrbRunSnapshot {
  const suffix = runId.at(-1);
  return {
    schema_version: 1, snapshot_at: at, capture: "process_local", ledger_head_seq: 0,
    page_end_seq: 0, live_tail: "ledger_poll", next_after_seq: null, has_more: false,
    known_omissions: [], gaps: [],
    evidence: [{
      event_id: `event-${suffix}`, seq: 0, kind: "node", occurred_at: at,
      summary: `Retained event for ${runId}`, capture: "process_local", nexus_path: null,
      occurrence_id: `occurrence-${suffix}`, phase: "settled", subject_key: "step-a",
      transition_request_id: null
    }],
    delegated_jobs: [{
      job_id: `job-${suffix}`, request_id: `request-${suffix}`, runtime: "reference", profile: "read",
      step_id: "step-a", status: "completed", output_present: false, artifact_count: 0,
      error_present: false, events: [], events_truncated: false
    }],
    pattern: { pattern_id: "bridge_chat", revision: "1", digest: "digest-b", exact: true, loom_path: "/loom/bridge_chat/1" },
    run: {
      run_id: runId, session_id: `session-${suffix}`, workflow_name: "bridge_chat", status: "done",
      created_at: at, started_at: at, finished_at: at, error_present: false,
      bridge_path: `/bridge/session-${suffix}`
    }
  };
}

function retainedWork() {
  const work = createBridgeWorkspace();
  work.setDraft("session-b", "Later draft B\nkept verbatim ✦");
  work.pending.set("session-b", Object.freeze({
    text: "Original offering B\nunchanged", requestId: "9bd060dd-1c72-4198-b2f6-9170364850df",
    uncertain: true, sending: false, error: "Admission response unknown"
  }));
  work.setDraft("session-c", "Draft C stays distinct");
  return work;
}

function workBytes(work: ReturnType<typeof createBridgeWorkspace>) {
  return JSON.stringify({ drafts: [...work.drafts], pending: [...work.pending] });
}

function mountBridge(work = retainedWork()) {
  page.url.href = "http://localhost/bridge/session-b";
  return render(BridgeView, {
    props: { sessionId: "session-b" }, context: new Map([[bridgeWorkspaceKey, work]])
  });
}

function retryControl(): HTMLButtonElement {
  const control = screen.getByRole("button", { name: /retry/i });
  expect(control, "Read recovery must be a native keyboard-operable button").toBeInstanceOf(HTMLButtonElement);
  const button = control as HTMLButtonElement;
  expect(button.disabled).toBe(false);
  expect(button.tabIndex).toBeGreaterThanOrEqual(0);
  button.focus();
  expect(document.activeElement).toBe(button);
  return button;
}

function expectBusy(button: HTMLButtonElement) {
  expect(button.isConnected, "Keep the read retry control available while its read is pending").toBe(true);
  expect(button.disabled, "Pending read must disable repeated activation").toBe(true);
  const communicatesBusy = Boolean(button.closest('[aria-busy="true"]')) ||
    /reading|loading|retrying/i.test(button.textContent ?? "");
  expect(communicatesBusy, "Pending retry needs a busy attribute or explicit reading label").toBe(true);
}

function expectNoEffects() {
  for (const mock of [sendBridgeMessage, createBridgeSession, cancelBridgeRun, decideConsent]) {
    expect(mock).not.toHaveBeenCalled();
  }
  expect(goto).not.toHaveBeenCalled();
  expect(replaceState).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getAtlasReferences).mockResolvedValue([]);
  vi.mocked(listenToRun).mockImplementation(() => vi.fn());
  bridgeRead.mockImplementation(async (id) => bridgeSnapshot(id ?? "session-a"));
  orbRead.mockImplementation(async (id) => orbSnapshot(id));
  page.url.href = "http://localhost/bridge/session-b";
});

afterEach(() => { cleanup(); });

describe("initial instrument read recovery", () => {
  it("Bridge failed-read control preserves local work without mistaking failure for a first visit", async () => {
    const work = retainedWork();
    const before = workBytes(work);
    bridgeRead.mockRejectedValueOnce(new Error("Bridge read temporarily unavailable"));
    mountBridge(work);
    expect(await screen.findByText("Bridge read temporarily unavailable")).toBeTruthy();
    expect(bridgeRead.mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    expect(screen.queryByRole("heading", { name: "Begin a séance." })).toBeNull();
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(workBytes(work)).toBe(before);
    expectNoEffects();
  });

  it("Bridge retries one exact-session read and restores draft plus unresolved offering unchanged", async () => {
    const work = retainedWork();
    const before = workBytes(work);
    const pending = work.pending.get("session-b");
    const recovery = deferred<BridgeSnapshot>();
    bridgeRead.mockRejectedValueOnce(new Error("Bridge read temporarily unavailable"))
      .mockReturnValueOnce(recovery.promise);
    mountBridge(work);
    await screen.findByText("Bridge read temporarily unavailable");
    const retry = retryControl();
    await act(() => { retry.click(); retry.click(); });
    expect(bridgeRead.mock.calls.map(([id]) => id)).toEqual(["session-b", "session-b"]);
    expectBusy(retry);
    await fireEvent.click(retry);
    expect(bridgeRead).toHaveBeenCalledTimes(2);
    expect(workBytes(work)).toBe(before);
    expectNoEffects();
    await act(() => recovery.resolve(bridgeSnapshot("session-b")));
    expect((await screen.findByLabelText("Message") as HTMLTextAreaElement).value).toBe(work.drafts.get("session-b"));
    expect(screen.getByText("Retained reply in session-b")).toBeTruthy();
    expect(screen.getByText("Offering outcome unknown")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry original offering" })).toBeTruthy();
    expect(screen.queryByText("Bridge read temporarily unavailable")).toBeNull();
    expect(workBytes(work)).toBe(before);
    expect(work.pending.get("session-b")).toBe(pending);
    expectNoEffects();
  });

  it("Bridge fences a late B retry when the reader selects C", async () => {
    const work = retainedWork();
    const before = workBytes(work);
    const recovery = deferred<BridgeSnapshot>();
    bridgeRead.mockRejectedValueOnce(new Error("Bridge B unavailable"))
      .mockReturnValueOnce(recovery.promise);
    const view = mountBridge(work);
    await screen.findByText("Bridge B unavailable");
    await fireEvent.click(retryControl());
    page.url.href = "http://localhost/bridge/session-c";
    await view.rerender({ sessionId: "session-c" });
    await screen.findByText("Retained reply in session-c");
    await act(() => recovery.resolve(bridgeSnapshot("session-b", [activeRun()])));
    expect(bridgeRead.mock.calls.map(([id]) => id)).toEqual(["session-b", "session-b", "session-c"]);
    expect(screen.getByText("Retained reply in session-c")).toBeTruthy();
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("Draft C stays distinct");
    expect(screen.queryByText("Retained reply in session-b")).toBeNull();
    expect(screen.queryByText("Late live B")).toBeNull();
    expect(listenToRun).not.toHaveBeenCalled();
    expect(workBytes(work)).toBe(before);
    expectNoEffects();
  });

  it("Bridge teardown fences a pending retry before it can attach a Run stream", async () => {
    const work = retainedWork();
    const before = workBytes(work);
    const recovery = deferred<BridgeSnapshot>();
    bridgeRead.mockRejectedValueOnce(new Error("Bridge B unavailable"))
      .mockReturnValueOnce(recovery.promise);
    const view = mountBridge(work);
    await screen.findByText("Bridge B unavailable");
    await fireEvent.click(retryControl());
    view.unmount();
    await act(() => recovery.resolve(bridgeSnapshot("session-b", [activeRun()])));
    expect(bridgeRead.mock.calls.map(([id]) => id)).toEqual(["session-b", "session-b"]);
    expect(listenToRun).not.toHaveBeenCalled();
    expect(getRunSnapshot).not.toHaveBeenCalled();
    expect(workBytes(work)).toBe(before);
    expectNoEffects();
  });

  it("Orb initially rejects another Run without replacing the requested URL selection", async () => {
    page.url.href = "http://localhost/orb/run-b?event=event-b&job=job-b";
    orbRead.mockResolvedValueOnce(orbSnapshot("run-a"));
    render(OrbView, { runId: "run-b" });
    expect((await screen.findByRole("alert")).textContent).toContain("another Run");
    expect(screen.queryByText("run-a", { selector: ".run-id" })).toBeNull();
    expect(page.url.search).toBe("?event=event-b&job=job-b");
    expect(orbRead.mock.calls.map(([id]) => id)).toEqual(["run-b"]);
    expectNoEffects();
  });

  it("Orb retries one exact-Run read and retains event plus delegated-job selection", async () => {
    page.url.href = "http://localhost/orb/run-b?event=event-b&job=job-b";
    const recovery = deferred<OrbRunSnapshot>();
    orbRead.mockRejectedValueOnce(new Error("Orb B unavailable")).mockReturnValueOnce(recovery.promise);
    const view = render(OrbView, { runId: "run-b" });
    await screen.findByText("Orb B unavailable");
    const retry = retryControl();
    await act(() => { retry.click(); retry.click(); });
    expect(orbRead.mock.calls.map(([id]) => id)).toEqual(["run-b", "run-b"]);
    expectBusy(retry);
    await fireEvent.click(retry);
    expect(orbRead).toHaveBeenCalledTimes(2);
    expect(page.url.search).toBe("?event=event-b&job=job-b");
    expectNoEffects();
    await act(() => recovery.resolve(orbSnapshot()));
    expect(await screen.findByText("run-b", { selector: ".run-id" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Retained event for run-b/ }).getAttribute("aria-current")).toBe("true");
    expect(screen.getByText("Selected historical evidence")).toBeTruthy();
    expect(view.container.querySelector("#delegated-job-job-b")?.getAttribute("aria-current")).toBe("true");
    expect(page.url.search).toBe("?event=event-b&job=job-b");
    expect(screen.queryByText("Orb B unavailable")).toBeNull();
    expectNoEffects();
  });

  it("Orb retry rejects a wrong Run and permits another read with unavailable linked evidence explicit", async () => {
    page.url.href = "http://localhost/orb/run-b?event=event-missing&job=job-missing";
    orbRead.mockRejectedValueOnce(new Error("Orb B unavailable"))
      .mockResolvedValueOnce(orbSnapshot("run-a"))
      .mockResolvedValueOnce(orbSnapshot());
    render(OrbView, { runId: "run-b" });
    await screen.findByText("Orb B unavailable");
    await fireEvent.click(retryControl());
    expect((await screen.findByRole("alert")).textContent).toContain("another Run");
    expect(screen.queryByText("run-a", { selector: ".run-id" })).toBeNull();
    expect(screen.queryByText("Selected historical evidence")).toBeNull();
    await fireEvent.click(retryControl());
    expect(await screen.findByText("run-b", { selector: ".run-id" })).toBeTruthy();
    expect(screen.getByText(/The linked event was not found in retained evidence/)).toBeTruthy();
    expect(screen.getByText(/The linked delegated job is not present/)).toBeTruthy();
    expect(orbRead.mock.calls.map(([id]) => id)).toEqual(["run-b", "run-b", "run-b"]);
    expect(page.url.search).toBe("?event=event-missing&job=job-missing");
    expectNoEffects();
  });

  it("Orb fences a late B retry after navigation to C even if the transport ignores abort", async () => {
    page.url.href = "http://localhost/orb/run-b?event=event-b&job=job-b";
    const recovery = deferred<OrbRunSnapshot>();
    orbRead.mockRejectedValueOnce(new Error("Orb B unavailable")).mockReturnValueOnce(recovery.promise);
    const view = render(OrbView, { runId: "run-b" });
    await screen.findByText("Orb B unavailable");
    await fireEvent.click(retryControl());
    const signal = orbRead.mock.calls[1]?.[1]?.signal;
    expect(signal?.aborted).toBe(false);
    page.url.href = "http://localhost/orb/run-c?event=event-c&job=job-c";
    await view.rerender({ runId: "run-c" });
    await screen.findByText("run-c", { selector: ".run-id" });
    expect(signal?.aborted).toBe(true);
    await act(() => recovery.resolve(orbSnapshot()));
    expect(screen.getByText("run-c", { selector: ".run-id" })).toBeTruthy();
    expect(screen.queryByText("run-b", { selector: ".run-id" })).toBeNull();
    expect(screen.getByRole("button", { name: /Retained event for run-c/ }).getAttribute("aria-current")).toBe("true");
    expect(orbRead.mock.calls.map(([id]) => id)).toEqual(["run-b", "run-b", "run-c"]);
    expect(page.url.search).toBe("?event=event-c&job=job-c");
    expectNoEffects();
  });

  it("Orb teardown cancels a pending retry and leaves its late response inert", async () => {
    page.url.href = "http://localhost/orb/run-b?event=event-b&job=job-b";
    const recovery = deferred<OrbRunSnapshot>();
    orbRead.mockRejectedValueOnce(new Error("Orb B unavailable")).mockReturnValueOnce(recovery.promise);
    const view = render(OrbView, { runId: "run-b" });
    await screen.findByText("Orb B unavailable");
    await fireEvent.click(retryControl());
    const signal = orbRead.mock.calls[1]?.[1]?.signal;
    expect(signal?.aborted).toBe(false);
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(() => recovery.resolve(orbSnapshot()));
    expect(view.container.textContent).toBe("");
    expect(orbRead.mock.calls.map(([id]) => id)).toEqual(["run-b", "run-b"]);
    expect(page.url.search).toBe("?event=event-b&job=job-b");
    expectNoEffects();
  });
});

describe("read retry overtaken by a real offering settlement", () => {
  it("keeps the original Bridge retry busy while admission requires a newer authoritative read", async () => {
    const work = createBridgeWorkspace();
    const offeringText = "Original delayed offering B";
    work.setDraft("session-b", offeringText);
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    const staleRead = deferred<BridgeSnapshot>();
    const newerRead = deferred<BridgeSnapshot>();
    bridgeRead.mockResolvedValueOnce(bridgeSnapshot("session-b"))
      .mockRejectedValueOnce(new Error("Returning Bridge B unavailable"))
      .mockReturnValueOnce(staleRead.promise)
      .mockReturnValueOnce(newerRead.promise);
    vi.mocked(sendBridgeMessage).mockReturnValueOnce(admission.promise);

    const original = mountBridge(work);
    await screen.findByLabelText("Message");
    await fireEvent.click(screen.getByRole("button", { name: /Offer/ }));
    expect(sendBridgeMessage).toHaveBeenCalledTimes(1);
    const requestId = work.pending.get("session-b")?.requestId;
    expect(requestId).toBeTruthy();
    expect(work.pending.get("session-b")?.sending).toBe(true);
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "Later B draft after offering" } });
    original.unmount();

    mountBridge(work);
    await screen.findByText("Returning Bridge B unavailable");
    const retry = retryControl();
    await fireEvent.click(retry);
    expectBusy(retry);
    expect(bridgeRead).toHaveBeenCalledTimes(3);

    const accepted: Awaited<ReturnType<typeof sendBridgeMessage>> = {
      run_id: "run-admitted-b", pattern_id: "bridge_chat", pattern_revision: "1",
      loom_path: "/loom/bridge_chat/1", orb_path: "/orb/run-admitted-b", evidence_capture: "process_local",
      turn: { role: "user", content: offeringText, run_id: "run-admitted-b", state: "settled", fragments: [], created_at: at }
    };
    // Settle through the original component's real submit continuation, after its unmount.
    await act(() => admission.resolve(accepted));
    expect(work.pending.has("session-b")).toBe(false);
    expect(work.settlements.get("session-b")).toBe(1);
    expect(work.drafts.get("session-b")).toBe("Later B draft after offering");
    expect(bridgeRead).toHaveBeenCalledTimes(3);

    const stale = bridgeSnapshot("session-b");
    stale.session!.turns![0]!.content = "Stale B snapshot from before admission";
    await act(() => staleRead.resolve(stale));
    expect(bridgeRead.mock.calls.map(([id]) => id)).toEqual(["session-b", "session-b", "session-b", "session-b"]);
    expect(screen.queryByText("Stale B snapshot from before admission")).toBeNull();
    expectBusy(retry);
    await fireEvent.click(retry);
    expect(bridgeRead).toHaveBeenCalledTimes(4);
    expect(sendBridgeMessage).toHaveBeenCalledTimes(1);

    const newest = bridgeSnapshot("session-b");
    newest.session!.turns = [accepted.turn, {
      role: "agent", content: "Newest authoritative B reply after admission", run_id: "run-admitted-b",
      state: "settled", fragments: [], created_at: at
    }];
    bridgeRead.mockResolvedValue(newest);
    await act(() => newerRead.resolve(newest));
    expect(await screen.findByText("Newest authoritative B reply after admission")).toBeTruthy();
    expect(screen.queryByText("Stale B snapshot from before admission")).toBeNull();
    expect(screen.getByText(offeringText)).toBeTruthy();
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("Later B draft after offering");
    expect(screen.queryByText("Returning Bridge B unavailable")).toBeNull();
    expect(screen.queryByRole("button", { name: "Retry original offering" })).toBeNull();
    expect(work.pending.size).toBe(0);
    expect(work.settlements.get("session-b")).toBe(1);
    expect(work.needsUnloadWarning).toBe(true);
    expect(sendBridgeMessage).toHaveBeenCalledExactlyOnceWith("session-b", offeringText, requestId);
    for (const effect of [createBridgeSession, cancelBridgeRun, decideConsent, getRunSnapshot, listenToRun, goto, replaceState]) {
      expect(effect).not.toHaveBeenCalled();
    }
  });
});
