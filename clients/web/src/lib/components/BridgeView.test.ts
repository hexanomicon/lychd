import { SvelteURL } from "svelte/reactivity";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BridgeSnapshot,
  DictationDiscovery,
  DictationResult,
  ConsentCard as ConsentCardModel,
  RunEventEnvelope,
  RunProjectionSnapshot
} from "$lib/api/models";
import { beforeNavigate, goto, replaceState } from "$app/navigation";

const mockPage = vi.hoisted(() => ({ state: {} as { bridgeComposerFocus?: string }, url: new URL("http://localhost/bridge") }));
vi.mock("$app/state", () => ({ page: mockPage }));
vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn(), goto: vi.fn(), replaceState: vi.fn() }));
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
  sendBridgeMessage: vi.fn(),
  getDictationDiscovery: vi.fn(),
  getDictationAttempt: vi.fn(),
  transcribeDictation: vi.fn(),
  recordDictationCorrection: vi.fn(),
  listDictationCorrections: vi.fn().mockResolvedValue([]),
  deleteDictationAttempt: vi.fn(),
  listDictationLexicon: vi.fn().mockResolvedValue([]),
  approveDictationLexicon: vi.fn(),
  deleteDictationLexicon: vi.fn(),
  getDictationSuggestions: vi.fn()
}));

import {
  ApiError,
  getDictationDiscovery,
  transcribeDictation,
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
import { createWorkCommandRegistry, workCommandKey, type CommandResult, type CommandTarget } from "$lib/bridge/work-commands";
import { createVoiceCapture } from "$lib/bridge/voice/capture";
import type { VoiceCaptureOptions, VoiceRecording } from "$lib/bridge/voice/capture";
vi.mock("$lib/bridge/voice/capture", () => ({ createVoiceCapture: vi.fn(), VOICE_MAX_WAV_BYTES: 960044 }));
import { bridgePinsStorageKey } from "$lib/bridge/pins";

const createdAt = "2026-07-28T00:00:00Z";
const failedStreamNotice = "This Run failed. The text shown here is not a completed answer.";
const failureReply = "The summoning faltered. This request could not be completed.";
const cancelMock = vi.mocked(cancelBridgeRun);
const decideConsentMock = vi.mocked(decideConsent);
const getSnapshotMock = vi.mocked(getBridgeSnapshot);
const getSessionsMock = vi.mocked(getBridgeSessions);
const getRunSnapshotMock = vi.mocked(getRunSnapshot);
const listenMock = vi.mocked(listenToRun);
const sendMock = vi.mocked(sendBridgeMessage);

const pendingConsent: ConsentCardModel = {
  args: { target: "chat:local" },
  can_decide: true,
  native_review_status: "not_required",
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
  localStorage.clear();
  mockPage.state = {};
  mockPage.url = new URL("http://localhost/bridge");
  getSnapshotMock.mockImplementation(async (sessionId) =>
    snapshot(sessionId ?? "session-a")
  );
  getRunSnapshotMock.mockResolvedValue(projection());
  getSessionsMock.mockReset();
  listenMock.mockImplementation(() => vi.fn());
  cancelMock.mockResolvedValue(cancelledProjection());
  vi.mocked(getDictationDiscovery).mockResolvedValue({
    status: "unavailable", reason: "unconfigured", profile_digest: null, languages: [],
    max_audio_bytes: 1048576, max_audio_seconds: 30, sample_rate_hz: 16000, channels: 1,
    sample_width_bytes: 2, raw_audio_retention_seconds: 300
  } satisfies DictationDiscovery);
});

