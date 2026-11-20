import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BridgeSnapshot, LoomView, OrbRunSnapshot, RunProjectionSnapshot } from "$lib/api/models";

const navigationHooks = vi.hoisted(() => ({
  before: [] as Array<(navigation: { from: { url: URL }; to?: { url: URL }; willUnload?: boolean; cancel: () => void }) => void>,
  after: [] as Array<(navigation: { type: "link" | "popstate"; to: { url: URL } }) => void>
}));

vi.mock("$app/state", async () => {
  const { SvelteURL } = await import("svelte/reactivity");
  return { page: { state: {}, url: new SvelteURL("http://localhost/bridge") } };
});
vi.mock("$app/navigation", () => ({ goto: vi.fn(), replaceState: vi.fn(),
  beforeNavigate: vi.fn((callback: (navigation: { from: { url: URL }; to?: { url: URL }; willUnload?: boolean; cancel: () => void }) => void) => { navigationHooks.before.push(callback); }),
  afterNavigate: vi.fn((callback: (navigation: { type: "link" | "popstate"; to: { url: URL } }) => void) => { navigationHooks.after.push(callback); }) }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  cancelBridgeRun: vi.fn(),
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getAltarStatus: vi.fn(),
  getArchiveProfile: vi.fn().mockResolvedValue({ profile: "local-public-notes@1", namespace_id: "00000000-0000-4000-8000-000000000001", owner_subject: { identity: "owner" }, policy_revision: "policy" }),
  recallArchiveSemanticNotes: vi.fn(), inspectArchiveSemanticRecall: vi.fn(), resolveArchiveSemanticRecall: vi.fn(),
  getArchiveBridgeDefault: vi.fn().mockResolvedValue({ current_default: null, requests_profile: null }),
  listArchiveNotes: vi.fn().mockResolvedValue({ records: [] }),
  getArchiveNote: vi.fn(), admitArchiveNote: vi.fn(), promoteArchiveNote: vi.fn(), revokeArchiveNote: vi.fn(), discoverArchiveGeneration: vi.fn(), registerArchiveGeneration: vi.fn(), deriveArchiveNote: vi.fn(), inspectArchiveDerivation: vi.fn(),
  getAtlasProject: vi.fn(),
  getAtlasReferences: vi.fn().mockResolvedValue([]),
  getBridgeSnapshot: vi.fn(),
  getBridgeSessions: vi.fn(),
  getOrbRun: vi.fn(),
  getRunSnapshot: vi.fn(),
  listenToRun: vi.fn(),
  sendBridgeMessage: vi.fn()
}));

import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { goto } from "$app/navigation";
import { createBridgeSession, getAltarStatus, getBridgeSnapshot, getArchiveNote, deriveArchiveNote, discoverArchiveGeneration, getOrbRun, sendBridgeMessage, listenToRun, cancelBridgeRun } from "$lib/api/client";
import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/shell/state/bridge-workspace.svelte";
import { getSeancesWorkspace, type SeancesWorkspace as SeancesContext } from "$lib/seances/workspace.svelte";
import { getEvaluationWorkspace, type EvaluationWorkspace } from "$lib/pages/loom/state/evaluation/workspace.svelte";
import AltarShell from "$lib/shell/components/AltarShell.svelte";
import BridgePage from "../../../../routes/bridge/+page.svelte";

const children = createRawSnippet(() => ({ render: () => "<div></div>" }));
const sessions = [
  { id: "session-a", title: "Newest A", created_at: "2026-10-10T12:00:00Z", pending_count: 0 },
  { id: "session-c", title: "Later selected C", created_at: "2026-10-09T12:00:00Z", pending_count: 0 },
  { id: "session-b", title: "Older B", created_at: "2026-10-08T12:00:00Z", pending_count: 0 }
];

function snapshot(sessionId = "session-a"): BridgeSnapshot {
  const session = sessions.find(({ id }) => id === sessionId);
  if (!session) throw new Error(`Unexpected session read: ${sessionId}`);
  return {
    sessions,
    session: { ...session, turns: [{
      role: "agent", content: `Retained answer for ${sessionId}`, run_id: `run-${sessionId.at(-1)}`,
      state: "done", fragments: [], created_at: session.created_at
    }] },
    active_runs: [], pending_consents: [], pending_count: 0
  };
}

