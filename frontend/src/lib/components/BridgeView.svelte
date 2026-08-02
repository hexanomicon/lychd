<script lang="ts">
  import { goto } from "$app/navigation";
  import { onDestroy, tick, untrack } from "svelte";
  import { SvelteMap, SvelteSet } from "svelte/reactivity";

  import {
    ApiError,
    cancelBridgeRun,
    createBridgeSession,
    getBridgeSnapshot,
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
  import { delegationStatusLabel } from "$lib/delegation/presentation";

  let { sessionId }: { sessionId?: string } = $props();
  let snapshot = $state<BridgeSnapshot | null>(null);
  let prompt = $state("");
  let loading = $state(true);
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
  const sendingSessions = new SvelteSet<string>();
  const pendingSubmissions = new SvelteMap<string, { prompt: string; requestId: string }>();
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

  let selected = $derived(snapshot?.session ?? null);
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
    const runAuthorityAtRequest = new Map(
      liveTurns.map((turn) => [turn.runId, turn.authorityGeneration])
    );
    const requestedIdentityChanged =
      id !== undefined && activeSessionIdentity !== null && activeSessionIdentity !== id;
    loading = true;
    error = "";
    if (requestedIdentityChanged) {
      snapshot = null;
      prompt = "";
    }
    try {
      const next = await getBridgeSnapshot(id);
      if (destroyed || version !== loadVersion) return;
      const nextSessionIdentity = next.session?.id ?? null;
      if (activeSessionIdentity !== null && activeSessionIdentity !== nextSessionIdentity) {
        prompt = "";
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
    untrack(() => void load(routeSessionId));
  });

  $effect.pre(() => {
    renderVersion;
    const target = thread;
    if (target && stickToTail) {
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
    try {
      const created = await createBridgeSession();
      if (destroyed) return;
      await goto(`/bridge/${created.session.id}`);
    } catch (cause) {
      if (!destroyed) omen(cause instanceof Error ? cause.message : "A séance could not be opened.");
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

  async function submit() {
    const text = prompt.trim();
    if (!text || !selected || sendingSessions.has(selected.id)) return;
    const targetSessionId = selected.id;
    const prior = pendingSubmissions.get(targetSessionId);
    const requestId = prior?.prompt === text ? prior.requestId : crypto.randomUUID();
    pendingSubmissions.set(targetSessionId, { prompt: text, requestId });
    sendingSessions.add(targetSessionId);
    error = "";
    prompt = "";
    try {
      const accepted = await sendBridgeMessage(targetSessionId, text, requestId);
      if (destroyed) return;
      if (pendingSubmissions.get(targetSessionId)?.requestId === requestId) {
        pendingSubmissions.delete(targetSessionId);
      }
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
      if (destroyed) return;
      const ambiguous = !(cause instanceof ApiError) || cause.status === undefined || cause.status >= 500;
      if (!ambiguous && pendingSubmissions.get(targetSessionId)?.requestId === requestId) {
        pendingSubmissions.delete(targetSessionId);
      }
      if (snapshot?.session?.id === targetSessionId) {
        if (!prompt) prompt = text;
        error = cause instanceof Error ? cause.message : "The offering was refused.";
      }
    } finally {
      if (!destroyed) sendingSessions.delete(targetSessionId);
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
    window.dispatchEvent(new CustomEvent("altar:attention", { detail: pending }));
  }

  async function reconcileConsentAuthority(targetSessionId: string) {
    if (destroyed) return;
    if (snapshot?.session?.id === targetSessionId) {
      // Cancellation revokes this session's visible consent authority immediately.
      // The refetch may fail, but stale action cards must never survive it.
      consentAuthorityVersion++;
      snapshot.pending_consents = [];
      snapshot.pending_count = 0;
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
<div class="instrument-deck instrument-deck--bridge">
  <aside class="bridge-rail">
    <h1 class="visually-hidden">Bridge — conversations</h1>
    <button class="rune-btn new-seance" type="button" onclick={createSession}>✦ &nbsp;New Séance</button>
    <div class="divider">⬡</div>
    {#if snapshot?.sessions.length}
      {#each snapshot.sessions as session (session.id)}
        <a class:current={selected?.id === session.id} class="seance" href="/bridge/{session.id}">
          <span class="t">{session.title}</span>
          <span class="m glyph">{new Date(session.created_at).toLocaleString()}</span>
        </a>
      {/each}
    {:else}
      <p class="glyph rail-empty">No séance yet — open one to speak.</p>
    {/if}
  </aside>

  <div class="bridge-thread">
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
          <article class="turn turn--agent" data-state={turn.state}>
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
      <div class="composer">
        <textarea
          bind:value={prompt}
          required
          rows="2"
          placeholder="Speak into the void…"
          onkeydown={keydown}
          aria-label="Message"
        ></textarea>
        <button
          class="rune-btn"
          disabled={sendingSessions.has(selected.id) || !prompt.trim()}
          type="button"
          onclick={submit}
        >
          Offer {#if sendingSessions.has(selected.id)}<span class="thinking-rune">⬢</span>{/if}
        </button>
      </div>
      {#if error}<div class="turn__fault">{error}</div>{/if}
    {/if}
  </div>

  <aside class="bridge-inspector">
    {#if selected}
      <div class="panel">
        <div class="panel-head"><span class="rune-head">Séance</span></div>
        <dl class="kv">
          <dt>identity</dt><dd class="glyph">{selected.id}</dd>
          <dt>title</dt><dd>{selected.title}</dd>
          <dt>turns</dt><dd>{(selected.turns?.length ?? 0) + selectedLiveTurns.length}</dd>
          <dt>attention</dt><dd>{snapshot?.pending_count ?? 0}</dd>
        </dl>
      </div>
      <div class="panel">
        <div class="panel-head"><span class="rune-head">Review this run</span></div>
        <p class="inspector-copy">
          Look into the Orb for retained evidence. From there, open the exact Pattern in Loom or a
          correlated capability transition in Nexus when those links exist.
        </p>
      </div>
    {/if}
  </aside>
</div>