describe("Bridge pinned conversation rail", () => {
  it("keeps pins separate from recent conversations, survives remount and stores no titles or drafts", async () => {
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole("textbox", { name: "Message" });
    await fireEvent.input(composer, { target: { value: "private draft" } });
    const pin = screen.getByRole("button", { name: "Pin conversation: Séance B" });
    pin.focus();
    await fireEvent.click(pin);
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Unpin conversation: Séance B" }));
    expect(JSON.parse(localStorage.getItem(bridgePinsStorageKey)!)).toEqual(["session-b"]);
    const nav = screen.getByRole("navigation", { name: "Conversations" });
    expect(within(nav).getAllByRole("link").map((link) => link.querySelector(".t")?.textContent)).toEqual(["Séance B", "Séance A"]);
    expect(screen.getByLabelText("Message")).toBe(composer);
    expect(sendMock).not.toHaveBeenCalled();
    expect(getSnapshotMock).toHaveBeenCalledTimes(1);
    view.unmount();
    const next = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByRole("button", { name: "Unpin conversation: Séance B" })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Unpin conversation: Séance B" }));
    expect(localStorage.getItem(bridgePinsStorageKey)).toBe("[]");
    next.unmount();
  });

  it("shows unloaded pins as identity links and permits pinning an off-page selection without extra reads", async () => {
    localStorage.setItem(bridgePinsStorageKey, JSON.stringify(["older-unloaded"]));
    const response = snapshot("session-b");
    getSnapshotMock.mockResolvedValue({ ...response, sessions: [response.sessions[0]!] });
    const view = render(BridgeView, { sessionId: "session-b" });
    await screen.findByLabelText("Message");
    expect(screen.getByRole("link", { name: /Conversation · older-unloaded/ }).getAttribute("href")).toBe("/bridge/older-unloaded");
    expect(screen.getByText("Selected conversation")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Pin conversation: Séance B" }));
    expect(screen.queryByText("Selected conversation")).toBeNull();
    expect(JSON.parse(localStorage.getItem(bridgePinsStorageKey)!)).toEqual(["older-unloaded", "session-b"]);
    expect(getSnapshotMock).toHaveBeenCalledTimes(1);
    expect(getSessionsMock).not.toHaveBeenCalled();
    expect(sendMock).not.toHaveBeenCalled();
    const unloadedPin = screen.getByRole("button", { name: "Unpin conversation: older-unloaded" });
    unloadedPin.focus();
    await fireEvent.click(unloadedPin);
    expect(document.activeElement).toBe(screen.getByRole("button", { name: /New Séance/ }));
    view.unmount();
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Bridge configured composer guidance", () => {
  const guidance = "Declare the complete URL public.\n\n/read-public https://example.com/page\n<b>Ask your question here</b>";

  function guidedSnapshot(activeRuns: RunProjectionSnapshot[] = []): BridgeSnapshot {
    return {
      ...snapshot("session-a", activeRuns),
      composer: { pattern_id: "bridge_chat", pattern_revision: "4", guidance }
    };
  }

  it("links literal server instructions to the composer and retains line breaks", async () => {
    getSnapshotMock.mockResolvedValueOnce(guidedSnapshot());
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole("textbox", { name: "Message" });
    const instructions = document.getElementById("composer-instructions");
    expect(instructions?.textContent).toBe(guidance);
    expect(instructions?.querySelector("b")).toBeNull();
    expect(composer.getAttribute("aria-describedby")?.split(" ")).toEqual([
      "composer-instructions", "composer-guidance", "composer-shortcuts"
    ]);
    expect(screen.getByRole("textbox", {
      name: "Message", description: /Declare the complete URL public.*<b>Ask your question here<\/b>/s
    })).toBe(composer);
    expect(screen.queryByText("bridge_chat")).toBeNull();
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it.each(["guidance", "composer"] as const)("removes instructions on refreshed null %s without changing the draft", async (removed) => {
    const refreshed = snapshot("session-a", [projection()]);
    refreshed.composer = removed === "composer"
      ? null
      : { pattern_id: "bridge_chat", pattern_revision: "1", guidance: null };
    getSnapshotMock.mockResolvedValueOnce(guidedSnapshot([projection()])).mockResolvedValueOnce(refreshed);
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole<HTMLTextAreaElement>("textbox", { name: "Message" });
    expect(document.getElementById("composer-instructions")?.textContent).toBe(guidance);
    await fireEvent.input(composer, { target: { value: "keep this draft" } });
    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(document.getElementById("composer-instructions")).toBeNull());
    expect(screen.getByRole("textbox", { name: "Message" })).toBe(composer);
    expect(composer.getAttribute("aria-describedby")).toBe("composer-guidance composer-shortcuts");
    expect(composer.value).toBe("keep this draft");
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("does not invent composer instructions from a historical Scout Run or a draft", async () => {
    const historical = {
      ...projection(), pattern_revision: "4", loom_path: "/loom/bridge_chat/4",
      run_status: "done", activity: "done", terminal: true
    };
    getSnapshotMock.mockResolvedValueOnce(snapshot("session-a", [historical]));
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole("textbox", { name: "Message" });
    await fireEvent.input(composer, { target: { value: "/read-public https://example.com/page\nA question" } });
    expect(document.getElementById("composer-instructions")).toBeNull();
    expect(composer.getAttribute("aria-describedby")).toBe("composer-guidance composer-shortcuts");
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("keeps the offered text and instructions after validation refuses the request", async () => {
    getSnapshotMock.mockResolvedValueOnce(guidedSnapshot());
    sendMock.mockRejectedValueOnce(Object.assign(new ApiError("Public-page admission refused"), { status: 400 }));
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole<HTMLTextAreaElement>("textbox", { name: "Message" });
    await offer("a question without its command");
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Public-page admission refused");
    expect(composer.value).toBe("a question without its command");
    expect(document.getElementById("composer-instructions")?.textContent).toBe(guidance);
    expect(sendMock).toHaveBeenCalledOnce();
    view.unmount();
  });
});

describe("Bridge route and stream ownership", () => {
  it.each(["running", "awaiting_peer"])("keeps a later draft unsent while the observed Run is %s", async (status) => {
    cancelMock.mockResolvedValue({ ...cancelledProjection(), cursor: 19 });
    getSnapshotMock
      .mockResolvedValueOnce(snapshot("session-a", [projection()]))
      .mockResolvedValue(snapshot("session-a", [cancelledProjection()]));
    const view = render(BridgeView, { sessionId: "session-a" });
    const composer = await screen.findByRole("textbox", { name: "Message" });
    await act(() => latestRunListener()(event("run-a", 18, "status", { text: status })));
    expect(screen.getByText(status.replaceAll("_", " "), { selector: ".circle-status > span:first-child" })).toBeTruthy();
    await fireEvent.input(composer, { target: { value: "my later draft" } });
    expect((screen.getByRole("button", { name: "Offer" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Wait for this Run to settle/).textContent).toContain("not queued");
    await fireEvent.keyDown(composer, { key: "Enter" });
    expect(sendMock).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole("button", { name: "Cancel run run-a" }));
    await waitFor(() => expect((screen.getByRole("button", { name: "Offer" }) as HTMLButtonElement).disabled).toBe(false));
    expect((composer as HTMLTextAreaElement).value).toBe("my later draft");
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("preserves older reading through incoming text until Latest turn is requested", async () => {
    getSnapshotMock.mockResolvedValue(snapshot("session-a", [projection()]));
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByText("authoritative partial");
    const conversation = screen.getByRole("region", { name: "Conversation" });
    Object.defineProperties(conversation, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 200 },
      scrollTop: { configurable: true, writable: true, value: 40 }
    });
    await fireEvent.scroll(conversation);
    await act(() => latestRunListener()(event("run-a", 18, "token", { text: " and more" })));
    expect(conversation.scrollTop).toBe(40);
    await fireEvent.click(screen.getByRole("button", { name: "Latest turn ↓" }));
    expect(conversation.scrollTop).toBe(1000);
    expect(document.activeElement).toBe(screen.getByText("authoritative partial and more").closest("article"));
    Object.defineProperty(conversation, "scrollHeight", { configurable: true, value: 1200 });
    await act(() => latestRunListener()(event("run-a", 19, "token", { text: " still" })));
    expect(conversation.scrollTop).toBe(1200);
    view.unmount();
  });

  it("lets Latest turn release an exact Run focus without moving or sending the draft", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-old");
    const initial = snapshot("session-a", [projection()]);
    initial.session!.turns = [{ ...accepted("run-old", "an older reply").turn, role: "agent" }];
    getSnapshotMock.mockResolvedValue(initial);
    const view = render(BridgeView, { sessionId: "session-a" });
    const older = (await screen.findByText("an older reply")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(older));
    const composer = screen.getByRole("textbox", { name: "Message" });
    await fireEvent.input(composer, { target: { value: "keep this draft" } });
    await fireEvent.click(screen.getByRole("button", { name: "Latest turn ↓" }));
    const latest = screen.getByText("authoritative partial").closest("article");
    expect(document.activeElement).toBe(latest);
    await act(() => latestRunListener()(event("run-a", 18, "token", { text: " grows" })));
    expect(document.activeElement).toBe(latest);
    expect((composer as HTMLTextAreaElement).value).toBe("keep this draft");
    expect(sendMock).not.toHaveBeenCalled();
    view.unmount();
  });

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
    expect(await screen.findAllByText("cancelled")).toHaveLength(1);
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
    expect(await screen.findAllByText("cancelled")).toHaveLength(1);
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
    expect(screen.queryByText(failedStreamNotice)).toBeNull();

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
    expect(screen.queryByText(failedStreamNotice)).toBeNull();
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
    expect(screen.getAllByText("cancelled")).toHaveLength(1);
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

    expect(await screen.findAllByText("cancelled")).toHaveLength(1);
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
      expect(screen.getAllByText("cancelled")).toHaveLength(1);
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

  it.each([
    { content: "authoritative partial\n  unfinished detail", doneText: null },
    { content: "", doneText: null },
    { content: "authoritative partial", doneText: failureReply }
  ])("shows a failed Run without inventing reply text for %j", async ({ content, doneText }) => {
    const retained = deferred<BridgeSnapshot>();
    getSnapshotMock.mockReset();
    getSnapshotMock.mockResolvedValueOnce(snapshot("session-a", [{ ...projection(), content }]))
      .mockReturnValueOnce(retained.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    expect(await screen.findByRole("button", { name: "Cancel run run-a" })).toBeTruthy();
    expect(screen.queryByText(failedStreamNotice)).toBeNull();

    vi.useFakeTimers();
    await act(() => latestRunListener()(event("run-a", 18, "done", {
      status: "failed", turn: doneText === null ? null : { content: doneText }
    })));

    const visibleContent = doneText ?? content;
    expect(screen.getAllByText("failed")).toHaveLength(1);
    expect(view.container.querySelector('[data-run-id="run-a"] .turn__body')?.textContent).toBe(
      visibleContent || "No reply text was retained for this Run."
    );
    if (visibleContent) {
      expect(screen.getByText(failedStreamNotice).getAttribute("role")).toBe("status");
    } else {
      expect(screen.queryByText(failedStreamNotice)).toBeNull();
    }
    expect(screen.getByRole("link", { name: "Look into the Orb" }).getAttribute("href")).toBe("/orb/run-a");
    expect(screen.queryByText("The turn has settled.")).toBeNull();
    expect(screen.queryByRole("button", { name: "Cancel run run-a" })).toBeNull();
    expect(listenMock).toHaveBeenCalledOnce();

    await act(() => vi.advanceTimersByTime(50));
    expect(getSnapshotMock).toHaveBeenCalledTimes(2);
    const refreshed = snapshot("session-a");
    refreshed.session!.turns = [{ ...accepted("run-a", failureReply).turn, role: "agent", state: "failed" }];
    await act(() => retained.resolve(refreshed));

    const rows = view.container.querySelectorAll('article.turn--agent[data-run-id="run-a"]');
    expect(rows).toHaveLength(1);
    expect(rows[0]?.querySelector(".turn__body")?.textContent).toBe(failureReply);
    expect(rows[0]?.getAttribute("data-state")).toBe("failed");
    expect(screen.queryByText(failedStreamNotice)).toBeNull();
    expect(screen.getByRole("link", { name: "Look into the Orb" }).getAttribute("href")).toBe("/orb/run-a");
    expect(screen.queryByRole("button", { name: "Cancel run run-a" })).toBeNull();
    expect(listenMock).toHaveBeenCalledOnce();
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

    expect(screen.getByText("settled A")).toBeTruthy();
    expect(screen.queryByText(failedStreamNotice)).toBeNull();

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


describe("Bridge reader preservation during refresh", () => {
  function retainedConversation() {
    const next = snapshot("session-a", [projection()]);
    next.session!.turns = [
      accepted("old-run", "earlier offering").turn,
      { ...accepted("old-run", "earlier reply").turn, role: "agent" }
    ];
    return next;
  }

  async function refreshFromRun(kind: "consent" | "done") {
    if (kind === "done") vi.useFakeTimers();
    await act(() => latestRunListener()(event("run-a", 18, kind,
      kind === "done" ? { status: "done", turn: { content: "latest reply" } } : {}
    )));
    if (kind === "done") {
      await act(() => vi.advanceTimersByTime(50));
      vi.useRealTimers();
    }
    expect(getSnapshotMock).toHaveBeenCalledTimes(2);
  }

  it.each(["consent", "done"] as const)("keeps the composer and retained content through a %s refresh after Run navigation", async (kind) => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=old-run");
    const refresh = deferred<BridgeSnapshot>();
    getSnapshotMock.mockResolvedValueOnce(retainedConversation()).mockReturnValueOnce(refresh.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    const article = (await screen.findByText("earlier reply")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(article));
    const composer = screen.getByLabelText<HTMLTextAreaElement>("Message");
    composer.focus();
    await fireEvent.input(composer, { target: { value: "next draft" } });

    await refreshFromRun(kind);
    expect(screen.getByText("earlier reply").closest("article")).toBe(article);
    expect(document.activeElement).toBe(composer);
    expect(composer.value).toBe("next draft");
    expect(view.container.querySelector(".mist")).toBeNull();

    const fresh = retainedConversation();
    fresh.session!.title = "Refreshed conversation";
    await act(() => refresh.resolve(fresh));
    expect(await screen.findByText("Refreshed conversation", { selector: ".conversation-title" })).toBeTruthy();
    expect(screen.getByText("earlier reply").closest("article")).toBe(article);
    expect(document.activeElement).toBe(composer);
    expect(composer.value).toBe("next draft");
    view.unmount();
  });

  it.each(["consent", "done"] as const)("keeps the reader's focused turn and scroll through a %s refresh without a Run hint", async (kind) => {
    const refresh = deferred<BridgeSnapshot>();
    getSnapshotMock.mockResolvedValueOnce(retainedConversation()).mockReturnValueOnce(refresh.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    const article = (await screen.findByText("earlier reply")).closest("article")!;
    const thread = screen.getByLabelText("Conversation");
    Object.defineProperties(thread, { scrollHeight: { value: 1200 }, clientHeight: { value: 200 } });
    thread.scrollTop = 150;
    await fireEvent.scroll(thread);
    article.focus();

    await refreshFromRun(kind);
    expect(article.isConnected).toBe(true);
    expect(document.activeElement).toBe(article);
    expect(thread.scrollTop).toBe(150);
    await act(() => refresh.resolve(retainedConversation()));
    expect(screen.getByText("earlier reply").closest("article")).toBe(article);
    expect(document.activeElement).toBe(article);
    expect(thread.scrollTop).toBe(150);
    view.unmount();
  });

  it("keeps prior content, draft and focus when a same-session refresh fails", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=old-run");
    const refresh = deferred<BridgeSnapshot>();
    getSnapshotMock.mockResolvedValueOnce(retainedConversation()).mockReturnValueOnce(refresh.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    const article = (await screen.findByText("earlier reply")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(article));
    const composer = screen.getByLabelText<HTMLTextAreaElement>("Message");
    composer.focus();
    await fireEvent.input(composer, { target: { value: "draft through failure" } });
    await refreshFromRun("consent");
    await act(() => refresh.reject(new Error("Conversation refresh unavailable")));
    expect(await screen.findByText("Conversation refresh unavailable")).toBeTruthy();
    expect(screen.getByText("earlier reply").closest("article")).toBe(article);
    expect(document.activeElement).toBe(composer);
    expect(composer.value).toBe("draft through failure");
    expect(view.container.querySelector(".mist")).toBeNull();
    view.unmount();
  });

  it("preserves the composer through the consent card's recovery refresh", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=old-run");
    const initial = retainedConversation();
    initial.pending_consents = [pendingConsent];
    const decision = deferred<Awaited<ReturnType<typeof decideConsent>>>();
    const refresh = deferred<BridgeSnapshot>();
    decideConsentMock.mockReturnValueOnce(decision.promise);
    getSnapshotMock.mockResolvedValueOnce(initial).mockReturnValueOnce(refresh.promise);
    const view = render(BridgeView, { sessionId: "session-a" });
    const article = (await screen.findByText("earlier reply")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(article));
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    const composer = screen.getByLabelText<HTMLTextAreaElement>("Message");
    composer.focus();
    await fireEvent.input(composer, { target: { value: "draft while deciding" } });
    await act(() => decision.reject(new TypeError("Consent response lost")));
    expect(getSnapshotMock).toHaveBeenCalledTimes(2);
    expect(article!.isConnected).toBe(true);
    expect(document.activeElement).toBe(composer);
    await act(() => refresh.resolve(structuredClone(initial)));
    expect(document.activeElement).toBe(composer);
    expect(composer.value).toBe("draft while deciding");
    expect((screen.getByRole("button", { name: "Refuse" }) as HTMLButtonElement).disabled).toBe(true);
    view.unmount();
  });

  it("applies each deliberate same-session Run navigation and reports an unavailable Run", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=old-run");
    getSnapshotMock.mockResolvedValueOnce(retainedConversation());
    const view = render(BridgeView, { sessionId: "session-a" });
    const oldArticle = (await screen.findByText("earlier reply")).closest("article");
    await waitFor(() => expect(document.activeElement).toBe(oldArticle));
    await act(() => { mockPage.url.search = "?run=run-a"; });
    const liveArticle = screen.getByText("authoritative partial").closest("article");
    await waitFor(() => expect(document.activeElement).toBe(liveArticle));
    await act(() => { mockPage.url.search = "?run=missing-run"; });
    expect(await screen.findByText("The requested Run is not available in this conversation.")).toBeTruthy();
    await act(() => { mockPage.url.search = "?run=old-run"; });
    await waitFor(() => expect(document.activeElement).toBe(oldArticle));
    expect(getSnapshotMock).toHaveBeenCalledOnce();
    view.unmount();
  });

  it.each(["success", "failure"] as const)("ignores a late refresh %s after navigating to another session", async (outcome) => {
    const refresh = deferred<BridgeSnapshot>();
    getSnapshotMock.mockResolvedValueOnce(retainedConversation()).mockReturnValueOnce(refresh.promise)
      .mockResolvedValueOnce(snapshot("session-b"));
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByText("earlier reply");
    await refreshFromRun("consent");
    await view.rerender({ sessionId: "session-b" });
    await screen.findByText("session-b");
    const composer = screen.getByLabelText<HTMLTextAreaElement>("Message");
    composer.focus();
    await fireEvent.input(composer, { target: { value: "session B draft" } });
    await act(() => outcome === "success"
      ? refresh.resolve(retainedConversation())
      : refresh.reject(new Error("Late session A error")));
    expect(screen.getByText("session-b")).toBeTruthy();
    expect(screen.queryByText("earlier reply")).toBeNull();
    expect(screen.queryByText("Late session A error")).toBeNull();
    expect(document.activeElement).toBe(composer);
    expect(composer.value).toBe("session B draft");
    view.unmount();
  });
});


describe("Bridge historical consent navigation", () => {
  function consentSnapshot(): BridgeSnapshot {
    return { ...snapshot("session-a", [projection(), projection("session-a", "run-b")]), pending_consents: [
      { ...pendingConsent, id: "consent-other", run_id: "run-b", tool_name: "other request" },
      { ...pendingConsent }
    ] };
  }

  it("focuses the exact current request once, preserves draft and uncertain choice, and returns to the exact Orb event", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-a&consent=consent-a&event=event-old");
    const current = consentSnapshot();
    getSnapshotMock.mockResolvedValue(current);
    const work = createBridgeWorkspace();
    work.setDraft("session-a", "later session draft");
    work.consentDecisions.set("consent-a", { sessionId: "session-a", verdict: "approve", sending: false, error: "Outcome unknown" });
    const view = render(BridgeView, { props: { sessionId: "session-a" }, context: new Map([[bridgeWorkspaceKey, work]]) });
    const composer = await screen.findByLabelText<HTMLTextAreaElement>("Message");
    const exact = document.querySelector('[data-consent-id="consent-a"]');
    await waitFor(() => expect(document.activeElement).toBe(exact));
    expect(exact).not.toBeNull();
    expect(within(exact as HTMLElement).getByRole<HTMLButtonElement>("button", { name: "Refuse" }).disabled).toBe(true);
    expect(composer.value).toBe("later session draft");
    expect(screen.getByRole("link", { name: "Return to Orb event →" }).getAttribute("href")).toBe("/orb/run-a?event=event-old");
    composer.focus();
    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(getSnapshotMock).toHaveBeenCalledTimes(2));
    expect(document.activeElement).toBe(composer);
    expect(work.consentDecisions.get("consent-a")?.verdict).toBe("approve");
    expect(composer.value).toBe("later session draft");
    expect(decideConsentMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it.each(["missing", "settled", "cancelled", "foreign-run", "no-run", "foreign-session", "unbound-run", "newer-round", "invalid-id"])(
    "reports an unavailable %s reference without choosing another card or Run", async (scenario) => {
      mockPage.url = new SvelteURL(`http://localhost/bridge/session-a?${scenario === "no-run" ? "" : "run=run-a&"}consent=${scenario === "invalid-id" ? "%2Fforeign" : "consent-a"}&event=event-old`);
      const current = consentSnapshot();
      if (scenario === "missing") current.pending_consents = [current.pending_consents[0]!];
      if (scenario === "settled") current.pending_consents[1]!.state = "consented";
      if (scenario === "cancelled") current.pending_consents[1]!.state = "cancelled";
      if (scenario === "foreign-run") current.pending_consents[1]!.run_id = "run-b";
      if (scenario === "foreign-session") current.active_runs = [projection("session-b")];
      if (scenario === "unbound-run") current.active_runs = [];
      if (scenario === "newer-round") current.pending_consents[1]!.id = "consent-new";
      getSnapshotMock.mockResolvedValueOnce(current);
      const view = render(BridgeView, { sessionId: "session-a" });
      expect(await screen.findByText("The requested consent is unavailable in this conversation at this read.")).toBeTruthy();
      await act(() => Promise.resolve());
      expect(document.activeElement?.closest("[data-consent-id], [data-run-id]")).toBeNull();
      expect(decideConsentMock).not.toHaveBeenCalled();
      expect(sendMock).not.toHaveBeenCalled();
      view.unmount();
    }
  );

  it("does not steal later focus when an unavailable request appears on stream refresh", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-a&consent=consent-a&event=event-old");
    const unavailable = consentSnapshot();
    unavailable.pending_consents = [unavailable.pending_consents[0]!];
    getSnapshotMock.mockResolvedValueOnce(unavailable).mockResolvedValueOnce(consentSnapshot());
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByText("The requested consent is unavailable in this conversation at this read.");
    const composer = screen.getByLabelText<HTMLTextAreaElement>("Message");
    composer.focus();
    await act(() => latestRunListener()(event("run-a", 18, "consent", {})));
    await waitFor(() => expect(document.querySelector('[data-consent-id="consent-a"]')).not.toBeNull());
    expect(screen.queryByText("The requested consent is unavailable in this conversation at this read.")).toBeNull();
    expect(document.activeElement).toBe(composer);
    expect(decideConsentMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("focuses an exact read-only native card without gaining review or judgment authority", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-a&consent=consent-a");
    const current = consentSnapshot();
    current.pending_consents[1] = { ...pendingConsent, can_decide: false, native_review_status: "unavailable" };
    getSnapshotMock.mockResolvedValueOnce(current);
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByLabelText("Message");
    const card = document.querySelector<HTMLElement>('[data-consent-id="consent-a"]')!;
    await waitFor(() => expect(document.activeElement).toBe(card));
    expect(within(card).getByText("The required review is unavailable or incomplete. Refresh before deciding.")).toBeTruthy();
    const approve = within(card).getByRole<HTMLButtonElement>("button", { name: "Consecrate" });
    const deny = within(card).getByRole<HTMLButtonElement>("button", { name: "Refuse" });
    expect(approve.disabled).toBe(true);
    expect(deny.disabled).toBe(true);
    await fireEvent.click(approve);
    await fireEvent.click(deny);
    expect(decideConsentMock).not.toHaveBeenCalled();
    view.unmount();
  });

  it("applies a deliberate same-session request change without refetching or choosing the first card", async () => {
    mockPage.url = new SvelteURL("http://localhost/bridge/session-a?run=run-a&consent=consent-a");
    getSnapshotMock.mockResolvedValueOnce(consentSnapshot());
    const view = render(BridgeView, { sessionId: "session-a" });
    await screen.findByLabelText("Message");
    await waitFor(() => expect(document.activeElement).toBe(document.querySelector('[data-consent-id="consent-a"]')));
    await act(() => { mockPage.url.search = "?run=run-b&consent=consent-other"; });
    await waitFor(() => expect(document.activeElement).toBe(document.querySelector('[data-consent-id="consent-other"]')));
    expect(getSnapshotMock).toHaveBeenCalledOnce();
    view.unmount();
  });
});

it("links the separate source recall focus without moving a session draft, unresolved offering or Consent", async () => {
  getSnapshotMock.mockImplementation(async () => ({ ...snapshot("session-a"), pending_consents: [pendingConsent], pending_count: 1 }));
  sendMock.mockRejectedValueOnce(new TypeError("Response lost"));
  const work = createBridgeWorkspace();
  const first = render(BridgeView, { props: { sessionId: "session-a" }, context: new Map([[bridgeWorkspaceKey, work]]) });
  await screen.findByLabelText("Message"); await offer("unresolved conversation offering");
  await fireEvent.input(screen.getByLabelText("Message"), { target: { value: "later conversation draft" } });
  const sources = screen.getByText("Public sources").closest("details")!;
  expect(sources.open).toBe(false);
  await fireEvent.click(screen.getByText("Public sources"));
  expect(sources.open).toBe(true);
  const link = screen.getByRole("link", { name: "Recall public sources" });
  expect(link.getAttribute("href")).toBe("/bridge?notes=recall");
  expect(work.drafts.get("session-a")).toBe("later conversation draft"); expect(sendMock).toHaveBeenCalledTimes(1); expect(decideConsentMock).not.toHaveBeenCalled();
  first.unmount();
  const returned = render(BridgeView, { props: { sessionId: "session-a" }, context: new Map([[bridgeWorkspaceKey, work]]) });
  await screen.findByRole("button", { name: "Retry original offering" });
  expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("later conversation draft");
  expect(screen.getByRole("region", { name: "Unresolved offering" }).textContent).toContain("unresolved conversation offering");
  expect(sendMock).toHaveBeenCalledTimes(1); expect(decideConsentMock).not.toHaveBeenCalled(); returned.unmount();
});


describe("Bridge command destination and shared voice composer", () => {
  function mountWork(execute = vi.fn((_text: string, _target: CommandTarget): CommandResult => ({ status: "preview", summary: "Two named nodes and one connection ready for review." }))) {
    const registry = createWorkCommandRegistry();
    registry.register({ instrument: "canvas", id: "board-a", label: "Architecture", snapshot: () => ({
      revisionKey: "1", commands: ["create node Vessel", "connect Vessel to Postgres"]
    }), execute });
    const work = createBridgeWorkspace();
    const view = render(BridgeView, { props: { sessionId: "session-a" },
      context: new Map<symbol, unknown>([[workCommandKey, registry], [bridgeWorkspaceKey, work]]) });
    return { view, registry, work, execute };
  }

  it("keeps Conversation default and sends typed work commands only to the closed preview registry", async () => {
    const { execute } = mountWork();
    const message = await screen.findByLabelText("Message");
    const mode = screen.getByLabelText("Send to") as HTMLSelectElement;
    expect(mode.value).toBe("chat");
    expect(screen.getByRole("option", { name: "Canvas · Architecture" })).toBeTruthy();
    await fireEvent.change(mode, { target: { value: "work" } });
    expect(screen.getByText("English commands · Canvas · Architecture")).toBeTruthy();
    expect(screen.getByText("connect Vessel to Postgres")).toBeTruthy();
    await fireEvent.input(message, { target: { value: "create node Vessel" } });
    await fireEvent.click(screen.getByRole("button", { name: "Send command" }));
    expect(execute).toHaveBeenCalledOnce();
    expect(execute.mock.calls[0]?.[0]).toBe("create node Vessel");
    expect(await screen.findByText(/preview: Two named nodes/)).toBeTruthy();
    expect((message as HTMLTextAreaElement).value).toBe("");
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("refuses absent work targets without falling through to conversation", async () => {
    render(BridgeView, { sessionId: "session-a" });
    const message = await screen.findByLabelText("Message");
    await fireEvent.change(screen.getByLabelText("Send to"), { target: { value: "work" } });
    await fireEvent.input(message, { target: { value: "create node Vessel" } });
    await fireEvent.keyDown(message, { key: "Enter" });
    expect(screen.getByText(/unavailable: The work target changed/)).toBeTruthy();
    expect((message as HTMLTextAreaElement).value).toBe("create node Vessel");
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("does not clear an edited-away-and-back draft after an asynchronous command", async () => {
    const pending = deferred<CommandResult>();
    const registry = createWorkCommandRegistry();
    registry.register({ instrument: "canvas", id: "a", label: "Board", snapshot: () => ({ revisionKey: "1", commands: [] }), execute: () => pending.promise });
    render(BridgeView, { props: { sessionId: "session-a" }, context: new Map([[workCommandKey, registry]]) });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await fireEvent.change(screen.getByLabelText("Send to"), { target: { value: "work" } });
    await fireEvent.input(message, { target: { value: "create node Vessel" } });
    await fireEvent.click(screen.getByRole("button", { name: "Send command" }));
    await fireEvent.input(message, { target: { value: "changed draft" } });
    await fireEvent.input(message, { target: { value: "create node Vessel" } });
    await act(() => pending.resolve({ status: "preview", summary: "Original preview ready." }));
    expect(message.value).toBe("create node Vessel");
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("retries the exact unresolved chat offering and UUID even after choosing work mode", async () => {
    const { work, execute } = mountWork();
    await screen.findByLabelText("Message");
    await act(() => work.pending.set("session-a", {
      text: "original chat offering", requestId: "original-uuid", uncertain: true, sending: false, error: "Response lost"
    }));
    sendMock.mockRejectedValueOnce(new TypeError("Response still lost"));
    await fireEvent.change(screen.getByLabelText("Send to"), { target: { value: "work" } });
    await fireEvent.click(screen.getByRole("button", { name: "Retry original offering" }));
    expect(sendMock).toHaveBeenCalledExactlyOnceWith("session-a", "original chat offering", "original-uuid");
    expect(execute).not.toHaveBeenCalled();
  });

  let finishCapture: (value: VoiceRecording | null) => void;
  let captureOptions: VoiceCaptureOptions;
  function enableVoice() {
    vi.mocked(getDictationDiscovery).mockResolvedValue({
      status: "available", reason: null, profile_digest: `sha256:${"a".repeat(64)}`, languages: ["en"],
      max_audio_bytes: 1048576, max_audio_seconds: 30, sample_rate_hz: 16000, channels: 1,
      sample_width_bytes: 2, raw_audio_retention_seconds: 300
    } satisfies DictationDiscovery);
    vi.mocked(transcribeDictation).mockImplementation(async (body) => ({
      attempt_id: body.attempt_id, status: "transcribed", original_text: "create node Vessel", language: "en",
      source_digest: `sha256:${"b".repeat(64)}`, profile_digest: `sha256:${"a".repeat(64)}`, reason: null
    } satisfies DictationResult));
    vi.mocked(createVoiceCapture).mockImplementation((options: VoiceCaptureOptions = {}) => {
      captureOptions = options;
      return {
        start: () => { options.onstate?.({ status: "recording", elapsedMs: 0, limitMs: 30000 });
          return new Promise<VoiceRecording | null>((resolve) => { finishCapture = resolve; }); },
        stop: vi.fn(async () => null), dispose: vi.fn(), cancel: vi.fn(),
        state: { status: "idle", elapsedMs: 0, limitMs: 30000 }
      } as ReturnType<typeof createVoiceCapture>;
    });
    vi.stubGlobal("FileReader", class {
      result: string | null = null;
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      readAsDataURL() { queueMicrotask(() => { this.result = "data:audio/wav;base64,UklGRg=="; this.onload?.(); }); }
      abort() {}
    });
  }
  async function completeVoice() {
    await act(async () => {
      captureOptions.onstate?.({ status: "complete", elapsedMs: 10, limitMs: 30000 });
      finishCapture({ blob: new Blob([new Uint8Array(48)], { type: "audio/wav" }), channels: 1, sampleRate: 16000, frames: 2, durationMs: .125 });
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    });
  }

  it("uses the shared voice claim for Enter and click, then keeps the ordinary unknown-send retry", async () => {
    enableVoice();
    sendMock.mockRejectedValueOnce(new TypeError("Response lost"));
    render(BridgeView, { sessionId: "session-a" });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await completeVoice();
    expect(message.value).toBe("create node Vessel");
    await fireEvent.input(message, { target: { value: "corrected offering" } });
    await fireEvent.keyDown(message, { key: "Enter" });
    await fireEvent.click(screen.getByRole("button", { name: "Offer" }));
    expect(sendMock).toHaveBeenCalledOnce();
    expect(sendMock.mock.calls[0]?.[1]).toBe("corrected offering");
    expect(screen.getByRole("button", { name: "Retry original offering" })).toBeTruthy();
  });

  it("dispatches an adopted voice command with its pinned target without recapturing on Send", async () => {
    enableVoice();
    const { registry, execute } = mountWork();
    const message = await screen.findByLabelText("Message");
    await fireEvent.change(screen.getByLabelText("Send to"), { target: { value: "work" } });
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await completeVoice();
    const recapture = vi.spyOn(registry, "capture");
    await fireEvent.keyDown(message, { key: "Enter" });
    expect(recapture).not.toHaveBeenCalled();
    expect(execute).toHaveBeenCalledOnce();
    expect(execute.mock.calls[0]?.[1].id).toBe("board-a");
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("suppresses autosend for a complete IME start/end within one render batch", async () => {
    enableVoice();
    render(BridgeView, { sessionId: "session-a" });
    const message = await screen.findByLabelText("Message");
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    const autosend = screen.getByLabelText("Automatically send after 2 seconds");
    await fireEvent.click(autosend);
    vi.useFakeTimers();
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await completeVoice();
    await act(() => {
      message.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
      message.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    });
    await act(() => vi.advanceTimersByTimeAsync(2500));
    expect(sendMock).not.toHaveBeenCalled();
    expect((message as HTMLTextAreaElement).value).toBe("create node Vessel");
  });

  it("keeps late speech separate after an edit-away-and-back during capture", async () => {
    enableVoice();
    render(BridgeView, { sessionId: "session-a" });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await fireEvent.input(message, { target: { value: "temporary" } });
    await fireEvent.input(message, { target: { value: "" } });
    await completeVoice();
    expect(message.value).toBe("");
    expect(screen.getByLabelText("Transcript suggestion")).toBeTruthy();
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("fences late capture on navigation even when the route identity returns unchanged", async () => {
    enableVoice();
    render(BridgeView, { sessionId: "session-a" });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await act(() => {
      const navigation = vi.mocked(beforeNavigate).mock.calls.at(-1)?.[0];
      navigation?.({} as Parameters<NonNullable<typeof navigation>>[0]);
      navigation?.({} as Parameters<NonNullable<typeof navigation>>[0]);
    });
    await completeVoice();
    expect(message.value).toBe("");
    expect(transcribeDictation).not.toHaveBeenCalled();
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("suspends a hidden shell capture before prop flush and preserves the draft", async () => {
    enableVoice();
    let visible = true;
    const view = render(BridgeView, { sessionId: "session-a", isVisible: () => visible });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.input(message, { target: { value: "Keep typed text" } });
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await act(() => { view.component.suspendVoice(); visible = false; });
    await completeVoice();
    expect(message.value).toBe("Keep typed text");
    expect(transcribeDictation).not.toHaveBeenCalled();
    expect(sendMock).not.toHaveBeenCalled();
    // A stale visible prop/button cannot start another microphone while its shell is hidden.
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    expect(createVoiceCapture).toHaveBeenCalledOnce();
    visible = true;
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    expect(createVoiceCapture).toHaveBeenCalledTimes(2);
    view.unmount();
  });

  it("does not revive a suspended autosend after reopening the shell", async () => {
    enableVoice();
    let visible = true;
    const view = render(BridgeView, { sessionId: "session-a", isVisible: () => visible });
    const message = await screen.findByLabelText("Message") as HTMLTextAreaElement;
    await waitFor(() => expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false));
    await fireEvent.click(screen.getByLabelText("Automatically send after 2 seconds"));
    vi.useFakeTimers();
    await fireEvent.click(screen.getByRole("button", { name: "Record voice" }));
    await completeVoice();
    await act(() => { view.component.suspendVoice(); visible = false; });
    await act(() => vi.advanceTimersByTimeAsync(2500));
    visible = true;
    await act(() => vi.advanceTimersByTimeAsync(2500));
    expect(sendMock).not.toHaveBeenCalled();
    expect(message.value).toBe("create node Vessel");
    view.unmount();
  });
});