const orb: OrbRunSnapshot = {
  schema_version: 1, snapshot_at: "2026-10-10T12:00:00Z", capture: "process_local",
  ledger_head_seq: 0, page_end_seq: 0, live_tail: "ledger_poll", next_after_seq: null,
  has_more: false, known_omissions: [], delegated_jobs: [], gaps: [],
  evidence: [{
    event_id: "event-b", seq: 0, kind: "node", occurred_at: "2026-10-08T12:00:00Z",
    summary: "B completed", capture: "process_local", nexus_path: null,
    occurrence_id: "occurrence-b", phase: "settled", subject_key: "step-b", transition_request_id: null
  }],
  pattern: { pattern_id: "bridge_chat", revision: "1", digest: "digest-b", exact: true, loom_path: "/loom/bridge_chat/1" },
  run: {
    run_id: "run-b", session_id: "session-b", workflow_name: "bridge_chat", status: "done",
    created_at: "2026-10-08T12:00:00Z", started_at: "2026-10-08T12:00:00Z",
    finished_at: "2026-10-08T12:00:00Z", error_present: false, bridge_path: "/bridge/session-b"
  }
};

async function visit(href: string, type: "link" | "popstate" = "link") {
  await act(() => {
    let canceled = false;
    for (const callback of navigationHooks.before) callback({ from: { url: new URL(page.url.href) }, to: { url: new URL(href, "http://localhost") }, willUnload: false, cancel: () => { canceled = true; } });
    if (canceled) return;
    page.url.href = new URL(href, "http://localhost").href;
    for (const callback of navigationHooks.after) callback({ type, to: { url: new URL(page.url.href) } });
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  navigationHooks.after = [];
  navigationHooks.before = [];
  localStorage.clear();
  page.url.href = "http://localhost/bridge";
  vi.mocked(getAltarStatus).mockResolvedValue({
    csrf: { cookie_name: "csrf", header_name: "X-CSRF-Token" }, pending_consents: 1
  });
  vi.mocked(getBridgeSnapshot).mockImplementation(async (sessionId) => snapshot(sessionId));
  vi.mocked(getOrbRun).mockResolvedValue(orb);
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })));
});

afterEach(() => { vi.unstubAllGlobals(); });

