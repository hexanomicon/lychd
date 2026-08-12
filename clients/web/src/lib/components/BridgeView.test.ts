import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BridgeSnapshot,
  ConsentCard as ConsentCardModel,
  RunEventEnvelope,
  RunProjectionSnapshot
} from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    status?: number;
  },
  cancelBridgeRun: vi.fn(),
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getBridgeSnapshot: vi.fn(),
  getRunSnapshot: vi.fn(),
  listenToRun: vi.fn(),
  sendBridgeMessage: vi.fn()
}));

import {
  cancelBridgeRun,
  decideConsent,
  getBridgeSnapshot,
  getRunSnapshot,
  listenToRun,
  sendBridgeMessage
} from "$lib/api/client";
import BridgeView from "./BridgeView.svelte";

const createdAt = "2026-07-28T00:00:00Z";
const cancelMock = vi.mocked(cancelBridgeRun);
const decideConsentMock = vi.mocked(decideConsent);
const getSnapshotMock = vi.mocked(getBridgeSnapshot);
const getRunSnapshotMock = vi.mocked(getRunSnapshot);
const listenMock = vi.mocked(listenToRun);
const sendMock = vi.mocked(sendBridgeMessage);

const pendingConsent: ConsentCardModel = {
  args: { target: "chat:local" },
  id: "consent-a",
  run_id: "run-a",
  session_id: "session-a",
  state: "pending_consent",
  tool_name: "request_coven_swap",
  vision: "Change the active capability"
};

function snapshot(
  sessionId: string,
  activeRuns: RunProjectionSnapshot[] = []
): BridgeSnapshot {
  const sessions = ["session-a", "session-b"].map((id) => ({
    id,
    title: `Séance ${id.at(-1)?.toUpperCase()}`,
    created_at: createdAt
  }));
  const selected = sessions.find((session) => session.id === sessionId);
  if (!selected) throw new Error("Unknown test session.");
  return {
    sessions,
    session: { ...selected, turns: [] },
    active_runs: activeRuns,
    pending_consents: [],
    pending_count: 0
  };
}

function projection(
  sessionId = "session-a",
  runId = "run-a"
): RunProjectionSnapshot {
  return {
    schema_version: 1,
    session_id: sessionId,
    run_id: runId,
    cursor: 17,
    content: "authoritative partial",
    run_status: "running",
    activity: "weaving",
    pattern_id: "bridge_chat",
    pattern_revision: "1",
    loom_path: "/loom/bridge_chat/1",
    orb_path: `/orb/${runId}`,
    evidence_capture: "process_local",
    fragments: [],
    occurrence_id: null,
    dispatch_occurrence_id: null,
    grant_id: null,
    capability_key: null,
    transition_occurrence_id: null,
    transition_request_id: null,
    transition_phase: null,
    delegated_job_id: null,
    delegated_runtime: null,
    delegated_profile: null,
    delegated_status: null,
    terminal: false
  };
}

function cancelledProjection(): RunProjectionSnapshot {
  return {
    ...projection(),
    run_status: "cancelled",
    activity: "cancelled",
    terminal: true
  };
}

function event(
  runId: string,
  seq: number,
  kind: RunEventEnvelope["kind"],
  payload: Record<string, unknown>
): RunEventEnvelope {
  return {
    schema_version: 1,
    run_id: runId,
    event_id: `00000000-0000-4000-8000-${seq.toString().padStart(12, "0")}`,
    seq,
    kind,
    occurred_at: createdAt,
    payload
  };
}

