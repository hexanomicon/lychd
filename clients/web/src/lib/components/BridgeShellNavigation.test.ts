import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BridgeSnapshot, OrbRunSnapshot, RunProjectionSnapshot } from "$lib/api/models";

const navigationHooks = vi.hoisted(() => ({
  before: [] as Array<(navigation: { from: { url: URL } }) => void>,
  after: [] as Array<(navigation: { type: "link" | "popstate"; to: { url: URL } }) => void>
}));

vi.mock("$app/state", async () => {
  const { SvelteURL } = await import("svelte/reactivity");
  return { page: { state: {}, url: new SvelteURL("http://localhost/bridge") } };
});
vi.mock("$app/navigation", () => ({ goto: vi.fn(), replaceState: vi.fn(),
  beforeNavigate: vi.fn((callback: (navigation: { from: { url: URL } }) => void) => { navigationHooks.before.push(callback); }),
  afterNavigate: vi.fn((callback: (navigation: { type: "link" | "popstate"; to: { url: URL } }) => void) => { navigationHooks.after.push(callback); }) }));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  cancelBridgeRun: vi.fn(),
  createBridgeSession: vi.fn(),
  decideConsent: vi.fn(),
  getAltarStatus: vi.fn(),
  getArchiveProfile: vi.fn().mockResolvedValue({ profile: "local-public-notes@1", namespace_id: "00000000-0000-4000-8000-000000000001", owner_subject: { identity: "owner" }, policy_revision: "policy" }),
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

import { page } from "$app/state";
import { createBridgeSession, getAltarStatus, getBridgeSnapshot, getOrbRun, sendBridgeMessage, listenToRun, cancelBridgeRun } from "$lib/api/client";
import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/bridge/workspace.svelte";
import AltarShell from "./AltarShell.svelte";
import BridgePage from "../../routes/bridge/+page.svelte";

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
    for (const callback of navigationHooks.before) callback({ from: { url: new URL(page.url.href) } });
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
    await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
    expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
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
    await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
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
    await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
    await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
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

  it("reveals focused applications entered from a narrow Bridge without unmounting the ordinary conversation", async () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
    await visit("/bridge/session-b");
    const shell = render(AltarShell, { children });
    const composer = await screen.findByLabelText("Message");
    for (const [label, query] of [
      ["Manage public notes", "notes=manage"],
      ["Recall public sources", "notes=recall"],
      ["Investigate public source", "investigation=new"]
    ]) {
      if (document.getElementById("bridge-dock")?.closest("[hidden]")) {
        await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
      }
      const link = screen.getByRole("link", { name: label });
      expect(link.getAttribute("href")).toBe(`/bridge?${query}`);
      await visit(link.getAttribute("href")!);
      const main = screen.getByRole("main");
      expect(main.hasAttribute("inert")).toBe(false);
      expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
      expect(document.activeElement).toBe(main);
      expect(document.getElementById("bridge-message")).toBe(composer);
    }
    await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
    const orbLink = screen.getByRole("link", { name: "Look into the Orb" });
    await visit(orbLink.getAttribute("href")!);
    expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole("main"));
    // Exercise the real focused route composition after leaving the modal.
    await visit("/bridge?notes=manage");
    const focused = render(BridgePage, { target: screen.getByRole("main") });
    expect(await screen.findByRole("heading", { name: "Public notes" })).toBeTruthy();
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    expect(cancelBridgeRun).not.toHaveBeenCalled();
    focused.unmount(); shell.unmount();
  });

  it("keeps the explicit attention URL a chooser without changing the remembered session", async () => {
    await visit("/bridge/session-b");
    const shell = render(AltarShell, { children });
    await screen.findByLabelText("Message");
    await visit("/bridge?attention=pending");
    await screen.findByRole("heading", { name: "Conversations awaiting consent" });
    expect(screen.queryByLabelText("Message")).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
    await fireEvent.click(screen.getByRole("button", { name: "Bridge" }));
    await screen.findByText("Retained answer for session-b");
    expect(vi.mocked(getBridgeSnapshot).mock.calls.map(([id]) => id)).toEqual(["session-b", undefined, "session-b"]);
    expect(sendBridgeMessage).not.toHaveBeenCalled();
    shell.unmount();
  });
});
