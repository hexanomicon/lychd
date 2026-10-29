<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { getOrbRun } from "$lib/api/client";
  import type { OrbRunPage, OrbRunSnapshot } from "$lib/api/models";
  import { getOrbCatalogue, listenToOrb, orbSnapshotSchema, type OrbConnection } from "$lib/orb/live";
  import { matchesOrbPattern, mergeOrbEvidence, mergeOrbGaps, projectOrbField, type OrbDetailLevel, type OrbFieldLens } from "$lib/graph/orb";
  import GraphCanvas from "./graph/GraphCanvas.svelte";
  import AnimatorRail from "./AnimatorRail.svelte";

  type Run = OrbRunSnapshot["run"];
  type Lens = OrbFieldLens & { readonly connection: OrbConnection; readonly note: string; readonly trimmed: boolean };
  let runs = $state.raw<Run[]>([]);
  let catalogue = $state.raw<OrbRunPage | null>(null);
  let lenses = $state.raw<ReadonlyMap<string, Lens>>(new Map());
  let loadingIds = $state.raw<ReadonlySet<string>>(new Set());
  let loading = $state(true);
  let initialReady = $state(false);
  let error = $state("");
  let notice = $state("");
  let level = $state<OrbDetailLevel>("stations");
  let zoomDriven = $state(true);
  let selectedRun = $state<string | null>(null);
  let selectedEvent = $state<string | null>(null);
  let selectedNode = $state<string | null>(null);
  let following = $state(true);
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let destroyed = false;
  let catalogueVersion = 0;
  let catalogueController: AbortController | undefined;
  const controllers = new Map<string, AbortController>();
  const stops = new Map<string, () => void>();
  const generations = new Map<string, number>();
  const recovered = new Set<string>();
  let field = $derived(projectOrbField(runs, lenses, level));
  let activeLens = $derived(selectedRun ? lenses.get(selectedRun) : undefined);
  let activeRun = $derived(activeLens?.snapshot.run ?? runs.find((run) => run.run_id === selectedRun));
  let record = $derived(activeLens?.snapshot.evidence.find((item) => item.event_id === selectedEvent));

  onMount(() => {
    void loadCatalogue();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && !loading) void loadCatalogue(false, true);
    }, 5000);
    return () => window.clearInterval(timer);
  });
  onDestroy(() => {
    destroyed = true;
    catalogueVersion++;
    catalogueController?.abort();
    for (const controller of controllers.values()) controller.abort();
    for (const stop of stops.values()) stop();
    stops.clear(); controllers.clear();
  });

  function updateLens(id: string, change: (current: Lens) => Lens) {
    const current = lenses.get(id);
    if (!current) return;
    lenses = new Map(lenses).set(id, change(current));
  }

  async function loadCatalogue(more = false, automatic = false) {
    const cursor = more ? catalogue?.next_cursor : undefined;
    if (more && !cursor) return;
    const version = ++catalogueVersion;
    catalogueController?.abort();
    const controller = new AbortController();
    catalogueController = controller;
    loading = true; error = "";
    try {
      const next = await getOrbCatalogue(cursor ?? undefined, controller.signal);
      if (destroyed || version !== catalogueVersion) return;
      const overlaps = next.runs.some((run) => runs.some((loaded) => loaded.run_id === run.run_id));
      catalogue = automatic && catalogue && overlaps ? { ...next, next_cursor: catalogue.next_cursor } : next;
      const retained = more || automatic ? runs : runs.filter((run) => lenses.has(run.run_id) || loadingIds.has(run.run_id));
      const merged = new Map(next.runs.map((run) => [run.run_id, run]));
      for (const run of retained) if (!merged.has(run.run_id)) merged.set(run.run_id, run);
      runs = [...merged.values()];
      if (!selectedRun || !runs.some((run) => run.run_id === selectedRun)) selectedRun = runs[0]?.run_id ?? null;
      if (!initialReady && !lenses.size && !loadingIds.size) {
        const ordered = runs.toSorted((a, b) => Number(["done", "failed", "cancelled"].includes(a.status)) - Number(["done", "failed", "cancelled"].includes(b.status)));
        await Promise.all(ordered.slice(0, 3).map((run) => openLens(run.run_id)));
      }
    } catch (cause) {
      if (!destroyed && version === catalogueVersion) error = cause instanceof Error ? cause.message : "The Run catalogue could not be read.";
    } finally {
      if (!destroyed && version === catalogueVersion) { loading = false; initialReady = true; }
    }
  }

  function closeLens(id: string) {
    generations.set(id, (generations.get(id) ?? 0) + 1);
    stops.get(id)?.(); stops.delete(id);
    controllers.get(id)?.abort(); controllers.delete(id);
    lenses = new Map([...lenses].filter(([key]) => key !== id));
    loadingIds = new Set([...loadingIds].filter((key) => key !== id));
    recovered.delete(id);
  }

  async function openLens(id: string, recovery = false) {
    if (destroyed || loadingIds.has(id)) return;
    if (!lenses.has(id) && lenses.size + loadingIds.size >= 3) {
      notice = "Three live Run lenses are open. Close one lens to unfold another; all loaded Run groups remain visible.";
      return;
    }
    notice = "";
    const generation = (generations.get(id) ?? 0) + 1;
    generations.set(id, generation);
    stops.get(id)?.(); stops.delete(id);
    updateLens(id, (lens) => ({ ...lens, connection: "closed", note: "Refreshing the retained account." }));
    controllers.get(id)?.abort();
    const controller = new AbortController(); controllers.set(id, controller);
    loadingIds = new Set([...loadingIds, id]);
    if (!recovery) recovered.delete(id);
    const current = () => !destroyed && generations.get(id) === generation;
    try {
      const snapshot = orbSnapshotSchema.parse(await getOrbRun(id, { limit: 100, signal: controller.signal }));
      if (!current()) return;
      if (snapshot.run.run_id !== id) throw new Error("The Orb returned another Run's evidence.");
      const pattern = snapshot.workflow && matchesOrbPattern(snapshot, snapshot.workflow) ? snapshot.workflow : null;
      lenses = new Map(lenses).set(id, { snapshot, pattern, connection: "connecting", note: "", trimmed: snapshot.has_more });
      if (typeof EventSource !== "undefined") {
        const stop = listenToOrb(id, snapshot.ledger_head_seq, {
          onConnection: (connection) => { if (current()) updateLens(id, (lens) => ({ ...lens, connection })); },
          onFault: (note) => { if (current()) updateLens(id, (lens) => ({ ...lens, note })); },
          onReset: () => {
            if (!current()) return;
            if (recovered.has(id)) { updateLens(id, (lens) => ({ ...lens, note: "Feed reset again. Refresh this lens to retry." })); return; }
            recovered.add(id);
            void openLens(id, true);
          },
          onFrame: (frame) => {
            if (!current()) return;
            updateLens(id, (lens) => {
              const all = mergeOrbEvidence(lens.snapshot.evidence, frame.snapshot.evidence);
              const gaps = mergeOrbGaps(lens.snapshot.gaps, frame.snapshot.gaps).slice(-100);
              return { ...lens, snapshot: { ...frame.snapshot, evidence: all.slice(-100), gaps },
                pattern: frame.snapshot.workflow && matchesOrbPattern(frame.snapshot, frame.snapshot.workflow) ? frame.snapshot.workflow : null,
                trimmed: lens.trimmed || all.length > 100 };
            });
            if (following && selectedRun === id && frame.snapshot.evidence.length) {
              const last = frame.snapshot.evidence.at(-1)!;
              const candidate = [...field.selections].find(([, value]) => value.runId === id && value.eventId === last.event_id);
              focusId = candidate?.[0] ?? `run:${id}`; focusRevision++;
            }
          }
        });
        if (current()) stops.set(id, stop); else stop();
      }
    } catch (cause) {
      if (current()) {
        const message = cause instanceof Error ? cause.message : "The Run lens could not be read.";
        if (lenses.has(id)) updateLens(id, (lens) => ({ ...lens, connection: "closed", note: message }));
        else notice = message;
      }
    } finally {
      if (current()) { loadingIds = new Set([...loadingIds].filter((key) => key !== id)); controllers.delete(id); }
    }
  }

  function selectNode(id: string) {
    const selection = field.selections.get(id);
    if (!selection) return;
    selectedNode = id; selectedRun = selection.runId; selectedEvent = selection.eventId ?? null; following = false;
    if (id === `run:${selection.runId}`) {
      if (level === "runs") { level = "stations"; zoomDriven = false; }
      if (!lenses.has(selection.runId)) void openLens(selection.runId);
    }
  }
  function selectRun(id: string) {
    selectedRun = id; selectedNode = `run:${id}`; selectedEvent = null;
    focusId = selectedNode; focusRevision++;
  }
  function selectRecord(id: string) {
    selectedEvent = id; following = false;
    const options = [...field.selections].filter(([, selection]) => selection.runId === selectedRun && selection.eventId === id);
    selectedNode = options.at(-1)?.[0] ?? (selectedRun ? `run:${selectedRun}` : null);
    focusId = selectedNode; focusRevision++;
  }
  function chooseLevel(value: OrbDetailLevel) { level = value; zoomDriven = false; }
  function zoomDetail(zoom: number) {
    if (!zoomDriven) return;
    if (zoom < 0.55) level = "runs";
    else if (zoom > 2.2) level = "records";
    else if ((level === "stations" && zoom > 1.35) || (level === "records" && zoom < 1.85)) level = "occurrences";
    else if ((level === "runs" && zoom > 0.85) || (level === "occurrences" && zoom < 1.1)) level = "stations";
  }
