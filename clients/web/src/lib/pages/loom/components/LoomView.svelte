<script lang="ts">
  import SchemaFields from "$lib/components/shared/SchemaFields.svelte";
  import { inspectionSelection, sameInspectionBinding, inspectionQuery, type InspectionSelection } from "$lib/api/inspection";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { navigationId, orbReturnHref, loomOriginHref } from "$lib/navigation/instruments";
  import { getContext, onDestroy, tick, untrack, type Snippet } from "svelte";
  import { workCommandKey, type CommandTarget, type CommandResult, type WorkCommandRegistry } from "$lib/shell/state/work-commands";
  import { parseLoomCommand } from "$lib/pages/loom/state/loom-commands";
  import { MediaQuery } from "svelte/reactivity";
  import { loomProjection } from "$lib/pages/loom/state/loom";
  import { matchesOrbPattern } from "$lib/graph/model";

  import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
  import type {
    LoomSummary,
    LoomView as LoomProjection,
    OrbRunSnapshot
  } from "$lib/api/models";
  import GraphCanvas from "$lib/graph/components/GraphCanvas.svelte";
  import GraphMapRail from "$lib/graph/components/GraphMapRail.svelte";
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";
  import DelegateMark from "$lib/components/shared/DelegateMark.svelte";
  import WorkflowLibrary from "./WorkflowLibrary.svelte";
  import type { StudioKey } from "../studio/session";
  import { compositionRecipe } from "../studio/compositions";
  import BlueprintStudio from "../studio/BlueprintStudio.svelte";
  import LoomEvaluation from "./LoomEvaluation.svelte";
  import LoomAffect from "./LoomAffect.svelte";
  import { createEvaluationWorkspace, getEvaluationWorkspace, hasEvaluationWorkspace, setEvaluationWorkspace } from "$lib/pages/loom/state/evaluation/workspace.svelte";

  let {
    patternId,
    revision
  }: {
    patternId?: string;
    revision?: string;
  } = $props();
  let composition = $derived(compositionRecipe(page.url.searchParams.get("composition")));
  let documentKey: StudioKey | null = $derived(composition ?? (page.url.searchParams.get("studio") === "sdlc" ? "sdlc" : null));
  let designing = $derived(documentKey !== null);
  const workCommands = getContext<WorkCommandRegistry | undefined>(workCommandKey);
  const evaluationWorkspace = hasEvaluationWorkspace() ? getEvaluationWorkspace() : createEvaluationWorkspace();
  if (!hasEvaluationWorkspace()) setEvaluationWorkspace(evaluationWorkspace);
  const views = ["score", "evaluation", "affect"] as const;
  type ViewName = typeof views[number];
  let activeView = $state<ViewName>("score");
  let unregisterCommands: (() => void) | undefined;
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let catalogue = $state.raw<LoomSummary[]>([]);
  let view = $state.raw<LoomProjection | null>(null);
  let sourceRun = $state.raw<OrbRunSnapshot | null>(null);
  let loading = $state(true);
  let error = $state("");
  const compact = new MediaQuery("(max-width: 48rem)");
  let mapOpen = $derived(!compact.current);
  let mapWidth = $state(172);
  let inspectorOpen = $state(true);
  let inspectorLeft = $state(false);
  let inspectorWidth = $state(270);
  let outlineMode = $state<"auto" | "open" | "closed">("auto");
  let outlineOpen = $derived(outlineMode === "auto" ? compact.current : outlineMode === "open");
  let stationOpener: { key: string; element: HTMLElement } | null = null;
  let selectedKey = $state<string | null>(null);
  let canvasLevel = $state<"pattern" | "stations">("stations");
  const uid = $props.id();
  let graph = $derived(view ? loomProjection(view) : null);
  let patternGraph = $derived(view ? loomProjection(view, "pattern") : null);
  let canvasGraph = $derived(canvasLevel === "pattern" ? patternGraph : graph);
  let canvasSelectedId = $derived(canvasLevel === "pattern" ? patternGraph?.nodes[0]?.id : selectedKey);
  let nodesByKey = $derived(new Map(graph?.nodes.map((node) => [node.id, node]) ?? []));
  let selectedSchema = $derived(view?.nodes.find(station => station.key === selectedKey)?.output_schema);
  let selectedNode = $derived(selectedKey ? nodesByKey.get(selectedKey) : undefined);
  let outgoingByKey = $derived(
    new Map(graph?.nodes.map((node) => [node.id, (graph?.edges ?? []).filter((edge) => edge.source === node.id)]) ?? [])
  );
  let incoming = $derived(graph?.edges.filter((edge) => edge.target === selectedKey) ?? []);
  let outgoing = $derived(selectedKey ? outgoingByKey.get(selectedKey) ?? [] : []);
  let loadVersion = 0;
  let sourceContextError = $state("");
  let sourceRunHint = $derived(page.url.searchParams.get("run"));
  let sourceRunId = $derived(navigationId(sourceRunHint));
  let inspectionContext = $derived(inspectionSelection(page.url.search));
  let returnHref = $derived(sourceRun ? orbReturnHref(sourceRun.run.run_id, page.url.search) : null);

  $effect(() => {
    if (designing) {
      loadVersion++;
      unregisterCommands?.();
      unregisterCommands = undefined;
      return;
    }
    const request = [patternId, revision, sourceRunId, sourceRunHint, inspectionContext.binding, inspectionContext.error] as const;
    untrack(() => { void load(...request); });
  });

  onDestroy(() => {
    loadVersion++;
    unregisterCommands?.();
    unregisterCommands = undefined;
  });

  function stationId(key: string) {
    return `${uid}-station-${encodeURIComponent(key)}`;
  }

  function setCanvasLevel(level: "pattern" | "stations") {
    canvasLevel = level;
    workCommands?.refresh();
  }

  function selectView(next: ViewName) {
    activeView = next;
    focusRevision++;
    workCommands?.refresh();
  }

  function tabKey(event: KeyboardEvent) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const index = views.indexOf(activeView);
    const next = event.key === "Home" ? views[0] : event.key === "End" ? views[views.length - 1] :
      views[(index + (event.key === "ArrowRight" ? 1 : views.length - 1)) % views.length];
    if (!next) return;
    selectView(next);
    void tick().then(() => document.getElementById(`${uid}-${next}-tab`)?.focus());
  }

  function zoomLevel(zoom: number) {
    if (canvasLevel === "stations" && zoom < 0.55) setCanvasLevel("pattern");
    else if (canvasLevel === "pattern" && zoom > 0.85) setCanvasLevel("stations");
  }

  async function selectCanvasNode(key: string, opener?: HTMLElement) {
    if (canvasLevel === "pattern") {
      const version = loadVersion;
      setCanvasLevel("stations");
      await tick();
      if (version === loadVersion) document.getElementById(`${uid}-station-title`)?.focus();
    } else await inspectStation(key, opener);
  }

  async function inspectStation(key: string, opener?: HTMLElement, command?: "inspect" | "focus") {
    if (!nodesByKey.has(key)) return false;
    inspectorOpen = true;
    const version = loadVersion;
    selectedKey = key;
    stationOpener = opener ? { key, element: opener } : null;
    if (command) {
      canvasLevel = "stations";
      outlineMode = "open";
      if (command === "focus") {
        focusId = key;
        focusRevision++;
      }
    }
    if (command) {
      // The inspector heading is already mounted. Focus in this same guarded
      // turn; its label updates with selection without a new post-mutation token.
      document.getElementById(`${uid}-station-title`)?.focus();
      workCommands?.refresh();
      return true;
    }
    workCommands?.refresh();
    await tick();
    if (version !== loadVersion || selectedKey !== key) return false;
    document.getElementById(`${uid}-station-title`)?.focus();
    return true;
  }

  function registerCommands(loaded: LoomProjection, version: number) {
    if (!workCommands) return;
    const id = JSON.stringify([loaded.pattern_id, loaded.revision]);
    const snapshot = () => {
      if (activeView !== "score" || loading || error || view !== loaded || version !== loadVersion ||
          (patternId && patternId !== loaded.pattern_id) ||
          (revision && revision !== loaded.revision)) throw new Error("Loom target is unavailable");
      return {
        revisionKey: JSON.stringify([loaded.pattern_id, loaded.revision, loaded.digest, version, sourceRunHint]),
        selectionKey: JSON.stringify([selectedKey, canvasLevel, outlineMode, focusRevision]),
        commands: ["inspect STATION", "focus STATION", "show pattern", "show stations"]
      };
    };
    const execute = async (text: string, captured: CommandTarget): Promise<CommandResult> => {
      const current = () => version === loadVersion && view === loaded &&
        captured.instrument === "loom" && captured.id === id && workCommands.isCurrent(captured);
      if (!current()) return { status: "stale", summary: "The Loom Pattern or selection changed. Capture it again." };
      const command = parseLoomCommand(text, loaded.nodes);
      if (command.kind === "unsupported") return { status: "unsupported", summary: command.summary };
      await tick();
      if (!current()) return { status: "stale", summary: "The Loom Pattern or selection changed. Capture it again." };
      if (command.kind === "station") {
        const focused = await inspectStation(command.key, undefined, command.action);
        if (!focused) return { status: "stale", summary: "Loom inspection changed before focus could settle." };
        return { status: "applied", summary: `Inspecting station ${command.key} in ${loaded.pattern_id}@${loaded.revision}. Read-only presentation.` };
      }
      if (command.level === "stations") outlineMode = "open";
      // This heading remains mounted across graph levels, so focus and level
      // change are one synchronous presentation operation after validation.
      document.getElementById(`${uid}-graph-title`)?.focus();
      setCanvasLevel(command.level);
      return { status: "applied", summary: `Showing ${command.level} in ${loaded.pattern_id}@${loaded.revision}. Read-only presentation.` };
    };
    unregisterCommands = workCommands.register({
      instrument: "loom", id, label: `Loom · ${loaded.pattern_id}@${loaded.revision}`, snapshot, execute
    });
  }

  async function returnToStation() {
    if (!selectedKey) return;
    if (stationOpener?.key === selectedKey && stationOpener.element.isConnected &&
        !stationOpener.element.closest("details:not([open])")) {
      stationOpener.element.focus();
      return;
    }
    outlineMode = "open";
    workCommands?.refresh();
    const key = selectedKey;
    const version = loadVersion;
    await tick();
    if (version === loadVersion && selectedKey === key) {
      document.getElementById(stationId(key))?.focus();
    }
  }

  async function load(
    requestedPattern?: string,
    requestedRevision?: string,
    requestedRun?: string | null,
    requestedHint?: string | null,
    requestedBinding?: InspectionSelection,
    bindingError?: string
  ) {
    const version = ++loadVersion;
    unregisterCommands?.();
    unregisterCommands = undefined;
    focusId = null;
    focusRevision = 0;
    loading = true;
    error = "";
    view = null;
    selectedKey = null;
    canvasLevel = "stations";
    stationOpener = null;
    sourceRun = null;
    sourceContextError = requestedHint && !requestedRun ? "Run context unavailable — the linked identity is invalid." : "";
    try {
      if (bindingError) throw new Error(bindingError);
      const [patterns, origin] = await Promise.all([
        getLoomCatalogue(),
        requestedRun
          ? getOrbRun(requestedRun, { limit: 1 }).catch((cause: unknown) => {
            if (typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403)) throw cause;
            return null;
          })
          : Promise.resolve(null)
      ]);
      if (version !== loadVersion) return;
      catalogue = patterns;
      const selected =
        requestedPattern && requestedRevision
          ? { pattern_id: requestedPattern, revision: requestedRevision }
          : patterns.find((pattern) => pattern.default) ??
            patterns.find((pattern) => pattern.active) ??
            patterns[0];
      if (!selected) return;
      const next = requestedBinding
        ? await getLoomPatternRevision(selected.pattern_id, selected.revision, requestedBinding)
        : await getLoomPatternRevision(selected.pattern_id, selected.revision);
      if (version !== loadVersion) return;
      if (next.pattern_id !== selected.pattern_id || next.revision !== selected.revision ||
          (requestedBinding && !sameInspectionBinding(requestedBinding, next.binding))) {
        throw new Error("Inspection context unavailable — the returned Pattern does not match the exact requested identity and source profile.");
      }
      view = next;
      selectedKey = next.nodes.find((node) => node.key === next.entry_node)?.key ?? next.nodes[0]?.key ?? null;
      const originMatches =
        origin !== null &&
        origin.run.run_id === requestedRun &&
        origin.pattern.loom_path !== null &&
        matchesOrbPattern(origin, next);
      sourceRun = originMatches ? origin : null;
      if (requestedRun && !originMatches) {
        sourceContextError = "Run context unavailable — this Run could not be verified against the displayed Pattern revision.";
      }
      if (!designing && (!requestedPattern || !requestedRevision) && (!requestedHint || requestedRun)) {
        const exactPath = `/loom/${next.pattern_id}/${next.revision}${requestedBinding ? inspectionQuery(requestedBinding) : ""}`;
        await goto(
          requestedRun
            ? loomOriginHref(exactPath, requestedRun, page.url.search) ?? exactPath
            : exactPath,
          {
          replace: true
          }
        );
      }
    } catch (cause) {
      if (version === loadVersion) {
        if (typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403)) evaluationWorkspace.clearProtected();
        error = cause instanceof Error ? cause.message : "The Loom cannot be read.";
      }
    } finally {
      if (version === loadVersion) {
        loading = false;
        if (view && !error) registerCommands(view, version);
      }
    }
  }
