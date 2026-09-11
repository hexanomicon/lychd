import { SvelteURL } from "svelte/reactivity";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BridgeSnapshot,
  ConsentCard as ConsentCardModel,
  RunEventEnvelope,
  RunProjectionSnapshot
} from "$lib/api/models";
import { goto, replaceState } from "$app/navigation";

const mockPage = vi.hoisted(() => ({ state: {} as { bridgeComposerFocus?: string }, url: new URL("http://localhost/bridge") }));
vi.mock("$app/state", () => ({ page: mockPage }));
vi.mock("$app/navigation", () => ({ goto: vi.fn(), replaceState: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    status?: number;
  },
  cancelBridgeRun: vi.fn(),
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getBridgeSnapshot: vi.fn(),
  getBridgeSessions: vi.fn(),
  getAtlasReferences: vi.fn().mockResolvedValue([]),
  getAtlasProject: vi.fn(),
  getRunSnapshot: vi.fn(),
  listenToRun: vi.fn(),
  sendBridgeMessage: vi.fn()
}));

import {
  ApiError,
  getAtlasProject,
  cancelBridgeRun,
  createBridgeSession,
  decideConsent,
  getBridgeSnapshot,
  getBridgeSessions,
  getRunSnapshot,
  listenToRun,
  sendBridgeMessage
} from "$lib/api/client";
import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/bridge/workspace.svelte";
import BridgeView from "./BridgeView.svelte";

const createdAt = "2026-07-28T00:00:00Z";
const cancelMock = vi.mocked(cancelBridgeRun);
const decideConsentMock = vi.mocked(decideConsent);
const getSnapshotMock = vi.mocked(getBridgeSnapshot);
const getSessionsMock = vi.mocked(getBridgeSessions);
const getRunSnapshotMock = vi.mocked(getRunSnapshot);
const listenMock = vi.mocked(listenToRun);
const sendMock = vi.mocked(sendBridgeMessage);

