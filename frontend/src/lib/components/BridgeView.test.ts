import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BridgeSnapshot,
  RunEventEnvelope,
  RunProjectionSnapshot
} from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getBridgeSnapshot: vi.fn(),
  getRunSnapshot: vi.fn(),
  listenToRun: vi.fn(),
  sendBridgeMessage: vi.fn()
}));

import {
  getBridgeSnapshot,
  getRunSnapshot,
  listenToRun,
  sendBridgeMessage
} from "$lib/api/client";
import BridgeView from "./BridgeView.svelte";

const createdAt = "2026-07-28T00:00:00Z";
const getSnapshotMock = vi.mocked(getBridgeSnapshot);
const getRunSnapshotMock = vi.mocked(getRunSnapshot);
const listenMock = vi.mocked(listenToRun);
const sendMock = vi.mocked(sendBridgeMessage);

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
    terminal: false
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
  const promise = new Promise<T>((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
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
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Bridge route and stream ownership", () => {
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

  it("reattaches exactly once after a hard close but not a transient reconnect", async () => {
    let active = projection();
    getSnapshotMock.mockImplementation(async (sessionId) =>
      sessionId === "session-b"
        ? snapshot("session-b")
        : snapshot("session-a", [active])
    );
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledOnce();

    const firstCall = listenMock.mock.calls[0];
    if (!firstCall) throw new Error("The initial stream was not attached.");
    await act(() => firstCall[2]("The run stream went quiet; reconnecting."));

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await view.rerender({ sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledOnce();

    const onHardClose = firstCall[4]?.onHardClose;
    if (!onHardClose) throw new Error("The hard-close hook was not registered.");
    await act(() => onHardClose());
    active = {
      ...active,
      cursor: 19,
      content: "recovered projection"
    };

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await view.rerender({ sessionId: "session-a" });
    expect(await screen.findByText("recovered projection")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledTimes(2);
    expect(listenMock.mock.calls[1]?.[4]?.initialCursor).toBe(19);

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await view.rerender({ sessionId: "session-a" });
    expect(await screen.findByText("recovered projection")).toBeTruthy();
    expect(listenMock).toHaveBeenCalledTimes(2);
  });

  it("keeps a delayed session-A admission out of session B", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValue(admission.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();

    await offer("message from A");
    expect(sendMock).toHaveBeenCalledWith("session-a", "message from A");

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
