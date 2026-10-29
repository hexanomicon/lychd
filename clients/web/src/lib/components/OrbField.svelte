<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  import { resolve } from "$app/paths";
  import { getOrbRun } from "$lib/api/client";
  import type { OrbRunPage, OrbRunSnapshot } from "$lib/api/models";
  import { getOrbCatalogue, listenToOrb, orbSnapshotSchema, type OrbConnection } from "$lib/orb/live";
  import { matchesOrbPattern, mergeOrbEvidence, mergeOrbGaps, projectOrbField, type OrbDetailLevel, type OrbFieldLens } from "$lib/graph/orb";
  import GraphCanvas from "./graph/GraphCanvas.svelte";
  import AnimatorRail from "./AnimatorRail.svelte";
  import OrbTimeline from "./OrbTimeline.svelte";
  import { appendFieldFrame, pruneFieldRun, trimFieldFrames, type FieldFrame } from "$lib/orb/field-history";

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
  let following = $state(false);
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let history = $state.raw<readonly FieldFrame[]>([]);
  let pausedFrame = $state.raw<FieldFrame | null>(null);
  let historyWindow = $state(90);
  let query = $state("");
  let statusFilter = $state("all");
  let inspectorOpen = $state(false);
  let runsOpen = $state(false);
  let optionsOpen = $state(false);
  let inspectorOpener: HTMLElement | undefined;
  let accessBlocked = false;
  let destroyed = false;
  let catalogueVersion = 0;
  let catalogueController: AbortController | undefined;
  const controllers = new Map<string, AbortController>();
  const stops = new Map<string, () => void>();
  const generations = new Map<string, number>();
  const metadataVersions = new Map<string, number>();
  const recovered = new Set<string>();
  let viewedRuns = $derived(pausedFrame?.runs ?? runs);
  let viewedLenses = $derived(pausedFrame?.lenses ?? lenses);
  let filteredRuns = $derived(viewedRuns.filter((run) => {
    const matches = `${run.workflow_name} ${run.run_id}`.toLowerCase().includes(query.trim().toLowerCase());
    return matches && (statusFilter === "all" || (statusFilter === "active" ? !["done", "failed", "cancelled"].includes(run.status) : statusFilter === "waiting" ? ["awaiting_hardware", "awaiting_consent", "awaiting_delegate", "awaiting_peer"].includes(run.status) : run.status === statusFilter));
  }));
  let field = $derived(projectOrbField(filteredRuns, viewedLenses, level));
  let activeLens = $derived(selectedRun ? viewedLenses.get(selectedRun) : undefined);
  let currentLens = $derived(selectedRun ? lenses.get(selectedRun) : undefined);
  let activeRun = $derived(runs.find((run) => run.run_id === selectedRun) ?? currentLens?.snapshot.run);
  let viewedRun = $derived(activeLens?.snapshot.run ?? viewedRuns.find((run) => run.run_id === selectedRun));
  let connectionLabel = $derived(lenses.size ? [...new Set([...lenses.values()].map((lens) => lens.connection))].join(" · ") : "No live lenses");
  let record = $derived(activeLens?.snapshot.evidence.find((item) => item.event_id === selectedEvent));

  onMount(() => {
    void loadCatalogue();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && !loading && !accessBlocked) void loadCatalogue(false, true);
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

  function captureField() {
    if (!initialReady) return;
    history = appendFieldFrame(history, runs, lenses, Date.now(), historyWindow);
  }
  function pauseField() {
    captureField();
    pausedFrame = history.at(-1) ?? null;
    following = false;
  }
  function seekField(id: number) {
    const frame = history.find((candidate) => candidate.id === id);
    if (!frame) return;
    pausedFrame = frame; following = false;
  }
  function liveField() { pausedFrame = null; }
  function resizeHistory(seconds: number) {
    historyWindow = seconds;
    history = trimFieldFrames(history, seconds);
  }
  function clearHistory() { history = []; pausedFrame = null; captureField(); }
  function authorityRefused(cause: unknown): boolean {
    return typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403);
  }
  function clearProtectedField() {
    accessBlocked = true;
    catalogueVersion++; catalogueController?.abort();
    loading = false; initialReady = true;
    for (const id of new Set([...lenses.keys(), ...loadingIds])) closeLens(id);
    runs = []; catalogue = null; history = []; pausedFrame = null; metadataVersions.clear();
    selectedRun = null; selectedNode = null; selectedEvent = null;
  }
  function clearProtectedRun(id: string) {
    closeLens(id);
    history = pruneFieldRun(history, id);
    if (pausedFrame) pausedFrame = pruneFieldRun([pausedFrame], id)[0] ?? null;
    if (selectedRun === id) { selectedNode = null; selectedEvent = null; }
  }
  function updateLens(id: string, change: (current: Lens) => Lens) {
    const current = lenses.get(id);
    if (!current) return;
    lenses = new Map(lenses).set(id, change(current));
  }
  function observeRun(run: Run, expectedVersion?: number) {
    const version = metadataVersions.get(run.run_id) ?? 0;
    if (expectedVersion !== undefined && expectedVersion !== version) return;
    metadataVersions.set(run.run_id, version + 1);
    runs = runs.map((current) => current.run_id === run.run_id ? run : current);
  }

  async function loadCatalogue(more = false, automatic = false) {
    if (automatic && accessBlocked) return;
    if (!automatic) accessBlocked = false;
    const cursor = more ? catalogue?.next_cursor : undefined;
    if (more && !cursor) return;
    const version = ++catalogueVersion;
    catalogueController?.abort();
    const controller = new AbortController();
    const observedVersions = new Map(metadataVersions);
    catalogueController = controller;
    loading = true; error = "";
    try {
      const next = await getOrbCatalogue(cursor ?? undefined, controller.signal);
      if (destroyed || version !== catalogueVersion) return;
      const overlaps = next.runs.some((run) => runs.some((loaded) => loaded.run_id === run.run_id));
      catalogue = automatic && catalogue && overlaps ? { ...next, next_cursor: catalogue.next_cursor } : next;
      const retained = more || automatic ? runs : runs.filter((run) => lenses.has(run.run_id) || loadingIds.has(run.run_id));
      const currentRuns = new Map(runs.map((run) => [run.run_id, run]));
      const merged = new Map(next.runs.map((run) => {
        const version = metadataVersions.get(run.run_id) ?? 0;
        const current = currentRuns.get(run.run_id);
        if (current && version !== (observedVersions.get(run.run_id) ?? 0)) return [run.run_id, current] as const;
        metadataVersions.set(run.run_id, version + 1);
        return [run.run_id, run] as const;
      }));
      for (const run of retained) if (!merged.has(run.run_id)) merged.set(run.run_id, run);
      runs = [...merged.values()];
      captureField();
      if (!selectedRun || !runs.some((run) => run.run_id === selectedRun)) selectedRun = runs[0]?.run_id ?? null;
      if (!initialReady && !lenses.size && !loadingIds.size) {
        const ordered = runs.toSorted((a, b) => Number(["done", "failed", "cancelled"].includes(a.status)) - Number(["done", "failed", "cancelled"].includes(b.status)));
        await Promise.all(ordered.slice(0, 3).map((run) => openLens(run.run_id)));
      }
    } catch (cause) {
      if (!destroyed && version === catalogueVersion) {
        if (authorityRefused(cause)) clearProtectedField();
        error = cause instanceof Error ? cause.message : "The Run catalogue could not be read.";
      }
    } finally {
      if (!destroyed && version === catalogueVersion) { loading = false; initialReady = true; captureField(); }
    }
  }

  function closeLens(id: string) {
    generations.set(id, (generations.get(id) ?? 0) + 1);
    stops.get(id)?.(); stops.delete(id);
    controllers.get(id)?.abort(); controllers.delete(id);
    lenses = new Map([...lenses].filter(([key]) => key !== id));
    loadingIds = new Set([...loadingIds].filter((key) => key !== id));
    recovered.delete(id);
    captureField();
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
    const metadataVersion = metadataVersions.get(id) ?? 0;
    loadingIds = new Set([...loadingIds, id]);
    if (!recovery) recovered.delete(id);
    const current = () => !destroyed && generations.get(id) === generation;
    try {
      const snapshot = orbSnapshotSchema.parse(await getOrbRun(id, { limit: 100, signal: controller.signal }));
      if (!current()) return;
      if (snapshot.run.run_id !== id) throw new Error("The Orb returned another Run's evidence.");
      const pattern = snapshot.workflow && matchesOrbPattern(snapshot, snapshot.workflow) ? snapshot.workflow : null;
      lenses = new Map(lenses).set(id, { snapshot, pattern, connection: "connecting", note: "", trimmed: snapshot.has_more });
      observeRun(snapshot.run, metadataVersion);
      captureField();
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
            observeRun(frame.snapshot.run);
            captureField();
            if (!pausedFrame && following && selectedRun === id && frame.snapshot.evidence.length) {
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
        if (authorityRefused(cause)) {
          if (typeof cause === "object" && cause !== null && "status" in cause && cause.status === 401) clearProtectedField();
          else clearProtectedRun(id);
          notice = message;
        } else if (lenses.has(id)) updateLens(id, (lens) => ({ ...lens, connection: "closed", note: message }));
        else notice = message;
      }
    } finally {
      if (current()) { loadingIds = new Set([...loadingIds].filter((key) => key !== id)); controllers.delete(id); }
    }
  }

  function selectNode(id: string, opener?: HTMLElement) {
    const selection = field.selections.get(id);
    if (!selection) return;
    selectedNode = id; selectedRun = selection.runId; selectedEvent = selection.eventId ?? null; following = false; inspectorOpen = true;
    inspectorOpener = opener;
    const node = field.projection.nodes.find((candidate) => candidate.id === id);
    if (node?.members?.length && node.kind !== "run") {
      if (level === "stations") level = "occurrences";
      else if (level === "occurrences") level = "records";
      zoomDriven = false;
    }
    if (id === `run:${selection.runId}`) {
      if (level === "runs") { level = "stations"; zoomDriven = false; }
      if (!pausedFrame && !lenses.has(selection.runId)) void openLens(selection.runId);
    }
  }
  function selectRun(id: string) {
    selectedRun = id; selectedNode = `run:${id}`; selectedEvent = null; inspectorOpen = true; runsOpen = false;
    focusId = selectedNode; focusRevision++;
  }
  function selectRecord(id: string) {
    selectedEvent = id; following = false; inspectorOpen = true;
    const options = [...field.selections].filter(([, selection]) => selection.runId === selectedRun && selection.eventId === id);
    selectedNode = options.at(-1)?.[0] ?? (selectedRun ? `run:${selectedRun}` : null);
    focusId = selectedNode; focusRevision++;
  }
  function chooseLevel(value: OrbDetailLevel) { level = value; zoomDriven = false; }
  function toggleFollowing() {
    following = !following;
    if (following && selectedRun) {
      pausedFrame = null;
      focusId = `run:${selectedRun}`; focusRevision++;
    }
  }
  function closeEvidence() {
    inspectorOpen = false;
    void tick().then(() => {
      const target = inspectorOpener?.isConnected ? inspectorOpener : document.getElementById("orb-evidence-toggle");
      target?.focus({ preventScroll: true });
    });
  }
  function dismissPanels(event: KeyboardEvent) {
    if (event.key !== "Escape" || event.defaultPrevented || !(event.target instanceof Element) || !event.target.closest(".orb-field")) return;
    const details = event.target.closest<HTMLDetailsElement>("details[open]");
    if (details?.classList.contains("run-list")) { runsOpen = false; details.querySelector("summary")?.focus(); }
    else if (details?.classList.contains("view-options")) { optionsOpen = false; details.querySelector("summary")?.focus(); }
    else if (inspectorOpen && event.target.closest("#orb-evidence")) closeEvidence();
    else return;
    event.preventDefault();
  }
  function zoomDetail(zoom: number) {
    if (!zoomDriven) return;
    if (zoom < 0.42) level = "runs";
    else if (zoom > 1.8) level = "records";
    else if ((level === "stations" && zoom > 1.05) || (level === "records" && zoom < 1.5)) level = "occurrences";
    else if ((level === "runs" && zoom > 0.58) || (level === "occurrences" && zoom < 0.88)) level = "stations";
  }
