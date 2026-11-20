<script lang="ts">
  import { beforeNavigate, goto, replaceState } from "$app/navigation";
  import { page } from "$app/state";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { bridgeHistoryContext, navigationId, orbReturnHref, type BridgeHistory, type BridgeHistoryEntry, type BridgeHistoryHost } from "$lib/navigation/instruments";
  import { getContext, onDestroy, onMount, tick, untrack } from "svelte";
  import { SvelteMap, SvelteSet } from "svelte/reactivity";

  import {
    ApiError,
    cancelBridgeRun,
    createBridgeSession,
    getBridgeSessions,
    getBridgeSnapshot,
    getAtlasProject,
    getRunSnapshot,
    listenToRun,
    sendBridgeMessage
  } from "$lib/api/client";
  import type { BridgeSnapshot, ConsentCard as ConsentCardModel } from "$lib/api/models";
  import {
    mergeSnapshotLiveTurns,
    replaceLiveTurnFromSnapshot,
    type LiveTurn
  } from "$lib/pages/bridge/state/projection";
  import ConsentCard from "$lib/components/shared/ConsentCard.svelte";
  import CircleRun from "$lib/pages/bridge/components/CircleRun.svelte";
  import CircleInspector from "$lib/pages/bridge/components/CircleInspector.svelte";
  import ConversationHeading from "$lib/components/conversation/ConversationHeading.svelte";
  import ConversationList from "$lib/components/conversation/ConversationList.svelte";
  import TurnHeader from "$lib/components/conversation/TurnHeader.svelte";
  import Button from "$lib/components/shared/Button.svelte";
  import Disclosure from "$lib/components/shared/Disclosure.svelte";
  import EmptyState from "$lib/components/shared/EmptyState.svelte";
  import FaultNotice from "$lib/components/shared/FaultNotice.svelte";
  import KeyValueList from "$lib/components/shared/KeyValueList.svelte";
  import LoadingState from "$lib/components/shared/LoadingState.svelte";
  import StatusPill from "$lib/components/shared/StatusPill.svelte";
  import DelegateMark from "$lib/components/shared/DelegateMark.svelte";
  import GenUI from "$lib/pages/bridge/components/GenUI.svelte";
  import AtlasLinks from "$lib/components/atlas/AtlasLinks.svelte";
  import AltarWelcome from "$lib/pages/bridge/components/AltarWelcome.svelte";
  import NamingCeremony from "$lib/pages/bridge/components/NamingCeremony.svelte";
  import { atlasHref } from "$lib/atlas/navigation";
  import { bridgeWorkspaceKey, createBridgeWorkspace, type BridgeWorkspace } from "$lib/shell/state/bridge-workspace.svelte";
  import { delegationStatusLabel } from "$lib/delegation/presentation";
  import { bridgePinsLimit, bridgePinsStorageKey, parsePinnedConversations, togglePinnedConversation } from "$lib/navigation/pins";
  import BridgeVoiceInput from "./BridgeVoiceInput.svelte";
  import DictationFeedback from "$lib/pages/bridge/components/DictationFeedback.svelte";
  import { workCommandKey, type CommandTarget, type CommandResult, type WorkCommandRegistry } from "$lib/shell/state/work-commands";
  import type { DictationDraft, DictationOptions } from "$lib/pages/bridge/state/voice/dictation";

  let {
    sessionId,
    embedded = false,
    visible = true,
    isVisible,
    search,
    onNavigate,
    onSessionResolved
  }: {
    onSessionResolved?: (id: string | null) => void;
    sessionId?: string;
    embedded?: boolean;
    visible?: boolean;
    isVisible?: () => boolean;
    search?: string;
    onNavigate?: (sessionId: string, search: string, composerFocus?: boolean) => void | Promise<void>;
  } = $props();
  const bridgeSearch = $derived(search ?? page.url.search);
  const bridgeParams = $derived(new URLSearchParams(bridgeSearch));
  let snapshot = $state<BridgeSnapshot | null>(null);
  const work = getContext<BridgeWorkspace | undefined>(bridgeWorkspaceKey) ?? createBridgeWorkspace();
  let pins = $state.raw<readonly string[]>([]);
  let pinNotice = $state("");
  let compactHistory = $state(false);
  // Open by default only in the full standalone view; the reader may toggle it.
  let historyOpen = $derived(!embedded && !compactHistory);
  onMount(() => {
    try { pins = parsePinnedConversations(localStorage.getItem(bridgePinsStorageKey)); }
    catch { /* Pinning remains available for this tab when storage is unavailable. */ }
    const media = window.matchMedia?.("(max-width: 48rem)");
    compactHistory = media?.matches ?? false;
    const changed = (event: MediaQueryListEvent) => { compactHistory = event.matches; };
    media?.addEventListener?.("change", changed);
    return () => media?.removeEventListener?.("change", changed);
  });
  function togglePin(id: string) {
    const next = togglePinnedConversation(pins, id);
    if (next === pins) { pinNotice = `You can pin up to ${bridgePinsLimit} conversations. Unpin one first.`; return; }
    const returnFocus = document.activeElement?.id === `bridge-pin-${id}`;
    pins = next;
    pinNotice = "";
    try { localStorage.setItem(bridgePinsStorageKey, JSON.stringify(next)); }
    catch { pinNotice = "Pins are kept for this tab; browser storage is unavailable."; }
    if (returnFocus) void tick().then(() => {
      if (!destroyed) (document.getElementById(`bridge-pin-${id}`) ?? document.querySelector<HTMLButtonElement>("[data-new-seance]"))?.focus({ preventScroll: true });
    });
  }
  const observedSettlements = new Map(work.settlements);
  let projectHint = $derived.by(() => {
    const id = bridgeParams.get("project");
    return id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id) ? id : null;
  });
  let attentionOnly = $derived(bridgeParams.get("attention") === "pending");
  let choosing = $derived(!sessionId && (attentionOnly || bridgeParams.get("choose") === "conversation" || !!projectHint));
  let hintedProject = $state<{ id: string; title: string } | null>(null);
  let projectError = $state("");
  let focusRun = $derived(navigationId(bridgeParams.get("run")));
  let focusConsent = $derived(bridgeParams.has("consent")
    ? navigationId(bridgeParams.get("consent")) : undefined);
  let consentReturnHref = $derived(focusConsent !== undefined && focusRun
    ? orbReturnHref(focusRun, bridgeSearch) : null);
  let focusNavigation: {
    sessionId: string | undefined;
    run: string | null;
    consent: string | null | undefined;
    handled: boolean;
  } | undefined;

  function setPrompt(text: string) {
    if (selected) work.setDraft(selected.id, text);
    notifyVoice();
  }

  function bridgeHref(id: string) {
    return `/bridge/${encodeURIComponent(id)}${projectHint ? `?project=${encodeURIComponent(projectHint)}` : ""}`;
  }
  function selectConversation(event: MouseEvent, id: string) {
    if (!onNavigate || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    invalidateVoiceContext();
    void Promise.resolve(onNavigate(id, projectHint ? `?project=${encodeURIComponent(projectHint)}` : ""))
      .catch((cause) => omen(cause instanceof Error ? cause.message : "Conversation navigation failed."));
  }
  let loading = $state(true);
  let creatingSession = $state(false);
  let error = $state("");
  let readError = $state("");
  let thread: HTMLDivElement | undefined;
  let loadVersion = 0;
  let sessionsRequest: AbortController | null = null;
  let sessionsLoading = $state(false);
  let sessionsError = $state("");
  let renderVersion = $state(0);
  let consentAuthorityVersion = 0;
  let stickToTail = $state(true);
  let releasedRunFocus = $state<string | null>(null);
  let liveTurns = $state<LiveTurn[]>([]);
  let activeSessionIdentity: string | null = null;
  const streams = new SvelteMap<string, () => void>();
  const refreshTimers = new SvelteMap<string, number>();
  const cancellingRuns = new SvelteSet<string>();
  const recoveredHardClosures = new Set<string>();
  let destroyed = false;
  const runStatuses = new Set([
    "queued",
    "running",
    "awaiting_hardware",
    "awaiting_consent",
    "awaiting_delegate",
    "awaiting_peer",
    "cancelling",
    "done",
    "failed",
    "cancelled"
  ]);

  function operatorState(value: string): string {
    if (value === "awaiting_hardware") return "awaiting animators";
    if (value === "awaiting_delegate") return "delegated labor";
    return value.replaceAll("_", " ");
  }

  let selected = $derived(choosing ? null : snapshot?.session ?? null);
  const sessionMetadata = $derived(new Map([
    ...(snapshot?.sessions ?? []).map((session) => [session.id, session] as const),
    ...(selected ? [[selected.id, selected] as const] : [])
  ]));
  const visiblePins = $derived(pins.filter((id) => !attentionOnly || (sessionMetadata.get(id)?.pending_count ?? 0) > 0));
  const recentSessions = $derived((snapshot?.sessions ?? []).filter((session) =>
    !pins.includes(session.id) && (!attentionOnly || (session.pending_count ?? 0) > 0)));

  // Conversation history is projected once through the BridgeHistory interface. While the
  // Bridge is the focused workspace the Altar shell lists it in the sidebar; when docked or
  // standalone, this view lists it itself. Either way this view owns data and intents.
  const historyHost = getContext<BridgeHistoryHost | undefined>(bridgeHistoryContext);
  const shellHistory = $derived(!!historyHost && !embedded);
  function historyEntry(id: string): BridgeHistoryEntry {
    const session = sessionMetadata.get(id);
    return {
      id,
      title: session?.title ?? `Conversation · ${id}`,
      pending: session?.pending_count ?? 0,
      loaded: !!session,
      marker: work.pending.has(id) ? "Offering unresolved" : work.refused.has(id) ? "Refused offering" : work.drafts.has(id) ? "Draft" : null
    };
  }
  const history: BridgeHistory = {
    get pinned() { return visiblePins.map(historyEntry); },
    get recent() { return recentSessions.map((session) => historyEntry(session.id)); },
    get unlisted() {
      return selected && !pins.includes(selected.id) && !snapshot?.sessions.some((session) => session.id === selected.id)
        ? historyEntry(selected.id) : null;
    },
    get selectedId() { return selected?.id ?? null; },
    get ready() { return !loading && !error; },
    get creating() { return creatingSession; },
    get hasMore() { return !!snapshot?.sessions_next_cursor; },
    get loadingMore() { return sessionsLoading; },
    get notice() { return sessionsError || pinNotice; },
    isPinned: (id) => pins.includes(id),
    href: bridgeHref,
    create: () => void createSession(),
    togglePin,
    select: selectConversation,
    loadMore: () => void loadMoreSessions()
  };
  // The view survives route changes inside the shell, so placement follows `embedded`.
  $effect(() => {
    if (!historyHost || embedded) return;
    return historyHost.register(history);
  });
  let focusedConsent = $derived(selected && sessionId === selected.id && focusRun && focusConsent && (
    (selected.turns ?? []).some((turn) => turn.run_id === focusRun) ||
    snapshot?.active_runs.some((run) => run.run_id === focusRun && run.session_id === selected.id)
  ) ? snapshot?.pending_consents.find((card) => card.id === focusConsent && card.run_id === focusRun &&
    card.state === "pending_consent") : undefined);
  let prompt = $derived(selected ? work.drafts.get(selected.id) ?? "" : "");
  let refusedOfferings = $derived(selected ? work.refused.get(selected.id) ?? [] : []);
  let pendingOffering = $derived(selected ? work.pending.get(selected.id) : undefined);

  let firstVisit = $derived(
    !choosing && !loading && !error && snapshot !== null && !selected &&
    snapshot.sessions.length === 0 && snapshot.active_runs.length === 0 &&
    snapshot.pending_consents.length === 0
  );
  let selectedLiveTurns = $derived(
    liveTurns.filter((turn) => turn.sessionId === selected?.id)
  );
  let hasUnsettledRun = $derived(selectedLiveTurns.some(
    (turn) => !["done", "failed", "cancelled"].includes(turn.runStatus)
  ));
  let runFocusKey = $derived(selected && focusRun ? `${selected.id}:${focusRun}` : null);
  let readingFocusedRun = $derived(!!runFocusKey && releasedRunFocus !== runFocusKey);
  let selectedPendingCount = $derived(
    snapshot?.pending_consents.filter((card) => card.state === "pending_consent").length ?? 0
  );
  // The inspector follows the focused Run, else the latest live Run, else the latest retained reply.
  const inspectedTurn = $derived(selectedLiveTurns.find((turn) => turn.runId === focusRun) ?? selectedLiveTurns.at(-1));
  const inspectedRunId = $derived(inspectedTurn?.runId ??
    (selected?.turns ?? []).findLast((turn) => turn.role === "agent" && !!turn.run_id)?.run_id ?? null);
  const inspectedPending = $derived(inspectedRunId
    ? snapshot?.pending_consents.filter((card) => card.run_id === inspectedRunId && card.state === "pending_consent").length ?? 0
    : 0);
  const showInspector = $derived(!embedded && !!selected && !!inspectedRunId);

  const workCommands = getContext<WorkCommandRegistry | undefined>(workCommandKey);
  let commandTarget = $state.raw<CommandTarget | null>(null);
  let commandResult = $state.raw<CommandResult | null>(null);
  let commandPending = $state(false);
  let composerMode = $state<"chat" | "work">("chat");
  let composing = $state(false);
  let contextEpoch = $state(0);
  let targetEpoch = $state(0);
  let voice = $state<ReturnType<typeof BridgeVoiceInput>>();
  export function suspendVoice() { voice?.suspend(); }
  $effect(() => {
    if (!visible) untrack(suspendVoice);
  });
  const destination = $derived(commandTarget
    ? `${commandTarget.instrument[0]?.toUpperCase()}${commandTarget.instrument.slice(1)} · ${commandTarget.label}`
    : "Work target unavailable");

  function readVoiceSnapshot(): DictationDraft {
    const id = selected?.id ?? "";
    return {
      sessionId: id,
      draftText: id ? work.drafts.get(id) ?? "" : "",
      draftRevision: id ? work.draftRevisions.get(id) ?? 0 : 0,
      mode: composerMode, contextEpoch, targetEpoch, composing,
      busy: destroyed || !(isVisible?.() ?? visible) || !id || loading || choosing || creatingSession || hasUnsettledRun ||
        !!work.pending.get(id) || commandPending ||
        [...work.consentDecisions.values()].some((decision) => decision.sessionId === id && decision.sending)
    };
  }
  const voiceSnapshot = $derived(readVoiceSnapshot());
  function notifyVoice() { voice?.notifyChanged(readVoiceSnapshot()); }
  function invalidateVoiceContext() {
    contextEpoch += 1;
    commandResult = null;
    notifyVoice();
  }
  beforeNavigate(() => invalidateVoiceContext());
  onMount(() => workCommands?.subscribe((target) => {
    commandTarget = target;
    targetEpoch += 1;
    notifyVoice();
  }));
  $effect(() => {
    const next = voiceSnapshot;
    untrack(() => voice?.notifyChanged(next));
  });

  function sameVoiceDraft(expected: DictationDraft, current: DictationDraft): boolean {
    return expected.sessionId === current.sessionId && expected.draftText === current.draftText &&
      expected.draftRevision === current.draftRevision && expected.mode === current.mode &&
      expected.contextEpoch === current.contextEpoch && expected.targetEpoch === current.targetEpoch &&
      expected.composing === current.composing;
  }
  function adoptVoice(expected: DictationDraft, nextText: string): DictationDraft | null {
    const current = readVoiceSnapshot();
    if (!sameVoiceDraft(expected, current) || expected.busy !== current.busy ||
        current.busy || current.composing || !current.sessionId) return null;
    work.setDraft(current.sessionId, nextText);
    const advanced = readVoiceSnapshot();
    notifyVoice();
    return advanced;
  }
  function changeMode(event: Event) {
    composerMode = (event.currentTarget as HTMLSelectElement).value === "work" ? "work" : "chat";
    invalidateVoiceContext();
  }
  function changeComposition(value: boolean) { composing = value; notifyVoice(); }

  async function submitWork(draft: DictationDraft, target: CommandTarget | null) {
    const current = readVoiceSnapshot();
    if (current.busy || current.composing || !sameVoiceDraft(draft, current)) return;
    if (!workCommands || !target || !workCommands.isCurrent(target)) {
      commandResult = { status: "unavailable", summary: "The work target changed or is unavailable. Select the current work target before sending." };
      return;
    }
    commandPending = true;
    commandResult = null;
    notifyVoice();
    try {
      const result = await workCommands.execute(draft.draftText.trim(), target);
      if (destroyed || draft.sessionId !== selected?.id || draft.contextEpoch !== contextEpoch) return;
      commandResult = result;
      // A late preview must never clear a replacement draft or a changed target.
      if ((result.status === "preview" || result.status === "applied") &&
          sameVoiceDraft(draft, readVoiceSnapshot()) && workCommands.isCurrent(target)) {
        work.setDraft(draft.sessionId, "");
      }
    } finally {
      commandPending = false;
      if (!destroyed) notifyVoice();
    }
  }
  const submitVoice: DictationOptions["submit"] = (draft, intent) => {
    const current = readVoiceSnapshot();
    if (!sameVoiceDraft(draft, current) || draft.busy !== current.busy || current.busy || current.composing) return;
    return draft.mode === "work" ? submitWork(draft, intent.target) : submit();
  };
  function sendComposer() {
    if (voice?.handleSend()) return;
    const draft = readVoiceSnapshot();
    if (draft.busy || draft.composing || !draft.draftText.trim()) return;
    if (draft.mode === "work") void submitWork(draft, workCommands?.capture() ?? null);
    else void submit();
  }

  let namingStarted = $state(false);
  let namingOpen = $state(false);
  let namingCeremony = $state<ReturnType<typeof NamingCeremony>>();
  let namingReturn: HTMLElement | null = null;
  let namingTools: HTMLElement | undefined;
  function captureNamingTools(node: HTMLElement) {
    namingTools = node;
    return () => { namingTools = undefined; };
  }
  async function openNaming() {
    namingReturn = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    namingStarted = true;
    namingOpen = true;
    await tick();
    namingCeremony?.focus();
  }
  function closeNaming() {
    namingOpen = false;
    if (namingReturn?.isConnected) namingReturn.focus();
    else namingTools?.focus();
  }

  async function askForName(text: string) {
    if (destroyed || loading || choosing || creatingSession) {
      throw new Error("Open a conversation and let it finish loading, then try the naming request again.");
    }
    let opened: string | undefined;
    if (!selected) {
      const version = loadVersion;
      creatingSession = true;
      try {
        const created = await createBridgeSession();
        if (destroyed || loadVersion !== version) throw new Error("The conversation changed. No naming request was sent.");
        opened = created.session.id;
        await load(opened);
        if (destroyed || snapshot?.session?.id !== opened) throw new Error("The new conversation could not be read. No naming request was sent.");
      } finally {
        if (!destroyed) creatingSession = false;
      }
    }
    const admitted = await submit(false, text);
    // Use the same admission, retained offering and stream recovery as ordinary chat.
    if (opened && !destroyed && selected?.id === opened) {
      if (onNavigate) await onNavigate(opened, "");
      else await goto(bridgeHref(opened), { reset: false });
    }
    if (!admitted) throw new Error("The naming request was not confirmed. Check the conversation for an active reply or an unresolved offering before trying again.");
  }

  function turnIsTerminal(turn: LiveTurn): boolean {
    return turn.state === "done" || turn.state === "failed" || turn.state === "cancelled";
  }

  function omen(text: string, fault = true) {
    window.dispatchEvent(new CustomEvent("altar:omen", { detail: { text, fault } }));
  }

  function retryRead() {
    if (loading || !readError || snapshot || destroyed) return;
    void load(sessionId, true);
  }

  async function load(id?: string, preserveReadError = false) {
    // A later selected session supersedes an earlier explicit composer-focus request.
    if (focusNewSession !== null && focusNewSession !== id) focusNewSession = null;
    invalidateVoiceContext();
    const version = ++loadVersion;
    sessionsRequest?.abort();
    sessionsRequest = null;
    sessionsLoading = false;
    sessionsError = "";
    const settlementsAtRequest = new Map(work.settlements);
    const runAuthorityAtRequest = new Map(
      liveTurns.map((turn) => [turn.runId, turn.authorityGeneration])
    );
    const requestedIdentityChanged =
      id !== undefined && activeSessionIdentity !== null && activeSessionIdentity !== id;
    loading = true;
    notifyVoice();
    error = "";
    if (!preserveReadError) readError = "";
    if (requestedIdentityChanged) {
      snapshot = null;
      onSessionResolved?.(null);
      releasedRunFocus = null;
      stickToTail = true;
    }
    try {
      const received = await getBridgeSnapshot(id);
      const next = choosing ? { ...received, session: null, active_runs: [], pending_consents: [] } : received;
      if (destroyed || version !== loadVersion) return;
      const nextSessionIdentity = next.session?.id ?? null;
      if (nextSessionIdentity && (work.settlements.get(nextSessionIdentity) ?? 0) !== (settlementsAtRequest.get(nextSessionIdentity) ?? 0)) {
        await load(id, preserveReadError);
        return;
      }
      activeSessionIdentity = nextSessionIdentity;
      for (const [id, decision] of work.consentDecisions) {
        if (decision.sessionId === nextSessionIdentity && !decision.sending &&
            !next.pending_consents.some((consent) => consent.id === id && consent.state === "pending_consent")) {
          work.consentDecisions.delete(id);
        }
      }
      const merged = mergeSnapshotLiveTurns(next, $state.snapshot(liveTurns));
      const terminalRecoveries = new Set<string>();
      for (const active of next.active_runs) {
        const index = merged.liveTurns.findIndex((turn) => turn.runId === active.run_id);
        const current = merged.liveTurns[index];
        const expectedGeneration = runAuthorityAtRequest.get(active.run_id);
        if (current && expectedGeneration !== undefined && (active.terminal || !streams.has(active.run_id))) {
          // Terminal authority remains decisive even when its stream has not closed.
          const refreshed = replaceLiveTurnFromSnapshot(
            current,
            active,
            expectedGeneration
          );
          merged.liveTurns[index] = refreshed;
          if (turnIsTerminal(refreshed)) {
            streams.get(active.run_id)?.();
            streams.delete(active.run_id);
            clearRefreshTimer(active.run_id);
          } else if (active.terminal) {
            terminalRecoveries.add(active.run_id);
          }
        }
      }
      for (const runId of merged.retiredRunIds) {
        streams.get(runId)?.();
        streams.delete(runId);
        clearRefreshTimer(runId);
      }
      snapshot = next;
      onSessionResolved?.(next.session?.id ?? null);
      readError = "";
      consentAuthorityVersion++;
      liveTurns = merged.liveTurns;
      for (const active of next.active_runs) {
        const turn = liveTurns.find((item) => item.runId === active.run_id);
        if (!turn) continue;
        if (terminalRecoveries.has(active.run_id)) {
          // Fence the superseded channel before using its one bounded recovery.
          streams.get(active.run_id)?.();
          streams.delete(active.run_id);
          turn.state = "stale";
          turn.activity = "projection stale";
          turn.authorityGeneration++;
          void recoverHardClosedRun(active.run_id, turn.sessionId);
        } else if (!turnIsTerminal(turn)) attachStream(turn, turn.cursor);
      }
      window.dispatchEvent(new CustomEvent("altar:attention", { detail: next.pending_count }));
    } catch (cause) {
      if (version === loadVersion) {
        onSessionResolved?.(null);
        error = cause instanceof Error ? cause.message : "The Bridge stayed dark.";
        if (!snapshot) readError = error;
      }
    } finally {
      if (version === loadVersion) { loading = false; notifyVoice(); }
    }
  }

  async function loadMoreSessions() {
    const cursor = snapshot?.sessions_next_cursor;
    if (!cursor || loading || sessionsLoading || destroyed) return;
    const version = loadVersion;
    const controller = new AbortController();
    sessionsRequest = controller;
    sessionsLoading = true;
    sessionsError = "";
    try {
      const next = await getBridgeSessions(cursor, controller.signal);
      if (destroyed || controller.signal.aborted || version !== loadVersion || !snapshot) return;
      const seen = new Set(snapshot.sessions.map((session) => session.id));
      const additional = next.sessions.filter((session) => {
        if (seen.has(session.id)) return false;
        seen.add(session.id);
        return true;
      });
      snapshot = {
        ...snapshot,
        sessions: [...snapshot.sessions, ...additional],
        sessions_next_cursor: next.next_cursor
      };
    } catch {
      if (!destroyed && !controller.signal.aborted && version === loadVersion) {
        sessionsError = "Older conversations could not be loaded. Try again.";
      }
    } finally {
      if (sessionsRequest === controller) {
        sessionsRequest = null;
        sessionsLoading = false;
      }
    }
  }

  $effect(() => {
    const routeSessionId = sessionId;
    choosing;
    untrack(() => void load(routeSessionId));
  });

  $effect(() => {
    const id = selected?.id;
    const revision = id ? work.settlements.get(id) ?? 0 : 0;
    if (id && revision !== (observedSettlements.get(id) ?? 0)) {
      observedSettlements.set(id, revision);
      untrack(() => void load(id));
    }
  });

  $effect(() => {
    const id = projectHint;
    const controller = new AbortController();
    untrack(() => {
      hintedProject = null;
      projectError = "";
      if (id) void getAtlasProject(id, controller.signal).then((project) => {
        if (!controller.signal.aborted && project.id === id) hintedProject = { id, title: project.title };
      }).catch(() => {
        if (!controller.signal.aborted) projectError = "The originating Atlas project is unavailable.";
      });
    });
    return () => controller.abort();
  });

  $effect(() => {
    const id = selected?.id;
    const routeSessionId = sessionId;
    const run = focusRun;
    const consent = focusConsent;
    const consentTarget = focusedConsent?.id;
    const ready = !loading;
    renderVersion;
    if (!focusNavigation || focusNavigation.sessionId !== routeSessionId || focusNavigation.run !== run ||
        focusNavigation.consent !== consent) {
      focusNavigation = { sessionId: routeSessionId, run, consent, handled: false };
      if (!run) stickToTail = true;
    }
    const navigation = focusNavigation;
    if (!id || !run || !ready || navigation.handled) return;
    void tick().then(() => {
      if (destroyed || selected?.id !== id || sessionId !== routeSessionId || focusRun !== run ||
          focusConsent !== consent || loading || focusNavigation !== navigation || navigation.handled) return;
      // Selection belongs to this navigation, including an unavailable historical request.
      navigation.handled = true;
      const target = consent !== undefined
        ? consentTarget && focusedConsent?.id === consentTarget
          ? thread?.querySelector<HTMLElement>(`[data-consent-id="${consentTarget}"]`) : null
        : thread?.querySelector<HTMLElement>(`[data-run-id="${run}"]`);
      if (!target) return;
      stickToTail = false;
      target.focus({ preventScroll: true });
      target.scrollIntoView?.({ block: "center" });
    });
  });

  $effect.pre(() => {
    renderVersion;
    const target = thread;
    if (target && stickToTail && !readingFocusedRun) {
      void tick().then(() => {
        if (!destroyed && target === thread && stickToTail && !readingFocusedRun) {
          target.scrollTop = target.scrollHeight;
        }
      });
    }
  });

  function captureThread(node: HTMLDivElement) {
    thread = node;
    return () => {
      if (thread === node) thread = undefined;
    };
  }

  onDestroy(() => {
    destroyed = true;
    loadVersion++;
    sessionsRequest?.abort();
    for (const close of streams.values()) close();
    streams.clear();
    for (const timer of refreshTimers.values()) window.clearTimeout(timer);
    refreshTimers.clear();
  });

  async function createSession() {
    if (creatingSession) return;
    creatingSession = true;
    invalidateVoiceContext();
    try {
      const created = await createBridgeSession();
      if (destroyed) return;
      if (onNavigate) {
        focusNewSession = created.session.id;
        await onNavigate(created.session.id, projectHint ? `?project=${encodeURIComponent(projectHint)}` : "", true);
      } else {
        await goto(bridgeHref(created.session.id), {
          reset: false,
          state: { bridgeComposerFocus: created.session.id }
        });
      }
    } catch (cause) {
      if (!destroyed) omen(cause instanceof Error ? cause.message : "A séance could not be opened.");
    } finally {
      if (!destroyed) { creatingSession = false; notifyVoice(); }
    }
  }

  let focusNewSession = $state<string | null>(null);
  export function focusSessionComposer(id: string) { focusNewSession = id; }
  function focusCreatedComposer(node: HTMLTextAreaElement) {
    if (selected?.id && focusNewSession === selected.id) {
      node.focus();
      focusNewSession = null;
    } else if (selected?.id && page.state?.bridgeComposerFocus === selected.id) {
      node.focus();
      const nextState = { ...page.state };
      delete nextState.bridgeComposerFocus;
      replaceState("", nextState);
    }
  }

  function clearRefreshTimer(runId: string) {
    const timer = refreshTimers.get(runId);
    if (timer !== undefined) window.clearTimeout(timer);
    refreshTimers.delete(runId);
  }

  function scheduleSettledRefresh(runId: string, targetSessionId: string) {
    clearRefreshTimer(runId);
    const expectedRouteSessionId = sessionId;
    const timer = window.setTimeout(() => {
      refreshTimers.delete(runId);
      if (destroyed) return;
      if (sessionId !== expectedRouteSessionId) return;
      if (snapshot?.session?.id !== targetSessionId) return;
      void load(sessionId);
    }, 50);
    refreshTimers.set(runId, timer);
  }

  function attachStream(turn: LiveTurn, initialCursor = turn.cursor) {
    if (destroyed || turn.state !== "streaming" || streams.has(turn.runId)) return;
    const targetRunId = turn.runId;
    const targetSessionId = turn.sessionId;
    let hardClosed = false;
    let close: (() => void) | undefined;
    close = listenToRun(
      targetRunId,
      (event) => {
        if (destroyed) return;
        const active = liveTurns.find((item) => item.runId === targetRunId);
        if (!active) return;
        if (event.seq <= active.cursor) return;
        active.cursor = event.seq;
        active.authorityGeneration++;
        const payload = event.payload;
        if (event.kind === "token") active.content += String(payload.text ?? "");
        else if (event.kind === "status") {
          active.activity = String(payload.text ?? "running");
          if (runStatuses.has(active.activity)) active.runStatus = active.activity;
        } else if (event.kind === "node") {
          active.occurrenceId =
            typeof payload.occurrence_id === "string" && payload.occurrence_id
              ? payload.occurrence_id
              : active.occurrenceId;
          active.delegatedJobId =
            typeof payload.delegated_job_id === "string" && payload.delegated_job_id
              ? payload.delegated_job_id
              : active.delegatedJobId;
          active.delegatedRuntime =
            typeof payload.delegated_runtime === "string" && payload.delegated_runtime
              ? payload.delegated_runtime
              : active.delegatedRuntime;
        } else if (event.kind === "dispatch") {
          active.capabilityKey = String(payload.text ?? "");
          active.grantId = typeof payload.grant_id === "string" ? payload.grant_id : null;
          active.dispatchOccurrenceId =
            typeof payload.occurrence_id === "string" ? payload.occurrence_id : null;
          active.occurrenceId =
            typeof payload.occurrence_id === "string" && payload.occurrence_id
              ? payload.occurrence_id
              : active.occurrenceId;
        } else if (event.kind === "transition") {
          active.transitionRequestId = String(payload.text ?? "");
          active.transitionOccurrenceId =
            typeof payload.occurrence_id === "string" ? payload.occurrence_id : null;
          active.transitionPhase =
            typeof payload.phase === "string" ? payload.phase : active.transitionPhase;
          active.capabilityKey =
            typeof payload.capability_key === "string"
              ? payload.capability_key
              : active.capabilityKey;
        } else if (event.kind === "fragment") active.fragments.push(payload);
        else if (event.kind === "consent") {
          if (snapshot?.session?.id === active.sessionId) void load(active.sessionId);
          else window.dispatchEvent(new CustomEvent("altar:attention"));
        } else if (event.kind === "done") {
          const settled = payload.turn;
          if (typeof settled === "object" && settled !== null && "content" in settled) {
            active.content = String(settled.content);
          }
          active.runStatus = String(payload.status ?? "done");
          active.state = active.runStatus === "cancelled"
            ? "cancelled"
            : active.runStatus.includes("fail")
              ? "failed"
              : "done";
          active.activity = active.runStatus;
          streams.delete(targetRunId);
          if (snapshot?.session?.id === active.sessionId) {
            scheduleSettledRefresh(targetRunId, active.sessionId);
          }
        }
        renderVersion++;
        notifyVoice();
      },
      (message) => omen(message, false),
      async () => {
        if (destroyed) return { cursor: initialCursor, terminal: true };
        omen("The run stream lost history; refreshing its authoritative snapshot.", false);
        const expectedGeneration = liveTurns.find(
          (item) => item.runId === targetRunId
        )?.authorityGeneration;
        const projection = await getRunSnapshot(targetRunId);
        if (destroyed) return { cursor: projection.cursor, terminal: true };
        const index = liveTurns.findIndex((item) => item.runId === targetRunId);
        const active = liveTurns[index];
        let refreshed = active;
        if (active) {
          refreshed = replaceLiveTurnFromSnapshot(
            $state.snapshot(active),
            projection,
            expectedGeneration
          );
          liveTurns[index] = refreshed;
          if (snapshot?.session?.id === targetSessionId) {
            void load(targetSessionId);
          }
        }
        if (refreshed && turnIsTerminal(refreshed)) {
          streams.get(targetRunId)?.();
          streams.delete(targetRunId);
          if (snapshot?.session?.id === targetSessionId) {
            scheduleSettledRefresh(targetRunId, targetSessionId);
          }
        }
        renderVersion++;
        notifyVoice();
        return {
          cursor: refreshed?.cursor ?? projection.cursor,
          terminal: refreshed ? turnIsTerminal(refreshed) : projection.terminal
        };
      },
      {
        initialCursor,
        onHardClose: () => {
          if (destroyed) return;
          hardClosed = true;
          if (close === undefined || streams.get(targetRunId) === close) {
            streams.delete(targetRunId);
          }
          const active = liveTurns.find((item) => item.runId === targetRunId);
          if (active?.state === "streaming") {
            active.state = "stale";
            active.activity = "projection stale";
            active.authorityGeneration++;
            renderVersion++;
            notifyVoice();
          }
          void recoverHardClosedRun(targetRunId, targetSessionId);
        }
      }
    );
    if (!hardClosed) streams.set(targetRunId, close);
  }

  async function recoverHardClosedRun(runId: string, targetSessionId: string) {
    if (recoveredHardClosures.has(runId)) return;
    recoveredHardClosures.add(runId);
    const expectedGeneration = liveTurns.find(
      (item) => item.runId === runId
    )?.authorityGeneration;
    try {
      const projection = await getRunSnapshot(runId);
      if (destroyed) return;
      if (projection.session_id !== targetSessionId) {
        throw new Error("The authoritative run snapshot changed session identity.");
      }
      const index = liveTurns.findIndex((item) => item.runId === runId);
      const active = liveTurns[index];
      if (!active) return;
      const recovered = replaceLiveTurnFromSnapshot(
        $state.snapshot(active),
        projection,
        expectedGeneration
      );
      liveTurns[index] = recovered;
      renderVersion++;
      notifyVoice();
      if (turnIsTerminal(recovered)) {
        if (snapshot?.session?.id === targetSessionId) {
          scheduleSettledRefresh(runId, targetSessionId);
        }
      } else {
        attachStream(recovered, recovered.cursor);
      }
    } catch {
      if (!destroyed) {
        omen("The run projection remains stale; refresh the Bridge to retry.", true);
      }
    }
  }

  function recoverRefused(requestId: string, restore: boolean) {
    if (!selected || (restore && prompt)) return;
    const retained = work.refused.get(selected.id) ?? [];
    const offering = retained.find((item) => item.requestId === requestId);
    if (!offering) return;
    if (restore) { work.setDraft(selected.id, offering.text); notifyVoice(); }
    const remaining = retained.filter((item) => item.requestId !== requestId);
    if (remaining.length) work.refused.set(selected.id, remaining);
    else work.refused.delete(selected.id);
  }

  async function submit(retry = false, preparedText?: string) {
    if (!selected || choosing) return;
    if (!retry && (loading || hasUnsettledRun)) return;
    const targetSessionId = selected.id;
    const prior = work.pending.get(targetSessionId);
    if (prior?.sending || (prior && !retry) || (retry && !prior)) return;
    const text = prior?.text ?? preparedText ?? prompt.trim();
    if (!text) return;
    const requestId = prior?.requestId ?? crypto.randomUUID();
    work.pending.set(targetSessionId, {
      text, requestId, uncertain: prior?.uncertain ?? false, sending: true, error: ""
    });
    error = "";
    if (!retry && preparedText === undefined) work.setDraft(targetSessionId, "");
    notifyVoice();
    try {
      const accepted = await sendBridgeMessage(targetSessionId, text, requestId);
      work.pending.delete(targetSessionId);
      const revision = (work.settlements.get(targetSessionId) ?? 0) + 1;
      if (!destroyed) observedSettlements.set(targetSessionId, revision);
      work.settlements.set(targetSessionId, revision);
      if (destroyed) return;
      if (snapshot?.session?.id === targetSessionId) {
        snapshot.session.turns ??= [];
        const alreadyProjected = snapshot.session.turns.some(
          (turn) =>
            turn.role === accepted.turn.role &&
            turn.content === accepted.turn.content &&
            turn.created_at === accepted.turn.created_at
        );
        if (!alreadyProjected) snapshot.session.turns.push(accepted.turn);
      }
      let live = liveTurns.find((turn) => turn.runId === accepted.run_id);
      if (!live) {
        live = {
          sessionId: targetSessionId,
          runId: accepted.run_id,
          cursor: -1,
          authorityGeneration: 0,
          content: "",
          runStatus: "queued",
          activity: "queued",
          state: "streaming",
          fragments: [],
          patternId: accepted.pattern_id,
          patternRevision: accepted.pattern_revision,
          loomPath: accepted.loom_path,
          orbPath: accepted.orb_path,
          evidenceCapture: accepted.evidence_capture,
          occurrenceId: null,
          dispatchOccurrenceId: null,
          grantId: null,
          capabilityKey: null,
          transitionOccurrenceId: null,
          transitionRequestId: null,
          transitionPhase: null,
          delegatedJobId: null,
          delegatedRuntime: null,
          delegatedProfile: null,
          delegatedStatus: null
        };
        liveTurns.push(live);
      }
      renderVersion++;
      notifyVoice();
      attachStream(live);
      return true;
    } catch (cause) {
      const uncertain = prior?.uncertain || !(cause instanceof ApiError) || cause.status === undefined || cause.status >= 500 || cause.status === 408;
      const message = cause instanceof Error ? cause.message : "The offering was refused.";
      if (uncertain) {
        work.pending.set(targetSessionId, { text, requestId, uncertain: true, sending: false, error: message });
      } else {
        work.pending.delete(targetSessionId);
        if (!work.drafts.has(targetSessionId)) work.setDraft(targetSessionId, text);
        else work.refused.set(targetSessionId, [
          ...work.refused.get(targetSessionId) ?? [], { requestId, text, error: message }
        ]);
        if (!destroyed && snapshot?.session?.id === targetSessionId) error = message;
      }
    } finally {
      if (!destroyed) notifyVoice();
    }
  }

  function applyRunProjection(
    runId: string,
    projection: Awaited<ReturnType<typeof getRunSnapshot>>
  ): LiveTurn {
    const index = liveTurns.findIndex((item) => item.runId === runId);
    const active = liveTurns[index];
    if (!active || projection.session_id !== active.sessionId) {
      throw new Error("The authoritative run snapshot changed identity.");
    }
    const updated = replaceLiveTurnFromSnapshot($state.snapshot(active), projection);
    liveTurns[index] = updated;
    if (turnIsTerminal(updated)) {
      streams.get(runId)?.();
      streams.delete(runId);
      clearRefreshTimer(runId);
    }
    renderVersion++;
    notifyVoice();
    return updated;
  }

  async function cancelRun(turn: LiveTurn) {
    if (turn.state === "done" || turn.state === "failed" || turn.state === "cancelled" || cancellingRuns.has(turn.runId)) {
      return;
    }
    cancellingRuns.add(turn.runId);
    try {
      const projection = await cancelBridgeRun(turn.runId);
      if (destroyed) return;
      const updated = applyRunProjection(turn.runId, projection);
      if (turnIsTerminal(updated)) {
        await reconcileConsentAuthority(turn.sessionId);
      }
    } catch (cause) {
      if (destroyed) return;
      try {
        const projection = await getRunSnapshot(turn.runId);
        if (destroyed) return;
        const updated = applyRunProjection(turn.runId, projection);
        if (turnIsTerminal(updated)) {
          await reconcileConsentAuthority(turn.sessionId);
        }
        if (!projection.terminal) throw cause;
      } catch (recheckCause) {
        omen(recheckCause instanceof Error ? recheckCause.message : "The cancellation outcome is unknown.");
      }
    } finally {
      if (!destroyed) cancellingRuns.delete(turn.runId);
    }
  }

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendComposer();
    }
  }

  function beginConsentDecision() {
    return consentAuthorityVersion;
  }

  function consentDecided(
    consent: ConsentCardModel,
    pending: number,
    authorityVersion: number
  ) {
    const targetSessionId = work.consentDecisions.get(consent.id)?.sessionId;
    if (targetSessionId) {
      const revision = (work.settlements.get(targetSessionId) ?? 0) + 1;
      if (!destroyed) observedSettlements.set(targetSessionId, revision);
      work.settlements.set(targetSessionId, revision);
    }
    if (destroyed || !snapshot || snapshot.session?.id !== targetSessionId) {
      window.dispatchEvent(new CustomEvent("altar:attention"));
      return;
    }
    if (authorityVersion !== consentAuthorityVersion) {
      refreshConsentAuthority();
      return;
    }
    consentAuthorityVersion++;
    const index = snapshot.pending_consents.findIndex((item) => item.id === consent.id);
    if (index >= 0) snapshot.pending_consents[index] = consent;
    snapshot.pending_count = pending;
    const selectedPending = snapshot.pending_consents.filter((card) => card.state === "pending_consent").length;
    if (snapshot.session) {
      snapshot.session.pending_count = selectedPending;
      const summary = snapshot.sessions.find((session) => session.id === snapshot?.session?.id);
      if (summary) summary.pending_count = selectedPending;
    }
    work.consentDecisions.delete(consent.id);
    window.dispatchEvent(new CustomEvent("altar:attention", { detail: pending }));
  }

  async function reconcileConsentAuthority(targetSessionId: string) {
    if (destroyed) return;
    if (snapshot?.session?.id === targetSessionId) {
      // Cancellation revokes this session's visible consent authority immediately.
      // The refetch may fail, but stale action cards must never survive it.
      consentAuthorityVersion++;
      snapshot.pending_consents = [];
      if (snapshot.session) snapshot.session.pending_count = 0;
      const summary = snapshot.sessions.find((session) => session.id === targetSessionId);
      if (summary) summary.pending_count = 0;
      window.dispatchEvent(new CustomEvent("altar:attention"));
      await load(targetSessionId);
      return;
    }
    window.dispatchEvent(new CustomEvent("altar:attention"));
  }

  function refreshConsentAuthority() {
    if (!destroyed && selected) void load(selected.id);
  }

  function trackScroll() {
    if (!thread) return;
    stickToTail = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 72;
  }

  function showLatest() {
    if (!thread) return;
    releasedRunFocus = runFocusKey;
    stickToTail = true;
    const turns = thread.querySelectorAll<HTMLElement>("article.turn");
    (turns.item(turns.length - 1) ?? thread).focus({ preventScroll: true });
    thread.scrollTop = thread.scrollHeight;
  }
