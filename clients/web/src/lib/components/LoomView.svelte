<script lang="ts">
  import { inspectionSelection, sameInspectionBinding, inspectionQuery, type InspectionSelection } from "$lib/api/inspection";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { navigationId, orbReturnHref, loomOriginHref } from "$lib/navigation/instruments";
  import { getContext, onDestroy, tick, untrack } from "svelte";
  import { workCommandKey, type CommandTarget, type CommandResult, type WorkCommandRegistry } from "$lib/bridge/work-commands";
  import { parseLoomCommand } from "$lib/graph/loom-commands";
  import { MediaQuery } from "svelte/reactivity";
  import { loomProjection } from "$lib/graph/loom";
  import { matchesOrbPattern } from "$lib/graph/orb";

  import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
  import type {
    LoomSummary,
    LoomView as LoomProjection,
    OrbRunSnapshot
  } from "$lib/api/models";
  import GraphCanvas from "./graph/GraphCanvas.svelte";
  import DelegateMark from "./DelegateMark.svelte";

  let {
    patternId,
    revision
  }: {
    patternId?: string;
    revision?: string;
  } = $props();
  const workCommands = getContext<WorkCommandRegistry | undefined>(workCommandKey);
  let unregisterCommands: (() => void) | undefined;
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let catalogue = $state.raw<LoomSummary[]>([]);
  let view = $state.raw<LoomProjection | null>(null);
  let sourceRun = $state.raw<OrbRunSnapshot | null>(null);
  let loading = $state(true);
  let error = $state("");
  const compact = new MediaQuery("(max-width: 48rem)");
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
      if (loading || error || view !== loaded || version !== loadVersion ||
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
          ? getOrbRun(requestedRun, { limit: 1 }).catch(() => null)
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
      if ((!requestedPattern || !requestedRevision) && (!requestedHint || requestedRun)) {
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
  <header class="loom-workspace-heading">
    <div class="loom-workspace-title"><h1>Loom</h1><span>Pattern topology</span></div>
    <details class="loom-catalogue">
      <summary>Pattern library <span>{catalogue.length}</span></summary>
      <nav aria-label="Pattern revisions">
        {#each catalogue as pattern (pattern.detail_path)}
          <a
            aria-current={view?.pattern_id === pattern.pattern_id && view?.revision === pattern.revision && sameInspectionBinding(view?.binding, pattern.binding) ? "page" : undefined}
            class="loom-pattern"
            href={pattern.detail_path}
          >
            <strong>{pattern.title}</strong>
            <code>{pattern.pattern_id}@{pattern.revision}</code>
            {#if pattern.binding}<span>{pattern.binding.executable ? "Executable in this Vessel" : "Observation only"} · {pattern.binding.profile_id}@{pattern.binding.profile_revision}</span>{/if}
            <span>{pattern.default ? "Default" : pattern.route_rank != null ? `Route ${pattern.route_rank}` : pattern.active ? "Active route" : "Retained"}</span>
          </a>
        {/each}
      </nav>
    </details>
  </header>

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
      <header class="loom-identity">
        <span class="loom-eyebrow">Registered Pattern</span>
        <div class="loom-title-row">
          <h2>{view.title}</h2>
          <span class="loom-read-only">Read only</span>
        </div>
        <p class="loom-description">{view.description}</p>
        <div class="loom-exact-identity">
          <strong><code>{view.pattern_id}@{view.revision}</code></strong>
          <span>Registered from source</span>
        </div>
        <div class="loom-entry-row">
          <p>Entry <code>{view.entry_node}</code></p>
          {#if returnHref}
            <nav aria-label="Run context"><a href={resolve(returnHref)}>Return to Run in Orb →</a></nav>
          {/if}
        </div>
        {#if sourceContextError}<p class="loom-context-error" role="status">{sourceContextError}</p>{/if}
      </header>

      <div class="loom-score-layout">
        <div class="loom-graph-column">
          <section class="loom-canvas-panel" aria-labelledby={`${uid}-graph-title`}>
            <header class="loom-section-head">
              <h3 id={`${uid}-graph-title`} tabindex="-1">Pattern graph</h3>
              <p>{graph.nodes.length} stations · {graph.edges.length} permissions</p>
            </header>
            <div class="loom-levels" role="group" aria-label="Graph detail">
              <button type="button" aria-pressed={canvasLevel === "pattern"} onclick={() => setCanvasLevel("pattern")}>Whole Pattern</button>
              <span aria-hidden="true">/</span>
              <button type="button" aria-pressed={canvasLevel === "stations"} onclick={() => setCanvasLevel("stations")}>Stations</button>
              <span class="loom-level-hint">{canvasLevel === "pattern" ? "Zoom in to reveal stations" : "Zoom out to fold the Pattern"}</span>
            </div>
            <div class="loom-flow-mount">
              {#if canvasGraph.nodes.length}
                <GraphCanvas {focusId} {focusRevision} projection={canvasGraph} selectedId={canvasSelectedId} onselect={selectCanvasNode} onzoom={zoomLevel} label={`${view.title} Pattern graph`} --graph-height="clamp(22rem, 48dvh, 40rem)" />
              {:else}
                <p class="loom-empty-graph">No stations declared in this Pattern revision.</p>
              {/if}
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
          <aside id={`${uid}-inspector`} class="loom-inspector" aria-label="Selected station">
            {#if selectedNode}
              <span class="loom-eyebrow">Selected station</span>
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
              <p class="loom-inspector-note">Permissions describe what this Pattern allows. Observed movement belongs to a Run in Orb.</p>
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
            <dl>
              <dt>Checkpoint</dt><dd>{view.checkpoint_schema}</dd>
              <dt>Entry</dt><dd>{view.entry_node}</dd>
              <dt>Implementation</dt><dd>{view.implementation_revision}</dd>
              <dt>Digest</dt><dd><code>{view.digest}</code></dd>
              <dt>Trigger</dt><dd>{view.trigger_hint}</dd>
              <dt>Source</dt><dd><a href={`/api/v1/loom/source/patterns/${encodeURIComponent(view.pattern_id)}/${encodeURIComponent(view.revision)}${inspectionQuery(view.binding)}`}>Mermaid source →</a></dd>
            </dl>
          </details>
        </div>
      </div>
    {:else}
      <div class="loom-read-state">
        <span class="loom-eyebrow">Registry empty</span>
        <h2>No Pattern revisions are registered</h2>
        <p>Registered revisions will appear here when the registry provides them.</p>
      </div>
    {/if}
  </section>
</div>

<style>
.loom-workspace { display:block; min-width:0; }
  .loom-workspace :is(a,button,summary,h3):focus-visible { outline:2px solid var(--color-rune); outline-offset:4px; }
  .loom-workspace :is(p,h2,h3,h4,code,strong,span,dd) { overflow-wrap:anywhere; }
  .loom-workspace button { cursor:pointer; font:inherit; }
  .loom-workspace a { color:var(--color-rune); }
  .loom-workspace-heading { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
  .loom-workspace-title { display:flex; flex-wrap:wrap; align-items:baseline; gap:.5rem 1rem; }
  .loom-workspace-title h1 { color:var(--color-bone); font:600 1.5rem/1.25 var(--font-body); letter-spacing:-.04em; }
  .loom-workspace-title > span { color:var(--color-ash); font-size:12px; }
  .loom-catalogue { position:relative; z-index:5; flex:0 0 auto; max-width:100%; }
  .loom-catalogue summary { min-height:38px; padding:.55rem .8rem; border:1px solid var(--color-control-border); border-radius:5px; color:var(--color-bone); background:var(--color-obsidian); cursor:pointer; font-size:13px; }
  .loom-catalogue summary span { margin-left:.5rem; color:var(--color-ash); }
  .loom-catalogue nav { position:absolute; right:0; top:calc(100% + .6rem); width:min(25rem,80vw); max-height:28rem; overflow-y:auto; display:grid; gap:.2rem; padding:.5rem; background:var(--color-obsidian); border:1px solid var(--color-control-border); border-radius:7px; box-shadow:0 16px 48px #0008; }
  .loom-pattern { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:baseline; gap:.35rem .7rem; min-width:0; padding:.8rem; border:1px solid transparent; border-radius:4px; text-decoration:none; }
  .loom-pattern strong { grid-column:1/-1; color:var(--color-bone); font-size:14px; font-weight:500; }
  .loom-pattern code,.loom-pattern span { color:var(--color-ash); font-size:12px; }
  .loom-pattern:hover { background:var(--color-obsidian-2); }
  .loom-pattern[aria-current="page"] { background:var(--color-obsidian-2); border-color:var(--color-engraving); box-shadow:inset 2px 0 var(--color-rune); }
  .loom-reading,.loom-graph-column,.loom-detail-column { min-width:0; }
  .loom-eyebrow { display:block; color:var(--color-ash); font-size:11px; letter-spacing:.07em; text-transform:uppercase; }
  .loom-identity { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:baseline; gap:.5rem 1.5rem; padding:0 0 1.25rem; }
  .loom-identity > .loom-eyebrow { grid-column:1/-1; }
  .loom-identity .loom-title-row { grid-column:1; grid-row:2; margin:0; }
  .loom-identity .loom-exact-identity { grid-column:2; grid-row:2; justify-content:flex-end; margin:0; }
  .loom-identity .loom-description { grid-column:1; grid-row:3; }
  .loom-identity .loom-entry-row { grid-column:2; grid-row:3; margin:0; justify-content:flex-end; }
  .loom-identity .loom-context-error { grid-column:1/-1; }
  .loom-title-row { display:flex; align-items:center; flex-wrap:wrap; gap:.8rem; margin:.45rem 0 .6rem; }
  .loom-title-row h2 { color:var(--color-bone); font:600 clamp(1.4rem,2.5vw,2rem)/1.2 var(--font-body); letter-spacing:-.035em; }
  .loom-read-only,.loom-kind { color:var(--color-ash); border:1px solid var(--color-control-border); border-radius:4px; padding:.2rem .45rem; font-size:11px; }
  .loom-description { max-width:58rem; color:var(--color-parchment); font-size:14px; line-height:1.7; }
  .loom-exact-identity { display:flex; align-items:baseline; flex-wrap:wrap; gap:.5rem 1rem; margin-top:.85rem; color:var(--color-ash); font-size:12px; }
  .loom-exact-identity strong { color:var(--color-bone); font-weight:500; }
  .loom-entry-row { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:.6rem; margin-top:.55rem; font-size:12px; }
  .loom-entry-row p { color:var(--color-ash); }
  .loom-entry-row code { margin-left:.45rem; color:var(--color-bone); }
  .loom-context-error { margin-top:.85rem; color:var(--color-parchment); border-left:2px solid var(--color-heat); padding-left:.8rem; font-size:13px; line-height:1.6; }
  .loom-score-layout { display:grid; grid-template-columns:minmax(0,1fr) 20rem; align-items:start; gap:1.75rem; }
  .loom-graph-column,.loom-detail-column { display:grid; gap:1.25rem; }
  .loom-canvas-panel,.loom-outline,.loom-inspector,.loom-source { min-width:0; border:0; border-radius:0; background:transparent; }
  .loom-canvas-panel { overflow:hidden; background:#000; }
  .loom-section-head { display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; gap:.4rem 1rem; padding:0 0 .75rem; }
  .loom-section-head h3 { color:var(--color-bone); font:600 14px/1.5 var(--font-body); letter-spacing:-.01em; }
  .loom-section-head p,.loom-score-guide,.loom-canvas-note { color:var(--color-ash); font-size:12px; line-height:1.7; }
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
  .loom-detail-column { padding-inline-start:1.4rem; border-inline-start:1px solid var(--color-engraving); }
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
  @container work-area (max-width:42rem) { .loom-identity { grid-template-columns:minmax(0,1fr); gap:.65rem; } .loom-identity :is(.loom-title-row,.loom-exact-identity,.loom-description,.loom-entry-row) { grid-column:1; grid-row:auto; justify-content:flex-start; } }
  @media(max-width:65rem) { .loom-score-layout { grid-template-columns:minmax(0,1fr); } .loom-detail-column { grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); align-items:start; padding-inline-start:0; border-inline-start:0; border-top:1px solid var(--color-engraving); padding-top:1rem; } }
  @media(max-width:48rem) { .loom-workspace-heading { flex-wrap:wrap; margin-bottom:1.2rem; } .loom-catalogue nav { right:auto; left:0; } .loom-graph-column { display:flex; flex-direction:column; } .loom-outline { order:-1; } .loom-detail-column { grid-template-columns:minmax(0,1fr); } .loom-outline > summary span { float:none; display:block; margin:.35rem 0 0; } .loom-station { padding-inline:.65rem; } .loom-station-tags { max-width:30%; } .loom-level-hint { flex-basis:100%; margin-left:0; } }
  @container work-area (max-width:65rem) { .loom-score-layout { grid-template-columns:minmax(0,1fr); } .loom-detail-column { grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); align-items:start; padding-inline-start:0; border-inline-start:0; border-top:1px solid var(--color-engraving); padding-top:1rem; } }
  @container work-area (max-width:48rem) { .loom-workspace-heading { flex-wrap:wrap; margin-bottom:1.2rem; } .loom-catalogue nav { right:auto; left:0; width:min(25rem,calc(100cqw - 2rem)); } .loom-graph-column { display:flex; flex-direction:column; } .loom-outline { order:-1; } .loom-detail-column { grid-template-columns:minmax(0,1fr); } .loom-outline > summary span { float:none; display:block; margin:.35rem 0 0; } .loom-station { padding-inline:.65rem; } .loom-station-tags { max-width:30%; } .loom-level-hint { flex-basis:100%; margin-left:0; } }
</style>