describe("shell-lifetime Bridge conversation", () => {
  it("starts a new work page at the top and restores its scroll on history return without remounting Bridge", async () => {
    await visit("/orb");
    const shell = render(AltarShell, { children });
    const composer = await screen.findByLabelText("Message");
    const main = screen.getByRole("main");
    main.scrollTop = 180;
    await visit("/atlas");
    expect(main.scrollTop).toBe(0);
    main.scrollTop = 90;
    await visit("/orb");
    expect(main.scrollTop).toBe(0);
    await visit("/atlas", "popstate");
    expect(main.scrollTop).toBe(90);
    expect(screen.getByLabelText("Message")).toBe(composer);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    shell.unmount();
  });
  it("keeps the exact B composer instance and draft across work routes and collapse without rereading or admitting", async () => {
    await visit("/bridge/session-b");
    const work = createBridgeWorkspace();
    const shell = render(AltarShell, { props: { children }, context: new Map([[bridgeWorkspaceKey, work]]) });
    const composer = await screen.findByLabelText("Message");
    await fireEvent.input(composer, { target: { value: "Unfinished B offering" } });
    await visit("/orb/run-other?run=run-other&consent=consent-other&event=event-other&attention=pending&project=00000000-0000-4000-8000-000000000099");
    await visit("/loom/bridge_chat/1?run=run-other");
    await visit("/nexus?choose=conversation");
    expect(screen.getByLabelText("Message")).toBe(composer);
    expect((composer as HTMLTextAreaElement).value).toBe("Unfinished B offering");
    expect(screen.queryByText(/requested consent is unavailable/)).toBeNull();
    expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Expand Bridge" }));
    expect(screen.getByLabelText("Message")).toBe(composer);
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    expect(work.drafts.get("session-b")).toBe("Unfinished B offering");
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    expect(createBridgeSession).not.toHaveBeenCalled();
    shell.unmount();
  });

  it("retains an active Run subscription across navigation and collapse until shell teardown", async () => {
    const active: RunProjectionSnapshot = {
      schema_version: 1, session_id: "session-b", run_id: "live-b", cursor: 17,
      content: "authoritative partial", run_status: "running", activity: "weaving",
      pattern_id: "bridge_chat", pattern_revision: "1", loom_path: "/loom/bridge_chat/1", orb_path: "/orb/live-b",
      evidence_capture: "process_local", fragments: [], occurrence_id: null,
      dispatch_occurrence_id: null, grant_id: null, capability_key: null,
      transition_occurrence_id: null, transition_request_id: null, transition_phase: null,
      delegated_job_id: null, delegated_runtime: null, delegated_profile: null, delegated_status: null, terminal: false
    };
    vi.mocked(getBridgeSnapshot).mockResolvedValue({ ...snapshot("session-b"), active_runs: [active] });
    const close = vi.fn();
    vi.mocked(listenToRun).mockReturnValue(close);
    await visit("/bridge/session-b");
    const shell = render(AltarShell, { children });
    await screen.findByText("authoritative partial");
    await visit("/canvas?run=unrelated");
    await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
    await visit("/atlas");
    await fireEvent.click(screen.getByRole("button", { name: "Expand Bridge" }));
    expect(listenToRun).toHaveBeenCalledTimes(1);
    expect(close).not.toHaveBeenCalled();
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    expect(cancelBridgeRun).not.toHaveBeenCalled();
    shell.unmount();
    expect(close).toHaveBeenCalledOnce();
  });

  it("changes only the ordinary selected conversation when selecting history beside a work route", async () => {
    await visit("/atlas");
    const shell = render(AltarShell, { children });
    await screen.findByText("Retained answer for session-a");
    await fireEvent.click(screen.getByText("Conversations"));
    await fireEvent.click(screen.getByRole("link", { name: /Older B/ }));
    await screen.findByText("Retained answer for session-b");
    expect(page.url.pathname).toBe("/atlas");
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual([undefined, "session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    shell.unmount();
  });

  it("preserves an explicit contextual Run and consent destination, then releases focus through the global control", async () => {
    await visit("/bridge/session-b?run=missing-run&consent=missing-consent&event=event-b");
    const shell = render(AltarShell, { children });
    expect(await screen.findByText(/requested consent is unavailable/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Return to Orb event →" }).getAttribute("href"))
      .toBe("/orb/missing-run?event=event-b");
    await visit("/orb/run-b?event=event-b");
    expect(screen.getByRole("link", { name: "Bridge" }).getAttribute("href")).toBe("/bridge/session-b");
    await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
    await fireEvent.click(screen.getByRole("button", { name: "Expand Bridge" }));
    expect(screen.queryByText(/requested consent is unavailable/)).toBeNull();
    expect(screen.getByRole("link", { name: "Orb" }).getAttribute("href")).toBe("/orb");
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    shell.unmount();
  });

  it("retains ordinary draft and unresolved admission through public-note and investigation application focus", async () => {
    await visit("/bridge/session-b");
    const work = createBridgeWorkspace();
    work.setDraft("session-b", "Public-note detour draft");
    work.pending.set("session-b", { text: "Unresolved offering", requestId: "request-b", uncertain: true, sending: false, error: "Unknown" });
    const shell = render(AltarShell, { props: { children }, context: new Map([[bridgeWorkspaceKey, work]]) });
    const composer = await screen.findByLabelText("Message");
    await visit("/bridge?notes=manage&run=other");
    await visit("/bridge?investigation=new&attention=pending");
    expect(screen.getByLabelText("Message")).toBe(composer);
    expect(work.pending.get("session-b")?.requestId).toBe("request-b");
    expect(work.needsUnloadWarning).toBe(true);
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    shell.unmount();
  });

  it("opens compatibility public-note applications in one narrow Memory boundary while preserving Bridge", async () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
    await visit("/bridge/session-b");
    const shell = render(AltarShell, { children });
    const composer = await screen.findByLabelText("Message");
    await fireEvent.input(composer, { target: { value: "Retained B draft" } });
    await visit("/bridge?notes=manage");
    expect(await screen.findByRole("heading", { name: "Public notes" })).toBeTruthy();
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(screen.getByRole("dialog", { name: "Memory" })).toBeTruthy();
    expect(document.getElementById("bridge-message")).toBe(composer);
    expect((document.getElementById("bridge-dock")?.closest(".dock-shell") as HTMLElement).inert).toBe(true);
    await visit("/bridge?notes=new");
    const publicDraft = await screen.findByLabelText(/^Complete replacement text/);
    await fireEvent.input(publicDraft, { target: { value: "Explicit public text" } });
    await fireEvent.click(screen.getByRole("button", { name: "Close Memory" }));
    await visit("/loom/bridge_chat/1");
    await fireEvent.click(screen.getByRole("button", { name: "Expand Bridge" }));
    const opener = screen.getByRole("button", { name: "Memory" });
    await fireEvent.click(opener);
    expect(screen.getByLabelText(/^Complete replacement text/)).toBe(publicDraft);
    expect((publicDraft as HTMLTextAreaElement).value).toBe("Explicit public text");
    expect((composer as HTMLTextAreaElement).value).toBe("Retained B draft");
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled(); expect(cancelBridgeRun).not.toHaveBeenCalled();
    await fireEvent.keyDown(window, { key: "Escape" });
    expect(document.activeElement).toBe(opener);
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(screen.getByRole("dialog", { name: "Bridge" })).toBeTruthy();
    shell.unmount();
  });

  it("keeps the explicit attention URL a chooser without changing the remembered session", async () => {
    await visit("/bridge/session-b");
    const shell = render(AltarShell, { children });
    await screen.findByLabelText("Message");
    await visit("/bridge?attention=pending");
    await screen.findByRole("heading", { name: "Conversations awaiting consent" });
    expect(screen.queryByLabelText("Message")).toBeNull();
    await visit("/orb");
    await fireEvent.click(screen.getByRole("button", { name: "Expand Bridge" }));
    await screen.findByText("Retained answer for session-b");
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b", undefined, "session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    shell.unmount();
  });
});

it("reveals the same conversation beside work after full focus without overwriting a collapsed preference", async () => {
  localStorage.setItem("lychd.bridge-dock.layout.v1", JSON.stringify({ side: "right", width: 536, open: false }));
  await visit("/orb");
  const shell = render(AltarShell, { children });
  // Collapsed content stays mounted; this read uses the node rather than the accessibility tree.
  await waitFor(() => expect(document.getElementById("bridge-message")).toBeTruthy());
  const composer = document.getElementById("bridge-message") as HTMLTextAreaElement;
  await fireEvent.input(composer, { target: { value: "Same draft in either presentation" } });
  const reads = vi.mocked(getBridgeSnapshot).mock.calls.length;
  await visit("/bridge");
  expect(screen.getByRole("main", { name: "Bridge workspace" }).id).toBe("altar-main");
  expect(document.querySelectorAll("#altar-main")).toHaveLength(1);
  expect(screen.getByLabelText("Message")).toBe(composer);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.queryByRole("button", { name: "Collapse Bridge" })).toBeNull();
  expect(getBridgeSnapshot).toHaveBeenCalledTimes(reads);
  await visit("/atlas");
  expect(screen.getByRole("button", { name: "Collapse Bridge" })).toBeTruthy();
  expect(screen.getByLabelText("Message")).toBe(composer);
  expect(document.getElementById("bridge-message")).toBe(composer);
  expect(composer.value).toBe("Same draft in either presentation");
  expect(JSON.parse(localStorage.getItem("lychd.bridge-dock.layout.v1")!)).toEqual({ side: "right", width: 536, open: false });
  expect(getBridgeSnapshot).toHaveBeenCalledTimes(reads);
  expect(sendBridgeMessage).not.toHaveBeenCalled();
  shell.unmount();
});

it("reveals a narrow work view after full focus without overwriting a saved open preference", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  localStorage.setItem("lychd.bridge-dock.layout.v1", JSON.stringify({ side: "left", width: 440, open: true }));
  const shell = render(AltarShell, { children });
  await screen.findByLabelText("Message");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("navigation", { name: "Instruments" }).closest("header")?.hasAttribute("inert")).toBe(false);
  await visit("/atlas");
  expect(screen.getByRole("main").hasAttribute("inert")).toBe(false);
  expect(screen.getByRole("button", { name: "Expand Bridge" })).toBeTruthy();
  expect(JSON.parse(localStorage.getItem("lychd.bridge-dock.layout.v1")!).open).toBe(true);
  shell.unmount();
});