</script>

<svelte:head>{#if !embedded}<title>Bridge — LychD</title>{/if}</svelte:head>
<div class="instrument-deck instrument-deck--bridge" class:instrument-deck--welcome={firstVisit && pins.length === 0} class:bridge-embedded={embedded} class:bridge-shell-history={shellHistory} class:bridge-with-inspector={showInspector}>
  {#if !shellHistory && (!firstVisit || pins.length > 0)}
    <aside class="bridge-rail" aria-label="Conversation history">
      <ConversationList {history} variant="disclosure" bind:open={() => historyOpen, (value) => { historyOpen = value; }} />
    </aside>
  {/if}

  <div class="bridge-thread">
    <ConversationHeading
      heading={firstVisit ? "Bridge — conversations" : "Bridge"}
      headingHidden={firstVisit || !!selected}
      title={selected?.title}
      pending={selected ? selectedPendingCount : 0}
      pinned={selected ? pins.includes(selected.id) : undefined}
      onpin={() => { if (selected) togglePin(selected.id); }}
      browseHref={embedded ? undefined : resolve("/seances")}
    >
      {#snippet tools()}
        <Disclosure variant="popover" summaryLabel="Conversation tools" summaryAttach={captureNamingTools}>
          {#snippet summary()}Tools{/snippet}
          <div class="bridge-tools" role="group" aria-label="Conversation tools">
            <Button size="sm" onclick={openNaming}>Naming ceremony</Button>
            {#if selected}
              <Disclosure>
                {#snippet summary()}Séance details{#if selectedPendingCount}<StatusPill tone="attention">{selectedPendingCount} awaiting consent</StatusPill>{/if}{/snippet}
                <KeyValueList>
                  <dt>identity</dt><dd class="glyph">{selected.id}</dd>
                  <dt>title</dt><dd>{selected.title}</dd>
                  <dt>turns</dt><dd>{(selected.turns?.length ?? 0) + selectedLiveTurns.length}</dd>
                  <dt>awaiting consent</dt><dd>{selectedPendingCount}</dd>
                </KeyValueList>
              </Disclosure>
            {/if}
            <Disclosure>
              {#snippet summary()}Public sources{/snippet}
              <nav class="atlas-links" aria-label="Bridge work"><a href="/bridge?investigation=new">Investigate public source</a><a href="/bridge?notes=manage">Manage public notes</a><a href="/bridge?notes=recall">Recall public sources</a></nav>
            </Disclosure>
            {#if selected}
              <Disclosure>
                {#snippet summary()}Project links{/snippet}
                <AtlasLinks kind="session" targetId={selected.id} suggestedProject={hintedProject} />
              </Disclosure>
            {/if}
          </div>
        </Disclosure>
      {/snippet}
    </ConversationHeading>
    {#if hintedProject}
      <nav class="atlas-links" aria-label="Originating project">
        <a href={atlasHref(hintedProject.id)}>← {hintedProject.title}</a>
        <span>Project context is not sent automatically.</span>
      </nav>
    {:else if projectError}<div class="thread-notice"><FaultNotice severity="status" message={projectError} /></div>{/if}
    {#if focusConsent !== undefined && !loading && !focusedConsent}
      <div class="thread-notice"><FaultNotice severity="status" message="The requested consent is unavailable in this conversation at this read." /></div>
    {/if}
    {#if consentReturnHref}
      <nav class="atlas-links" aria-label="Historical consent origin">
        <a href={resolve(consentReturnHref)}>Return to Orb event →</a>
      </nav>
    {/if}
    {#if focusRun && !loading && selected && !(selected.turns ?? []).some((turn) => turn.role === "agent" && turn.run_id === focusRun) && !selectedLiveTurns.some((turn) => turn.runId === focusRun)}
      <div class="thread-notice"><FaultNotice severity="status" message="The requested Run is not available in this conversation." /></div>
    {/if}
    {#if namingStarted}
      <div hidden={!namingOpen}>
        <NamingCeremony bind:this={namingCeremony} onclose={closeNaming} onask={askForName} />
      </div>
    {/if}
    <!-- This named overflow region needs native keyboard scrolling. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="thread-scroll"
      {@attach captureThread}
      onscroll={trackScroll}
      aria-label="Conversation"
      role="region"
      tabindex="0"
    >
      {#if readError && !snapshot}
        <FaultNotice message={readError} onretry={retryRead} retrying={loading} retryLabel="Retry read" retryingLabel="Reading…" />
      {:else if loading && !selected}
        <LoadingState label="Loading conversation…" />
      {:else if error && !selected}
        <FaultNotice message={error} onretry={() => void load(sessionId)} retryLabel="Retry conversation" />
      {:else if choosing}
        <EmptyState title={attentionOnly ? "Conversations awaiting consent" : "Choose a conversation"}>
          <p>{attentionOnly ? "Select a marked conversation to review its pending requests." : "Select a conversation from the list or open a new séance."}</p>
          {#if attentionOnly && !snapshot?.sessions.some((session) => (session.pending_count ?? 0) > 0)}
            <p>{snapshot?.pending_count ? snapshot.sessions_next_cursor ? "Load more conversations to find older pending requests." : "Pending requests have no available Bridge conversation." : "No conversation is awaiting consent."}</p>
          {/if}
        </EmptyState>
      {:else if firstVisit}
        <AltarWelcome onbegin={createSession} onnaming={openNaming} pending={creatingSession} />
      {:else if !selected}
        <EmptyState glyph="⬡" title="The Bridge awaits">
          <p>Open a séance to begin a local communion.</p>
        </EmptyState>
      {:else}
        {#if !(selected.turns?.length || selectedLiveTurns.length || snapshot?.pending_consents.length)}
          <EmptyState glyph="✦" title="What shall we explore?">
            <p>Offer a question, an idea, or a piece of work.</p>
          </EmptyState>
        {/if}
        {#each selected.turns ?? [] as turn (turn.run_id ? JSON.stringify([selected.id, turn.role, turn.run_id]) : turn)}
          <article
            class:turn--user={turn.role === "user"}
            class:turn--agent={turn.role === "agent"}
            class="turn"
            data-run-id={turn.role === "agent" ? turn.run_id : undefined}
            tabindex="-1"
            data-state={turn.state === "failed" ? "failed" : "done"}
          >
            <TurnHeader role={turn.role === "agent" ? "agent" : "user"} name={turn.role === "agent" ? "LychD" : "You"} />
            {#if turn.role === "agent" && turn.run_id}
              <CircleRun runId={turn.run_id} />
            {/if}
            <div class="turn__body">{turn.content}</div>
            {#if turn.role === "agent" && (turn.fragments?.length ?? 0) > 0}
              <div class="turn__extras">
                {#each turn.fragments ?? [] as fragment (fragment)}<GenUI descriptor={fragment} />{/each}
              </div>
            {/if}
          </article>
        {/each}
        {#each selectedLiveTurns as turn (turn.runId)}
          <article class="turn turn--agent" data-state={turn.state} data-run-id={turn.runId} tabindex="-1">
            <TurnHeader role="agent" name="LychD" />
            <CircleRun runId={turn.runId} {turn} cancelling={cancellingRuns.has(turn.runId)} oncancel={() => void cancelRun(turn)} />
            <div class="turn__body">{turn.content || (turnIsTerminal(turn) ? "No reply text was retained for this Run." : "")}</div>
            {#if turn.runStatus === "failed" && turn.content}
              <p class="turn__fault" role="status">This Run failed. The text shown here is not a completed answer.</p>
            {/if}
            {#if turn.runStatus === "awaiting_hardware" || turn.transitionRequestId}
              <div class="body-crossing">
                <span class="body-crossing__title">Capability transition</span>
                <span>
                  {turn.capabilityKey ?? "capability"} ·
                  {operatorState(turn.transitionPhase ?? turn.runStatus)}
                </span>
                {#if turn.transitionOccurrenceId}
                  <span title={turn.transitionOccurrenceId}>
                    transition occurrence {turn.transitionOccurrenceId.slice(0, 12)}
                  </span>
                {/if}
              </div>
            {/if}
            {#if turn.runStatus === "awaiting_delegate" || turn.delegatedJobId}
              <div class="body-crossing delegate-crossing" data-state={turn.delegatedStatus ?? turn.runStatus}>
                <span class="body-crossing__title">
                  <DelegateMark /> Delegated labor
                </span>
                <span>
                  {turn.delegatedRuntime ?? "runtime"} ·
                  {turn.delegatedProfile ?? "contained profile"}
                </span>
                <span>
                  {turn.delegatedJobId ? `AgentJob ${turn.delegatedJobId.slice(0, 12)}` : "AgentJob pending"}
                  · {delegationStatusLabel(turn.delegatedStatus ?? turn.runStatus)}
                </span>
              </div>
            {/if}
            <div class="turn__extras">
              {#each turn.fragments as fragment (fragment)}<GenUI descriptor={fragment} />{/each}
            </div>
          </article>
        {/each}
        {#each snapshot?.pending_consents ?? [] as consent (consent.id)}
          <ConsentCard
            {consent}
            sessionId={selected.id}
            decisions={work.consentDecisions}
            onauthority={beginConsentDecision}
            ondecided={consentDecided}
            onrefresh={refreshConsentAuthority}
          />
        {/each}
      {/if}
    </div>

    {#if selected && (!stickToTail || readingFocusedRun)}
      <div class="latest-turn"><button type="button" onclick={showLatest}>Latest turn ↓</button></div>
    {/if}

    {#if selected}
      {#each refusedOfferings as refused (refused.requestId)}
        <section class="offering-recovery" aria-label="Refused offering">
          <strong>Offering refused</strong>
          <p class="offering-recovery__text">{refused.text}</p>
          <p>{refused.error}</p>
          <div class="offering-recovery__actions">
            <Button size="sm" disabled={!!prompt} onclick={() => recoverRefused(refused.requestId, true)}>Restore refused offering</Button>
            <Button size="sm" variant="ghost" onclick={() => recoverRefused(refused.requestId, false)}>Dismiss refused offering</Button>
          </div>
          {#if prompt}<p>Your current draft is kept. Send or clear it before restoring this text.</p>{/if}
        </section>
      {/each}
      {#if pendingOffering}
        <section class="offering-recovery" aria-label="Unresolved offering" aria-live="polite">
          <strong>{pendingOffering.sending ? "Sending offering…" : "Offering outcome unknown"}</strong>
          <p class="offering-recovery__text">{pendingOffering.text}</p>
          {#if pendingOffering.error}<p>{pendingOffering.error}</p>{/if}
          <p>{pendingOffering.sending ? "You can continue browsing while this request settles." : "Retry the original offering to recover its result before sending a new one."}</p>
          <Button size="sm" disabled={pendingOffering.sending} onclick={() => void submit(true)}>Retry original offering</Button>
        </section>
      {/if}
      <div class="composer-area" role="region" aria-label="Bridge composer">
        <div class="composer-shell">
          {#if composerMode === "work"}
            <div class="command-help">
              <p>English commands · {destination}</p>
              {#if commandTarget}
                <details><summary>Command examples</summary>
                  <ul>{#each commandTarget.commands as command (command)}<li><code>{command}</code></li>{/each}</ul>
                </details>
              {:else}<p>Open Canvas, Loom or Orb to choose a work target.</p>{/if}
              <p>Canvas commands create a preview. Review and Apply on the board.</p>
            </div>
          {/if}
          <label class="composer-label" for="bridge-message">Your next offering</label>
          {#if snapshot?.composer?.guidance}
            <p id="composer-instructions" class="composer-instructions">{snapshot.composer.guidance}</p>
          {/if}
          <div class="composer">
            <textarea
              id="bridge-message"
              bind:value={() => prompt, setPrompt}
              {@attach focusCreatedComposer}
              required
              rows="2"
              placeholder="What would you like to explore?"
              onkeydown={keydown}
              oncompositionstart={() => changeComposition(true)}
              oncompositionend={() => changeComposition(false)}
              aria-label="Message"
              aria-describedby={snapshot?.composer?.guidance ? "composer-instructions composer-guidance composer-shortcuts" : "composer-guidance composer-shortcuts"}
            ></textarea>
          </div>
          <div class="composer-actions" class:composer-actions--work={composerMode === "work"}>
            <div class="composer-voice">
              {#key selected.id}
                <BridgeVoiceInput bind:this={voice} snapshot={voiceSnapshot} target={commandTarget}
                  readSnapshot={readVoiceSnapshot} onadopt={adoptVoice} onsubmit={submitVoice}
                  isTargetCurrent={(target) => workCommands?.isCurrent(target) === true}>
                  {#snippet feedback(context)}<DictationFeedback {...context} />{/snippet}
                </BridgeVoiceInput>
              {/key}
            </div>
            <div class="composer-trail">
              <label class="visually-hidden" for="bridge-destination">Send to</label>
              <select id="bridge-destination" value={composerMode} onchange={changeMode}>
                <option value="chat">Conversation</option>
                <option value="work">{destination}</option>
              </select>
              <button
                class="composer-send"
                disabled={voiceSnapshot.busy || composing || !prompt.trim()}
                type="button"
                aria-label={composerMode === "work" ? "Send command" : "Offer"}
                title={composerMode === "work" ? "Send command" : "Offer"}
                onclick={sendComposer}
              ><span aria-hidden="true">↑</span></button>
            </div>
          </div>
        </div>
        {#if commandPending}<p class="command-result" role="status">Preparing command…</p>{/if}
        {#if commandResult}<p class="command-result" role="status">{commandResult.status}: {commandResult.summary}</p>{/if}
        <div class="composer-footer">
          <p id="composer-shortcuts">Enter to {composerMode === "work" ? "send command" : "offer"} · Shift + Enter for a new line</p>
          <p id="composer-guidance" class:visually-hidden={!loading && !pendingOffering && !hasUnsettledRun} role="status">{loading ? "Refreshing this conversation before another offering." : pendingOffering ? "Resolve the original offering first. This later draft is kept and is not queued." : hasUnsettledRun ? "Wait for this Run to settle before offering again. You can keep writing; this draft is not queued." : "Draft stays in this open tab."}</p>
        </div>
        {#if error}<FaultNotice message={error} />{/if}
      </div>
    {/if}
  </div>

  {#if showInspector && inspectedRunId}
    <CircleInspector runId={inspectedRunId} turn={inspectedTurn} pending={inspectedPending} />
  {/if}
</div>

<style>
  /* Thread flow and turn grammar. Instrument-specific sizing follows below. */
  .bridge-rail { display: flex; flex-direction: column; gap: 8px; }
  .bridge-thread { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .thread-scroll { display: flex; flex-direction: column; flex: 1; overflow-y: auto; }
  .turn--user { align-self: flex-end; }
  .turn--user .turn__body { color: var(--color-text-strong); }
  .turn--agent { align-self: flex-start; width: 100%; }
  .turn--agent .turn__body { transition: border-color var(--duration-rise) var(--ease-settle); }
  .turn__extras:empty { display: none; }
  /* The streaming caret blinks only while a turn is streaming. */
  .turn--agent[data-state="streaming"] .turn__body::after {
    content: "";
    display: inline-block;
    width: 8px;
    height: 15px;
    margin-left: 2px;
    vertical-align: text-bottom;
    background: var(--color-status-active);
    animation: var(--animate-caret-blink);
  }

  /* Body crossings: capability transitions and delegated work inside an agent turn. */
  .body-crossing {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.65rem;
    align-items: center;
    margin-top: 0.45rem;
    padding: 0.65rem 0.75rem;
    border: 1px solid color-mix(in srgb, var(--color-status-ready) 40%, var(--color-border-subtle));
    border-radius: var(--radius-block);
    background: color-mix(in srgb, var(--color-status-ready) 6%, var(--color-surface-panel));
    color: var(--color-status-ready);
    font-size: var(--text-xs);
  }
  .body-crossing__title { font-family: var(--font-body); font-variant: normal; letter-spacing: normal; }
  .delegate-crossing {
    border-color: color-mix(in srgb, var(--color-interactive) 45%, var(--color-border-subtle));
    border-left-width: 3px;
    background: var(--color-surface-panel);
  }
  .delegate-crossing[data-state="running"] { color: var(--color-status-active); }
  .delegate-crossing:is([data-state="failed"], [data-state="cancelled"], [data-state="timed_out"], [data-state="lost"]) { color: var(--color-status-fault); }

  .composer { gap: 10px; align-items: flex-end; transition: border-color var(--duration-drift), box-shadow var(--duration-drift); }
  .composer textarea { flex: 1; border: none; outline: none; color: var(--color-text-strong); font-family: var(--font-body); }
  .composer textarea::placeholder { color: var(--color-text-muted); }
  @media (prefers-reduced-motion: reduce) { .turn--agent[data-state="streaming"] .turn__body::after { animation: none; } }
  @media (max-width: 48rem) { .body-crossing { grid-template-columns: 1fr; } }
  @media (forced-colors: active) { .body-crossing { border-color: CanvasText; } }

  .instrument-deck--bridge { display: grid; grid-template-columns: 17rem minmax(0, 1fr); gap: 0; padding: 0; min-height: 0; height: 100%; overflow: hidden; background: var(--color-surface-page); }
  .instrument-deck--welcome { grid-template-columns: minmax(0, 1fr); }
  /* In the Altar shell the sidebar owns history; the optional third column is the Circle inspector. */
  .bridge-shell-history { grid-template-columns: minmax(0, 1fr); }
  .bridge-with-inspector { grid-template-columns: 17rem minmax(0, 1fr) 20rem; }
  .bridge-shell-history.bridge-with-inspector { grid-template-columns: minmax(0, 1fr) 20rem; }
  .bridge-rail { width: auto; min-width: 0; padding: 1.25rem .85rem; border-right: 1px solid var(--color-border-subtle); overflow-y: auto; background: var(--color-surface-panel); }
  /* Native details keeps history reachable without making it the dock's first reading task. */
  .bridge-thread { min-height: 0; overflow: hidden; }
  .bridge-tools { display: flex; flex-direction: column; align-items: stretch; gap: .25rem; min-width: 16rem; font-size: var(--text-sm); }
  .thread-notice { padding: .5rem clamp(1rem, 3vw, 2rem); }
  .thread-scroll { min-height: 4rem; padding: 1.5rem max(1rem, calc((100% - 48rem) / 2)); gap: 1.75rem; scrollbar-gutter: stable; }
  .thread-scroll:focus-visible { outline: 1px solid var(--color-interactive); outline-offset: -3px; }
  .turn { max-width: 100%; overflow-wrap: anywhere; }
  .turn--user { max-width: min(42rem, 92%); }
  .turn__body { white-space: pre-wrap; font-size: 1rem; line-height: 1.75; box-shadow: none; }
  .turn--user .turn__body { padding: .85rem 1rem; background: var(--color-surface-raised); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-panel); }
  .turn--agent .turn__body { padding: .25rem 0; color: var(--color-text-strong); background: transparent; border: 0; border-radius: 0; }
  .turn--agent[data-state="stale"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-border-control); }
  .turn--agent[data-state="failed"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-status-fault); }
  .turn--agent[data-state="cancelled"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-text-muted); }
  .latest-turn { display: flex; justify-content: center; padding: .25rem 1rem .5rem; }
  .latest-turn button { min-height: 2.75rem; padding: .4rem 1rem; border: 1px solid var(--color-border-control); border-radius: var(--radius-glyph); color: var(--color-interactive); background: var(--color-surface-panel); cursor: pointer; }
  .composer-area { flex: 0 1 auto; min-height: 0; max-height: min(36rem, 65dvh); overflow-y: auto; overscroll-behavior: contain; padding: .8rem clamp(1rem, 3vw, 2rem) 1rem; border-top: 1px solid var(--color-border-subtle); }
  .composer-area:focus-visible { outline: 2px solid var(--color-interactive); outline-offset: -2px; }
  .composer-shell { display: flex; flex-direction: column; max-width: 52rem; margin-inline: auto; padding: .85rem 1rem .6rem; border: 1px solid var(--color-border-control); border-radius: 1.25rem; background: var(--color-surface-panel); }
  .composer-shell:focus-within { border-color: var(--color-interactive); }
  .command-help, .command-result { font-size: var(--text-sm); line-height: 1.6; overflow-wrap: anywhere; }
  .command-help { padding: 0 0 .75rem; margin: 0 0 .75rem; border-bottom: 1px solid var(--color-border-subtle); }
  .command-help p + p { margin-top: .35rem; }
  .command-help summary { min-height: 2.75rem; align-content: center; cursor: pointer; }
  .command-help ul { padding-left: 1.4rem; }
  .command-help code { white-space: pre-wrap; overflow-wrap: anywhere; }
  .command-result { margin: .65rem 0 0; color: var(--color-text-body); }
  .composer-label { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
  .composer-instructions { margin: .25rem 0 .75rem; color: var(--color-text-body); font-size: var(--text-sm); line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
  .composer { display: flex; margin: 0; padding: 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
  .composer:focus-within { box-shadow: none; border: 0; }
  .composer textarea { display: block; width: 100%; min-width: 0; min-height: 3rem; max-height: 16rem; padding: 0; resize: vertical; font-size: 1rem; line-height: 1.5; background: transparent; }
  .composer-actions { order: 2; position: relative; --voice-action-reserve: 15rem; padding-top: .35rem; }
  .composer-actions--work { --voice-action-reserve: 18rem; }
  /* Destination and send sit at the row's end; the voice toolbar reserves their width. */
  .composer-trail { position: absolute; inset-block-start: .35rem; inset-inline-end: 0; display: flex; align-items: center; gap: .6rem; max-width: var(--voice-action-reserve); }
  #bridge-destination { min-width: 0; max-width: 11rem; min-height: 2.25rem; margin: 0; padding: .25rem 1.75rem .25rem .75rem; border: 1px solid var(--color-border-subtle); border-radius: 999px; background-color: var(--color-surface-raised); color: var(--color-text-strong); font: 500 var(--text-xs)/1.2 var(--font-body); }
  .composer-send { display: grid; place-items: center; flex: 0 0 auto; width: 2.75rem; height: 2.75rem; padding: 0; border: 1px solid var(--color-action); border-radius: 50%; background: var(--color-action); color: var(--color-on-action); font: 600 1.1rem/1 var(--font-body); cursor: pointer; }
  .composer-send:hover:not(:disabled) { background: var(--color-action-hover); border-color: var(--color-action-hover); }
  .composer-send:disabled { opacity: .35; cursor: default; }
  .composer-send:focus-visible, #bridge-destination:focus-visible { outline: 2px solid var(--color-interactive); outline-offset: 2px; }
  .composer-voice { min-width: 0; }
  .composer-footer { display: flex; max-width: 52rem; justify-content: space-between; gap: .3rem 1.5rem; flex-wrap: wrap; margin: .35rem auto 0; color: var(--color-text-muted); font-size: var(--text-xs); line-height: 1.6; }
  .composer-footer p { max-width: 38rem; }
  .offering-recovery { flex: 0 1 auto; min-height: 4rem; margin: .75rem 1rem; padding: .8rem 1rem; border: 0; border-left: 2px solid var(--color-interactive); border-radius: 0; background: var(--color-surface-panel); max-height: min(22rem, 45dvh); overflow-y: auto; overscroll-behavior: contain; }
  .offering-recovery p { margin: .5rem 0; color: var(--color-text-body); line-height: 1.6; }
  .offering-recovery .offering-recovery__text { color: var(--color-text-strong); white-space: pre-wrap; max-height: 12rem; overflow: auto; overflow-wrap: anywhere; }
  .offering-recovery__actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .5rem; }
  .atlas-links { display: flex; flex-wrap: wrap; gap: .35rem 1rem; align-items: center; padding: .5rem clamp(1rem, 3vw, 2rem); color: var(--color-text-body); font-size: var(--text-sm); }
  .atlas-links a { color: var(--color-interactive); min-height: 2.75rem; display: inline-flex; align-items: center; }
  .turn:focus-visible { outline: 2px solid var(--color-interactive); outline-offset: 3px; }
  .bridge-embedded { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); height: 100%; overflow: hidden; }
  .bridge-embedded.instrument-deck--welcome { grid-template-rows: minmax(0, 1fr); }
  .bridge-embedded .bridge-rail { padding: 0 .95rem; border: 0; max-height: min(18rem, 35dvh); overflow: auto; background: transparent; }
  .bridge-embedded .atlas-links { padding: .25rem .95rem; gap: .25rem .75rem; }
  .bridge-embedded .thread-scroll { padding: 1rem .95rem; gap: 1.5rem; flex: 1; min-height: 4rem; }
  .bridge-embedded .composer-area { padding: .4rem .65rem .45rem; }
  .bridge-embedded .composer-shell { padding: .3rem .6rem .4rem; }
  .bridge-embedded .composer textarea { min-height: 3rem; }
  .bridge-embedded .composer-voice { --voice-label-display: none; }
  .bridge-embedded .composer-actions { --voice-action-reserve: 13rem; }
  .bridge-embedded .turn__body { font-size: var(--text-base); line-height: 1.7; }
  @media (max-width: 64rem) {
    .bridge-with-inspector { grid-template-columns: 17rem minmax(0, 1fr); }
    .bridge-shell-history.bridge-with-inspector { grid-template-columns: minmax(0, 1fr); }
    .bridge-with-inspector > :global(.circle-inspector) { display: none; }
  }
  @media (max-width: 48rem) {
    .instrument-deck--bridge, .bridge-with-inspector, .bridge-shell-history.bridge-with-inspector { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
    .bridge-rail { display: block; max-height: 35dvh; padding: 0 .95rem; border-right: 0; border-bottom: 1px solid var(--color-border-subtle); overflow: auto; }
    .thread-scroll { padding: 1rem .95rem; }
    .composer-area { padding: .4rem .65rem .45rem; }
    .composer-shell { padding: .3rem .6rem .4rem; }
    .composer textarea { min-height: 3rem; }
    .composer-voice { --voice-label-display: none; }
    .composer-actions { --voice-action-reserve: 13rem; }
    .composer-footer { gap: .2rem .5rem; }
    .turn--user { max-width: 95%; }
  }
</style>
