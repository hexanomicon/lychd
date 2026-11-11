<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import PageHeader from "../shared/PageHeader.svelte";
  import { onMount, tick, untrack } from "svelte";
  import { ApiError, getBridgeSessions, getBridgeSnapshot } from "$lib/api/client";
  import type { BridgeSnapshot, BridgeTurnView, SessionPage } from "$lib/api/models";
  import { navigationId } from "$lib/navigation/instruments";
  import { bridgePinsLimit, bridgePinsStorageKey, parsePinnedConversations, togglePinnedConversation } from "$lib/bridge/pins";
  import { createSeancesWorkspace, getSeancesWorkspace, hasSeancesWorkspace } from "$lib/seances/workspace.svelte";
  import { materialKinds, materialMarkdown, sourceSignature, type MaterialKind, type SeanceMaterial } from "$lib/seances/material";

  let { sessionId }: { sessionId?: string } = $props();
  const work = hasSeancesWorkspace() ? getSeancesWorkspace() : createSeancesWorkspace((id) => goto(resolve("/bridge/[session_id]", { session_id: id })));
  let sessions = $state.raw<SessionPage["sessions"]>([]);
  let cursor = $state<string | null>(null);
  let catalogueLoading = $state(false);
  let catalogueError = $state("");
  let pins = $state.raw<readonly string[]>([]);
  let query = $state("");
  let snapshot = $state.raw<BridgeSnapshot | null>(null);
  let loading = $state(false);
  let readError = $state("");
  let notice = $state("");
  let view = $state<"transcript" | "material">("transcript");
  let readAt = $state("");
  let generation = 0;
  let accessVersion = 0;
  let alive = true;
  const catalogueRequest = new AbortController();
  const selected = $derived(snapshot?.session?.id === sessionId ? snapshot?.session : null);
  const material = $derived(selected ? work.materials.get(selected.id) ?? [] : []);
  const titles = $derived(new Map(sessions.map((item) => [item.id, item.title])));
  const matchingSessions = $derived(sessions.filter((item) => `${item.title} ${item.id}`.toLowerCase().includes(query.trim().toLowerCase())));
  const matchingPins = $derived(pins.filter((id) => `${titles.get(id) ?? ""} ${id}`.toLowerCase().includes(query.trim().toLowerCase())));

  onMount(() => {
    readPins();
    void loadCatalogue();
    return () => { alive = false; generation++; catalogueRequest.abort(); };
  });
  function readPins() {
    try { pins = parsePinnedConversations(localStorage.getItem(bridgePinsStorageKey)); }
    catch { /* Optional pin storage may be unavailable. */ }
  }
  function pin(id: string) {
    const next = togglePinnedConversation(pins, id);
    if (next === pins) { notice = `You can pin up to ${bridgePinsLimit} séances. Unpin one first.`; return; }
    pins = next;
    try { localStorage.setItem(bridgePinsStorageKey, JSON.stringify(next)); }
    catch { notice = "Pins are kept for this tab; browser storage is unavailable."; }
  }
  function denyAccess() {
    accessVersion++;
    generation++;
    sessions = [];
    cursor = null;
    snapshot = null;
    loading = false;
    catalogueLoading = false;
    catalogueError = "Catalogue access was refused. Retry after access is restored.";
    work.materials.clear();
    readError = "Access to séances is unavailable. Read again after access is restored.";
  }
  async function loadCatalogue() {
    if (catalogueLoading) return;
    const access = accessVersion;
    catalogueLoading = true;
    catalogueError = "";
    try {
      const next = await getBridgeSessions(cursor ?? undefined, catalogueRequest.signal);
      if (!alive || access !== accessVersion) return;
      const seen = new Set(sessions.map((item) => item.id));
      sessions = [...sessions, ...next.sessions.filter((item) => !seen.has(item.id) && !!seen.add(item.id))];
      cursor = next.next_cursor ?? null;
    } catch (cause) {
      if (alive && access === accessVersion) {
        if (cause instanceof ApiError && [401, 403].includes(cause.status ?? 0)) denyAccess();
        catalogueError = cause instanceof Error ? cause.message : "Séances could not be loaded.";
      }
    } finally { if (alive && access === accessVersion) catalogueLoading = false; }
  }

  async function read(id?: string) {
    const version = ++generation;
    snapshot = null;
    readError = "";
    notice = "";
    loading = false;
    if (id === undefined) return;
    if (navigationId(id) !== id) { readError = "This séance identity is invalid."; return; }
    loading = true;
    try {
      const next = await getBridgeSnapshot(id);
      if (!alive || version !== generation) return;
      if (next.session?.id !== id) { throw new Error("The requested séance was not returned. No other conversation has been selected."); }
      snapshot = next;
      readAt = new Date().toLocaleTimeString();
    } catch (cause) {
      if (!alive || version !== generation) return;
      if (cause instanceof ApiError && [401, 403].includes(cause.status ?? 0)) denyAccess();
      readError = cause instanceof Error ? cause.message : "This séance is unavailable.";
    } finally { if (alive && version === generation) loading = false; }
  }
  $effect(() => {
    const id = sessionId;
    untrack(() => { void read(id); });
  });
  async function continueConversation() {
    if (!selected) return;
    try { await work.continueInBridge(selected.id); }
    catch { notice = "Bridge could not be opened. Your inspected séance has not changed."; }
  }
  function select(turn: BridgeTurnView) {
    if (!selected) return;
    notice = work.add(selected.id, turn) ?? "Quotation added to Working material.";
  }
  function editNote(item: SeanceMaterial, element: HTMLTextAreaElement) {
    const error = work.update(item.sessionId, item.id, { note: element.value });
    if (error) { notice = error; element.value = item.note; }
  }
  async function inspectSource(item: SeanceMaterial) {
    const turn = selected?.turns?.find((turn) => sourceSignature(turn) === sourceSignature(item.source));
    if (!turn) { notice = "The selected quotation is not present in this retained read. Refresh or follow its exact session and Run reference."; return; }
    view = "transcript";
    await tick();
    const node = [...document.querySelectorAll<HTMLElement>("[data-seance-source]")].find((node) => node.dataset.seanceSource === sourceSignature(turn));
    node?.focus({ preventScroll: true });
    node?.scrollIntoView?.({ block: "center" });
  }
  async function copyMaterial() {
    if (!selected) return;
    try { await navigator.clipboard.writeText(materialMarkdown(selected.title, material)); notice = "Working material copied. Keep the copy somewhere safe before closing this tab."; }
    catch { notice = "Clipboard access is unavailable. Use Export Markdown to keep this material."; }
  }
  function exportMaterial() {
    if (!selected) return;
    const url = URL.createObjectURL(new Blob([materialMarkdown(selected.title, material)], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `seance-${selected.id}.md`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    notice = "Markdown download requested. Check the file before closing this tab.";
  }
</script>

<svelte:head><title>Séances — LychD</title></svelte:head>
<svelte:window onstorage={(event) => { if (event.key === bridgePinsStorageKey) readPins(); }} />
<div class="seances-workspace">
  <PageHeader title="Séances" description="Return to a conversation. Gather what matters for the next use.">
    {#snippet actions()}<a class="new-seance" href={resolve("/bridge?choose=conversation")}>New Séance in Bridge</a>{/snippet}
  </PageHeader>
  {#if notice}<p class="notice" role="status">{notice}</p>{/if}
  <div class="workspace-body">
    <aside class="catalogue" aria-label="Séance catalogue">
      <label for="seance-search">Find in loaded séances</label><input id="seance-search" type="search" bind:value={query} placeholder="Title or identity" />
      <h2>Pinned</h2>
      {#each matchingPins as id (id)}
        <div class="catalogue-row"><a href={resolve("/seances/[session_id]", { session_id: id })} aria-current={sessionId === id ? "page" : undefined}>{titles.get(id) ?? `Séance · ${id}`}{#if !titles.has(id)}<small>Details not loaded</small>{/if}</a><button type="button" aria-label={`Unpin séance ${titles.get(id) ?? id}`} onclick={() => pin(id)}>−</button></div>
      {:else}<p class="muted">No matching pins.</p>{/each}
      <h2>Recent séances</h2><p class="muted">Newest created first</p>
      {#each matchingSessions.filter((item) => !pins.includes(item.id)) as item (item.id)}
        <div class="catalogue-row"><a href={resolve("/seances/[session_id]", { session_id: item.id })} aria-current={sessionId === item.id ? "page" : undefined}>{item.title}<small>{new Date(item.created_at).toLocaleDateString()}{item.pending_count ? ` · ${item.pending_count} awaiting consent` : ""}</small></a><button type="button" aria-label={`Pin séance ${item.title}`} onclick={() => pin(item.id)}>+</button></div>
      {:else}{#if !catalogueLoading}<p class="muted">{query ? "No match in the loaded catalogue." : "No recent séances."}</p>{/if}{/each}
      {#if catalogueError}<p role="alert">{catalogueError}</p>{/if}
      {#if cursor || catalogueError}<button type="button" onclick={loadCatalogue} disabled={catalogueLoading}>{catalogueLoading ? "Loading…" : catalogueError ? "Retry catalogue" : "Load more séances"}</button>{:else if catalogueLoading}<p role="status">Loading séances…</p>{/if}
    </aside>
    <section class="detail" aria-label="Inspected séance">
      {#if loading}<p role="status">Reading séance…</p>
      {:else if readError}<h2>Séance unavailable</h2><p role="alert">{readError}</p><button type="button" onclick={() => read(sessionId)}>Retry read</button>
      {:else if selected}
        <header class="detail-heading"><div><h2>{selected.title}</h2><p class="identity">{selected.id}</p></div><button class="primary" type="button" onclick={continueConversation}>Continue in Bridge</button></header>
        <div class="read-status"><p>Retained read · {readAt}. Live replies and consent stay in Bridge.</p><button type="button" onclick={() => read(sessionId)}>Refresh transcript</button></div>
        {#if snapshot?.active_runs.length || selected.pending_count}<p class="notice">Live activity is available in Bridge. {selected.pending_count} awaiting consent. Continue in Bridge to review current actions.</p>{/if}
        <nav class="view-switch" aria-label="Séance views"><button type="button" aria-pressed={view === "transcript"} onclick={() => { view = "transcript"; }}>Transcript</button><button type="button" aria-pressed={view === "material"} onclick={() => { view = "material"; }}>Working material ({material.length})</button></nav>
        {#if view === "transcript"}
          <div class="transcript">
            {#each selected.turns ?? [] as turn (turn)}
              <article class={["retained-turn", { "user-turn": turn.role === "user" }]} data-seance-source={sourceSignature(turn)} tabindex="-1">
                <header><strong>{turn.role === "user" ? "You" : "LychD"}</strong><time datetime={turn.created_at}>{new Date(turn.created_at).toLocaleString()}</time><span>{turn.state}</span></header>
                <p class="quotation">{turn.content || "No text retained."}</p>
                <footer><button type="button" onclick={() => select(turn)} disabled={!turn.content}>Select quotation</button>{#if navigationId(turn.run_id)}<a href={resolve("/orb/[run_id]", { run_id: turn.run_id! })}>Run evidence →</a>{/if}</footer>
                {#if turn.fragments?.length}<p class="muted">{turn.fragments.length} retained fragments. Continue in Bridge to inspect them.</p>{/if}
              </article>
            {:else}<div class="empty"><h3>No retained turns yet</h3><p>Continue in Bridge to begin, or refresh after a reply settles.</p></div>{/each}
          </div>
        {:else}
          <div class="material-heading"><p>Manually selected quotations and notes. Kept in this open tab; export to keep. Not saved to Archive. Up to 32 selections and 128,000 quotation and note characters across this tab.</p><div class="actions"><button type="button" disabled={!material.length} onclick={copyMaterial}>Copy material</button><button type="button" disabled={!material.length} onclick={exportMaterial}>Export Markdown</button></div></div>
          {#each material as item (item.id)}
            <article class="material-card">
              <label>Use as <select value={item.kind} onchange={(event) => work.update(item.sessionId, item.id, { kind: event.currentTarget.value as MaterialKind })}>{#each materialKinds as kind (kind)}<option>{kind}</option>{/each}</select></label>
              <blockquote>{item.source.content}</blockquote><p class="muted">{item.source.role === "user" ? "You" : "LychD"} · {item.source.created_at}{item.source.run_id ? ` · Run ${item.source.run_id}` : " · No supplied Run identity"}</p>
              <label>Your note<textarea value={item.note} oninput={(event) => editNote(item, event.currentTarget)} rows="2" placeholder="Why keep this?"></textarea></label>
              <div class="actions"><button type="button" onclick={() => inspectSource(item)}>Inspect source</button><button type="button" onclick={() => work.remove(item.sessionId, item.id)}>Remove selection</button></div>
            </article>
          {:else}<div class="empty"><h3>Keep a thread worth following</h3><p>Select a quotation in Transcript, then mark it as a topic, open question or material for later use. Nothing is extracted automatically.</p></div>{/each}
        {/if}
      {:else}<div class="empty"><h2>Choose a séance</h2><p>Inspect its retained conversation without changing the conversation currently open in Bridge.</p><p>Topics, questions and selected material begin with your own source selections.</p></div>{/if}
    </section>
  </div>
</div>

<style>
  .seances-workspace { color: var(--color-parchment); min-height: 100%; padding: 1.5rem; }
  .detail-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
  h2 { font: 600 var(--text-lg)/1.4 var(--font-body); color: var(--color-bone); }
  h3 { color: var(--color-bone); font-size: var(--text-base); }
  p { line-height: 1.6; margin: .5rem 0; }
  .muted, .read-status, time { color: var(--color-ash); font-size: var(--text-xs); }
  .workspace-body { display: grid; grid-template-columns: minmax(12rem, 15rem) minmax(0, 1fr); gap: 1.5rem; margin-top: 1.5rem; }
  .catalogue { border-right: 1px solid var(--color-engraving); padding-right: 1rem; min-width: 0; }
  .catalogue h2 { margin-top: 1.5rem; font-size: var(--text-sm); }
  .catalogue-row { display: flex; align-items: center; gap: .25rem; margin-top: .3rem; }
  .catalogue-row a { flex: 1; min-width: 0; display: block; padding: .65rem; color: var(--color-parchment); text-decoration: none; overflow-wrap: anywhere; border-radius: var(--radius-rune); font-size: var(--text-sm); }
  .catalogue-row a[aria-current="page"] { color: var(--color-bone); background: var(--color-obsidian-2); box-shadow: inset 2px 0 var(--color-accent); }
  small { display: block; margin-top: .35rem; color: var(--color-ash); font-size: var(--text-2xs); }
  .new-seance { padding: .65rem .8rem; color: var(--color-bone); border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); font-size: var(--text-sm); }
  .detail { min-width: 0; }
  .identity { font-family: var(--font-mono); font-size: var(--text-2xs); color: var(--color-ash); overflow-wrap: anywhere; }
  .read-status { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
  .view-switch { display: flex; gap: .5rem; margin: 1rem 0; padding-bottom: .75rem; border-bottom: 1px solid var(--color-engraving); }
  button, select, input, textarea { font: inherit; font-size: var(--text-sm); color: var(--color-parchment); background: var(--color-obsidian); border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); }
  button { cursor: pointer; min-height: 2.5rem; padding: .45rem .75rem; }
  button:hover, a:hover { color: var(--color-bone); border-color: var(--color-rune); }
  button[aria-pressed="true"] { color: var(--color-bone); border-color: var(--color-accent); }
  button.primary { color: var(--color-void); background: var(--color-bone); border-color: var(--color-bone); }
  button:disabled { opacity: .5; cursor: default; }
  label { display: block; font-size: var(--text-xs); color: var(--color-ash); }
  input, textarea { display: block; width: 100%; padding: .65rem; margin-top: .4rem; box-sizing: border-box; }
  select { margin-left: .5rem; padding: .5rem; }
  textarea { resize: vertical; }
  .retained-turn, .material-card { padding: 1.25rem 0; border-bottom: 1px solid var(--color-engraving); }
  .retained-turn header { display: flex; flex-wrap: wrap; align-items: baseline; gap: .75rem; font-size: var(--text-xs); }
  .retained-turn strong { color: var(--color-bone); }
  .user-turn { padding-inline: 1rem; background: var(--color-obsidian); border-radius: var(--radius-glyph); }
  .quotation, blockquote { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.75; font-size: var(--text-sm); }
  blockquote { margin: 1rem 0; padding-left: 1rem; border-left: 2px solid var(--color-accent); }
  footer, .actions { display: flex; align-items: center; flex-wrap: wrap; gap: .75rem; margin-top: .75rem; }
  footer a { font-size: var(--text-xs); color: var(--color-rune); }
  .material-heading { font-size: var(--text-xs); color: var(--color-ash); }
  .empty { max-width: 40rem; padding: 3rem 1rem; color: var(--color-ash); }
  .notice { font-size: var(--text-xs); padding: .65rem .8rem; background: var(--color-obsidian); border-left: 2px solid var(--color-rune); }
  :focus-visible, article:focus { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @container work-area (max-width: 48rem) { .workspace-body { grid-template-columns: 1fr; } .catalogue { border-right: 0; border-bottom: 1px solid var(--color-engraving); padding: 0 0 1rem; } .seances-workspace { padding: 1rem; } }
</style>