function accepted(
  runId: string,
  content: string
): Awaited<ReturnType<typeof sendBridgeMessage>> {
  return {
    run_id: runId,
    pattern_id: "bridge_chat",
    pattern_revision: "1",
    loom_path: "/loom/bridge_chat/1",
    orb_path: `/orb/${runId}`,
    evidence_capture: "process_local",
    turn: {
      role: "user",
      content,
      run_id: runId,
      state: "settled",
      fragments: [],
      created_at: createdAt
    }
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((accept, refuse) => {
    resolve = accept;
    reject = refuse;
  });
  return { promise, reject, resolve };
}

async function offer(text: string) {
  await fireEvent.input(screen.getByLabelText("Message"), {
    target: { value: text }
  });
  await fireEvent.click(screen.getByRole("button", { name: /Offer/ }));
  await act(async () => {
    await Promise.resolve();
  });
}

function latestRunListener() {
  const call = listenMock.mock.calls.at(-1);
  if (!call) throw new Error("The run stream was not attached.");
  return call[1];
}

beforeEach(() => {
  vi.clearAllMocks();
  getSnapshotMock.mockImplementation(async (sessionId) =>
    snapshot(sessionId ?? "session-a")
  );
  getRunSnapshotMock.mockResolvedValue(projection());
  listenMock.mockImplementation(() => vi.fn());
  cancelMock.mockResolvedValue(cancelledProjection());
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Bridge route and stream ownership", () => {
  it("renders retained GenUI descriptors from settled turns", async () => {
    const settled = snapshot("session-a");
    if (!settled.session) throw new Error("The fixture has no selected session.");
    settled.session.turns = [
      {
        role: "agent",
        content: "The plan remains visible.",
        run_id: "run-settled",
        state: "settled",
        fragments: [
          {
            kind: "genui.plan_checklist",
            schema_version: 1,
            props: { title: "Retained plan", steps: ["inspect"] },
            actions: []
          }
        ],
        created_at: createdAt
      }
    ];
    getSnapshotMock.mockResolvedValue(settled);

    const view = render(BridgeView, { sessionId: "session-a" });

    expect(await screen.findByText("Retained plan")).toBeTruthy();
    expect(screen.getByText("inspect")).toBeTruthy();
    view.unmount();
  });

  it("cancels a live Run and presents the authoritative cancelled state", async () => {
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    const view = render(BridgeView, { sessionId: "session-a" });
    const stop = await screen.findByRole("button", { name: "Cancel run run-a" });

    await fireEvent.click(stop);

    expect(cancelMock).toHaveBeenCalledWith("run-a");
    expect(await screen.findAllByText("cancelled")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Cancel run run-a" })).toBeNull();
    view.unmount();
  });

  it("reconciles cancellation from authoritative consent state", async () => {
    const initial = snapshot("session-a", [projection()]);
    initial.pending_consents = [pendingConsent];
    initial.pending_count = 2;
    const reconciled = snapshot("session-a", [cancelledProjection()]);
    reconciled.pending_count = 0;
    getSnapshotMock.mockResolvedValueOnce(initial).mockResolvedValue(reconciled);
    const attention: Array<number | undefined> = [];
    const receiveAttention = (event: Event) => {
      attention.push((event as CustomEvent<number | undefined>).detail);
    };
    window.addEventListener("altar:attention", receiveAttention);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByRole("button", { name: "Consecrate" })).toBeTruthy();

    await fireEvent.click(screen.getByRole("button", { name: "Cancel run run-a" }));

    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull();
    expect(attention.at(-1)).toBe(0);
    window.removeEventListener("altar:attention", receiveAttention);
    view.unmount();
  });

  it("revokes consent authority on the session selected by the root Bridge route", async () => {
    const initial = snapshot("session-a", [projection()]);
    initial.pending_consents = [pendingConsent];
    initial.pending_count = 1;
    getSnapshotMock
      .mockResolvedValueOnce(initial)
      .mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    const view = render(BridgeView);
    expect(await screen.findByRole("button", { name: "Consecrate" })).toBeTruthy();

    await fireEvent.click(screen.getByRole("button", { name: "Cancel run run-a" }));

    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull();
    view.unmount();
  });

  it("preserves a root-route draft while cancellation refreshes the same session", async () => {
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    const view = render(BridgeView);
    const message = (await screen.findByLabelText("Message")) as HTMLTextAreaElement;
    await fireEvent.input(message, { target: { value: "Keep this unsent thought" } });

    await fireEvent.click(screen.getByRole("button", { name: "Cancel run run-a" }));

    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(message.value).toBe("Keep this unsent thought");
    view.unmount();
  });

  it("revokes stale consent authority when cancellation refetch fails", async () => {
    const initial = snapshot("session-a", [projection()]);
    initial.pending_consents = [pendingConsent];
    initial.pending_count = 1;
    getSnapshotMock
      .mockResolvedValueOnce(initial)
      .mockRejectedValue(new Error("Snapshot unavailable"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByRole("button", { name: "Consecrate" })).toBeTruthy();

    await fireEvent.click(screen.getByRole("button", { name: "Cancel run run-a" }));

    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull();
    expect(screen.getByText("Snapshot unavailable")).toBeTruthy();
    view.unmount();
  });

  it("ignores an older consent count after a newer snapshot arrives", async () => {
    const initial = snapshot("session-a", [projection()]);
    initial.pending_consents = [pendingConsent];
    initial.pending_count = 1;
    getSnapshotMock.mockResolvedValue(initial);
    const decision = deferred<Awaited<ReturnType<typeof decideConsent>>>();
    decideConsentMock.mockReturnValue(decision.promise);
    const attention: number[] = [];
    const receiveAttention = (event: Event) => {
      attention.push((event as CustomEvent<number>).detail);
    };
    window.addEventListener("altar:attention", receiveAttention);
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));

    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    await act(() =>
      decision.resolve({
        consent: { ...pendingConsent, state: "consented" },
        pending_count: 0
      })
    );
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(3));

    expect(screen.getByRole("button", { name: "Consecrate" })).toBeTruthy();
    expect(attention).not.toContain(0);
    window.removeEventListener("altar:attention", receiveAttention);
    view.unmount();
  });

  it("resolves a lost cancel response from the authoritative Run projection", async () => {
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    cancelMock.mockRejectedValue(new Error("Response lost"));
    getRunSnapshotMock.mockResolvedValue(cancelledProjection());
    const view = render(BridgeView, { sessionId: "session-a" });

    await fireEvent.click(await screen.findByRole("button", { name: "Cancel run run-a" }));

    expect(getRunSnapshotMock).toHaveBeenCalledWith("run-a");
    expect(await screen.findAllByText("cancelled")).toHaveLength(2);
    expect(screen.queryByText("Response lost")).toBeNull();
    view.unmount();
  });

  it("reconstructs and reattaches an active run after a route remount", async () => {
    const active = projection();
    const close = vi.fn();
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [active]));
    listenMock.mockReturnValue(close);
    const view = render(BridgeView, { sessionId: "session-a" });

    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledWith(
      "run-a",
      expect.any(Function),
      expect.any(Function),
      expect.any(Function),
      {
        initialCursor: 17,
        onHardClose: expect.any(Function)
      }
    );

    const onEvent = latestRunListener();
    await act(() =>
      onEvent(event("run-a", 18, "token", { text: " continuation" }))
    );
    expect(screen.getByText("authoritative partial continuation")).toBeTruthy();

    view.unmount();
    expect(close).toHaveBeenCalledOnce();

    listenMock.mockClear();
    const remounted = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledWith(
      "run-a",
      expect.any(Function),
      expect.any(Function),
      expect.any(Function),
      {
        initialCursor: 17,
        onHardClose: expect.any(Function)
      }
    );
    remounted.unmount();
  });

  it("performs one bounded authoritative recovery after a hard close", async () => {
    const active = projection();
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [active]));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledOnce();

    const firstCall = listenMock.mock.calls[0];
    if (!firstCall) throw new Error("The initial stream was not attached.");
    await act(() => firstCall[2]("The run stream went quiet; reconnecting."));
    expect(listenMock).toHaveBeenCalledOnce();

    const onHardClose = firstCall[4]?.onHardClose;
    if (!onHardClose) throw new Error("The hard-close hook was not registered.");
    getRunSnapshotMock.mockResolvedValue({
      ...projection(),
      cursor: 19,
      content: "recovered projection"
    });
    await act(() => onHardClose("The Vessel emitted an invalid run event."));

    expect(await screen.findByText("recovered projection")).toBeTruthy();
    expect(getRunSnapshotMock).toHaveBeenCalledOnce();
    expect(listenMock).toHaveBeenCalledTimes(2);
    expect(listenMock.mock.calls[1]?.[4]?.initialCursor).toBe(19);

    const secondHardClose = listenMock.mock.calls[1]?.[4]?.onHardClose;
    if (!secondHardClose) throw new Error("The recovered stream has no hard-close hook.");
    await act(() => secondHardClose("The Vessel emitted an invalid run event."));
    expect(screen.getByText("projection stale")).toBeTruthy();
    expect(getRunSnapshotMock).toHaveBeenCalledOnce();
    expect(listenMock).toHaveBeenCalledTimes(2);
    view.unmount();
  });

  it("does not let delayed hard-close recovery overwrite a newer session projection", async () => {
    const sessionRefresh = deferred<BridgeSnapshot>();
    const recovery = deferred<RunProjectionSnapshot>();
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockReturnValueOnce(sessionRefresh.promise);
    getRunSnapshotMock.mockReturnValue(recovery.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();

    const firstCall = listenMock.mock.calls[0];
    if (!firstCall) throw new Error("The initial stream was not attached.");
    const onHardClose = firstCall[4]?.onHardClose;
    if (!onHardClose) throw new Error("The hard-close hook was not registered.");
    await act(() => onHardClose("The Vessel emitted an invalid run event."));
    await act(() => firstCall[1](event("run-a", 18, "consent", {})));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));

    await act(() =>
      sessionRefresh.resolve(
        snapshot("session-a", [
          { ...projection(), cursor: 24, content: "newer session projection" }
        ])
      )
    );
    expect(await screen.findByText("newer session projection")).toBeTruthy();

    await act(() =>
      recovery.resolve({ ...projection(), cursor: 19, content: "delayed recovery" })
    );

    expect(screen.queryByText("delayed recovery")).toBeNull();
    expect(screen.getByText("newer session projection")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledTimes(2);
    expect(listenMock.mock.calls[1]?.[4]?.initialCursor).toBe(24);
    view.unmount();
  });

  it("does not poll a terminal projection that legitimately lacks an agent turn", async () => {
    vi.useFakeTimers();
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    const view = render(BridgeView, { sessionId: "session-a" });
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getAllByText("cancelled")).toHaveLength(2);
    getSnapshotMock.mockClear();

    await act(() => vi.advanceTimersByTime(500));

    expect(getSnapshotMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("keeps a delayed session-A admission out of session B", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValue(admission.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();

    await offer("message from A");
    expect(sendMock).toHaveBeenCalledWith("session-a", "message from A", expect.any(String));

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("");

    await act(() => admission.resolve(accepted("run-a", "message from A")));
    expect(screen.queryByText("message from A")).toBeNull();

    const onEvent = latestRunListener();
    await act(() => onEvent(event("run-a", 0, "token", { text: "answer for A" })));
    expect(screen.queryByText("answer for A")).toBeNull();

    await view.rerender({ sessionId: "session-a" });
    expect(await screen.findByText("answer for A")).toBeTruthy();
  });

  it("does not attach a run stream when admission completes after destroy", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValue(admission.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();
    await offer("late admission");

    view.unmount();
    await act(() => admission.resolve(accepted("run-a", "late admission")));

    expect(listenMock).not.toHaveBeenCalled();
  });

  it("does not let a delayed session-A failure block or stain session B", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock
      .mockReturnValueOnce(admission.promise)
      .mockResolvedValueOnce(accepted("run-b", "message from B"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();
    await offer("message from A");

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await offer("message from B");
    expect(sendMock).toHaveBeenNthCalledWith(2, "session-b", "message from B", expect.any(String));

    await act(() => admission.reject(new Error("session A failed late")));
    expect(screen.queryByText("session A failed late")).toBeNull();
    expect(screen.getByText("message from B")).toBeTruthy();
    view.unmount();
  });

  it("reuses one request identity after an ambiguous admission response", async () => {
    sendMock
      .mockRejectedValueOnce(new TypeError("response lost"))
      .mockResolvedValueOnce(accepted("run-a", "one offering"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();

    await offer("one offering");
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("one offering");
    await fireEvent.click(screen.getByRole("button", { name: /Offer/ }));
    await act(async () => {
      await Promise.resolve();
    });

    expect(sendMock).toHaveBeenCalledTimes(2);
    const firstRequestId = sendMock.mock.calls[0]?.[2];
    const secondRequestId = sendMock.mock.calls[1]?.[2];
    expect(firstRequestId).toMatch(/^[0-9a-f-]{36}$/i);
    expect(secondRequestId).toBe(firstRequestId);
    expect(await screen.findByText("one offering")).toBeTruthy();
    view.unmount();
  });

  it("removes the previous session authority when replacement loading fails", async () => {
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a"))
      .mockRejectedValueOnce(new Error("Session B unavailable"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();
    expect(screen.getByLabelText("Message")).toBeTruthy();

    await view.rerender({ sessionId: "session-b" });

    expect(await screen.findByText("Session B unavailable")).toBeTruthy();
    expect(screen.queryByText("session-a")).toBeNull();
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("rechecks the route inside a delayed DONE refresh and clears timers on destroy", async () => {
    sendMock.mockResolvedValue(accepted("run-a", "message from A"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();
    await offer("message from A");

    const onEvent = latestRunListener();
    vi.useFakeTimers();
    await act(() =>
      onEvent(
        event("run-a", 1, "done", {
          status: "done",
          turn: { content: "settled A" }
        })
      )
    );

    await view.rerender({ sessionId: "session-b" });
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText("session-b")).toBeTruthy();
    getSnapshotMock.mockClear();

    await act(() => vi.advanceTimersByTime(50));
    expect(getSnapshotMock).not.toHaveBeenCalled();
    expect(screen.getByText("session-b")).toBeTruthy();

    await view.rerender({ sessionId: "session-a" });
    await act(async () => {
      await Promise.resolve();
    });
    await act(() =>
      onEvent(
        event("run-a", 1, "done", {
          status: "done",
          turn: { content: "settled A" }
        })
      )
    );
    view.unmount();
    getSnapshotMock.mockClear();

    await act(() => vi.advanceTimersByTime(50));
    expect(getSnapshotMock).not.toHaveBeenCalled();
  });
});