</script>

<svelte:head><title>{view ? `${view.title} · ${view.pattern_id}@${view.revision} — Loom` : "Loom — LychD"}</title></svelte:head>
<div class="instrument-deck instrument-deck--loom loom-workspace">
  {#if documentKey}{#key documentKey}<BlueprintStudio {documentKey} {catalogue} />{/key}{:else}
  {#snippet library()}
    <WorkflowLibrary {catalogue} patternPath={catalogue.find(item => item.pattern_id === view?.pattern_id && item.revision === view?.revision && sameInspectionBinding(item.binding, view?.binding))?.detail_path} />
    <a class="design-link" href={resolve("/loom") + "?studio=sdlc"}>Design workflow</a>
  {/snippet}
  {#if !view || !canvasGraph?.nodes.length || activeView !== "score"}
    <div class="standalone-library">{@render library()}</div>
  {/if}
  <section class="loom-reading" aria-label="Registered Pattern" aria-busy={loading}>
    {#if loading}
      <div class="loom-read-state" role="status">
        <span class="loom-eyebrow">Reading the registry</span>
        <h2>Loading Pattern revision…</h2>
      </div>
    {:else if error}
      <div class="loom-read-state">
        <h2>Pattern unavailable</h2>
        <p role="alert">{error}</p>
        <button class="loom-button" type="button" onclick={() => load(patternId, revision, sourceRunId, sourceRunHint, inspectionContext.binding, inspectionContext.error)}>Retry reading Pattern</button>
      </div>
    {:else if view && graph && canvasGraph}
      {#snippet identity()}
        <div class="pattern-identity">
          <h2>{view?.title}</h2>
          <code>{view?.pattern_id}@{view?.revision}</code>
          {#if returnHref}<a href={resolve(returnHref)}>Return to Run in Orb →</a>{/if}
          {#if sourceContextError}<p role="status">{sourceContextError}</p>{/if}
        </div>
      {/snippet}
      {#snippet viewsBar()}
      <div class="loom-views" role="tablist" aria-label="Loom views">
        <button type="button" role="tab" id={`${uid}-score-tab`} aria-selected={activeView === "score"} aria-controls={`${uid}-score-panel`} tabindex={activeView === "score" ? 0 : -1} onclick={() => selectView("score")} onkeydown={tabKey}>Score</button>
        <button type="button" role="tab" id={`${uid}-evaluation-tab`} aria-selected={activeView === "evaluation"} aria-controls={`${uid}-evaluation-panel`} tabindex={activeView === "evaluation" ? 0 : -1} onclick={() => selectView("evaluation")} onkeydown={tabKey}>Evaluation</button>
        <button type="button" role="tab" id={`${uid}-affect-tab`} aria-selected={activeView === "affect"} aria-controls={`${uid}-affect-panel`} tabindex={activeView === "affect" ? 0 : -1} onclick={() => selectView("affect")} onkeydown={tabKey}>Affect</button>
      </div>
      {/snippet}
      {#if activeView !== "score" || !canvasGraph.nodes.length}
        <div class="standalone-tools">{@render identity()}{@render viewsBar()}</div>
      {/if}
      {#if activeView === "evaluation"}
        <div role="tabpanel" id={`${uid}-evaluation-panel`} aria-labelledby={`${uid}-evaluation-tab`}><LoomEvaluation score={view} linkedRunId={sourceRun?.run.run_id ?? null} /></div>
      {:else if activeView === "affect"}
        <div role="tabpanel" id={`${uid}-affect-panel`} aria-labelledby={`${uid}-affect-tab`}><LoomAffect score={view} stationKey={selectedKey} /></div>
      {:else}
      <div role="tabpanel" id={`${uid}-score-panel`} aria-labelledby={`${uid}-score-tab`}>
      <div class={["loom-score-layout", { "inspector-left": inspectorLeft, "inspector-folded": !inspectorOpen }]} style:--inspector-width={`${inspectorWidth}px`}>
        <div class="loom-graph-column">
          <section class="loom-canvas-panel" aria-labelledby={`${uid}-graph-title`}>
            <h3 id={`${uid}-graph-title`} class="graph-title" tabindex="-1">Pattern graph</h3>
            <div class="loom-flow-mount" style:--graph-map-width={mapOpen ? `min(${mapWidth}px,38%)` : "2.15rem"}>
              {#if canvasGraph.nodes.length}
                <GraphCanvas presentation="loom" frameLabel={canvasLevel === "stations" ? view.title : undefined} {focusId} {focusRevision} projection={canvasGraph} selectedId={canvasSelectedId} onselect={selectCanvasNode} onzoom={zoomLevel} label={`${view.title} Pattern graph`} --graph-height="max(420px,calc(100dvh - 3rem))" navigatorRight={inspectorLeft}>
                  {#snippet navigator(minimap: Snippet)}
                    <GraphMapRail bind:open={mapOpen} bind:width={mapWidth} {minimap} name="Loom Map" right={inspectorLeft}>
                      {@render identity()}
                      {@render library()}
                      <details class="map-stations" open><summary>Declared stations</summary>
                        {#each graph?.nodes ?? [] as node (node.id)}
                          <button type="button" aria-label={`Locate ${node.label} on canvas`} aria-pressed={selectedKey === node.id}
                            onclick={event => {
                              setCanvasLevel("stations"); focusId = node.id; focusRevision++;
                              void inspectStation(node.id, event.currentTarget);
                            }}>{node.label}<small>{node.kind}</small></button>
                        {/each}
                      </details>
                    </GraphMapRail>
                  {/snippet}
                </GraphCanvas>
              {:else}
                <p class="loom-empty-graph">No stations declared in this Pattern revision.</p>
              {/if}
            </div>
            <div class="loom-levels" role="group" aria-label="Graph detail">
              <button type="button" aria-pressed={canvasLevel === "pattern"} onclick={() => setCanvasLevel("pattern")}>Whole Pattern</button>
              <span aria-hidden="true">/</span>
              <button type="button" aria-pressed={canvasLevel === "stations"} onclick={() => setCanvasLevel("stations")}>Stations</button>
              <span class="loom-level-hint">{canvasLevel === "pattern" ? "Zoom in to reveal stations" : "Zoom out to fold the Pattern"}</span>
            </div>
            <p class="loom-canvas-note">Read-only layout · Connections are declared permissions</p>
            <p class="loom-canvas-note">Bridge commands (deterministic English): <code>inspect STATION</code>, <code>focus STATION</code>, <code>show pattern</code>, <code>show stations</code>. Use an exact station key or an unambiguous label.</p>
          </section>
          <details class="loom-outline" open={outlineOpen} ontoggle={(event) => {
            if (!event.currentTarget.isConnected) return;
            if (event.currentTarget.open !== outlineOpen) {
              outlineMode = event.currentTarget.open ? "open" : "closed";
              workCommands?.refresh();
            }
          }}>
            <summary>Graph outline <span>Stations &amp; permissions</span></summary>
            <p class="loom-score-guide">Select a station to inspect its declared permissions.</p>
            <ol class="loom-stations" aria-label="Declared stations">
              {#each graph.nodes as node, index (node.id)}
                <li class="loom-station" data-selected={selectedKey === node.id}>
                  <button
                    id={stationId(node.id)}
                    class="loom-station-select"
                    type="button"
                    aria-label={`Inspect ${node.label} (${node.id})`}
                    aria-pressed={selectedKey === node.id}
                    aria-controls={`${uid}-inspector`}
                    onclick={(event) => inspectStation(node.id, event.currentTarget)}
                  >
                    <span class="loom-station-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                    <span class="loom-station-identity">
                      <strong>{#if node.kind === "delegate"}<DelegateMark />{/if}{node.label}</strong>
                      <code>{node.id}</code>
                    </span>
                    <span class="loom-station-tags">
                      <span class="loom-kind">{node.kind}</span>
                      {#if node.id === view.entry_node}<span>Entry</span>{/if}
                      {#if selectedKey === node.id}<span class="loom-selection-mark">Selected</span>{/if}
                    </span>
                  </button>
                  <div class="loom-successors">
                    {#if outgoingByKey.get(node.id)?.length}
                      <span class="loom-field-label">Permitted next</span>
                      <ul aria-label={`Permitted next stations from ${node.label}`}>
                        {#each outgoingByKey.get(node.id) ?? [] as edge (edge.id)}
                          <li>
                            <span aria-hidden="true">→</span>
                            <span>{nodesByKey.get(edge.target)?.label ?? edge.target}</span>
                            {#if edge.source === edge.target}<span class="loom-loop">Self-loop</span>{/if}
                          </li>
                        {/each}
                      </ul>
                    {:else}
                      <p>No outgoing permission declared</p>
                    {/if}
                  </div>
                </li>
              {:else}
                <li class="loom-empty-score">This revision declares no stations.</li>
              {/each}
            </ol>
          </details>
        </div>

        <div class="loom-detail-column">
          {#if canvasGraph.nodes.length && inspectorOpen}{@render viewsBar()}{/if}
          <div class="inspector-seam">
            <button type="button" aria-label={inspectorOpen ? "Collapse station inspector" : "Expand station inspector"}
              aria-expanded={inspectorOpen} aria-controls={`${uid}-inspector`} title={inspectorOpen ? "Collapse station inspector" : "Expand station inspector"}
              onclick={() => inspectorOpen = !inspectorOpen}>{inspectorOpen !== inspectorLeft ? "›" : "‹"}</button>
          </div>
          {#if inspectorOpen}
          <PaneGrip bind:width={inspectorWidth} name="Station inspector width" side={inspectorLeft ? "left" : "right"} min={208} max={480} />
          <aside id={`${uid}-inspector`} class="loom-inspector" aria-label="Selected station">
            {#if selectedNode}
              <span class="loom-eyebrow">{selectedNode.kind}</span>
              <button class="swap-panels" type="button" title="Swap Map and station inspector" aria-label="Swap Map and station inspector"
                onclick={() => inspectorLeft = !inspectorLeft}>⇄</button>
              <h3 id={`${uid}-station-title`} tabindex="-1">{selectedNode.label}</h3>
              <div class="loom-inspector-identity">
                <code>{selectedNode.id}</code><span class="loom-kind">{selectedNode.kind}</span>
                {#if selectedNode.id === view.entry_node}<span>Entry</span>{/if}
              </div>
              <section class="loom-permissions" aria-labelledby={`${uid}-incoming-title`}>
                <h4 id={`${uid}-incoming-title`}>Incoming permissions <span>{incoming.length}</span></h4>
                <ul aria-label="Incoming permissions">
                  {#each incoming as edge (edge.id)}
                    <li>
                      <div class="loom-permission-route">
                        {#if nodesByKey.has(edge.source)}
                          <button type="button" onclick={() => inspectStation(edge.source)} aria-label={`Inspect ${nodesByKey.get(edge.source)?.label} (${edge.source})`}>{nodesByKey.get(edge.source)?.label}</button>
                        {:else}<code>{edge.source}</code>{/if}
                        <span aria-hidden="true">→</span><span>{selectedNode.label}</span>
                      </div>
                      <div class="loom-permission-identity"><code>{edge.source} → {edge.target}</code><span>{edge.label}</span></div>
                      {#if edge.source === edge.target}<span class="loom-loop">Self-loop</span>{/if}
                    </li>
                  {:else}<li class="loom-no-permission">No incoming permission declared</li>{/each}
                </ul>
              </section>
              <section class="loom-permissions" aria-labelledby={`${uid}-outgoing-title`}>
                <h4 id={`${uid}-outgoing-title`}>Outgoing permissions <span>{outgoing.length}</span></h4>
                <ul aria-label="Outgoing permissions">
                  {#each outgoing as edge (edge.id)}
                    <li>
                      <div class="loom-permission-route">
                        <span>{selectedNode.label}</span><span aria-hidden="true">→</span>
                        {#if nodesByKey.has(edge.target)}
                          <button type="button" onclick={() => inspectStation(edge.target)} aria-label={`Inspect ${nodesByKey.get(edge.target)?.label} (${edge.target})`}>{nodesByKey.get(edge.target)?.label}</button>
                        {:else}<code>{edge.target}</code>{/if}
                      </div>
                      <div class="loom-permission-identity"><code>{edge.source} → {edge.target}</code><span>{edge.label}</span></div>
                      {#if edge.source === edge.target}<span class="loom-loop">Self-loop</span>{/if}
                    </li>
                  {:else}<li class="loom-no-permission">No outgoing permission declared</li>{/each}
                </ul>
              </section>
              {#if selectedSchema}<SchemaFields source={selectedSchema} title="Declared output schema" />{/if}
              <p class="loom-inspector-note">Permissions describe what this Pattern allows. Observed movement belongs to a Run in Orb.</p>
              <button class="loom-back" type="button" onclick={() => { selectView("affect"); document.getElementById(`${uid}-affect-tab`)?.focus(); }}>Inspect affect coverage &amp; Crucible example</button>
              <button class="loom-back" type="button" onclick={returnToStation}>← Back to selected station</button>
            {:else}
              <h3>No station selected</h3>
              <p class="loom-inspector-note">This revision has no declared stations to inspect.</p>
            {/if}
          </aside>
          {#if view.binding}<section class="loom-source" aria-label="Pattern inspection binding"><h3>Inspection binding</h3><dl>
            <dt>Availability</dt><dd>{view.binding.executable ? "Executable in this Vessel" : "Observation only · not executable in this Vessel"}</dd>
            <dt>Publication</dt><dd>{view.binding.publication}</dd><dt>Source</dt><dd>{view.binding.source_id}</dd><dt>Registrant</dt><dd>{view.binding.registrant_id}</dd><dt>Source generation</dt><dd>{view.binding.source_generation}</dd><dt>Profile</dt><dd>{view.binding.profile_id}@{view.binding.profile_revision}</dd>
          </dl><p class="loom-canvas-note">Inspection grants no routing, admission or resume authority. This binding does not change the Pattern digest.</p></section>{/if}
          <details class="loom-source">
            <summary>Identity &amp; source</summary>
            <p class="loom-canvas-note">{view.description}</p>
            <dl>
              <dt>Checkpoint</dt><dd>{view.checkpoint_schema}</dd>
              <dt>Entry</dt><dd>{view.entry_node}</dd>
              <dt>Implementation</dt><dd>{view.implementation_revision}</dd>
              <dt>Digest</dt><dd><code>{view.digest}</code></dd>
              <dt>Trigger</dt><dd>{view.trigger_hint}</dd>
              <dt>Source</dt><dd><a href={`/api/v1/loom/source/patterns/${encodeURIComponent(view.pattern_id)}/${encodeURIComponent(view.revision)}${inspectionQuery(view.binding)}`}>Mermaid source →</a></dd>
            </dl>
          </details>
          {/if}
        </div>
      </div>
      </div>
      {/if}
    {:else}
      <div class="loom-read-state">
        <span class="loom-eyebrow">Registry empty</span>
        <h2>No Pattern revisions are registered</h2>
        <p>Registered revisions will appear here when the registry provides them.</p>
      </div>
    {/if}
  </section>
  {/if}
</div>

<style>
  .loom-workspace { display:block; min-width:0; padding:0; }
  .graph-title { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
  .pattern-identity { display:grid; gap:.25rem; padding:.35rem .25rem .8rem; }
  .pattern-identity h2 { margin:0; font:500 1.2rem/1.15 var(--font-rune); color:var(--color-bone); }
  .pattern-identity code { color:var(--color-ash); font:10px var(--font-glyph); }
  .pattern-identity a,.pattern-identity p { font-size:11px; }
  .design-link { display:inline-block; margin-bottom:.55rem; padding:.3rem .45rem; font-size:12px; border:1px solid var(--color-engraving); border-radius:4px; text-decoration:none; }
  .standalone-library,.standalone-tools { max-width:28rem; padding:0 .85rem; }
  .loom-views { display:flex; flex-wrap:wrap; gap:.15rem; border-bottom:1px solid var(--color-engraving); }
  .loom-views button { padding:.5rem .55rem; background:transparent; color:var(--color-ash); border:0; border-bottom:2px solid transparent; font-size:12px; }
  .loom-views button[aria-selected="true"] { color:var(--color-bone); border-bottom-color:var(--color-accent); }
  .loom-workspace :is(a,button,summary,h3):focus-visible { outline:2px solid var(--color-rune); outline-offset:4px; }
  .loom-workspace :is(p,h2,h3,h4,code,strong,span,dd) { overflow-wrap:anywhere; }
  .loom-workspace button { cursor:pointer; font:inherit; }
  .loom-workspace a { color:var(--color-rune); }
  .loom-reading,.loom-graph-column,.loom-detail-column { min-width:0; }
  .loom-eyebrow { display:block; color:var(--color-ash); font-size:11px; letter-spacing:.07em; text-transform:uppercase; }
  .loom-score-layout { display:grid; grid-template-columns:minmax(0,1fr) min(var(--inspector-width),36%); align-items:start; gap:0; }
  .loom-score-layout.inspector-left { grid-template-columns:min(var(--inspector-width),36%) minmax(0,1fr); }
  .inspector-left .loom-detail-column { grid-column:1; grid-row:1; }
  .inspector-left .loom-graph-column { grid-column:2; grid-row:1; }
  .loom-score-layout.inspector-folded { grid-template-columns:minmax(0,1fr) 1.5rem; gap:.5rem; }
  .loom-score-layout.inspector-folded.inspector-left { grid-template-columns:1.5rem minmax(0,1fr); }
  .map-stations summary { padding:.35rem 0; color:var(--color-ash); font-size:12px; cursor:pointer; }
  .map-stations button { display:flex; width:100%; gap:.3rem; align-items:baseline; justify-content:space-between; text-align:left; font-size:12px; color:var(--color-parchment); background:transparent; border:1px solid transparent; padding:.4rem; }
  .map-stations button[aria-pressed="true"] { color:var(--color-rune); border-color:var(--color-control-border); }
  .map-stations small { color:var(--color-ash); font-size:10px; }
  .inspector-seam { position:absolute; z-index:6; top:.4rem; inset-inline-start:-.6rem; }
  .inspector-seam button,.swap-panels { border:1px solid var(--color-control-border); border-radius:4px; padding:.35rem; background:var(--color-obsidian); color:var(--color-bone); }
  .inspector-left .inspector-seam { inset-inline:auto -1rem; }
  .swap-panels { float:inline-end; }
  .loom-graph-column,.loom-detail-column { display:grid; gap:1.25rem; }
  .loom-canvas-panel,.loom-outline,.loom-inspector,.loom-source { min-width:0; border:0; border-radius:0; background:transparent; }
  .loom-canvas-panel { overflow:hidden; background:var(--color-void); }
  .loom-score-guide,.loom-canvas-note { color:var(--color-ash); font-size:12px; line-height:1.7; }
  .loom-levels { display:flex; align-items:center; flex-wrap:wrap; gap:.35rem; padding:.55rem .65rem; border:1px solid var(--color-engraving); border-radius:6px; background:var(--color-obsidian); color:var(--color-ash); font-size:12px; }
  .loom-levels button { min-height:34px; padding:.35rem .65rem; border:1px solid transparent; border-radius:4px; background:transparent; color:var(--color-parchment); }
  .loom-levels button[aria-pressed="true"] { border-color:var(--color-control-border); background:var(--color-obsidian-2); color:var(--color-bone); }
  .loom-levels button:hover { color:var(--color-rune); }
  .loom-level-hint { margin-left:auto; padding:.3rem; }
  .loom-flow-mount { min-width:0; }
  .loom-empty-graph { display:grid; place-content:center; min-height:29rem; padding:2rem; text-align:center; color:var(--color-parchment); }
  .loom-canvas-note { padding:.75rem 0; border-top:1px solid var(--color-engraving); }
  .loom-outline { border-block:1px solid var(--color-engraving); }
  .loom-outline > summary,.loom-source summary { padding:1rem 0; color:var(--color-bone); cursor:pointer; font-size:13px; }
  .loom-outline > summary span { float:right; margin-left:.6rem; color:var(--color-ash); font-size:12px; }
  .loom-score-guide { padding:.2rem 0 1rem; }
  .loom-stations { margin:0; padding:0; list-style:none; }
  .loom-station { padding:0 .75rem 1rem; border-top:1px solid var(--color-engraving); }
  .loom-station[data-selected="true"] { background:color-mix(in srgb,var(--color-rune) 5%,var(--color-void)); box-shadow:inset 2px 0 var(--color-rune); }
  .loom-station-select { display:flex; width:100%; text-align:left; align-items:flex-start; gap:.8rem; padding:1rem 0 .75rem; border:0; background:transparent; color:var(--color-bone); }
  .loom-station-select:hover .loom-station-identity strong { color:var(--color-rune); }
  .loom-station-number { padding-top:.15rem; color:var(--color-ash); font:11px/1.6 var(--font-glyph); }
  .loom-station-identity { flex:1; min-width:0; }
  .loom-station-identity strong { display:block; font-size:14px; font-weight:500; }
  .loom-station-identity code { display:block; margin-top:.3rem; color:var(--color-ash); font-size:12px; }
  .loom-station-tags { display:flex; flex-direction:column; align-items:flex-end; gap:.4rem; max-width:35%; color:var(--color-ash); font-size:11px; }
  .loom-kind { display:inline-block; font-family:var(--font-glyph); }
  .loom-selection-mark { color:var(--color-rune); }
  .loom-successors { margin-left:1.8rem; font-size:13px; color:var(--color-parchment); }
  .loom-field-label { display:block; margin-bottom:.4rem; color:var(--color-ash); font-size:11px; }
  .loom-successors ul { display:flex; flex-wrap:wrap; gap:.4rem 1rem; list-style:none; padding:0; }
  .loom-successors li { display:flex; flex-wrap:wrap; align-items:baseline; gap:.4rem; }
  .loom-loop { display:inline-block; color:var(--color-ash); font-size:11px; border:1px solid var(--color-engraving); border-radius:3px; padding:.1rem .35rem; }
  .loom-detail-column { position:relative; min-height:16rem; padding-inline-start:1rem; border-inline-start:1px solid var(--color-engraving); }
  .loom-inspector { padding:0; }
  .loom-inspector h3 { margin:.6rem 0 .8rem; color:var(--color-bone); font:600 1.2rem/1.3 var(--font-body); letter-spacing:-.025em; scroll-margin-top:1rem; }
  .loom-inspector-identity { display:flex; align-items:center; flex-wrap:wrap; gap:.5rem; margin-bottom:1.25rem; font-size:12px; }
  .loom-permissions { border-top:1px solid var(--color-engraving); padding:1rem 0; }
  .loom-permissions h4 { display:flex; justify-content:space-between; gap:.5rem; color:var(--color-bone); font-size:13px; font-weight:500; }
  .loom-permissions h4 span { color:var(--color-ash); font-weight:400; }
  .loom-permissions ul { display:grid; gap:1rem; list-style:none; padding:0; margin-top:.85rem; }
  .loom-permissions li { min-width:0; }
  .loom-permission-route { display:flex; flex-wrap:wrap; align-items:baseline; gap:.3rem .5rem; color:var(--color-bone); font-size:13px; line-height:1.6; }
  .loom-permission-route button { padding:.2rem 0; border:0; background:none; color:var(--color-rune); text-align:left; text-decoration:underline; text-underline-offset:.2em; overflow-wrap:anywhere; }
  .loom-permission-identity { display:flex; flex-wrap:wrap; gap:.35rem .65rem; color:var(--color-ash); font-size:11px; line-height:1.7; }
  .loom-no-permission { color:var(--color-ash); font-size:13px; }
  .loom-inspector-note { border-top:1px solid var(--color-engraving); padding-top:1rem; color:var(--color-parchment); font-size:12px; line-height:1.7; }
  .loom-back { display:block; min-height:38px; margin-top:.8rem; padding:.5rem .7rem; border:1px solid var(--color-control-border); border-radius:5px; background:var(--color-obsidian); color:var(--color-rune); text-align:left; font-size:12px; }
  .loom-source { border-top:1px solid var(--color-engraving); }
  .loom-source > h3 { padding:1rem 0 0; font:500 13px var(--font-body); }
  .loom-source dl { display:grid; gap:.4rem; padding:0 0 1rem; font-size:12px; }
  .loom-source dt { margin-top:.6rem; color:var(--color-ash); }
  .loom-source dd { min-width:0; margin:0; color:var(--color-bone); line-height:1.6; }
  .loom-button { min-height:40px; padding:.5rem .9rem; border:1px solid var(--color-bone); border-radius:5px; background:var(--color-bone); color:var(--color-void); }
  .loom-button:hover { border-color:var(--color-rune); }
  .loom-read-state { padding:clamp(1.5rem,4vw,3.5rem) 0; border:0; background:transparent; }
  .loom-read-state h2 { margin:.65rem 0 1rem; font:600 clamp(1.5rem,3vw,2.5rem)/1.2 var(--font-body); letter-spacing:-.035em; }
  .loom-read-state p { max-width:40rem; color:var(--color-parchment); font-size:14px; line-height:1.7; }
  .loom-read-state .loom-button { margin-top:1.25rem; }
  .loom-empty-score { padding:1.25rem 0; color:var(--color-parchment); }

  @media(max-width:48rem) { .loom-graph-column { display:flex; flex-direction:column; } .loom-outline { order:-1; } .loom-detail-column { grid-template-columns:minmax(0,1fr); } .loom-outline > summary span { float:none; display:block; margin:.35rem 0 0; } .loom-station { padding-inline:.65rem; } .loom-station-tags { max-width:30%; } .loom-level-hint { flex-basis:100%; margin-left:0; } }
  @container work-area (max-width:42rem) {
    .loom-score-layout,.loom-score-layout.inspector-left,.loom-score-layout.inspector-folded { grid-template-columns:minmax(0,1fr); }
    .loom-score-layout :is(.loom-detail-column,.loom-graph-column) { grid-column:1; grid-row:auto; }
    .loom-detail-column { min-height:2rem; padding:1rem 0 0; border:0; border-top:1px solid var(--color-engraving); }
    .inspector-seam,.inspector-left .inspector-seam { top:.1rem; inset-inline:.1rem auto; }
  }
  @container work-area (max-width:48rem) { .loom-graph-column { display:flex; flex-direction:column; } .loom-outline { order:-1; } .loom-detail-column { grid-template-columns:minmax(0,1fr); } .loom-outline > summary span { float:none; display:block; margin:.35rem 0 0; } .loom-station { padding-inline:.65rem; } .loom-station-tags { max-width:30%; } .loom-level-hint { flex-basis:100%; margin-left:0; } }
</style>
