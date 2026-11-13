<script lang="ts">
  import { beforeNavigate, goto, replaceState } from "$app/navigation";
  import { page } from "$app/state";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { navigationId, orbReturnHref } from "$lib/navigation/instruments";
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
  import DelegateMark from "$lib/components/shared/DelegateMark.svelte";
  import GenUI from "$lib/pages/bridge/components/GenUI.svelte";
  import AtlasLinks from "$lib/components/atlas/AtlasLinks.svelte";
  import AltarWelcome from "$lib/pages/bridge/components/AltarWelcome.svelte";
  import NamingCeremony from "$lib/pages/bridge/components/NamingCeremony.svelte";
  import { atlasHref } from "$lib/atlas/navigation";
  import { bridgeWorkspaceKey, createBridgeWorkspace, type BridgeWorkspace } from "$lib/pages/bridge/state/workspace.svelte";
  import { delegationStatusLabel } from "$lib/delegation/presentation";
  import { bridgePinsLimit, bridgePinsStorageKey, parsePinnedConversations, togglePinnedConversation } from "$lib/pages/bridge/state/pins";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
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
      if (!destroyed) (document.getElementById(`bridge-pin-${id}`) ?? document.querySelector<HTMLButtonElement>(".new-seance"))?.focus({ preventScroll: true });
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
{#snippet conversationEntry(id: string)}
  {@const session = sessionMetadata.get(id)}
  <div class="conversation-row">
    <a class:current={selected?.id === id} class="seance" href={bridgeHref(id)} onclick={(event) => selectConversation(event, id)} aria-current={selected?.id === id ? "page" : undefined}>
      <span class="t">{session?.title ?? `Conversation · ${id}`}</span>
      {#if session?.pending_count}<span class="chip">{session.pending_count} awaiting consent</span>{/if}
      {#if work.pending.has(id)}<span class="chip">Offering unresolved</span>{:else if work.refused.has(id)}<span class="chip">Refused offering</span>{:else if work.drafts.has(id)}<span class="chip">Draft</span>{/if}
      {#if !session}<span class="m">Details not loaded</span>{/if}
    </a>
    <button id={`bridge-pin-${id}`} class="pin-conversation" type="button" aria-label={`${pins.includes(id) ? "Unpin" : "Pin"} conversation: ${session?.title ?? id}`} aria-pressed={pins.includes(id)} onclick={() => togglePin(id)} title={pins.includes(id) ? "Unpin conversation" : "Pin conversation"}><AltarIcon name="pin" size={16} /></button>
  </div>
{/snippet}
<div class="instrument-deck instrument-deck--bridge" class:instrument-deck--welcome={firstVisit && pins.length === 0} class:bridge-embedded={embedded}>
  {#if !firstVisit || pins.length > 0}
  <aside class="bridge-rail" aria-label="Conversation history">
    <details class="conversation-list" open={!embedded && !compactHistory}>
      <summary>Conversations</summary>
    <button class="rune-btn new-seance" type="button" disabled={creatingSession} aria-busy={creatingSession} onclick={createSession}>✦ &nbsp;{creatingSession ? "Opening…" : "New Séance"}</button>
    <nav aria-label="Conversations">
    <h2 class="archive-label">Pinned</h2>
    {#each visiblePins as id (id)}{@render conversationEntry(id)}{:else}<p class="rail-empty">No pinned conversations.</p>{/each}
    {#if selected && !pins.includes(selected.id) && !snapshot?.sessions.some((session) => session.id === selected.id)}
      <h2 class="archive-label">Selected conversation</h2>
      {@render conversationEntry(selected.id)}
    {/if}
    <h2 class="archive-label">Recent conversations</h2>
    <p class="archive-order">Newest created first</p>
    {#if snapshot?.sessions.length}
      {#each recentSessions as session (session.id)}{@render conversationEntry(session.id)}{/each}
    {:else if !loading && !error}
      <p class="glyph rail-empty">No séance yet — open one to speak.</p>
    {/if}
    {#if snapshot?.sessions_next_cursor}
      <button class="rune-btn" type="button" disabled={loading || sessionsLoading} aria-busy={sessionsLoading} onclick={loadMoreSessions}>
        {sessionsLoading ? "Loading conversations…" : "Load more conversations"}
      </button>
    {/if}
    {#if sessionsError}<p class="turn__fault" role="status">{sessionsError}</p>{/if}
    {#if pinNotice}<p class="rail-empty" role="status">{pinNotice}</p>{/if}
    </nav>
    </details>
  </aside>
  {/if}

  <div class="bridge-thread">
    <header class="bridge-heading">
      <div>
        {#if !firstVisit}
          <h1>Bridge</h1>
          {#if selected}<p class="conversation-title">{selected.title}</p>{/if}
        {:else}
          <h1 class="visually-hidden">Bridge — conversations</h1>
        {/if}
        {#if selected && selectedPendingCount}
          <p class="conversation-attention">{selectedPendingCount} awaiting consent</p>
        {/if}
      </div>
      <details class="conversation-tools">
        <summary aria-label="Conversation tools" {@attach captureNamingTools}>Tools</summary>
        <div class="bridge-tools" role="group" aria-label="Conversation tools">
          <button class="rune-btn" type="button" onclick={openNaming}>Naming ceremony</button>
          {#if selected}
            <details class="seance-details">
              <summary>Séance details{#if selectedPendingCount}<span class="chip">{selectedPendingCount} awaiting consent</span>{/if}</summary>
              <dl class="kv">
                <dt>identity</dt><dd class="glyph">{selected.id}</dd>
                <dt>title</dt><dd>{selected.title}</dd>
                <dt>turns</dt><dd>{(selected.turns?.length ?? 0) + selectedLiveTurns.length}</dd>
                <dt>awaiting consent</dt><dd>{selectedPendingCount}</dd>
              </dl>
            </details>
          {/if}
          <details class="public-sources">
            <summary>Public sources</summary>
            <nav class="atlas-links" aria-label="Bridge work"><a href="/bridge?investigation=new">Investigate public source</a><a href="/bridge?notes=manage">Manage public notes</a><a href="/bridge?notes=recall">Recall public sources</a></nav>
          </details>
          {#if selected}
            <details class="project-details">
              <summary>Project links</summary>
              <AtlasLinks kind="session" targetId={selected.id} suggestedProject={hintedProject} />
            </details>
          {/if}
        </div>
      </details>
    </header>
    {#if hintedProject}
      <nav class="atlas-links" aria-label="Originating project">
        <a href={atlasHref(hintedProject.id)}>← {hintedProject.title}</a>
        <span>Project context is not sent automatically.</span>
      </nav>
    {:else if projectError}<p class="turn__fault" role="status">{projectError}</p>{/if}
    {#if focusConsent !== undefined && !loading && !focusedConsent}
      <p class="turn__fault" role="status">The requested consent is unavailable in this conversation at this read.</p>
    {/if}
    {#if consentReturnHref}
      <nav class="atlas-links" aria-label="Historical consent origin">
        <a href={resolve(consentReturnHref)}>Return to Orb event →</a>
      </nav>
    {/if}
    {#if focusRun && !loading && selected && !(selected.turns ?? []).some((turn) => turn.role === "agent" && turn.run_id === focusRun) && !selectedLiveTurns.some((turn) => turn.runId === focusRun)}
      <p class="turn__fault" role="status">The requested Run is not available in this conversation.</p>
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
        <div class="turn__fault" role="alert">{readError}</div>
        <button class="rune-btn" type="button" disabled={loading} aria-busy={loading} onclick={retryRead}>
          {loading ? "Reading…" : "Retry read"}
        </button>
      {:else if loading && !selected}
        <p class="bridge-loading" role="status">Loading conversation…</p>
        <div class="mist" aria-hidden="true"></div><div class="mist" aria-hidden="true"></div>
      {:else if error && !selected}
        <div class="turn__fault" role="alert">{error}</div>
        <button class="rune-btn retry-conversation" type="button" onclick={() => void load(sessionId)}>Retry conversation</button>
      {:else if choosing}
        <div class="shell-placeholder">
          <h2 class="rune-head">{attentionOnly ? "Conversations awaiting consent" : "Choose a conversation"}</h2>
          <p>{attentionOnly ? "Select a marked conversation to review its pending requests." : "Select a conversation from the list or open a new séance."}</p>
          {#if attentionOnly && !snapshot?.sessions.some((session) => (session.pending_count ?? 0) > 0)}
            <p>{snapshot?.pending_count ? snapshot.sessions_next_cursor ? "Load more conversations to find older pending requests." : "Pending requests have no available Bridge conversation." : "No conversation is awaiting consent."}</p>
          {/if}
        </div>
      {:else if firstVisit}
        <AltarWelcome onbegin={createSession} onnaming={openNaming} pending={creatingSession} />
      {:else if !selected}
        <div class="shell-placeholder">
          <span class="glyph-big">⬡</span>
          <span class="rune-head">The Bridge awaits</span>
          <p>Open a séance to begin a local communion.</p>
        </div>
      {:else}
        {#if !(selected.turns?.length || selectedLiveTurns.length || snapshot?.pending_consents.length)}
          <div class="conversation-empty">
            <span aria-hidden="true">✦</span>
            <h2>What shall we explore?</h2>
            <p>Offer a question, an idea, or a piece of work.</p>
          </div>
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
            <div class="turn__meta"><span class="who">{turn.role === "agent" ? "LychD" : "You"}</span></div>
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
            <div class="turn__meta">
              <span class="who">LychD</span>
            </div>
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
          <button class="rune-btn" type="button" disabled={!!prompt} onclick={() => recoverRefused(refused.requestId, true)}>Restore refused offering</button>
          <button class="rune-btn" type="button" onclick={() => recoverRefused(refused.requestId, false)}>Dismiss refused offering</button>
          {#if prompt}<p>Your current draft is kept. Send or clear it before restoring this text.</p>{/if}
        </section>
      {/each}
      {#if pendingOffering}
        <section class="offering-recovery" aria-label="Unresolved offering" aria-live="polite">
          <strong>{pendingOffering.sending ? "Sending offering…" : "Offering outcome unknown"}</strong>
          <p class="offering-recovery__text">{pendingOffering.text}</p>
          {#if pendingOffering.error}<p>{pendingOffering.error}</p>{/if}
          <p>{pendingOffering.sending ? "You can continue browsing while this request settles." : "Retry the original offering to recover its result before sending a new one."}</p>
          <button class="rune-btn" type="button" disabled={pendingOffering.sending} onclick={() => void submit(true)}>Retry original offering</button>
        </section>
      {/if}
      <div class="composer-area" role="region" aria-label="Bridge composer">
        <div class="composer-shell">
          <div class="composer-destination">
            <label for="bridge-destination">Send to</label>
            <select id="bridge-destination" value={composerMode} onchange={changeMode}>
              <option value="chat">Conversation</option>
              <option value="work">{destination}</option>
            </select>
          </div>
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
            <button
              class="rune-btn composer-send"
              disabled={voiceSnapshot.busy || composing || !prompt.trim()}
              type="button"
              onclick={sendComposer}
            >
              {composerMode === "work" ? "Send command" : "Offer"}
            </button>
          </div>
        </div>
        {#if commandPending}<p class="command-result" role="status">Preparing command…</p>{/if}
        {#if commandResult}<p class="command-result" role="status">{commandResult.status}: {commandResult.summary}</p>{/if}
        <div class="composer-footer">
          <p id="composer-shortcuts">Enter to {composerMode === "work" ? "send command" : "offer"} · Shift + Enter for a new line</p>
          <p id="composer-guidance" class:visually-hidden={!loading && !pendingOffering && !hasUnsettledRun} role="status">{loading ? "Refreshing this conversation before another offering." : pendingOffering ? "Resolve the original offering first. This later draft is kept and is not queued." : hasUnsettledRun ? "Wait for this Run to settle before offering again. You can keep writing; this draft is not queued." : "Draft stays in this open tab."}</p>
        </div>
        {#if error}<div class="turn__fault" role="alert">{error}</div>{/if}
      </div>
    {/if}
  </div>

</div>

<style>
  .instrument-deck--bridge { display: grid; grid-template-columns: 17rem minmax(0, 1fr); gap: 0; padding: 0; min-height: 0; height: 100%; overflow: hidden; background: var(--color-void); }
  .instrument-deck--welcome { grid-template-columns: minmax(0, 1fr); }
  .bridge-rail { width: auto; min-width: 0; padding: 1.25rem .85rem; border-right: 1px solid var(--color-engraving); overflow-y: auto; background: var(--color-obsidian); }
  .conversation-list { width: 100%; }
  /* Native details keeps history reachable without making it the dock's first reading task. */
  .conversation-list > summary { min-height: 2.75rem; margin-bottom: .65rem; color: var(--color-bone); font: 600 var(--text-sm)/1.5 var(--font-body); cursor: pointer; }
  .conversation-list nav { display: flex; flex-direction: column; gap: .15rem; margin-top: 1rem; }
  .archive-label { margin: 1.25rem .5rem .35rem; font: 600 var(--text-xs)/1.4 var(--font-body); color: var(--color-parchment); }
  .archive-order, .rail-empty { color: var(--color-ash); font-size: var(--text-xs); line-height: 1.6; }
  .archive-order { margin: 0 .5rem .5rem; }
  .conversation-row { display: grid; grid-template-columns: minmax(0, 1fr) 2.75rem; align-items: center; gap: .15rem; }
  .pin-conversation { display: grid; place-items: center; min-height: 2.75rem; border: 0; border-radius: var(--radius-glyph); color: var(--color-ash); background: transparent; cursor: pointer; }
  .pin-conversation:hover { color: var(--color-bone); background: var(--color-obsidian-2); }
  .pin-conversation[aria-pressed="true"] { color: var(--color-accent); }
  .new-seance { width: 100%; min-height: 2.75rem; box-shadow: none; background: var(--color-bone); border-color: var(--color-bone); color: var(--color-void); }
  .new-seance:hover:not(:disabled) { background: var(--color-parchment); border-color: var(--color-parchment); color: var(--color-void); }
  .seance { min-width: 0; min-height: 2.75rem; padding: .7rem .65rem; border: 0; border-left: 2px solid transparent; border-radius: var(--radius-glyph); overflow-wrap: anywhere; }
  .seance:hover { background: var(--color-obsidian-2); }
  .seance.current { border: 0; border-left: 2px solid var(--color-rune); background: var(--color-obsidian-2); box-shadow: none; }
  .seance .t { font-size: var(--text-sm); line-height: 1.5; margin-bottom: .15rem; color: var(--color-bone); }
  .seance .m { font-family: var(--font-body); }
  .seance .chip { display: inline; margin: .2rem .45rem .2rem 0; padding: 0; border: 0; border-radius: 0; background: transparent; color: var(--color-parchment); font-size: var(--text-xs); white-space: normal; }
  .bridge-thread { min-height: 0; overflow: hidden; }
  .bridge-heading { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: .25rem 1rem; padding: .8rem clamp(1rem, 3vw, 2rem) .35rem; border-bottom: 1px solid var(--color-engraving); }
  .bridge-heading > div { min-width: 0; }
  .bridge-heading h1 { color: var(--color-ash); font: 600 var(--text-xs)/1.5 var(--font-body); letter-spacing: .06em; text-transform: uppercase; }
  .conversation-title { margin-top: .45rem; color: var(--color-bone); font: 600 clamp(1.125rem, 1.5vw, 1.4rem)/1.4 var(--font-body); overflow-wrap: anywhere; }
  .conversation-attention { margin-top: .25rem; font-size: var(--text-sm); color: var(--color-bone); line-height: 1.5; }
  .conversation-tools { min-width: 0; font-size: var(--text-sm); }
  .conversation-tools > summary { min-width: 2.75rem; min-height: 2.75rem; align-content: center; color: var(--color-parchment); cursor: pointer; }
  .conversation-tools[open] { grid-column: 1 / -1; }
  .seance-details { min-width: 0; font-size: var(--text-sm); }
  .seance-details summary { display: list-item; min-height: 2.75rem; align-content: center; white-space: nowrap; cursor: pointer; }
  .seance-details .chip { margin-left: .5rem; white-space: normal; }
  .seance-details .kv { position: static; width: 100%; padding: .75rem 0; border: 0; border-radius: 0; background: transparent; }
  .bridge-tools { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: flex-start; gap: 0 1rem; max-height: min(20rem, 40dvh); padding: .25rem 0 0; overflow-y: auto; overscroll-behavior: contain; border-top: 1px solid var(--color-engraving); font-size: var(--text-sm); }
  .bridge-tools > details { min-width: 0; padding: 0; border: 0; background: transparent; }
  .bridge-tools > details[open] { flex-basis: 100%; }
  .bridge-tools summary { min-height: 2.75rem; align-content: center; cursor: pointer; color: var(--color-parchment); }
  .thread-scroll { min-height: 4rem; padding: 1.5rem max(1rem, calc((100% - 48rem) / 2)); gap: 1.75rem; scrollbar-gutter: stable; }
  .thread-scroll:focus-visible { outline: 1px solid var(--color-rune); outline-offset: -3px; }
  .turn { max-width: 100%; overflow-wrap: anywhere; }
  .turn--user { max-width: min(42rem, 92%); }
  .turn--user .turn__meta { justify-content: flex-end; }
  .turn__body { white-space: pre-wrap; font-size: 1rem; line-height: 1.75; box-shadow: none; }
  .turn--user .turn__body { padding: .85rem 1rem; background: var(--color-obsidian-2); border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); }
  .turn--agent .turn__body { padding: .25rem 0; color: var(--color-bone); background: transparent; border: 0; border-radius: 0; }
  .turn--agent[data-state="stale"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-control-border); }
  .turn--agent[data-state="failed"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-ember); }
  .turn--agent[data-state="cancelled"] .turn__body { padding-left: .85rem; border-left: 2px solid var(--color-ash); }
  .turn__meta { flex-wrap: wrap; gap: .4rem .75rem; }
  .turn__meta .who { color: var(--color-parchment); font: 600 var(--text-sm)/1.5 var(--font-body); font-variant: normal; letter-spacing: 0; }
  .conversation-empty { margin: auto; padding: 3rem 1rem; text-align: center; }
  .conversation-empty > span { color: var(--color-accent); font-size: 1.6rem; }
  .conversation-empty h2 { margin: 1rem 0 .7rem; font: 500 1.65rem/1.3 var(--font-body); color: var(--color-bone); }
  .conversation-empty p, .bridge-loading { color: var(--color-parchment); }
  .retry-conversation { align-self: flex-start; min-height: 2.75rem; }
  .latest-turn { display: flex; justify-content: center; padding: .25rem 1rem .5rem; }
  .latest-turn button { min-height: 2.75rem; padding: .4rem 1rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); color: var(--color-rune); background: var(--color-obsidian); cursor: pointer; }
  .composer-area { flex: 0 1 auto; min-height: 0; max-height: min(36rem, 65dvh); overflow-y: auto; overscroll-behavior: contain; padding: .8rem clamp(1rem, 3vw, 2rem) 1rem; border-top: 1px solid var(--color-engraving); }
  .composer-area:focus-visible { outline: 2px solid var(--color-rune); outline-offset: -2px; }
  .composer-shell { max-width: 52rem; margin-inline: auto; padding: .65rem .85rem .75rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  .composer-shell:focus-within { border-color: var(--color-rune); }
  .composer-destination { display: flex; align-items: center; gap: .75rem; margin-bottom: .55rem; min-width: 0; font-size: var(--text-sm); }
  .composer-destination label { flex: 0 0 auto; color: var(--color-parchment); }
  #bridge-destination { flex: 1 1 auto; width: auto; min-width: 0; max-width: 28rem; min-height: 2.75rem; margin: 0; padding: .4rem .25rem; border: 0; border-radius: 0; background: transparent; color: var(--color-bone); font: inherit; }
  .command-help, .command-result { font-size: var(--text-sm); line-height: 1.6; overflow-wrap: anywhere; }
  .command-help { padding: 0 0 .75rem; margin: 0 0 .75rem; border-bottom: 1px solid var(--color-engraving); }
  .command-help p + p { margin-top: .35rem; }
  .command-help summary { min-height: 2.75rem; align-content: center; cursor: pointer; }
  .command-help ul { padding-left: 1.4rem; }
  .command-help code { white-space: pre-wrap; overflow-wrap: anywhere; }
  .command-result { margin: .65rem 0 0; color: var(--color-parchment); }
  .composer-label { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
  .composer-instructions { margin: .25rem 0 .75rem; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
  .composer { display: flex; margin: 0; padding: 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
  .composer:focus-within { box-shadow: none; border: 0; }
  .composer textarea { display: block; width: 100%; min-width: 0; min-height: 3rem; max-height: 16rem; padding: 0; resize: vertical; font-size: 1rem; line-height: 1.5; background: transparent; }
  .composer-actions { position: relative; --voice-action-reserve: 6rem; padding-top: .35rem; border-top: 1px solid var(--color-engraving); }
  .composer-actions--work { --voice-action-reserve: 9rem; }
  .composer-voice { min-width: 0; }
  .composer-send { position: absolute; inset-block-start: .35rem; inset-inline-end: 0; min-width: 5rem; min-height: 2.75rem; margin: 0; padding: .5rem 1rem; border-color: var(--color-bone); background: var(--color-bone); color: var(--color-void); box-shadow: none; }
  .composer-send:hover:not(:disabled) { background: var(--color-parchment); border-color: var(--color-parchment); color: var(--color-void); }
  .composer-send:disabled { opacity: .5; }
  .composer-footer { display: flex; max-width: 52rem; justify-content: space-between; gap: .3rem 1.5rem; flex-wrap: wrap; margin: .35rem auto 0; color: var(--color-ash); font-size: var(--text-xs); line-height: 1.6; }
  .composer-footer p { max-width: 38rem; }
  .offering-recovery { flex: 0 1 auto; min-height: 4rem; margin: .75rem 1rem; padding: .8rem 1rem; border: 0; border-left: 2px solid var(--color-rune); border-radius: 0; background: var(--color-obsidian); max-height: min(22rem, 45dvh); overflow-y: auto; overscroll-behavior: contain; }
  .offering-recovery p { margin: .5rem 0; color: var(--color-parchment); line-height: 1.6; }
  .offering-recovery .offering-recovery__text { color: var(--color-bone); white-space: pre-wrap; max-height: 12rem; overflow: auto; overflow-wrap: anywhere; }
  .offering-recovery .rune-btn { min-height: 2.75rem; margin: .25rem .35rem .25rem 0; }
  .atlas-links { display: flex; flex-wrap: wrap; gap: .35rem 1rem; align-items: center; padding: .5rem clamp(1rem, 3vw, 2rem); color: var(--color-parchment); font-size: var(--text-sm); }
  .atlas-links a { color: var(--color-rune); min-height: 2.75rem; display: inline-flex; align-items: center; }
  .public-sources .atlas-links { padding: 0 0 .35rem; }
  .turn:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .bridge-embedded { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); height: 100%; overflow: hidden; }
  .bridge-embedded.instrument-deck--welcome { grid-template-rows: minmax(0, 1fr); }
  .bridge-embedded .bridge-rail { padding: 0 .95rem; border: 0; max-height: min(18rem, 35dvh); overflow: auto; background: transparent; }
  .bridge-embedded .conversation-list > summary { margin: 0; font-weight: 500; }
  .bridge-embedded .conversation-list nav { margin-top: .25rem; padding-bottom: .75rem; }
  .bridge-embedded .bridge-heading { padding: .2rem .95rem; gap: .15rem .5rem; }
  .bridge-embedded .bridge-heading h1 { display: none; }
  .bridge-embedded .conversation-title { margin: 0; font: 600 var(--text-base)/1.5 var(--font-body); }
  .bridge-embedded .seance-details { font-size: var(--text-xs); }
  .bridge-embedded .seance-details[open] { width: 100%; }
  .bridge-embedded .seance-details .kv { position: static; width: 100%; }
  .bridge-embedded .bridge-tools { padding: .25rem 0 0; gap: 0 1rem; font-size: var(--text-xs); }
  .bridge-embedded .atlas-links { padding: .25rem .95rem; gap: .25rem .75rem; }
  .bridge-embedded .public-sources .atlas-links { padding-inline: 0; }
  .bridge-embedded .thread-scroll { padding: 1rem .95rem; gap: 1.5rem; flex: 1; min-height: 4rem; }
  .bridge-embedded .composer-area { padding: .4rem .65rem .45rem; }
  .bridge-embedded .composer-shell { padding: .3rem .6rem .4rem; }
  .bridge-embedded .composer textarea { min-height: 3rem; }
  .bridge-embedded .composer-destination { margin-bottom: .1rem; gap: .5rem; }
  .bridge-embedded .composer-voice { --voice-label-display: none; }
  .bridge-embedded .composer-send { min-width: 4.5rem; padding-inline: .75rem; }
  .bridge-embedded .turn__body { font-size: var(--text-base); line-height: 1.7; }
  @media (max-width: 48rem) {
    .instrument-deck--bridge { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
    .bridge-rail { display: block; max-height: 35dvh; padding: 0 .95rem; border-right: 0; border-bottom: 1px solid var(--color-engraving); overflow: auto; }
    .conversation-list > summary { margin: 0; }
    .conversation-list nav { max-height: 12rem; overflow-y: auto; margin-top: .5rem; padding-bottom: .75rem; }
    .bridge-heading { gap: .25rem .5rem; padding: .25rem .95rem; }
    .conversation-title { margin-top: .25rem; font-size: var(--text-base); }
    .seance-details { font-size: var(--text-xs); }
    .seance-details summary { white-space: normal; }
    .seance-details .kv { position: static; width: 100%; grid-template-columns: minmax(0, .7fr) minmax(0, 1fr); }
    .bridge-tools { padding-inline: 0; font-size: var(--text-xs); }
    .thread-scroll { padding: 1rem .95rem; }
    .composer-area { padding: .4rem .65rem .45rem; }
    .composer-shell { padding: .3rem .6rem .4rem; }
    .composer textarea { min-height: 3rem; }
    .composer-destination { margin-bottom: .1rem; gap: .5rem; }
    .composer-voice { --voice-label-display: none; }
    .composer-send { min-width: 4.5rem; padding-inline: .75rem; }
    .composer-footer { gap: .2rem .5rem; }
    .turn--user { max-width: 95%; }
  }
</style>