it("navigates from the trailing-slash Bridge root to the exact selected conversation", async () => {
  page.url.href = "http://localhost/bridge/";
  const shell = render(AltarShell, { children });
  await screen.findByLabelText("Message");
  await fireEvent.click(screen.getByRole("link", { name: /Older B/ }));
  expect(goto).toHaveBeenCalledWith("/bridge/session-b", { reset: false });
  expect(sendBridgeMessage).not.toHaveBeenCalled();
  shell.unmount();
});

it("opens the actual default séance and preserves active A while inspecting B", async () => {
  await visit("/atlas");
  const shell = render(AltarShell, { children });
  const composer = await screen.findByLabelText("Message");
  await fireEvent.input(composer, { target: { value: "Keep A draft" } });
  expect(screen.getByRole("link", { name: "Open Séance" }).getAttribute("href")).toBe("/seances/session-a");
  expect(screen.getByRole("link", { name: "Bridge" }).getAttribute("href")).toBe("/bridge");
  await visit("/seances/session-b");
  expect(screen.getByLabelText("Message")).toBe(composer);
  expect((composer as HTMLTextAreaElement).value).toBe("Keep A draft");
  expect(screen.getByRole("link", { name: "Open Séance" }).getAttribute("href")).toBe("/seances/session-a");
  expect(getBridgeSnapshot).toHaveBeenCalledExactlyOnceWith(undefined);
  expect(sendBridgeMessage).not.toHaveBeenCalled();
  await visit("/bridge");
  expect(screen.getByRole("link", { name: "Browse séances" }).getAttribute("href")).toBe("/seances");
  shell.unmount();
});

