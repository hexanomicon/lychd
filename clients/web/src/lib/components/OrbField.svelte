<script lang="ts">
  import { getContext, onDestroy, onMount, tick, untrack } from "svelte";
  import { resolve } from "$app/paths";
  import { getOrbRun } from "$lib/api/client";
  import type { OrbRunPage, OrbRunSnapshot } from "$lib/api/models";
  import { getOrbCatalogue, listenToOrb, orbSnapshotSchema, type OrbConnection } from "$lib/orb/live";
  import { matchesOrbPattern, mergeOrbEvidence, mergeOrbGaps, projectOrbField, type OrbDetailLevel, type OrbFieldLens } from "$lib/graph/orb";
  import { projectRuntime } from "$lib/graph/runtime";
  import { observeRuntime, emptyRuntimeState, type RuntimeReadState } from "$lib/orb/runtime";
  import RuntimeEvidence from "./RuntimeEvidence.svelte";
  import GraphCanvas from "./graph/GraphCanvas.svelte";
  import AnimatorRail from "./AnimatorRail.svelte";
  import OrbTimeline from "./OrbTimeline.svelte";
  import { appendFieldFrame, pruneFieldRun, sameOrbRun, trimFieldFrames, type FieldFrame } from "$lib/orb/field-history";

  import { workCommandKey, type WorkCommandRegistry, type CommandTarget, type CommandResult } from "$lib/bridge/work-commands";
  import { parseOrbPresentationCommand, seekObservationFrame, orbPresentationExamples } from "$lib/orb/presentation-commands";
  import type { GraphCameraCommand } from "./graph/camera-command";

  const workCommands = getContext<WorkCommandRegistry | undefined>(workCommandKey);
  let presentationEpoch = 0;
  let commandSequence = 0;
  let cameraCommand = $state.raw<GraphCameraCommand | null>(null);
  let timelineControlRevision = $state(0);

  type Run = OrbRunSnapshot["run"];
  type Lens = OrbFieldLens & { readonly connection: OrbConnection; readonly note: string; readonly trimmed: boolean };
  let runtime = $state.raw<RuntimeReadState>(emptyRuntimeState);
  let runtimeReader: ReturnType<typeof observeRuntime> | undefined;
  let runtimeMode = $state(false);
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
  let runtimeField = $derived(projectRuntime(runtime.snapshot, runtime.received));
  let runtimeSelection = $derived(selectedNode ? runtimeField.selections.get(selectedNode) : undefined);
  let combinedProjection = $derived({ identity: field.projection.identity, nodes: [...field.projection.nodes, ...runtimeField.projection.nodes], edges: [...field.projection.edges, ...runtimeField.projection.edges] });
  let activeLens = $derived(selectedRun ? viewedLenses.get(selectedRun) : undefined);
  let currentLens = $derived(selectedRun ? lenses.get(selectedRun) : undefined);
  let activeRun = $derived(runs.find((run) => run.run_id === selectedRun) ?? currentLens?.snapshot.run);
  let viewedRun = $derived(activeLens?.snapshot.run ?? viewedRuns.find((run) => run.run_id === selectedRun));
  let connectionLabel = $derived(lenses.size ? [...new Set([...lenses.values()].map((lens) => lens.connection))].join(" · ") : "No live lenses");
  let record = $derived(activeLens?.snapshot.evidence.find((item) => item.event_id === selectedEvent));

  function commandSnapshot() {
    return {
      revisionKey: JSON.stringify([presentationEpoch, pausedFrame?.id ?? "live", historyWindow, level, zoomDriven, following, query, statusFilter, accessBlocked]),
      selectionKey: JSON.stringify([selectedRun, selectedNode, selectedEvent]),
      commands: orbPresentationExamples
    };
  }
  function presentationChanged() { presentationEpoch++; workCommands?.refresh(); }
  function manualCamera() { following = false; presentationChanged(); }
  function commandCurrent(captured: CommandTarget) {
    const snapshot = commandSnapshot();
    return !destroyed && !accessBlocked && captured.instrument === "orb" && captured.id === "orb:tab-observation"
      && captured.revisionKey === snapshot.revisionKey && captured.selectionKey === snapshot.selectionKey
      && !!workCommands?.isCurrent(captured);
  }
  async function executePresentation(text: string, captured: CommandTarget): Promise<CommandResult> {
    const command = parseOrbPresentationCommand(text);
    if (!command) return { status: "unsupported", summary: "Unsupported tab observation presentation command. Use the listed English commands." };
    if (!commandCurrent(captured)) return { status: "stale", summary: "The tab observation presentation target changed." };
    if (!initialReady || !history.length) return { status: "unavailable", summary: "No tab observation captures are available." };
    if (command.kind === "camera") {
      if (!field.projection.nodes.length) return { status: "unavailable", summary: "No tab observation graph is visible." };
      const status = await new Promise<"applied" | "stale" | "unavailable">((resolve) => {
        cameraCommand?.complete("stale");
        let settled = false;
        const timeout = setTimeout(() => complete(commandCurrent(captured) ? "unavailable" : "stale"), 1000);
        const complete: GraphCameraCommand["complete"] = (result) => {
          if (settled) return;
          settled = true;
          clearTimeout(timeout);
          resolve(result);
        };
        cameraCommand = { id: ++commandSequence, action: command.action, isCurrent: () => !settled && commandCurrent(captured), complete };
      });
      return { status, summary: status === "applied" ? "Updated the tab observation camera." : "The tab observation camera command was not completed." };
    }
    if (command.kind === "seek") {
      const frame = seekObservationFrame(history, pausedFrame?.id ?? null, command.seconds);
      if (!frame) return { status: "unavailable", summary: "Requested tab observation time is outside the retained captures, or the selected capture was trimmed." };
      timelineControlRevision++;
      seekField(frame.id);
      return { status: "applied", summary: `Showing tab observation capture ${frame.id}, received ${new Date(frame.observedAt).toISOString()}. This is the nearest retained capture.` };
    }
    timelineControlRevision++;
    if (command.kind === "pause") { if (!pausedFrame) pauseField(); else presentationChanged(); }
    else liveField();
    return { status: "applied", summary: command.kind === "pause" ? "Paused tab observation presentation; incoming updates continue." : "Showing the latest tab observation capture." };
  }
  onMount(() => workCommands?.register({
    instrument: "orb", id: "orb:tab-observation", label: "Orb · tab observation",
    snapshot: commandSnapshot, execute: executePresentation
  }));
  // Incoming live receipts do not change presentation intent. Explicit handlers
  // also refresh synchronously to fence away-and-back gestures.
  $effect(() => {
    void selectedRun; void selectedNode; void selectedEvent; void pausedFrame;
    void historyWindow; void query; void statusFilter; void level; void zoomDriven; void following;
    untrack(() => workCommands?.refresh());
  });

  onMount(() => {
    runtimeReader = observeRuntime((next) => runtime = next);
    void loadCatalogue();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && !loading && !accessBlocked) void loadCatalogue(false, true);
    }, 5000);
    return () => window.clearInterval(timer);
  });
  onDestroy(() => {
    runtimeReader?.stop();
    destroyed = true;
    cameraCommand?.complete("stale");
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
    presentationChanged();
  }
  function seekField(id: number) {
    const frame = history.find((candidate) => candidate.id === id);
    if (!frame) return;
    pausedFrame = frame; following = false;
    presentationChanged();
  }
  function liveField() { pausedFrame = null; presentationChanged(); }
  function resizeHistory(seconds: number) {
    historyWindow = seconds;
    history = trimFieldFrames(history, seconds);
    presentationChanged();
  }
  function clearHistory() { history = []; pausedFrame = null; captureField(); presentationChanged(); }
  function authorityRefused(cause: unknown): boolean {
    return typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403);
  }
  function clearProtectedField() {
    runtimeReader?.clear();
    accessBlocked = true;
    presentationChanged();
    cameraCommand?.complete("stale");
    catalogueVersion++; catalogueController?.abort();
    loading = false; initialReady = true;
    for (const id of new Set([...lenses.keys(), ...loadingIds])) closeLens(id);
    runs = []; catalogue = null; history = []; pausedFrame = null; metadataVersions.clear();
    selectedRun = null; selectedNode = null; selectedEvent = null;
  }
  function clearProtectedRun(id: string) {
    presentationChanged();
    cameraCommand?.complete("stale");
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
    const current = runs.find((candidate) => candidate.run_id === run.run_id);
    if (!current || sameOrbRun(current, run)) return;
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
    loading = true;
    try {
      const next = await getOrbCatalogue(cursor ?? undefined, controller.signal);
      if (destroyed || version !== catalogueVersion) return;
      error = "";
      const overlaps = next.runs.some((run) => runs.some((loaded) => loaded.run_id === run.run_id));
      catalogue = automatic && catalogue && overlaps ? { ...next, next_cursor: catalogue.next_cursor } : next;
      const retained = more || automatic ? runs : runs.filter((run) => lenses.has(run.run_id) || loadingIds.has(run.run_id));
      const currentRuns = new Map(runs.map((run) => [run.run_id, run]));
      const merged = new Map(next.runs.map((run) => {
        const version = metadataVersions.get(run.run_id) ?? 0;
        const current = currentRuns.get(run.run_id);
        if (current && version !== (observedVersions.get(run.run_id) ?? 0)) return [run.run_id, current] as const;
        metadataVersions.set(run.run_id, version + 1);
        return [run.run_id, current && sameOrbRun(current, run) ? current : run] as const;
      }));
      for (const run of retained) if (!merged.has(run.run_id)) merged.set(run.run_id, run);
      const nextRuns = [...merged.values()];
      if (nextRuns.length !== runs.length || nextRuns.some((run, index) => run !== runs[index])) runs = nextRuns;
      captureField();
      if (!selectedRun || !runs.some((run) => run.run_id === selectedRun)) selectedRun = runs[0]?.run_id ?? null;
      if (!initialReady && !lenses.size && !loadingIds.size) {
        const ordered = runs.toSorted((a, b) => Number(["done", "failed", "cancelled"].includes(a.status)) - Number(["done", "failed", "cancelled"].includes(b.status)));
        await Promise.all(ordered.slice(0, 3).map((run) => openLens(run.run_id)));
      }
    } catch (cause) {
      if (!destroyed && version === catalogueVersion) {
        if (authorityRefused(cause)) clearProtectedField();
        error = cause instanceof TypeError && cause.message === "Failed to fetch"
          ? `Cannot reach the Run catalogue.${runs.length ? " Showing the last received field." : ""} Use Refresh Runs to retry.`
          : cause instanceof Error ? cause.message : "The Run catalogue could not be read.";
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
    if (runtimeField.selections.has(id)) {
      selectedNode = id; runtimeMode = true; inspectorOpen = true; inspectorOpener = opener; following = false;
      presentationChanged();
      return;
    }
    runtimeMode = false;
    const selection = field.selections.get(id);
    if (!selection) return;
    selectedNode = id; selectedRun = selection.runId; selectedEvent = selection.eventId ?? null; following = false; inspectorOpen = true;
    inspectorOpener = opener;
    presentationChanged();
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
    runtimeMode = false;
    selectedRun = id; selectedNode = `run:${id}`; selectedEvent = null; inspectorOpen = true; runsOpen = false;
    focusId = selectedNode; focusRevision++;
    presentationChanged();
  }
  function selectRecord(id: string) {
    selectedEvent = id; following = false; inspectorOpen = true;
    const options = [...field.selections].filter(([, selection]) => selection.runId === selectedRun && selection.eventId === id);
    selectedNode = options.at(-1)?.[0] ?? (selectedRun ? `run:${selectedRun}` : null);
    focusId = selectedNode; focusRevision++;
    presentationChanged();
  }
  function chooseLevel(value: OrbDetailLevel) { level = value; zoomDriven = false; presentationChanged(); }
  function toggleFollowing() {
    following = !following;
    presentationChanged();
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
    presentationChanged();
    if (!zoomDriven) return;
    if (zoom < 0.42) level = "runs";
    else if (zoom > 1.8) level = "records";
    else if ((level === "stations" && zoom > 1.05) || (level === "records" && zoom < 1.5)) level = "occurrences";
    else if ((level === "runs" && zoom > 0.58) || (level === "occurrences" && zoom < 0.88)) level = "stations";
  }
</script>

<svelte:head><title>Orb — runtime and workflow field</title></svelte:head>
<svelte:document onkeydown={dismissPanels} onvisibilitychange={() => { runtimeReader?.visibility(); if (document.visibilityState === "visible" && !loading) void loadCatalogue(false, true); }} />
<div class="orb-field">
  <header class="field-header">
    <div class="field-title"><h1>Orb</h1>{#if query.trim() || statusFilter !== "all"}<span>{filteredRuns.length}/{viewedRuns.length} Run groups</span>{/if}</div>
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
    <button type="button" aria-pressed={runtimeMode && inspectorOpen} onclick={(event) => { runtimeMode = true; inspectorOpen = true; inspectorOpener = event.currentTarget; }}>Runtime <span>{runtime.snapshot?.components.length ?? 0}</span></button>
    <button class="refresh" type="button" disabled={loading} aria-busy={loading} onclick={() => loadCatalogue()}>{loading && !initialReady ? "Reading…" : "Refresh Runs"}</button>
    <button id="orb-evidence-toggle" type="button" aria-label={inspectorOpen ? "Hide evidence" : "Show evidence"} aria-expanded={inspectorOpen} aria-controls="orb-evidence" onclick={(event) => { if (inspectorOpen) closeEvidence(); else { inspectorOpener = event.currentTarget; inspectorOpen = true; } }}>Evidence</button>
  </header>
  {#if error}<p class="field-fault" role="alert">{error}</p>{/if}
  {#if notice}<p class="field-notice" role="status">{notice}</p>{/if}
  <div class="field-layout">
    <section class="canvas-area" aria-label="Runtime and parallel Run graph">
      {#if runtimeField.projection.nodes.length || (viewedRuns.length && initialReady)}
        <GraphCanvas projection={combinedProjection} selectedId={selectedNode} onselect={selectNode} label="Runtime and parallel Run workflow field" presentation="orb" hideMinimap={true} onzoom={zoomDetail} onviewportinteraction={manualCamera} {cameraCommand} {focusId} {focusRevision} />
        {#if viewedRuns.length && !filteredRuns.length}<p class="filter-empty">No Run groups match this filter. <button type="button" onclick={() => { query = ""; statusFilter = "all"; }}>Clear filters</button></p>{/if}
        <div class="field-caption"><span>{pausedFrame ? "Captured Runs · latest runtime window" : "Latest observed field"}</span><span>{runtime.snapshot?.components.length ?? 0} runtime components · {lenses.size} evidence lenses · {connectionLabel}</span></div>
      {:else}<div class="field-empty"><h2>{!initialReady ? "Reading the Run field…" : error ? "Run field unavailable" : "No retained Runs in this account"}</h2><p>Open a conversation to create work, then inspect its recorded workflow here.</p><a href={resolve("/bridge")}>Open Bridge →</a></div>{/if}
    </section>
    <aside id="orb-evidence" class="field-feed" aria-label={runtimeMode ? "Runtime evidence" : "Run evidence"} hidden={!inspectorOpen}>
      <header><div><h2>{runtimeMode ? "Runtime evidence" : pausedFrame ? "Captured evidence" : "Run evidence"}</h2><p>{runtimeMode ? "Latest runtime window · independent of Run playback" : pausedFrame ? new Date(pausedFrame.observedAt).toLocaleString() : "Selected Run · bounded ledger feed"}</p></div><button type="button" aria-label="Close evidence inspector" onclick={closeEvidence}>×</button></header>
      {#if runtimeMode}
        <RuntimeEvidence state={runtime} field={runtimeField} selected={runtimeSelection} onselect={selectNode} onrefresh={() => runtimeReader?.refresh()} />
      {:else if activeRun || viewedRun}
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
  <OrbTimeline controlRevision={timelineControlRevision} frames={history} cursorId={pausedFrame?.id ?? null} onseeking={seekField} onlive={liveField} onpause={pauseField} windowSeconds={historyWindow} onwindowchange={resizeHistory} {connectionLabel} />
</div>

<style>
.orb-field { flex:1 1 0; width:100%; height:100%; min-height:28rem; min-width:0; display:flex; flex-direction:column; position:relative; overflow:hidden; background:#000; color:var(--color-bone); }
  .field-header { position:relative; z-index:8; display:flex; align-items:center; flex-wrap:wrap; gap:.45rem; flex:none; margin:.9rem .9rem 0; padding:.5rem .65rem; border:1px solid var(--color-engraving); border-radius:8px; background:var(--color-obsidian); box-shadow:0 8px 28px #0005; }
  .field-title { display:flex; align-items:baseline; gap:.65rem; margin-inline-end:.65rem; white-space:nowrap; }
  h1 { margin:0; color:var(--color-bone); font:600 1.05rem/1.2 var(--font-body); letter-spacing:-.025em; }
  .field-title > span,.coverage { color:var(--color-ash); font:12px/1.5 var(--font-body); }
  h2 { margin:0; font:600 1rem/1.4 var(--font-body); letter-spacing:-.015em; }
  p,small,dt { color:var(--color-parchment); line-height:1.6; }
  button,input,select,summary { min-height:36px; border:1px solid var(--color-control-border); border-radius:5px; background:transparent; color:var(--color-bone); font:400 13px/1.4 var(--font-body); }
  button { padding:.45rem .65rem; cursor:pointer; }
  button:hover:not(:disabled),summary:hover { border-color:var(--color-rune); background:var(--color-obsidian-2); }
  button[aria-pressed="true"] { border-color:var(--color-rune); color:var(--color-rune); background:color-mix(in srgb,var(--color-rune) 7%,var(--color-obsidian)); }
  button:disabled { opacity:.5; cursor:wait; }
  button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  input { width:100%; min-width:0; padding:.45rem .7rem; background:var(--color-void); }
  input::placeholder { color:var(--color-ash); opacity:1; }
  select { padding:.4rem .55rem; background:var(--color-obsidian); }
  .search { flex:1 1 10rem; min-width:9rem; max-width:19rem; }
  .refresh { margin-inline-start:auto; }
  a { color:var(--color-rune); text-decoration:underline; text-underline-offset:.2em; }
  .run-list > summary,.view-options > summary { display:flex; align-items:center; gap:.45rem; padding:.4rem .65rem; cursor:pointer; list-style:none; }
  .run-list > summary::after,.view-options > summary::after { content:"⌄"; color:var(--color-ash); }
  .run-list[open] > summary,.view-options[open] > summary { border-color:var(--color-rune); }
  .run-list > summary span { color:var(--color-ash); font:12px var(--font-glyph); }
  .run-list-panel,.options-panel { position:absolute; inset-block-start:calc(100% + .6rem); inset-inline-end:0; width:min(39rem,100%); max-height:min(65vh,38rem); overflow:auto; overscroll-behavior:contain; padding:1.15rem; border:1px solid var(--color-control-border); border-radius:8px; background:var(--color-obsidian); box-shadow:0 16px 48px #0009; }
  .options-panel { width:min(28rem,100%); display:flex; flex-direction:column; gap:.7rem; }
  .options-panel > div { display:flex; flex-wrap:wrap; gap:.4rem; }
  .options-panel p,.run-list-panel > p { margin:.75rem 0; font-size:13px; }
  .run-list ul { margin:1rem 0; padding:0; list-style:none; }
  .run-list li { display:grid; grid-template-columns:minmax(0,1fr) auto auto; align-items:center; gap:.6rem; padding:.7rem 0; border-top:1px solid var(--color-engraving); }
  .run-list li > button:first-child { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.3rem .6rem; width:100%; border-color:transparent; text-align:left; }
  .run-list li code { grid-column:1/-1; color:var(--color-ash); font-size:11px; overflow-wrap:anywhere; }
  .run-list li span,.run-list li a { font-size:12px; }
  .field-layout { display:flex; flex:1; min-height:0; min-width:0; position:relative; overflow:hidden; }
  .canvas-area { flex:1; min-height:0; min-width:0; position:relative; background:#000; }
  .field-caption { position:absolute; top:.9rem; left:1.1rem; right:1.1rem; display:flex; justify-content:space-between; gap:1rem; color:var(--color-ash); font:11px/1.5 var(--font-body); pointer-events:none; }
  .field-feed { flex:0 0 clamp(18rem,31%,25rem); width:clamp(18rem,31%,25rem); min-width:0; min-height:0; overflow:auto; overscroll-behavior:contain; padding:1.25rem; border-inline-start:1px solid var(--color-engraving); background:var(--color-obsidian); }
  .field-feed[hidden] { display:none; }
  .field-feed > header { display:flex; justify-content:space-between; align-items:start; gap:.8rem; padding-bottom:1rem; margin-bottom:1rem; border-bottom:1px solid var(--color-engraving); }
  .field-feed > header p { margin:.35rem 0 0; font-size:12px; color:var(--color-ash); }
  .field-feed > header button { flex:none; min-width:36px; font-size:20px; padding:0; border-color:transparent; }
  .run-name { margin:1rem 0 .4rem; color:var(--color-bone); font-size:1.1rem; font-weight:600; letter-spacing:-.02em; }
  .run-identity,.record-detail code { display:block; font:12px/1.6 var(--font-glyph); color:var(--color-ash); overflow-wrap:anywhere; }
  .feed-status,.record-detail dl { display:grid; grid-template-columns:auto minmax(0,1fr); gap:.55rem .8rem; margin:1rem 0; font-size:12px; }
  dt { color:var(--color-ash); }
  dd { margin:0; min-width:0; overflow-wrap:anywhere; }
  .detail-link { display:inline-flex; padding-block:.5rem; font-size:13px; }
  .lens-actions { display:flex; flex-wrap:wrap; gap:.45rem; margin:1rem 0; }
  .feed-boundary { padding:.75rem 0; font-size:12px; line-height:1.65; }
  .field-feed :global(.animator-rail) { margin-top:1rem; padding:.8rem 0; border-inline:0; background:transparent; }
  .live-records { list-style:none; padding:0; margin:1rem 0; }
  .live-records button { display:grid; grid-template-columns:2.3rem minmax(0,1fr); gap:.55rem; width:100%; padding:.85rem 0; border:0; border-bottom:1px solid var(--color-engraving); border-radius:0; background:transparent; text-align:left; }
  .live-records button[aria-pressed="true"] { box-shadow:inset 2px 0 var(--color-rune); padding-inline-start:.65rem; }
  .live-records strong { display:block; font-size:13px; font-weight:500; overflow-wrap:anywhere; }
  .live-records small,.live-records time { display:block; margin-top:.25rem; color:var(--color-ash); font-size:12px; overflow-wrap:anywhere; }
  .record-seq { color:var(--color-ash); font:12px/1.5 var(--font-glyph); }
  .record-detail { border-top:1px solid var(--color-engraving); padding-top:1rem; }
  .record-detail h3 { font:600 1rem/1.5 var(--font-body); overflow-wrap:anywhere; }
  .record-detail a { font-size:13px; }
  .field-notice,.field-fault { flex:none; margin:.65rem .9rem 0; padding:.75rem .85rem; border:1px solid var(--color-engraving); border-inline-start:2px solid var(--color-rune); background:var(--color-obsidian); font-size:13px; overflow-wrap:anywhere; }
  .field-feed .field-notice { margin:1rem 0; }
  .field-fault { border-inline-start-color:var(--color-ember); }
  .field-empty { display:flex; flex-direction:column; justify-content:center; gap:1rem; height:100%; min-height:12rem; padding:clamp(1.5rem,5vw,4rem); }
  .field-empty h2 { max-width:30rem; font-size:clamp(1.5rem,3vw,2.4rem); line-height:1.2; letter-spacing:-.035em; }
  .field-empty p,.field-empty a { max-width:32rem; font-size:14px; }
  .filter-empty { position:absolute; inset:35% 1rem auto; text-align:center; font-size:14px; }
  .filter-empty button { margin-inline-start:.5rem; background:var(--color-obsidian); }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; border:0; }
  @media(max-width:56rem) { .field-header { margin:.6rem .6rem 0; padding:.45rem; gap:.4rem; } .search { max-width:none; } .refresh { margin-inline-start:0; } .field-caption { flex-direction:column; gap:.2rem; } .field-feed { position:absolute; inset:0 0 0 auto; z-index:7; width:min(25rem,100%); box-shadow:-12px 0 40px #0008; } }
  @media(max-width:35rem) { .field-title { flex:1; } .search { flex-basis:100%; order:2; } .field-title > span { font-size:11px; } .run-list li { grid-template-columns:minmax(0,1fr) auto; } .run-list li > button:first-child { grid-column:1/-1; } .field-feed { padding:1rem; } }
  @container work-area (max-width:56rem) { .search { max-width:none; } .refresh { margin-inline-start:0; } .field-caption { flex-direction:column; gap:.2rem; } .field-feed { position:absolute; inset:0 0 0 auto; z-index:7; width:min(25rem,100%); box-shadow:-12px 0 40px #0008; } }
  @media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none; transition:none; scroll-behavior:auto; } }
</style>
