<script lang="ts">
  import { goto } from "$app/navigation";
  import { onDestroy, tick } from "svelte";
  import { SvelteMap } from "svelte/reactivity";

  import {
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
  let sending = $state(false);
  let error = $state("");
  let thread: HTMLDivElement | undefined;
  let loadVersion = 0;
  let renderVersion = $state(0);
  let stickToTail = true;
  let liveTurns = $state<LiveTurn[]>([]);
  const streams = new SvelteMap<string, () => void>();
  const refreshTimers = new SvelteMap<string, number>();
  const recoveredHardClosures = new Set<string>();
  let destroyed = false;
  const runStatuses = new Set([
    "queued",
    "running",
    "awaiting_hardware",
    "awaiting_consent",
    "awaiting_delegate",
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

  function omen(text: string, fault = true) {
    window.dispatchEvent(new CustomEvent("altar:omen", { detail: { text, fault } }));
  }

  async function load(id?: string) {
    const version = ++loadVersion;
    loading = true;
    error = "";
    try {
      const next = await getBridgeSnapshot(id);
      if (version !== loadVersion) return;
      const merged = mergeSnapshotLiveTurns(next, $state.snapshot(liveTurns));
      for (const active of next.active_runs) {
        const index = merged.liveTurns.findIndex((turn) => turn.runId === active.run_id);
        const current = merged.liveTurns[index];
        if (current && !streams.has(active.run_id)) {
          merged.liveTurns[index] = replaceLiveTurnFromSnapshot(
            current,
            active
          );
        }
      }
      for (const runId of merged.retiredRunIds) {
        streams.get(runId)?.();
        streams.delete(runId);
        clearRefreshTimer(runId);
      }
      snapshot = next;
      liveTurns = merged.liveTurns;
      for (const active of next.active_runs) {
        const turn = liveTurns.find((item) => item.runId === active.run_id);
        if (!turn) continue;
        if (active.terminal) scheduleSettledRefresh(active.run_id, active.session_id);
        else attachStream(turn, active.cursor);
      }
      window.dispatchEvent(new CustomEvent("altar:attention", { detail: next.pending_count }));
    } catch (cause) {
      if (version === loadVersion) error = cause instanceof Error ? cause.message : "The Bridge stayed dark.";
    } finally {
      if (version === loadVersion) loading = false;
    }
  }

  $effect(() => {
    void load(sessionId);
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
      await goto(`/bridge/${created.session.id}`);
    } catch (cause) {
      omen(cause instanceof Error ? cause.message : "A séance could not be opened.");
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
      if (sessionId !== expectedRouteSessionId) return;
      if (snapshot?.session?.id !== targetSessionId) return;
      void load(sessionId);
    }, 50);
    refreshTimers.set(runId, timer);
  }

  function attachStream(turn: LiveTurn, initialCursor = -1) {
    if (turn.state !== "streaming" || streams.has(turn.runId)) return;
    const targetRunId = turn.runId;
    const targetSessionId = turn.sessionId;
    let hardClosed = false;
    let close: (() => void) | undefined;
    close = listenToRun(
      targetRunId,
      (event) => {
        const active = liveTurns.find((item) => item.runId === targetRunId);
        if (!active) return;
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
          active.state = String(payload.status).includes("fail") ? "failed" : "done";
          active.runStatus = String(payload.status ?? "done");
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
        omen("The run stream lost history; refreshing its authoritative snapshot.", false);
        const projection = await getRunSnapshot(targetRunId);
        const index = liveTurns.findIndex((item) => item.runId === targetRunId);
        const active = liveTurns[index];
        if (active) {
          liveTurns[index] = replaceLiveTurnFromSnapshot(
            $state.snapshot(active),
            projection
          );
          if (snapshot?.session?.id === targetSessionId) {
            void load(targetSessionId);
          }
        }
        if (projection.terminal) {
          streams.get(targetRunId)?.();
          streams.delete(targetRunId);
          if (snapshot?.session?.id === targetSessionId) {
            scheduleSettledRefresh(targetRunId, targetSessionId);
          }
        }
        renderVersion++;
        return { cursor: projection.cursor, terminal: projection.terminal };
      },
      {
        initialCursor,
        onHardClose: () => {
          hardClosed = true;
          if (close === undefined || streams.get(targetRunId) === close) {
            streams.delete(targetRunId);
          }
          const active = liveTurns.find((item) => item.runId === targetRunId);
          if (active?.state === "streaming") {
            active.state = "stale";
            active.activity = "projection stale";
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
    try {
      const projection = await getRunSnapshot(runId);
      if (destroyed) return;
      if (projection.session_id !== targetSessionId) {
        throw new Error("The authoritative run snapshot changed session identity.");
      }
      const index = liveTurns.findIndex((item) => item.runId === runId);
      const active = liveTurns[index];
      if (!active) return;
      const recovered = replaceLiveTurnFromSnapshot($state.snapshot(active), projection);
      liveTurns[index] = recovered;
      renderVersion++;
      if (projection.terminal) {
        if (snapshot?.session?.id === targetSessionId) {
          scheduleSettledRefresh(runId, targetSessionId);
        }
      } else {
        attachStream(recovered, projection.cursor);
      }
    } catch {
      if (!destroyed) {
        omen("The run projection remains stale; refresh the Bridge to retry.", true);
      }
    }
  }

  async function submit() {
    const text = prompt.trim();
    if (!text || !selected || sending) return;
    const targetSessionId = selected.id;
    sending = true;
    error = "";
    prompt = "";
    try {
      const accepted = await sendBridgeMessage(targetSessionId, text);
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
      if (snapshot?.session?.id === targetSessionId && !prompt) prompt = text;
      error = cause instanceof Error ? cause.message : "The offering was refused.";
    } finally {
      sending = false;
    }
  }

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  function consentDecided(consent: ConsentCardModel, pending: number) {
    if (!snapshot) return;
    const index = snapshot.pending_consents.findIndex((item) => item.id === consent.id);
    if (index >= 0) snapshot.pending_consents[index] = consent;
    snapshot.pending_count = pending;
    window.dispatchEvent(new CustomEvent("altar:attention", { detail: pending }));
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
            </nav>
            <div class="turn__extras">
              {#each turn.fragments as fragment (fragment)}<GenUI descriptor={fragment} />{/each}
            </div>
          </article>
        {/each}
        {#each snapshot?.pending_consents ?? [] as consent (consent.id)}
          <ConsentCard {consent} ondecided={consentDecided} />
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
        <button class="rune-btn" disabled={sending || !prompt.trim()} type="button" onclick={submit}>
          Offer {#if sending}<span class="thinking-rune">⬢</span>{/if}
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