it("continues in inspected B explicitly and focuses its composer after the delayed exact read", async () => {
  let context: SeancesContext | undefined;
  const inspect = createRawSnippet(() => {
    context = getSeancesWorkspace();
    return { render: () => "<div>Inspected séance B</div>" };
  });
  await visit("/seances/session-b");
  const work = createBridgeWorkspace();
  const shell = render(AltarShell, { props: { children: inspect }, context: new Map([[bridgeWorkspaceKey, work]]) });
  const composer = await screen.findByLabelText("Message");
  await fireEvent.input(composer, { target: { value: "A stays safe" } });
  let finish!: (value: BridgeSnapshot) => void;
  vi.mocked(getBridgeSnapshot).mockImplementation((id) => id === "session-b" ? new Promise((resolve) => { finish = resolve; }) : Promise.resolve(snapshot(id)));
  await act(() => context!.continueInBridge("session-b"));
  expect(work.drafts.get("session-a")).toBe("A stays safe");
  expect(page.url.pathname).toBe("/seances/session-b");
  await act(() => finish(snapshot("session-b")));
  await screen.findByText("Retained answer for session-b");
  expect(document.activeElement).toBe(screen.getByLabelText("Message"));
  expect(document.querySelectorAll("#bridge-message")).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Open Séance" }).getAttribute("href")).toBe("/seances/session-b");
  expect(sendBridgeMessage).not.toHaveBeenCalled();
  shell.unmount();
});

it("warns before losing document-local material even after leaving Séances", async () => {
  let context: SeancesContext | undefined;
  const inspect = createRawSnippet(() => {
    context = getSeancesWorkspace();
    return { render: () => "<div>Inspected séance B</div>" };
  });
  await visit("/seances/session-b");
  const shell = render(AltarShell, { children: inspect });
  await screen.findByLabelText("Message");
  await act(() => { context!.add("session-b", snapshot("session-b").session!.turns![0]!); });
  await visit("/atlas");
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(true);
  expect(context!.materials.get("session-b")).toHaveLength(1);
  shell.unmount();
});

