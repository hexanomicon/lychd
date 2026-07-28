<script lang="ts">
  import { goto } from "$app/navigation";
  import { onDestroy } from "svelte";

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
  import GenUI from "./GenUI.svelte";

  let { sessionId }: { sessionId?: string } = $props();
  let snapshot = $state<BridgeSnapshot | null>(null);
  let prompt = $state("");
  let loading = $state(true);
  let sending = $state(false);
  let error = $state("");
  let thread: HTMLElement;
  let loadVersion = 0;
  let renderVersion = $state(0);
  let liveTurns = $state<LiveTurn[]>([]);
  const streams = new Map<string, () => void>();
  const refreshTimers = new Map<string, number>();

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

  $effect(() => {
    renderVersion;
    if (thread) {
      queueMicrotask(() => {
        thread.scrollTop = thread.scrollHeight;
      });
    }
  });

  onDestroy(() => {
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
        else if (event.kind === "status" || event.kind === "node") {
          active.status = String(payload.text ?? event.kind);
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
        }
      }
    );
    if (!hardClosed) streams.set(targetRunId, close);
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
          status: "queued",
          state: "streaming",
          fragments: []
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
</script>

<svelte:head><title>Bridge — LychD</title></svelte:head>
<div class="instrument-deck" aria-label="Bridge">
  <aside class="bridge-rail">
    <button class="rune-btn new-seance" type="button" onclick={createSession}>✦ &nbsp;New Séance</button>
    <div class="divider">◆</div>
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
    <div class="thread-scroll" bind:this={thread} aria-live="polite">
      {#if loading}
        <div class="mist"></div><div class="mist"></div>
      {:else if error && !selected}
        <div class="turn__fault">{error}</div>
      {:else if !selected}
        <div class="shell-placeholder">
          <span class="glyph-big">◈</span>
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
          </article>
        {/each}
        {#each selectedLiveTurns as turn (turn.runId)}
          <article class="turn turn--agent" data-state={turn.state}>
            <div class="turn__meta">
              <span class="who">LychD</span>
              <span class="status">{turn.status}</span>
            </div>
            <div class="turn__body">{turn.content}</div>
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
          placeholder="Speak into the Bridge…"
          onkeydown={keydown}
          aria-label="Message"
        ></textarea>
        <button class="rune-btn" disabled={sending || !prompt.trim()} type="button" onclick={submit}>
          Offer {#if sending}<span class="thinking-rune">◆</span>{/if}
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
        <div class="panel-head"><span class="rune-head">Context floor</span></div>
        <div class="floor">
          <div class="block volatile"><span class="layer">L0</span><span class="k">live projection</span></div>
          <div class="block"><span class="layer">L1</span><span class="k">session turns</span></div>
          <div class="block" data-state="stub"><span class="layer">L2</span><span class="k">memory</span></div>
        </div>
      </div>
    {/if}
  </aside>
</div>