</script>

<svelte:head><title>Orb — workflow field</title></svelte:head>
<svelte:document onkeydown={dismissPanels} onvisibilitychange={() => { if (document.visibilityState === "visible" && !loading) void loadCatalogue(false, true); }} />
<div class="orb-field">
  <header class="field-header">
    <div class="field-title"><h1>Orb</h1><span>{filteredRuns.length}/{viewedRuns.length} Run groups</span></div>
    <label class="search"><span class="sr-only">Filter Runs</span><input type="search" placeholder="Find workflow or Run…" bind:value={query} /></label>
    <label><span class="sr-only">Run status filter</span><select aria-label="Run status filter" bind:value={statusFilter}><option value="all">All states</option><option value="active">Active</option><option value="running">Running</option><option value="waiting">Waiting</option><option value="done">Done</option><option value="failed">Failed</option><option value="cancelled">Cancelled</option></select></label>
    <details class="run-list" bind:open={runsOpen}>
      <summary>Runs <span>{viewedRuns.length}</span></summary>
      <div class="run-list-panel" id="orb-run-list">
        <h2>Semantic Run list · {viewedRuns.length} loaded</h2>
        <p>All loaded groups remain on the field. Up to three evidence lenses can follow live at once.</p>
        <ul>{#each filteredRuns as run (run.run_id)}<li><button type="button" aria-pressed={selectedRun === run.run_id} onclick={() => selectRun(run.run_id)}><strong>{run.workflow_name}</strong><span>{run.status}</span><code>{run.run_id}</code></button><button type="button" disabled={loadingIds.has(run.run_id)} onclick={() => lenses.has(run.run_id) ? closeLens(run.run_id) : openLens(run.run_id)}>{lenses.has(run.run_id) ? "Close lens" : loadingIds.has(run.run_id) ? "Opening…" : "Unfold Run"}</button><a href={resolve(`/orb/${encodeURIComponent(run.run_id)}`)}>History →</a></li>{/each}</ul>
        {#if catalogue?.next_cursor}<button type="button" disabled={loading} onclick={() => loadCatalogue(true)}>Load more retained Runs</button>{/if}
        <p class="coverage">Paged catalogue · refreshes every 5 seconds while visible · {catalogue?.capture.replaceAll("_", " ") ?? "reading"}</p>
      </div>
    </details>
    <details class="view-options" bind:open={optionsOpen}>
      <summary>View</summary><div class="options-panel">
        <div role="group" aria-label="Graph detail">
          <button type="button" aria-pressed={level === "runs"} onclick={() => chooseLevel("runs")}>Run groups</button>
          <button type="button" aria-pressed={level === "stations"} onclick={() => chooseLevel("stations")}>Stations</button>
          <button type="button" aria-pressed={level === "occurrences"} onclick={() => chooseLevel("occurrences")}>Occurrences</button>
          <button type="button" aria-pressed={level === "records"} onclick={() => chooseLevel("records")}>Records</button>
        </div>
        <button type="button" aria-pressed={zoomDriven} onclick={() => zoomDriven = !zoomDriven}>Zoom changes detail</button>
        <button type="button" aria-pressed={following} onclick={toggleFollowing}>{following ? "Pause following" : "Follow selected Run"}</button>
        <p>Run → station/subject → supplied occurrence → loaded records. Deeper subworkflow structure is unavailable until its owner supplies it.</p>
        <p>Dashed paths are declared permissions; membership and recorded Animator selections are separate relations. A latest-record halo is an observation, not continuous computation.</p>
        <button type="button" onclick={clearHistory}>Clear tab history</button>
      </div>
    </details>
    <button class="refresh" type="button" disabled={loading} onclick={() => loadCatalogue()}>{loading ? "Reading…" : "Refresh Runs"}</button>
    <button id="orb-evidence-toggle" type="button" aria-label={inspectorOpen ? "Hide evidence" : "Show evidence"} aria-expanded={inspectorOpen} aria-controls="orb-evidence" onclick={(event) => { if (inspectorOpen) closeEvidence(); else { inspectorOpener = event.currentTarget; inspectorOpen = true; } }}>Evidence</button>
  </header>
  {#if error}<p class="field-fault" role="alert">{error}</p>{/if}
  {#if notice}<p class="field-notice" role="status">{notice}</p>{/if}
  <div class="field-layout">
    <section class="canvas-area" aria-label="Parallel Run graph">
      {#if viewedRuns.length && initialReady}
        <GraphCanvas projection={field.projection} selectedId={selectedNode} onselect={selectNode} label="Parallel Run workflow field" presentation="orb" hideMinimap={true} onzoom={zoomDetail} onviewportinteraction={() => following = false} {focusId} {focusRevision} />
        {#if !filteredRuns.length}<p class="filter-empty">No Run groups match this filter. <button type="button" onclick={() => { query = ""; statusFilter = "all"; }}>Clear filters</button></p>{/if}
        <div class="field-caption"><span>{pausedFrame ? "Captured field" : "Latest observed field"}</span><span>{lenses.size} evidence lenses · {connectionLabel}</span></div>
      {:else}<div class="field-empty"><h2>{!initialReady ? "Reading the Run field…" : error ? "Run field unavailable" : "No retained Runs in this account"}</h2><p>Open a conversation to create work, then inspect its recorded workflow here.</p><a href={resolve("/bridge")}>Open Bridge →</a></div>{/if}
    </section>
    <aside id="orb-evidence" class="field-feed" aria-label="Run evidence" hidden={!inspectorOpen}>
      <header><div><h2>{pausedFrame ? "Captured evidence" : "Run evidence"}</h2><p>{pausedFrame ? new Date(pausedFrame.observedAt).toLocaleString() : "Selected Run · bounded ledger feed"}</p></div><button type="button" aria-label="Close evidence inspector" onclick={closeEvidence}>×</button></header>
      {#if activeRun || viewedRun}
        {@const run = activeRun ?? viewedRun!}
        <p class="run-name">{run.workflow_name}</p><code class="run-identity">{run.run_id}</code>
        {#if !filteredRuns.some((candidate) => candidate.run_id === run.run_id)}<p class="feed-boundary">Selected Run is outside the current filter.</p>{/if}
        <dl class="feed-status"><dt>Latest fetched status</dt><dd>{activeRun?.status ?? "Not in current catalogue"}</dd><dt>Connection now</dt><dd>{currentLens?.connection ?? "lens closed"}</dd>{#if pausedFrame}<dt>Status at capture</dt><dd>{viewedRun?.status ?? "Not supplied"}</dd>{/if}</dl>
        <a class="detail-link" href={resolve(`/orb/${encodeURIComponent(run.run_id)}`)}>Open exact Run and history →</a>
        {#if activeLens}
          <AnimatorRail evidence={activeLens.snapshot.evidence} onselect={(seq) => { const event = activeLens?.snapshot.evidence.find((item) => item.seq === seq); if (event) selectRecord(event.event_id); }} />
          {#if currentLens?.note}<p class="field-notice" role="status">{currentLens.note}</p>{/if}
          <div class="lens-actions">{#if currentLens}<button type="button" disabled={loadingIds.has(run.run_id)} onclick={() => openLens(run.run_id)}>Refresh lens</button><button type="button" onclick={() => closeLens(run.run_id)}>Close live lens</button>{:else}<button type="button" disabled={loadingIds.has(run.run_id)} onclick={() => openLens(run.run_id)}>Open live lens</button>{/if}</div>
          <p class="feed-boundary">{activeLens.snapshot.evidence.length} loaded records · {activeLens.snapshot.gaps.length} reported gaps. {activeLens.snapshot.has_more || activeLens.trimmed ? "More retained history exists outside this lens." : "Capture remains bounded; omissions may apply."}</p>
          {#if activeLens.snapshot.known_omissions.length}<details><summary>Capture omissions</summary><ul>{#each activeLens.snapshot.known_omissions as omission (omission)}<li>{omission}</li>{/each}</ul></details>{/if}
          <ol class="live-records" aria-label="Selected Run live records">
            {#each activeLens.snapshot.evidence.toReversed() as event (event.event_id)}
              <li><button type="button" aria-pressed={selectedEvent === event.event_id} onclick={() => selectRecord(event.event_id)}><span class="record-seq">#{event.seq}</span><span><strong>{event.summary}</strong><small>{event.subject_key ?? "Unknown subject"}</small><time datetime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time></span></button></li>
            {:else}<li class="feed-empty">No structural records are supplied yet.</li>{/each}
          </ol>
          {#if record}<section class="record-detail" aria-label="Selected live record"><h3>{record.summary}</h3><dl><dt>Event</dt><dd><code>{record.event_id}</code></dd><dt>Sequence</dt><dd>#{record.seq}</dd><dt>Subject</dt><dd>{record.subject_key ?? "Not supplied"}</dd><dt>Occurrence</dt><dd>{record.occurrence_id ?? "Not supplied"}</dd><dt>Phase</dt><dd>{record.phase ?? "Not supplied"}</dd></dl><a href={resolve(`/orb/${encodeURIComponent(run.run_id)}?event=${encodeURIComponent(record.event_id)}`)}>Inspect this exact record →</a></section>
          {:else if selectedEvent}<p class="field-notice">The selected record is outside this lens window. Open the exact Run history to inspect it.</p>{/if}
        {:else}<button type="button" disabled={loadingIds.has(run.run_id)} onclick={() => openLens(run.run_id)}>{loadingIds.has(run.run_id) ? "Opening lens…" : "Open live lens"}</button>{/if}
      {:else}<p>Select a Run group to inspect its account.</p>{/if}
    </aside>
  </div>
  <OrbTimeline frames={history} cursorId={pausedFrame?.id ?? null} onseeking={seekField} onlive={liveField} onpause={pauseField} windowSeconds={historyWindow} onwindowchange={resizeHistory} {connectionLabel} />
</div>

<style>
  .orb-field { flex:1 1 0; width:100%; height:100%; min-height:28rem; min-width:0; display:flex; flex-direction:column; background:#000; color:var(--color-bone); position:relative; overflow:hidden; }
  .field-header { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; padding:.55rem .85rem; border-bottom:1px solid var(--color-engraving); background:var(--color-void); position:relative; z-index:8; }
  .field-title { display:flex; gap:.65rem; align-items:baseline; margin-inline-end:.3rem; white-space:nowrap; }
  h1 { font:500 1.15rem/1.2 var(--font-body); margin:0; }
  .field-title > span,.coverage { color:var(--color-ash); font:11px/1.5 var(--font-glyph); }
  h2 { font:500 1rem/1.4 var(--font-body); margin:0; }
  p,small,dt { color:var(--color-parchment); line-height:1.55; }
  button,input,select,summary { border:1px solid var(--color-engraving); border-radius:var(--radius-glyph); background:var(--color-void); color:var(--color-bone); font:inherit; font-size:12px; min-height:36px; }
  button { padding:.4rem .65rem; cursor:pointer; }
  button:hover,summary:hover { border-color:var(--color-rune-dim); }
  button[aria-pressed="true"] { border-color:var(--color-rune); color:var(--color-rune); }
  button:disabled { opacity:.5; cursor:wait; }
  button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible { outline:2px solid var(--color-rune); outline-offset:2px; }
  input { padding:.4rem .65rem; width:100%; min-width:0; }
  select { padding:.3rem .5rem; }
  .search { flex:1; min-width:9rem; max-width:18rem; }
  .refresh { margin-inline-start:auto; }
  a { color:var(--color-rune); text-decoration:underline; text-underline-offset:.2em; }
  .run-list > summary,.view-options > summary { padding:.4rem .65rem; cursor:pointer; list-style:none; }
  .run-list > summary span { color:var(--color-ash); font:11px var(--font-glyph); }
  .run-list-panel,.options-panel { position:absolute; inset-block-start:calc(100% + .35rem); inset-inline-end:.85rem; width:min(38rem,calc(100% - 1.7rem)); max-height:min(65vh,38rem); overflow:auto; padding:1rem; border:1px solid var(--color-engraving); background:var(--color-obsidian); box-shadow:0 12px 36px #000a; }
  .options-panel { width:min(25rem,calc(100% - 1.7rem)); display:flex; flex-direction:column; gap:.6rem; }
  .options-panel > div { display:flex; flex-wrap:wrap; gap:.35rem; }
  .options-panel p,.run-list-panel > p { font-size:12px; margin:.65rem 0; }
  .run-list ul { padding:0; list-style:none; margin:.75rem 0; }
  .run-list li { display:grid; grid-template-columns:minmax(0,1fr) auto auto; align-items:center; gap:.55rem; border-top:1px solid var(--color-engraving); padding:.55rem 0; }
  .run-list li > button:first-child { text-align:left; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.25rem .5rem; width:100%; }
  .run-list li code { grid-column:1/-1; color:var(--color-ash); font-size:10px; overflow-wrap:anywhere; }
  .run-list li span,.run-list li a { font-size:11px; }
  .field-layout { display:flex; flex:1; min-height:0; min-width:0; position:relative; overflow:hidden; }
  .canvas-area { flex:1; min-height:0; min-width:0; position:relative; background:#000; }
  .field-caption { position:absolute; top:.75rem; left:.9rem; right:.9rem; display:flex; justify-content:space-between; gap:1rem; color:var(--color-ash); font:10px/1.4 var(--font-glyph); pointer-events:none; }
  .field-feed { flex:0 0 clamp(17rem,30%,23rem); width:clamp(17rem,30%,23rem); min-width:0; min-height:0; overflow:auto; padding:1rem; border-inline-start:1px solid var(--color-engraving); background:var(--color-void); }
  .field-feed[hidden] { display:none; }
  .field-feed > header { display:flex; justify-content:space-between; align-items:start; gap:.5rem; padding-bottom:.6rem; border-bottom:1px solid var(--color-engraving); margin-bottom:.75rem; }
  .field-feed > header p { margin:.3rem 0 0; font-size:11px; }
  .field-feed > header button { border:0; min-width:36px; font-size:20px; padding:0; }
  .run-name { font-weight:600; margin:.75rem 0 .35rem; }
  .run-identity,.record-detail code { overflow-wrap:anywhere; display:block; font-size:10px; }
  .feed-status,.record-detail dl { display:grid; grid-template-columns:auto minmax(0,1fr); gap:.4rem .65rem; margin:.8rem 0; font-size:11px; }
  dd { margin:0; min-width:0; overflow-wrap:anywhere; }
  .detail-link { display:inline-flex; padding-block:.4rem; font-size:12px; }
  .lens-actions { display:flex; flex-wrap:wrap; gap:.4rem; margin:.75rem 0; }
  .feed-boundary { font-size:11px; }
  .field-feed :global(.animator-rail) { margin-top:.75rem; padding:.7rem; }
  .live-records { list-style:none; padding:0; margin:.75rem 0; }
  .live-records button { width:100%; text-align:left; display:grid; grid-template-columns:2.2rem minmax(0,1fr); gap:.4rem; border-radius:0; border-inline:0; border-top:0; background:transparent; }
  .live-records strong { display:block; font-size:12px; font-weight:500; overflow-wrap:anywhere; }
  .live-records small,.live-records time { display:block; color:var(--color-ash); font-size:10px; overflow-wrap:anywhere; }
  .record-seq { color:var(--color-ash); font:10px/1.5 var(--font-glyph); }
  .record-detail { border-top:1px solid var(--color-engraving); padding-top:.75rem; }
  .record-detail h3 { font-size:13px; overflow-wrap:anywhere; }
  .record-detail a { font-size:12px; }
  .field-notice,.field-fault { padding:.5rem .85rem; margin:0; border-bottom:1px solid var(--color-engraving); border-inline-start:2px solid var(--color-rune); font-size:12px; overflow-wrap:anywhere; }
  .field-fault { border-inline-start-color:var(--color-ember); }
  .field-empty { height:100%; min-height:12rem; padding:2rem; display:flex; flex-direction:column; justify-content:center; gap:1rem; }
  .field-empty p,.field-empty a { font-size:13px; }
  .filter-empty { position:absolute; inset:35% 1rem auto; text-align:center; font-size:13px; }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; border:0; }
  @media(max-width:56rem) { .field-header { gap:.4rem; padding:.5rem; } .field-title { flex-basis:auto; } .search { max-width:none; } .refresh { margin-left:0; } .field-caption { flex-direction:column; gap:.2rem; } .field-feed { position:absolute; inset:0 0 0 auto; z-index:7; width:min(23rem,100%); } }
  @media(max-width:35rem) { .field-title { flex:1; } .search { flex-basis:100%; order:2; } .field-title > span { font-size:10px; } .run-list li { grid-template-columns:minmax(0,1fr) auto; } .run-list li > button:first-child { grid-column:1/-1; } }
</style>