</script>

<svelte:head><title>Orb — workflow field</title></svelte:head>
<svelte:document onvisibilitychange={() => { if (document.visibilityState === "visible" && !loading) void loadCatalogue(false, true); }} />
<div class="orb-field">
  <header class="field-header">
    <div><p class="eyebrow">Parallel workflows · retained evidence</p><h1>Orb</h1><p>{runs.length} loaded Run groups · {lenses.size} live lenses · {catalogue?.capture.replaceAll("_", " ") ?? "reading catalogue"}</p></div>
    <button type="button" disabled={loading} onclick={() => loadCatalogue()}>{loading ? "Reading…" : "Refresh Runs"}</button>
  </header>
  {#if error}<p class="field-fault" role="alert">{error}</p>{/if}
  {#if notice}<p class="field-notice" role="status">{notice}</p>{/if}
  <div class="field-layout">
    <section class="canvas-area" aria-label="Parallel Run graph">
      <div class="field-tools">
        <div role="group" aria-label="Graph detail">
          <button type="button" aria-pressed={level === "runs"} onclick={() => chooseLevel("runs")}>Run groups</button>
          <button type="button" aria-pressed={level === "stations"} onclick={() => chooseLevel("stations")}>Stations</button>
          <button type="button" aria-pressed={level === "occurrences"} onclick={() => chooseLevel("occurrences")}>Occurrences</button>
          <button type="button" aria-pressed={level === "records"} onclick={() => chooseLevel("records")}>Records</button>
        </div>
        <button type="button" aria-pressed={zoomDriven} onclick={() => zoomDriven = !zoomDriven}>Zoom changes detail</button>
        <button type="button" aria-pressed={following} onclick={() => following = !following}>{following ? "Pause following" : "Follow selected Run"}</button>
      </div>
      {#if runs.length && initialReady}
        <GraphCanvas projection={field.projection} selectedId={selectedNode} onselect={selectNode} label="Parallel Run workflow field" onzoom={zoomDetail} onviewportinteraction={() => following = false} {focusId} {focusRevision} />
      {:else}<div class="field-empty"><h2>{!initialReady ? "Reading the Run field…" : error ? "Run field unavailable" : "No retained Runs in this account"}</h2><p>Open a conversation to create work, then inspect its recorded workflow here.</p><a href={resolve("/bridge")}>Open Bridge →</a></div>{/if}
      <p class="field-legend">Permission edges come from exact declared scores. Membership edges connect supplied Run records to their subjects. Neither claims an observed traversal.</p>
      <p class="field-boundary">Zoom unfolds Run → station/subject → supplied occurrence → loaded records, within each 100-record lens. Deeper subworkflow structure is unavailable until its owner supplies it. Folding changes no evidence.</p>
    </section>
    <aside class="field-feed" aria-labelledby="live-evidence-title">
      <header><h2 id="live-evidence-title">Live evidence</h2><p>Selected Run · bounded ledger feed</p></header>
      {#if activeRun}
        <p class="run-name">{activeRun.workflow_name}</p><code class="run-identity">{activeRun.run_id}</code>
        <dl class="feed-status"><dt>Recorded status</dt><dd>{activeRun.status}</dd><dt>Connection</dt><dd>{activeLens?.connection ?? "lens closed"}</dd></dl>
        <a class="detail-link" href={resolve(`/orb/${encodeURIComponent(activeRun.run_id)}`)}>Open exact Run and history →</a>
        {#if activeLens}
          <AnimatorRail evidence={activeLens.snapshot.evidence} onselect={(seq) => { const event = activeLens?.snapshot.evidence.find((item) => item.seq === seq); if (event) selectRecord(event.event_id); }} />
          {#if activeLens.note}<p class="field-notice" role="status">{activeLens.note}</p>{/if}
          <div class="lens-actions"><button type="button" disabled={loadingIds.has(activeRun.run_id)} onclick={() => openLens(activeRun!.run_id)}>Refresh lens</button><button type="button" onclick={() => closeLens(activeRun!.run_id)}>Close live lens</button></div>
          <p class="feed-boundary">{activeLens.snapshot.evidence.length} loaded records · {activeLens.snapshot.gaps.length} reported gaps. {activeLens.trimmed || activeLens.snapshot.has_more ? "More retained history exists outside this lens." : "Capture remains bounded; omissions may apply."}</p>
          {#if activeLens.snapshot.known_omissions.length}<details><summary>Capture omissions</summary><ul>{#each activeLens.snapshot.known_omissions as omission (omission)}<li>{omission}</li>{/each}</ul></details>{/if}
          <ol class="live-records" aria-label="Selected Run live records">
            {#each activeLens.snapshot.evidence.toReversed() as event (event.event_id)}
              <li><button type="button" aria-pressed={selectedEvent === event.event_id} onclick={() => selectRecord(event.event_id)}><span class="record-seq">#{event.seq}</span><span><strong>{event.summary}</strong><small>{event.subject_key ?? "Unknown subject"}</small><time datetime={event.occurred_at}>{new Date(event.occurred_at).toLocaleTimeString()}</time></span></button></li>
            {:else}<li class="feed-empty">No structural records are supplied yet.</li>{/each}
          </ol>
          {#if record}<section class="record-detail" aria-label="Selected live record"><h3>{record.summary}</h3><dl><dt>Event</dt><dd><code>{record.event_id}</code></dd><dt>Sequence</dt><dd>#{record.seq}</dd><dt>Subject</dt><dd>{record.subject_key ?? "Not supplied"}</dd><dt>Occurrence</dt><dd>{record.occurrence_id ?? "Not supplied"}</dd><dt>Phase</dt><dd>{record.phase ?? "Not supplied"}</dd></dl><a href={resolve(`/orb/${encodeURIComponent(activeRun.run_id)}?event=${encodeURIComponent(record.event_id)}`)}>Inspect this exact record →</a></section>
          {:else if selectedEvent}<p class="field-notice">The selected record is outside this lens window. Open the exact Run history to inspect it.</p>{/if}
        {:else}<button type="button" disabled={loadingIds.has(activeRun.run_id)} onclick={() => openLens(activeRun!.run_id)}>{loadingIds.has(activeRun.run_id) ? "Opening lens…" : "Open live lens"}</button>{/if}
      {:else}<p>Select a Run group to inspect its account.</p>{/if}
    </aside>
  </div>
  <details class="run-list" open><summary>Semantic Run list · {runs.length} loaded</summary><p>The catalogue refreshes every 5 seconds while visible. It is paged, not a complete universal history. At most three live lenses remain open at once.</p>
    <ul>{#each runs as run (run.run_id)}<li><button type="button" aria-pressed={selectedRun === run.run_id} onclick={() => selectRun(run.run_id)}><strong>{run.workflow_name}</strong><span>{lenses.get(run.run_id)?.snapshot.run.status ?? run.status}</span><code>{run.run_id}</code></button><button type="button" disabled={loadingIds.has(run.run_id)} onclick={() => lenses.has(run.run_id) ? closeLens(run.run_id) : openLens(run.run_id)}>{lenses.has(run.run_id) ? "Close lens" : loadingIds.has(run.run_id) ? "Opening…" : "Unfold Run"}</button><a href={resolve(`/orb/${encodeURIComponent(run.run_id)}`)}>History →</a></li>{/each}</ul>
    {#if catalogue?.next_cursor}<button type="button" disabled={loading} onclick={() => loadCatalogue(true)}>Load more retained Runs</button>{/if}
  </details>
</div>

<style>
  .orb-field { padding: clamp(1rem, 2vw, 2rem); color: var(--color-bone); min-width: 0; }
  .field-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; }
  h1 { font: 600 clamp(1.7rem, 3vw, 2.2rem)/1.2 var(--font-body); margin: .3rem 0; }
  .eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: var(--text-xs); }
  p, small, dt { color: var(--color-parchment); line-height: 1.55; }
  .field-header p, .field-legend, .field-boundary, .feed-boundary, .field-feed p, .run-list > p { font-size: var(--text-sm); }
  button { background: var(--color-obsidian); border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); padding: .6rem .8rem; min-height: 2.75rem; color: var(--color-bone); font: inherit; cursor: pointer; }
  button[aria-pressed="true"] { border-color: var(--color-rune); color: var(--color-rune); box-shadow: inset 0 -2px var(--color-rune); }
  button:disabled { opacity: .55; cursor: wait; }
  button:focus-visible, a:focus-visible, summary:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  a { color: var(--color-rune); text-decoration: underline; text-underline-offset: .2em; }
  .field-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem); gap: 1.2rem; align-items: start; }
  .canvas-area, .field-feed { min-width: 0; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); overflow: hidden; }
  .field-tools { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; padding: .8rem; border-bottom: 1px solid var(--color-engraving); }
  .field-tools > div { display: flex; flex-wrap: wrap; gap: .3rem; }
  .field-tools button { font-size: var(--text-sm); }
  .field-legend, .field-boundary { padding: .6rem 1rem; }
  .field-boundary { border-top: 1px solid var(--color-engraving); }
  .field-feed { padding: 1rem; }
  .field-feed h2 { font: 500 1.3rem/1.4 var(--font-body); }
  .field-feed header { border-bottom: 1px solid var(--color-engraving); padding-bottom: .8rem; margin-bottom: 1rem; }
  .run-name { font-weight: 600; }
  .run-identity, .record-detail code { overflow-wrap: anywhere; display: block; font-size: var(--text-xs); }
  .feed-status, .record-detail dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .5rem .75rem; margin: .9rem 0; font-size: var(--text-sm); }
  dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
  .detail-link { display: inline-flex; padding-block: .4rem; font-size: var(--text-sm); }
  .lens-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin: .8rem 0; font-size: var(--text-sm); }
  .live-records { list-style: none; padding: 0; margin: 1rem 0; max-height: 30rem; overflow: auto; scrollbar-gutter: stable; }
  .live-records button { width: 100%; text-align: left; display: grid; grid-template-columns: 2.5rem minmax(0, 1fr); gap: .5rem; border-radius: 0; border-inline: 0; border-top: 0; background: transparent; }
  .live-records strong { display: block; font-size: var(--text-sm); font-weight: 500; overflow-wrap: anywhere; }
  .live-records small, .live-records time { display: block; color: var(--color-parchment); font-size: var(--text-xs); overflow-wrap: anywhere; }
  .record-seq { color: var(--color-parchment); font: var(--text-xs)/1.5 var(--font-glyph); }
  .record-detail { border-top: 1px solid var(--color-engraving); padding-top: 1rem; }
  .record-detail h3 { font-size: var(--text-base); overflow-wrap: anywhere; }
  .record-detail a { font-size: var(--text-sm); }
  .field-notice, .field-fault { padding: .8rem; margin-block: .7rem; border-left: 2px solid var(--color-rune); overflow-wrap: anywhere; }
  .field-fault { border-color: var(--color-ember); }
  .field-empty { min-height: 25rem; padding: 3rem 1.5rem; display: flex; flex-direction: column; justify-content: center; gap: 1rem; }
  .run-list { margin-top: 1.2rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); padding: 1rem; }
  summary { cursor: pointer; min-height: 2.75rem; padding-block: .5rem; }
  .run-list ul { list-style: none; padding: 0; }
  .run-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: .8rem; border-top: 1px solid var(--color-engraving); padding: .6rem 0; }
  .run-list li > button:first-child { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .3rem .7rem; text-align: left; }
  .run-list code { grid-column: 1 / -1; font-size: var(--text-xs); overflow-wrap: anywhere; color: var(--color-parchment); }
  .run-list li span, .run-list li a { font-size: var(--text-sm); }
  @media (max-width: 70rem) { .field-layout { grid-template-columns: minmax(0, 1fr); } .field-feed { max-width: none; } }
  @media (max-width: 40rem) { .field-header { align-items: flex-start; flex-direction: column; } .run-list li { grid-template-columns: minmax(0, 1fr) auto; } .run-list li > button:first-child { grid-column: 1 / -1; } .run-list li a { justify-self: end; } }
</style>