it("retains a shell-owned evaluation draft across navigation and warns only until it is discarded", async () => {
  let context: EvaluationWorkspace | undefined;
  const inspect = createRawSnippet(() => {
    context = getEvaluationWorkspace();
    return { render: () => "<div>Review workspace</div>" };
  });
  await visit("/loom/bridge_chat/1");
  const shell = render(AltarShell, { children: inspect });
  await screen.findByLabelText("Message");
  const score: LoomView = { schema_version: 1, pattern_id: "bridge_chat", revision: "1", digest: "sha256:test", implementation_revision: "test", checkpoint_schema: "test@1", entry_node: "start", nodes: [{ key: "start", kind: "step", label: "Start" }], edges: [], title: "Bridge", description: "Test score", publication: "published", mermaid_source: "flowchart TD", trigger_hint: "test" };
  await act(() => context!.start(score));
  const id = context!.activeId!;
  await visit("/atlas");
  const pending = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(pending);
  expect(pending.defaultPrevented).toBe(true);
  expect(context!.activeId).toBe(id);
  expect(context!.active?.score.pattern_id).toBe("bridge_chat");
  await act(() => context!.discard(id));
  const empty = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(empty);
  expect(empty.defaultPrevented).toBe(false);
  shell.unmount();
});

it("discards a queued B composer focus when explicit C selection supersedes it", async () => {
  let context: SeancesContext | undefined;
  const inspect = createRawSnippet(() => {
    context = getSeancesWorkspace();
    return { render: () => "<button type='button'>Workspace focus target</button>" };
  });
  await visit("/seances/session-b");
  const shell = render(AltarShell, { children: inspect });
  await screen.findByLabelText("Message");
  let finish!: (value: BridgeSnapshot) => void;
  vi.mocked(getBridgeSnapshot).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  await act(() => context!.continueInBridge("session-b"));
  await visit("/bridge/session-c");
  await screen.findByText("Retained answer for session-c");
  await act(() => finish(snapshot("session-b")));
  expect(screen.queryByText("Retained answer for session-b")).toBeNull();
  await visit("/atlas");
  const target = screen.getByRole("button", { name: "Workspace focus target" });
  target.focus();
  await fireEvent.click(screen.getByText("Conversations"));
  await fireEvent.click(screen.getByRole("link", { name: /Older B/ }));
  await screen.findByText("Retained answer for session-b");
  expect(document.activeElement).not.toBe(screen.getByLabelText("Message"));
  expect(page.url.pathname).toBe("/atlas");
  shell.unmount();
});

it("keeps exact unknown preparation recoverable when a legacy URL requests a different notes focus from another instrument", async () => {
  const recordId = "00000000-0000-4000-8000-000000000003", generationId = "00000000-0000-4000-8000-000000000004";
  vi.mocked(getArchiveNote).mockResolvedValue({ namespace_id: "00000000-0000-4000-8000-000000000001", reference: { record_id: recordId, revision_digest: "b".repeat(64), lifecycle_version: 2 }, source_key: "public-source", source_revision: "r1", source_digest: "c".repeat(64), producer: "author", observed_at: sessions[0]!.created_at, created_at: sessions[0]!.created_at, lifecycle: "promoted" });
  vi.mocked(discoverArchiveGeneration).mockResolvedValue({ generation_id: generationId, manifest_digest: "a".repeat(64) });
  vi.mocked(deriveArchiveNote).mockRejectedValue(new Error("Response lost"));
  await visit(`/bridge?notes=${recordId}`);
  const shell = render(AltarShell, { children });
  await screen.findByText("Configured generation");
  await fireEvent.click(screen.getByRole("button", { name: "Review preparation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Prepare this promoted revision" }));
  await screen.findByText(/Earlier preparation outcome remains unknown/);
  const frozen = screen.getByRole("button", { name: "Check frozen preparation reference" });
  await fireEvent.click(screen.getByRole("button", { name: "Close Memory" }));
  await visit("/loom/bridge_chat/1");
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  await visit("/bridge?notes=new");
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(page.url.pathname).toBe("/loom/bridge_chat/1");
  expect(page.url.search).toBe("");
  expect(screen.getByRole("button", { name: "Check frozen preparation reference" })).toBe(frozen);
  expect(screen.getByText(/Earlier preparation outcome remains unknown/)).toBeTruthy();
  expect(screen.queryByRole("form", { name: "Public note intake" })).toBeNull();
  expect(deriveArchiveNote).toHaveBeenCalledTimes(1); expect(getArchiveNote).toHaveBeenCalledTimes(1);
  confirm.mockReturnValue(true);
  await visit("/bridge?notes=new");
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(page.url.search).toBe("?notes=new");
  expect(screen.getByRole("form", { name: "Public note intake" })).toBeTruthy();
  expect(deriveArchiveNote).toHaveBeenCalledTimes(1);
  confirm.mockRestore(); shell.unmount();
});
