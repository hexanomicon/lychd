<script lang="ts">
  import { goto, replaceState } from "$app/navigation";
  import { page } from "$app/state";
  import { getContext, onDestroy, tick, untrack } from "svelte";
  import { SvelteMap, SvelteSet } from "svelte/reactivity";

  import {
    ApiError,
    cancelBridgeRun,
    createBridgeSession,
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
  } from "$lib/bridge/projection";
  import ConsentCard from "./ConsentCard.svelte";
  import DelegateMark from "./DelegateMark.svelte";
  import GenUI from "./GenUI.svelte";
  import AtlasLinks from "./AtlasLinks.svelte";
  import AltarWelcome from "./AltarWelcome.svelte";
  import { atlasHref } from "$lib/atlas/navigation";
  import { bridgeWorkspaceKey, createBridgeWorkspace, type BridgeWorkspace } from "$lib/bridge/workspace.svelte";
  import { delegationStatusLabel } from "$lib/delegation/presentation";

  let { sessionId }: { sessionId?: string } = $props();
  let snapshot = $state<BridgeSnapshot | null>(null);
  const work = getContext<BridgeWorkspace | undefined>(bridgeWorkspaceKey) ?? createBridgeWorkspace();
  const observedSettlements = new Map(work.settlements);
  let projectHint = $derived.by(() => {
    const id = page.url.searchParams.get("project");
    return id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id) ? id : null;
  });
  let attentionOnly = $derived(page.url.searchParams.get("attention") === "pending");
  let choosing = $derived(!sessionId && (attentionOnly || page.url.searchParams.get("choose") === "conversation" || !!projectHint));
  let hintedProject = $state<{ id: string; title: string } | null>(null);
  let projectError = $state("");
  let focusRun = $derived.by(() => {
    const id = page.url.searchParams.get("run");
    return id && /^[a-zA-Z0-9_-]{1,128}$/.test(id) ? id : null;
  });
  let focusedElement: HTMLElement | undefined;

  function setPrompt(text: string) {
    if (selected) work.setDraft(selected.id, text);
  }

  function bridgeHref(id: string) {
    return `/bridge/${encodeURIComponent(id)}${projectHint ? `?project=${encodeURIComponent(projectHint)}` : ""}`;
  }
  let loading = $state(true);
  let creatingSession = $state(false);
  let error = $state("");
  let thread: HTMLDivElement | undefined;
  let loadVersion = 0;
  let renderVersion = $state(0);
  let consentAuthorityVersion = 0;
  let stickToTail = true;
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

  function turnIsTerminal(turn: LiveTurn): boolean {
    return turn.state === "done" || turn.state === "failed" || turn.state === "cancelled";
  }

  function omen(text: string, fault = true) {
    window.dispatchEvent(new CustomEvent("altar:omen", { detail: { text, fault } }));
  }

  async function load(id?: string) {
    const version = ++loadVersion;
    const settlementsAtRequest = new Map(work.settlements);
    const runAuthorityAtRequest = new Map(
      liveTurns.map((turn) => [turn.runId, turn.authorityGeneration])
    );
    const requestedIdentityChanged =
      id !== undefined && activeSessionIdentity !== null && activeSessionIdentity !== id;
    loading = true;
    error = "";
    if (requestedIdentityChanged) {
      snapshot = null;
    }
    try {
      const received = await getBridgeSnapshot(id);
      const next = choosing ? { ...received, session: null, active_runs: [], pending_consents: [] } : received;
      if (destroyed || version !== loadVersion) return;
      const nextSessionIdentity = next.session?.id ?? null;
      if (nextSessionIdentity && (work.settlements.get(nextSessionIdentity) ?? 0) !== (settlementsAtRequest.get(nextSessionIdentity) ?? 0)) {
        await load(id);
        return;
      }
      activeSessionIdentity = nextSessionIdentity;
      const merged = mergeSnapshotLiveTurns(next, $state.snapshot(liveTurns));
      for (const active of next.active_runs) {
        const index = merged.liveTurns.findIndex((turn) => turn.runId === active.run_id);
        const current = merged.liveTurns[index];
        const expectedGeneration = runAuthorityAtRequest.get(active.run_id);
        if (current && expectedGeneration !== undefined && !streams.has(active.run_id)) {
          merged.liveTurns[index] = replaceLiveTurnFromSnapshot(
            current,
            active,
            expectedGeneration
          );
        }
      }
      for (const runId of merged.retiredRunIds) {
        streams.get(runId)?.();
        streams.delete(runId);
        clearRefreshTimer(runId);
      }
      snapshot = next;
      consentAuthorityVersion++;
      liveTurns = merged.liveTurns;
      for (const active of next.active_runs) {
        const turn = liveTurns.find((item) => item.runId === active.run_id);
        if (!turn) continue;
        if (!turnIsTerminal(turn)) attachStream(turn, turn.cursor);
      }
      window.dispatchEvent(new CustomEvent("altar:attention", { detail: next.pending_count }));
    } catch (cause) {
      if (version === loadVersion) error = cause instanceof Error ? cause.message : "The Bridge stayed dark.";
    } finally {
      if (version === loadVersion) loading = false;
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
    const run = focusRun;
    const ready = !loading;
    renderVersion;
    if (!id || !run || !ready) {
      focusedElement = undefined;
      if (!run) stickToTail = true;
      return;
    }
    void tick().then(() => {
      if (destroyed || selected?.id !== id || focusRun !== run) return;
      const target = thread?.querySelector<HTMLElement>(`[data-run-id="${run}"]`);
      if (!target || target === focusedElement) return;
      focusedElement = target;
      stickToTail = false;
      target.focus({ preventScroll: true });
      target.scrollIntoView?.({ block: "center" });
    });
  });

  $effect.pre(() => {
    renderVersion;
    const target = thread;
    if (target && stickToTail && !focusRun) {
      void tick().then(() => {
        target.scrollTop = target.scrollHeight;
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
    for (const close of streams.values()) close();
    streams.clear();
    for (const timer of refreshTimers.values()) window.clearTimeout(timer);
    refreshTimers.clear();
  });

  async function createSession() {
    if (creatingSession) return;
    creatingSession = true;
    try {
      const created = await createBridgeSession();
      if (destroyed) return;
      await goto(bridgeHref(created.session.id), {
        keepFocus: true,
        state: { bridgeComposerFocus: created.session.id }
      });
    } catch (cause) {
      if (!destroyed) omen(cause instanceof Error ? cause.message : "A séance could not be opened.");
    } finally {
      if (!destroyed) creatingSession = false;
    }
  }

  function focusCreatedComposer(node: HTMLTextAreaElement) {
    if (selected?.id && page.state.bridgeComposerFocus === selected.id) {
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
    if (restore) work.setDraft(selected.id, offering.text);
    const remaining = retained.filter((item) => item.requestId !== requestId);
    if (remaining.length) work.refused.set(selected.id, remaining);
    else work.refused.delete(selected.id);
  }

  async function submit(retry = false) {
    if (!selected || choosing) return;
    const targetSessionId = selected.id;
    const prior = work.pending.get(targetSessionId);
    if (prior?.sending || (prior && !retry) || (retry && !prior)) return;
    const text = prior?.text ?? prompt.trim();
    if (!text) return;
    const requestId = prior?.requestId ?? crypto.randomUUID();
    work.pending.set(targetSessionId, {
      text, requestId, uncertain: prior?.uncertain ?? false, sending: true, error: ""
    });
    error = "";
    if (!retry) work.setDraft(targetSessionId, "");
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
      attachStream(live);
    } catch (cause) {
      const uncertain = prior?.uncertain || !(cause instanceof ApiError) || cause.status === undefined || cause.status >= 500;
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
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
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
    if (!snapshot) return;
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
    if (selected) void load(selected.id);
  }

  function trackScroll() {
    if (!thread) return;
    stickToTail = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 72;
  }
</script>

<svelte:head><title>Bridge — LychD</title></svelte:head>
<div class="instrument-deck instrument-deck--bridge" class:instrument-deck--welcome={firstVisit}>
  <h1 class="visually-hidden">Bridge — conversations</h1>
  {#if !firstVisit}
  <aside class="bridge-rail">
    <button class="rune-btn new-seance" type="button" disabled={creatingSession} aria-busy={creatingSession} onclick={createSession}>✦ &nbsp;{creatingSession ? "Opening…" : "New Séance"}</button>
    <div class="divider">⬡</div>
    {#if snapshot?.sessions.length}
      {#each snapshot.sessions.filter((session) => !attentionOnly || (session.pending_count ?? 0) > 0) as session (session.id)}
        <a class:current={selected?.id === session.id} class="seance" href={bridgeHref(session.id)}>
          <span class="t">{session.title}</span>
          {#if session.pending_count}<span class="chip">{session.pending_count} awaiting consent</span>{/if}
          {#if work.pending.has(session.id)}<span class="chip">Offering unresolved</span>{:else if work.refused.has(session.id)}<span class="chip">Refused offering</span>{:else if work.drafts.has(session.id)}<span class="chip">Draft</span>{/if}
          <span class="m glyph">{new Date(session.created_at).toLocaleString()}</span>
        </a>
      {/each}
    {:else if !loading && !error}
      <p class="glyph rail-empty">No séance yet — open one to speak.</p>
    {/if}
  </aside>
  {/if}

  <div class="bridge-thread">
    {#if hintedProject}
      <nav class="atlas-links" aria-label="Originating project">
        <a href={atlasHref(hintedProject.id)}>← {hintedProject.title}</a>
        <span>Project context is not sent automatically.</span>
      </nav>
    {:else if projectError}<p class="turn__fault" role="status">{projectError}</p>{/if}
    {#if selected}<AtlasLinks kind="session" targetId={selected.id} suggestedProject={hintedProject} />{/if}
    {#if focusRun && !loading && selected && !(selected.turns ?? []).some((turn) => turn.role === "agent" && turn.run_id === focusRun) && !selectedLiveTurns.some((turn) => turn.runId === focusRun)}
      <p class="turn__fault" role="status">The requested Run is not available in this conversation.</p>
    {/if}
    <div
      class="thread-scroll"
      {@attach captureThread}
      onscroll={trackScroll}
      aria-label="Conversation"
    >
      {#if loading}
        <div class="mist"></div><div class="mist"></div>
      {:else if error && !selected}
        <div class="turn__fault">{error}</div>
      {:else if choosing}
        <div class="shell-placeholder">
          <h2 class="rune-head">{attentionOnly ? "Conversations awaiting consent" : "Choose a conversation"}</h2>
          <p>{attentionOnly ? "Select a marked conversation to review its pending requests." : "Select a conversation from the list or open a new séance."}</p>
          {#if attentionOnly && !snapshot?.sessions.some((session) => (session.pending_count ?? 0) > 0)}
            <p>{snapshot?.pending_count ? "Pending requests have no available Bridge conversation." : "No conversation is awaiting consent."}</p>
          {/if}
        </div>
      {:else if firstVisit}
        <AltarWelcome onbegin={createSession} pending={creatingSession} />
      {:else if !selected}
        <div class="shell-placeholder">
          <span class="glyph-big">⬡</span>
          <span class="rune-head">The Bridge awaits</span>
          <p>Open a séance to begin a local communion.</p>
        </div>
      {:else}
        {#each selected.turns ?? [] as turn (turn)}
          <article
            class:turn--user={turn.role === "user"}
            class:turn--agent={turn.role === "agent"}
            class="turn"
            data-run-id={turn.role === "agent" ? turn.run_id : undefined}
            tabindex="-1"
            data-state={turn.state === "failed" ? "failed" : "done"}
          >
            {#if turn.role === "agent"}<div class="turn__meta"><span class="who">LychD</span></div>{/if}
            <div class="turn__body">{turn.content}</div>
            {#if turn.role === "agent" && (turn.fragments?.length ?? 0) > 0}
              <div class="turn__extras">
                {#each turn.fragments ?? [] as fragment (fragment)}<GenUI descriptor={fragment} />{/each}
              </div>
            {/if}
            {#if turn.role === "agent" && turn.run_id}
              <a class="settled-evidence" href="/orb/{turn.run_id}">Look into the Orb →</a>
            {/if}
          </article>
        {/each}
        {#each selectedLiveTurns as turn (turn.runId)}
          <article class="turn turn--agent" data-state={turn.state} data-run-id={turn.runId} tabindex="-1">
            <div class="turn__meta">
              <span class="who">LychD</span>
              <span class="chip" data-state={turn.runStatus}>{operatorState(turn.runStatus)}</span>
              <span class="status" aria-live="polite">{operatorState(turn.activity)}</span>
            </div>
            <div class="turn__body">{turn.content}</div>
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
            <nav class="run-sigil" aria-label="Run links">
              <span class="run-sigil__id">run {turn.runId.slice(0, 12)}</span>
              <span>{turn.patternId}@{turn.patternRevision}</span>
              <a href={turn.delegatedJobId ? `${turn.orbPath}?job=${encodeURIComponent(turn.delegatedJobId)}` : turn.orbPath}>
                Look into the Orb →
              </a>
              {#if turn.state !== "done" && turn.state !== "failed" && turn.state !== "cancelled"}
                <button
                  class="run-stop"
                  type="button"
                  disabled={cancellingRuns.has(turn.runId)}
                  aria-label={`Cancel run ${turn.runId}`}
                  title="Cancel Run"
                  onclick={() => void cancelRun(turn)}
                >■</button>
              {/if}
            </nav>
            <div class="turn__extras">
              {#each turn.fragments as fragment (fragment)}<GenUI descriptor={fragment} />{/each}
            </div>
          </article>
        {/each}
        {#each snapshot?.pending_consents ?? [] as consent (consent.id)}
          <ConsentCard
            {consent}
            onauthority={beginConsentDecision}
            ondecided={consentDecided}
            onrefresh={refreshConsentAuthority}
          />
        {/each}
      {/if}
    </div>

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
      <div class="composer">
        <textarea
          bind:value={() => prompt, setPrompt}
          {@attach focusCreatedComposer}
          required
          rows="2"
          placeholder="Speak into the void…"
          onkeydown={keydown}
          aria-label="Message"
        ></textarea>
        <button
          class="rune-btn"
          disabled={!!pendingOffering || !prompt.trim()}
          type="button"
          onclick={() => void submit()}
        >
          Offer
        </button>
      </div>
      {#if error}<div class="turn__fault">{error}</div>{/if}
    {/if}
  </div>

  {#if selected}
    <aside class="bridge-inspector">
      <div class="panel">
        <div class="panel-head"><span class="rune-head">Séance</span></div>
        <dl class="kv">
          <dt>identity</dt><dd class="glyph">{selected.id}</dd>
          <dt>title</dt><dd>{selected.title}</dd>
          <dt>turns</dt><dd>{(selected.turns?.length ?? 0) + selectedLiveTurns.length}</dd>
          <dt>awaiting consent</dt><dd>{snapshot?.pending_consents.filter((card) => card.state === "pending_consent").length ?? 0}</dd>
        </dl>
      </div>
    </aside>
  {/if}
</div>

<style>
  .offering-recovery { margin: .8rem 1rem; padding: 1rem; border: 1px solid var(--color-rune-dim); border-radius: var(--radius-panel); background: var(--color-obsidian-2); }
  .offering-recovery p { margin: .5rem 0; color: var(--color-ash); }
  .offering-recovery .offering-recovery__text { color: var(--color-bone); white-space: pre-wrap; max-height: 12rem; overflow: auto; overflow-wrap: anywhere; }
  .atlas-links { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; padding: .75rem 1rem; color: var(--color-ash); }
  .atlas-links a { color: var(--color-rune); min-height: 2.75rem; display: inline-flex; align-items: center; }
  .turn:focus-visible { outline: 2px solid var(--color-rune); outline-offset: -2px; }
</style>