const pendingConsent: ConsentCardModel = {
  args: { target: "chat:local" },
  id: "consent-a",
  run_id: "run-a",
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
    created_at: createdAt,
    pending_count: 0
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
  mockPage.state = {};
  mockPage.url = new URL("http://localhost/bridge");
  getSnapshotMock.mockImplementation(async (sessionId) =>
    snapshot(sessionId ?? "session-a")
  );
  getRunSnapshotMock.mockResolvedValue(projection());
  getSessionsMock.mockReset();
  listenMock.mockImplementation(() => vi.fn());
  cancelMock.mockResolvedValue(cancelledProjection());
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Bridge route and stream ownership", () => {
  it("loads one older page at a time, retaining the selected conversation and unique rail identities", async () => {
    getSnapshotMock.mockResolvedValueOnce({ ...snapshot("session-a"), sessions_next_cursor: "older-page" });
    const page = deferred<Awaited<ReturnType<typeof getBridgeSessions>>>();
    getSessionsMock.mockReturnValueOnce(page.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    const more = await screen.findByRole("button", { name: "Load more conversations" });
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "retained draft" } });
    await fireEvent.click(more);
    await fireEvent.click(more);
    expect(getSessionsMock).toHaveBeenCalledOnce();
    expect(getSessionsMock.mock.calls[0]?.[0]).toBe("older-page");
    expect((more as HTMLButtonElement).disabled).toBe(true);
    const older = { id: "session-c", title: "Séance C", created_at: createdAt, pending_count: 0 };
    await act(() => page.resolve({
      sessions: [...snapshot("session-a").sessions, older, older], next_cursor: null
    }));
    expect(screen.getAllByRole("link", { name: /Séance C/ })).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: /Séance A/ })).toHaveLength(1);
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("retained draft");
    expect(screen.queryByRole("button", { name: "Load more conversations" })).toBeNull();
    view.unmount();
  });

  it("keeps a failed page retryable without discarding already loaded conversations", async () => {
    getSnapshotMock.mockResolvedValueOnce({ ...snapshot("session-a"), sessions_next_cursor: "older-page" });
    getSessionsMock.mockRejectedValueOnce(new Error("network unavailable"));
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Load more conversations" }));
    expect(await screen.findByText("Older conversations could not be loaded. Try again.")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Séance A/ })).toBeTruthy();
    getSessionsMock.mockResolvedValueOnce({ sessions: [], next_cursor: null });
    await fireEvent.click(screen.getByRole("button", { name: "Load more conversations" }));
    await waitFor(() => expect(screen.queryByText("Older conversations could not be loaded. Try again.")).toBeNull());
    expect(getSessionsMock.mock.calls.map(([cursor]) => cursor)).toEqual(["older-page", "older-page"]);
    view.unmount();
  });

  it("aborts and discards an older page when the route snapshot changes", async () => {
    getSnapshotMock.mockResolvedValueOnce({ ...snapshot("session-a"), sessions_next_cursor: "older-page" });
    const page = deferred<Awaited<ReturnType<typeof getBridgeSessions>>>();
    getSessionsMock.mockReturnValueOnce(page.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Load more conversations" }));
    const signal = getSessionsMock.mock.calls[0]?.[1];
    await view.rerender({ sessionId: "session-b" });
    await waitFor(() => expect(getSnapshotMock).toHaveBeenLastCalledWith("session-b"));
    expect(signal?.aborted).toBe(true);
    await act(() => page.resolve({
      sessions: [{ id: "session-c", title: "Stale page", created_at: createdAt, pending_count: 0 }], next_cursor: "stale-cursor"
    }));
    expect(screen.queryByRole("link", { name: /Stale page/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Load more conversations" })).toBeNull();
    view.unmount();
  });

  it("aborts an in-flight older page when a live event refreshes the same session or the view unmounts", async () => {
    getSnapshotMock.mockResolvedValue({ ...snapshot("session-a", [projection()]), sessions_next_cursor: "older-page" });
    const page = deferred<Awaited<ReturnType<typeof getBridgeSessions>>>();
    getSessionsMock.mockReturnValue(page.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Load more conversations" }));
    const firstSignal = getSessionsMock.mock.calls[0]?.[1];
    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Load more conversations" }));
    const secondSignal = getSessionsMock.mock.calls[1]?.[1];
    expect(secondSignal?.aborted).toBe(false);
    view.unmount();
    expect(secondSignal?.aborted).toBe(true);
    await act(() => page.reject(new Error("aborted transport")));
  });

  it("keeps older pending conversations discoverable in the attention filter", async () => {
    mockPage.url = new URL("http://localhost/bridge?attention=pending");
    getSnapshotMock.mockResolvedValueOnce({ ...snapshot("session-a"), pending_count: 1, sessions_next_cursor: "older-page" });
    getSessionsMock.mockResolvedValueOnce({
      sessions: [{ id: "session-c", title: "Older pending séance", created_at: createdAt, pending_count: 1 }], next_cursor: null
    });
    const view = render(BridgeView);
    expect(await screen.findByText("Load more conversations to find older pending requests.")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Load more conversations" }));
    expect(await screen.findByRole("link", { name: /Older pending séance/ })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Séance A/ })).toBeNull();
    view.unmount();
  });

  it("keeps the original uncertain consent verdict through its recovery refresh", async () => {
    getSnapshotMock.mockImplementation(async () => ({
      ...snapshot("session-a"), pending_consents: [pendingConsent], pending_count: 1
    }));
    decideConsentMock.mockRejectedValue(new TypeError("decision response lost"));
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));

    const refuse = await screen.findByRole("button", { name: "Refuse" });
    expect((refuse as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.click(refuse);
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    expect(decideConsentMock.mock.calls).toEqual([
      [pendingConsent.id, "approve"], [pendingConsent.id, "approve"]
    ]);
    view.unmount();
  });

  it("keeps an in-flight consent decision busy through a stream-triggered refresh", async () => {
    getSnapshotMock.mockImplementation(async () => ({
      ...snapshot("session-a", [projection()]), pending_consents: [pendingConsent], pending_count: 1
    }));
    const decision = deferred<Awaited<ReturnType<typeof decideConsent>>>();
    decideConsentMock.mockReturnValue(decision.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));
    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));

    expect((await screen.findByRole("button", { name: "Refuse" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Consecrate" }) as HTMLButtonElement).disabled).toBe(true);
    await act(() => decision.resolve({ consent: { ...pendingConsent, state: "consented" }, pending_count: 0 }));
    expect(decideConsentMock).toHaveBeenCalledOnce();
    view.unmount();
  });

  it("does not admit a message while Enter confirms an IME composition", async () => {
    sendMock.mockResolvedValue(accepted("run-a", "日本語"));
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByLabelText("Message");
    await fireEvent.input(composer, { target: { value: "日本語" } });
    await fireEvent.keyDown(composer, { key: "Enter", isComposing: true });
    expect(sendMock).not.toHaveBeenCalled();
    expect((composer as HTMLTextAreaElement).value).toBe("日本語");
    await fireEvent.keyDown(composer, { key: "Enter" });
    expect(sendMock).toHaveBeenCalledOnce();
    view.unmount();
  });

  it("opens the first séance once and focuses its composer", async () => {
    getSnapshotMock.mockResolvedValueOnce({
      sessions: [], session: null, active_runs: [], pending_consents: [], pending_count: 0
    });
    let finish!: (value: Awaited<ReturnType<typeof createBridgeSession>>) => void;
    vi.mocked(createBridgeSession).mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    const view = render(BridgeView);
    expect(await screen.findByRole("heading", { name: "Begin a séance." })).toBeTruthy();
    const begin = screen.getByRole("button", { name: "New Séance" });
    await fireEvent.click(begin);
    await fireEvent.click(begin);
    expect(createBridgeSession).toHaveBeenCalledTimes(1);
    expect((begin as HTMLButtonElement).disabled).toBe(true);
    const created = snapshot("session-b").session;
    if (!created) throw new Error("The fixture has no created session.");
    finish({ session: created });
    await waitFor(() => expect(goto).toHaveBeenCalledWith("/bridge/session-b", {
      keepFocus: true, state: { bridgeComposerFocus: "session-b" }
    }));
    view.unmount();
    mockPage.state = { bridgeComposerFocus: "session-b" };
    const destination = render(BridgeView, { sessionId: "session-b" });
    const composer = await screen.findByRole("textbox", { name: "Message" });
    await waitFor(() => expect(document.activeElement).toBe(composer));
    expect(replaceState).toHaveBeenCalledWith("", {});
    expect(screen.queryByRole("heading", { name: "Begin a séance." })).toBeNull();
    destination.unmount();
  });

  it("does not mistake a pending or failed read for first use", async () => {
    let fail!: (reason: Error) => void;
    getSnapshotMock.mockReturnValueOnce(new Promise((_resolve, reject) => { fail = reject; }));
    const view = render(BridgeView);
    expect(screen.queryByRole("heading", { name: "Begin a séance." })).toBeNull();
    fail(new Error("Bridge unavailable"));
    expect(await screen.findByText("Bridge unavailable")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Begin a séance." })).toBeNull();
    expect(createBridgeSession).not.toHaveBeenCalled();
    view.unmount();
  });

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

  it("resumes from a snapshot after HTTP 429 closes the stream and capacity becomes free", async () => {
    class BudgetEventSource extends EventTarget {
      static CLOSED = 2;
      static instances: BudgetEventSource[] = [];
      readyState = 1;
      onerror: ((event: Event) => void) | null = null;
      constructor(_url: string) {
        super();
        BudgetEventSource.instances.push(this);
      }
      close() { this.readyState = BudgetEventSource.CLOSED; }
      rejectHttp() {
        this.close();
        this.onerror?.(new Event("error"));
      }
    }
    vi.stubGlobal("EventSource", BudgetEventSource);
    const actual = await vi.importActual<typeof import("$lib/api/client")>("$lib/api/client");
    listenMock.mockImplementation(actual.listenToRun);
    const recovery = deferred<RunProjectionSnapshot>();
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [projection()]));
    getRunSnapshotMock.mockReturnValueOnce(recovery.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    const first = BudgetEventSource.instances[0];
    if (!first) throw new Error("The initial stream was not attached.");

    // Model the browser's permanent CLOSED result for the server's HTTP 429.
    await act(() => first.rejectHttp());
    expect(getRunSnapshotMock).toHaveBeenCalledOnce();
    expect(BudgetEventSource.instances).toHaveLength(1);
    expect(screen.getByText("projection stale")).toBeTruthy();

    // Capacity is now free. The recovery snapshot admits one new stream at its cursor.
    await act(() => recovery.resolve({ ...projection(), cursor: 19, content: "recovered projection" }));
    expect(BudgetEventSource.instances).toHaveLength(2);
    const resumed = BudgetEventSource.instances[1];
    if (!resumed) throw new Error("The recovered stream was not attached.");
    await act(() => {
      resumed.dispatchEvent(new MessageEvent("token", {
        data: JSON.stringify(event("run-a", 20, "token", { text: " continued" }))
      }));
    });
    expect(await screen.findByText("recovered projection continued")).toBeTruthy();

    // A repeated refusal exhausts the same Run's recovery budget instead of looping.
    await act(() => resumed.rejectHttp());
    expect(getRunSnapshotMock).toHaveBeenCalledOnce();
    expect(BudgetEventSource.instances).toHaveLength(2);
    expect(screen.getByText("projection stale")).toBeTruthy();
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

  it("settles an attached stream from a terminal session snapshot without an agent turn", async () => {
    const close = vi.fn();
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValueOnce(snapshot("session-b"))
      .mockResolvedValueOnce(snapshot("session-a", [cancelledProjection()]));
    listenMock.mockReturnValue(close);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();

    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await view.rerender({ sessionId: "session-a" });

    expect(await screen.findAllByText("cancelled")).toHaveLength(2);
    expect(screen.getByText("authoritative partial")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Cancel run run-a" })).toBeNull();
    expect(close).toHaveBeenCalledOnce();
    expect(listenMock).toHaveBeenCalledOnce();
    view.unmount();
  });

  it.each([18, 17])("recovers once when terminal session authority is overtaken, with recovery cursor %s", async (cursor) => {
    const terminalRead = deferred<BridgeSnapshot>();
    const recovery = deferred<RunProjectionSnapshot>();
    const close = vi.fn();
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValueOnce(snapshot("session-b"))
      .mockReturnValueOnce(terminalRead.promise);
    getRunSnapshotMock.mockReturnValueOnce(recovery.promise);
    listenMock.mockReturnValue(close);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("authoritative partial")).toBeTruthy();
    const onEvent = latestRunListener();
    await view.rerender({ sessionId: "session-b" });
    expect(await screen.findByText("session-b")).toBeTruthy();
    await view.rerender({ sessionId: "session-a" });
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(3));

    await act(() => onEvent(event("run-a", 18, "token", { text: " continuation" })));
    await act(() => terminalRead.resolve(snapshot("session-a", [{ ...cancelledProjection(), cursor: 18 }])));

    await waitFor(() => expect(getRunSnapshotMock).toHaveBeenCalledOnce());
    expect(close).toHaveBeenCalledOnce();
    expect(screen.getByText("projection stale")).toBeTruthy();
    await act(() => recovery.resolve({
      ...cancelledProjection(), cursor, content: "authoritative partial continuation"
    }));

    expect(screen.getByText("authoritative partial continuation")).toBeTruthy();
    if (cursor === 18) {
      expect(screen.getAllByText("cancelled")).toHaveLength(2);
    } else {
      expect(screen.getByText("projection stale")).toBeTruthy();
      getSnapshotMock.mockImplementation(async (id) =>
        snapshot(id ?? "session-a", id === "session-b" ? [] : [cancelledProjection()])
      );
      await view.rerender({ sessionId: "session-b" });
      expect(await screen.findByText("session-b")).toBeTruthy();
      await view.rerender({ sessionId: "session-a" });
      expect(await screen.findByText("projection stale")).toBeTruthy();
    }
    expect(getRunSnapshotMock).toHaveBeenCalledOnce();
    expect(listenMock).toHaveBeenCalledOnce();
    view.unmount();
  });

  it.each(["authoritative partial", ""])("shows a failed Run without inventing reply text when retained content is %j", async (content) => {
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [{ ...projection(), content }]));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByRole("button", { name: "Cancel run run-a" })).toBeTruthy();

    await act(() => latestRunListener()(event("run-a", 18, "done", { status: "failed", turn: null })));

    expect(screen.getAllByText("failed")).toHaveLength(2);
    expect(screen.getByText(content || "No reply text was retained for this Run.")).toBeTruthy();
    expect(screen.queryByText("The turn has settled.")).toBeNull();
    expect(screen.queryByRole("button", { name: "Cancel run run-a" })).toBeNull();
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
    expect(screen.getByRole("region", { name: "Unresolved offering" }).textContent).toContain("one offering");
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));
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

  it("keeps a timed-out offering and its retry identity separate from a later draft", async () => {
    const timeout = Object.assign(new ApiError("Admission timed out"), { status: 408 });
    sendMock
      .mockRejectedValueOnce(timeout)
      .mockResolvedValueOnce(accepted("run-a", "original offering"));
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByText("session-a")).toBeTruthy();

    await offer("original offering");
    expect(screen.getByRole("region", { name: "Unresolved offering" }).textContent).toContain("original offering");
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "later draft" } });
    expect((screen.getByRole("button", { name: "Offer" }) as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));

    expect(sendMock).toHaveBeenCalledTimes(2);
    expect(sendMock).toHaveBeenNthCalledWith(2, "session-a", "original offering", sendMock.mock.calls[0]?.[2]);
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("later draft");
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


describe("Bridge shell recovery and deliberate handoffs", () => {
  function mountWithWork(work: ReturnType<typeof createBridgeWorkspace>, sessionId = "session-a") {
    return render(BridgeView, { props: { sessionId }, context: new Map([[bridgeWorkspaceKey, work]]) });
  }

  it("retains an uncertain consent across instrument remount and later middleware refusal", async () => {
    getSnapshotMock.mockImplementation(async (id = "session-a") => ({
      ...snapshot(id), pending_consents: id === "session-a" ? [pendingConsent] : [], pending_count: 1
    }));
    const refusal = new ApiError("Scope refused");
    Object.assign(refusal, { status: 403 });
    decideConsentMock.mockRejectedValueOnce(new TypeError("decision response lost"))
      .mockRejectedValueOnce(refusal)
      .mockResolvedValueOnce({ consent: { ...pendingConsent, state: "consented" }, pending_count: 0 });
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));
    expect(work.needsUnloadWarning).toBe(true);
    first.unmount();
    const other = mountWithWork(work, "session-b");
    await screen.findByLabelText("Message");
    expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull();
    other.unmount();
    const returned = mountWithWork(work);
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));
    await screen.findByText("Scope refused");
    const refuse = await screen.findByRole("button", { name: "Refuse" });
    expect((refuse as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.click(refuse);
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    expect(decideConsentMock.mock.calls).toEqual(Array(3).fill([pendingConsent.id, "approve"]));
    expect(await screen.findByRole("group", { name: "approved consent" })).toBeTruthy();
    expect(work.consentDecisions.size).toBe(0);
    expect(work.needsUnloadWarning).toBe(false);
    returned.unmount();
  });

  it("reconciles a consent response delivered after the original Bridge unmounts", async () => {
    let decided = false;
    getSnapshotMock.mockImplementation(async () => ({
      ...snapshot("session-a"), pending_consents: decided ? [] : [pendingConsent], pending_count: decided ? 0 : 1
    }));
    const response = deferred<Awaited<ReturnType<typeof decideConsent>>>();
    decideConsentMock.mockReturnValue(response.promise);
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await fireEvent.click(await screen.findByRole("button", { name: "Consecrate" }));
    first.unmount();
    const returned = mountWithWork(work);
    expect((await screen.findByRole("button", { name: "Refuse" }) as HTMLButtonElement).disabled).toBe(true);
    decided = true;
    await act(() => response.resolve({ consent: { ...pendingConsent, state: "consented" }, pending_count: 0 }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Consecrate" })).toBeNull());
    expect(getSnapshotMock).toHaveBeenCalledTimes(3);
    expect(decideConsentMock).toHaveBeenCalledOnce();
    expect(work.consentDecisions.size).toBe(0);
    expect(work.needsUnloadWarning).toBe(false);
    returned.unmount();
  });

  it("restores exact-session drafts across remounts without sending or leaking them", async () => {
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await screen.findByLabelText("Message");
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "unfinished A" } });
    expect(work.needsUnloadWarning).toBe(true);
    first.unmount();
    const other = mountWithWork(work, "session-b");
    await screen.findByLabelText("Message");
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("");
    other.unmount();
    const returned = mountWithWork(work);
    await screen.findByLabelText("Message");
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("unfinished A");
    expect(sendMock).not.toHaveBeenCalled();
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "" } });
    expect(work.needsUnloadWarning).toBe(false);
    returned.unmount();
  });

  it("retains the immutable unknown request across remount, later refusal, and a different draft", async () => {
    const refusal = new ApiError("Scope refused");
    Object.assign(refusal, { status: 403 });
    sendMock.mockRejectedValueOnce(new TypeError("Response lost"))
      .mockRejectedValueOnce(refusal)
      .mockResolvedValueOnce(accepted("run-a", "original offering"));
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await screen.findByLabelText("Message");
    await offer("original offering");
    first.unmount();
    const returned = mountWithWork(work);
    await screen.findByRole("button", { name: "Retry original offering" });
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "later draft" } });
    await fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter" });
    expect(sendMock).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Offer" }) as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));
    await screen.findByText("Scope refused");
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));
    await waitFor(() => expect(sendMock).toHaveBeenCalledTimes(3));
    expect(sendMock.mock.calls.map((call) => call[2])).toEqual(Array(3).fill(sendMock.mock.calls[0]![2]));
    expect(sendMock.mock.calls.every((call) => call[1] === "original offering")).toBe(true);
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("later draft");
    expect(work.pending.size).toBe(0);
    returned.unmount();
  });

  it("settles an in-flight response after unmount and refreshes the remounted conversation", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValueOnce(admission.promise);
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await screen.findByLabelText("Message");
    await offer("in flight");
    first.unmount();
    const returned = mountWithWork(work);
    await screen.findByLabelText("Message");
    getSnapshotMock.mockClear();
    await act(() => admission.resolve(accepted("run-a", "in flight")));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledWith("session-a"));
    expect(work.pending.size).toBe(0);
    expect(work.needsUnloadWarning).toBe(false);
    expect(sendMock).toHaveBeenCalledTimes(1);
    returned.unmount();
  });

  it("recovers a failure arriving after unmount with the same request identity", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValueOnce(admission.promise).mockResolvedValueOnce(accepted("run-a", "late failure"));
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await screen.findByLabelText("Message");
    await offer("late failure");
    first.unmount();
    await act(() => admission.reject(new TypeError("Lost late")));
    const returned = mountWithWork(work);
    await screen.findByRole("button", { name: "Retry original offering" });
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));
    expect(sendMock.mock.calls[1]![2]).toBe(sendMock.mock.calls[0]![2]);
    returned.unmount();
  });

  it("keeps a definitely refused text alongside a later draft across remount", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValueOnce(admission.promise);
    const work = createBridgeWorkspace();
    const first = mountWithWork(work);
    await screen.findByLabelText("Message");
    await offer("refused original");
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "later draft" } });
    const refusal = Object.assign(new ApiError("Admission refused"), { status: 403 });
    await act(() => admission.reject(refusal));
    first.unmount();
    const returned = mountWithWork(work);
    await screen.findByRole("region", { name: "Refused offering" });
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("later draft");
    expect(screen.getByText("refused original")).toBeTruthy();
    expect(work.pending.size).toBe(0);
    expect((screen.getByRole("button", { name: "Restore refused offering" }) as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "" } });
    await fireEvent.click(screen.getByRole("button", { name: "Restore refused offering" }));
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("refused original");
    expect(work.refused.size).toBe(0);
    expect(sendMock).toHaveBeenCalledTimes(1);
    returned.unmount();
  });

  it("hides the prior composer immediately when a same-component attention chooser read stalls", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge");
    const work = createBridgeWorkspace();
    const view = render(BridgeView, { context: new Map([[bridgeWorkspaceKey, work]]) });
    await screen.findByLabelText("Message");
    await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "draft for A" } });
    const read = deferred<BridgeSnapshot>();
    getSnapshotMock.mockReturnValueOnce(read.promise);
    await act(() => { mockPage.url.search = "?attention=pending"; });
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(screen.queryByRole("button", { name: "Offer" })).toBeNull();
    await act(() => read.reject(new Error("Chooser unavailable")));
    expect(await screen.findByText("Chooser unavailable")).toBeTruthy();
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(work.drafts.get("session-a")).toBe("draft for A");
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("refetches when admission completes ahead of an older returning session snapshot", async () => {
    const admission = deferred<Awaited<ReturnType<typeof sendBridgeMessage>>>();
    sendMock.mockReturnValueOnce(admission.promise);
    const work = createBridgeWorkspace();
    const view = mountWithWork(work);
    await screen.findByLabelText("Message");
    await offer("message arriving during return");
    await view.rerender({ sessionId: "session-b" });
    await screen.findByText("session-b");
    const olderRead = deferred<BridgeSnapshot>();
    getSnapshotMock.mockReturnValueOnce(olderRead.promise);
    await view.rerender({ sessionId: "session-a" });
    const newest = snapshot("session-a", [projection()]);
    newest.session!.turns = [accepted("run-a", "message arriving during return").turn];
    getSnapshotMock.mockResolvedValueOnce(newest);
    await act(() => admission.resolve(accepted("run-a", "message arriving during return")));
    await act(() => olderRead.resolve(snapshot("session-a")));
    expect(await screen.findByText("message arriving during return")).toBeTruthy();
    expect(getSnapshotMock).toHaveBeenCalledTimes(4);
    expect(sendMock).toHaveBeenCalledTimes(1);
    view.unmount();
  });

  it("focuses the exact Run again after another session and browser return", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-a");
    const settled = snapshot("session-a");
    settled.session!.turns = [{ ...accepted("run-a", "result for A").turn, role: "agent" }];
    getSnapshotMock.mockImplementation(async (id) => id === "session-b" ? snapshot(id) : settled);
    const view = render(BridgeView, { sessionId: "session-a" });
    const first = (await screen.findByText("result for A")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(first));
    await act(() => { mockPage.url.search = ""; });
    await view.rerender({ sessionId: "session-b" });
    await screen.findByText("session-b");
    await act(() => { mockPage.url.search = "?run=run-a"; });
    await view.rerender({ sessionId: "session-a" });
    const returned = (await screen.findByText("result for A")).closest("article");
    expect(returned).not.toBe(first);
    await waitFor(() => expect(document.activeElement).toBe(returned));
    view.unmount();
  });

  it("clears only the decided session's attention while preserving another session count", async () => {
    const initial = snapshot("session-a");
    initial.pending_consents = [{ ...pendingConsent }];
    initial.session!.pending_count = initial.sessions[0]!.pending_count = 1;
    initial.sessions[1]!.pending_count = 2;
    initial.pending_count = 3;
    getSnapshotMock.mockResolvedValueOnce(initial);
    decideConsentMock.mockResolvedValueOnce({ consent: { ...pendingConsent, state: "refused" }, pending_count: 2 });
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByRole("button", { name: "Consecrate" });
    await fireEvent.click(screen.getByRole("button", { name: "Refuse" }));
    await waitFor(() => expect(screen.getByRole("link", { name: /Séance A/ }).textContent).not.toContain("awaiting consent"));
    expect(screen.getByRole("link", { name: /Séance B/ }).textContent).toContain("2 awaiting consent");
    const label = screen.getByText("awaiting consent", { selector: "dt" });
    expect(label.nextElementSibling?.textContent).toBe("0");
    view.unmount();
  });

  it("opens a project chooser without selecting or submitting to the newest conversation", async () => {
    const id = "00000000-0000-4000-8000-000000000001";
    mockPage.url = new URL(`http://localhost/bridge?project=${id}&choose=conversation`);
    vi.mocked(getAtlasProject).mockResolvedValue({ id, title: "Project A" } as Awaited<ReturnType<typeof getAtlasProject>>);
    const view = render(BridgeView);
    await screen.findByRole("heading", { name: "Choose a conversation" });
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(screen.getByRole("link", { name: /Séance A/ }).getAttribute("href")).toBe(`/bridge/session-a?project=${id}`);
    expect(screen.getByRole("link", { name: /Project A/ }).getAttribute("href")).toBe(`/atlas/${id}`);
    expect(sendMock).not.toHaveBeenCalled();
    expect(createBridgeSession).not.toHaveBeenCalled();
    view.unmount();
  });

  it("routes global attention through only sessions with pending consent", async () => {
    mockPage.url = new URL("http://localhost/bridge?attention=pending");
    const next = snapshot("session-b");
    next.sessions[0]!.pending_count = 2;
    next.pending_count = 3;
    getSnapshotMock.mockResolvedValueOnce(next);
    const view = render(BridgeView);
    await screen.findByRole("heading", { name: "Conversations awaiting consent" });
    expect(screen.getByRole("link", { name: /Séance A.*2 awaiting consent/ }).getAttribute("href")).toBe("/bridge/session-a");
    expect(screen.queryByRole("link", { name: /Séance B/ })).toBeNull();
    expect(screen.queryByLabelText("Message")).toBeNull();
    view.unmount();
  });
});
