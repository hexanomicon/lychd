<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { resolve } from "$app/paths";
  import { navigationId, orbReturnHref, loomOriginHref } from "$lib/navigation/instruments";
  import { onDestroy, tick } from "svelte";
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
  let returnHref = $derived(sourceRun ? orbReturnHref(sourceRun.run.run_id, page.url.search) : null);

  $effect(() => {
    void load(patternId, revision, sourceRunId, sourceRunHint);
  });

  onDestroy(() => {
    loadVersion++;
  });

  function stationId(key: string) {
    return `${uid}-station-${encodeURIComponent(key)}`;
  }

  function zoomLevel(zoom: number) {
    if (canvasLevel === "stations" && zoom < 0.55) canvasLevel = "pattern";
    else if (canvasLevel === "pattern" && zoom > 0.85) canvasLevel = "stations";
  }

  async function selectCanvasNode(key: string, opener?: HTMLElement) {
    if (canvasLevel === "pattern") {
      const version = loadVersion;
      canvasLevel = "stations";
      await tick();
      if (version === loadVersion) document.getElementById(`${uid}-station-title`)?.focus();
    } else await inspectStation(key, opener);
  }

  async function inspectStation(key: string, opener?: HTMLElement) {
    if (!nodesByKey.has(key)) return;
    const version = loadVersion;
    selectedKey = key;
    stationOpener = opener ? { key, element: opener } : null;
    await tick();
    if (version === loadVersion && selectedKey === key) {
      document.getElementById(`${uid}-station-title`)?.focus();
    }
  }

  async function returnToStation() {
    if (!selectedKey) return;
    if (stationOpener?.key === selectedKey && stationOpener.element.isConnected &&
        !stationOpener.element.closest("details:not([open])")) {
      stationOpener.element.focus();
      return;
    }
    outlineMode = "open";
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
    requestedHint?: string | null
  ) {
    const version = ++loadVersion;
    loading = true;
    error = "";
    view = null;
    selectedKey = null;
    canvasLevel = "stations";
    stationOpener = null;
    sourceRun = null;
    sourceContextError = requestedHint && !requestedRun ? "Run context unavailable — the linked identity is invalid." : "";
    try {
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
      const next = await getLoomPatternRevision(selected.pattern_id, selected.revision);
      if (version !== loadVersion) return;
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
        const exactPath = `/loom/${next.pattern_id}/${next.revision}`;
        await goto(
          requestedRun
            ? loomOriginHref(exactPath, requestedRun, page.url.search) ?? exactPath
            : exactPath,
          {
          replaceState: true
          }
        );
      }
    } catch (cause) {
      if (version === loadVersion) {
        error = cause instanceof Error ? cause.message : "The Loom cannot be read.";
      }
    } finally {
      if (version === loadVersion) loading = false;
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
        {#each catalogue as pattern (`${pattern.pattern_id}@${pattern.revision}`)}
          <a
            aria-current={view?.pattern_id === pattern.pattern_id && view?.revision === pattern.revision ? "page" : undefined}
            class="loom-pattern"
            href={pattern.detail_path}
          >
            <strong>{pattern.title}</strong>
            <code>{pattern.pattern_id}@{pattern.revision}</code>
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
        <button class="loom-button" type="button" onclick={() => load(patternId, revision, sourceRunId, sourceRunHint)}>Retry reading Pattern</button>
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
              <h3 id={`${uid}-graph-title`}>Pattern graph</h3>
              <p>{graph.nodes.length} stations · {graph.edges.length} permissions</p>
            </header>
            <div class="loom-levels" role="group" aria-label="Graph detail">
              <button type="button" aria-pressed={canvasLevel === "pattern"} onclick={() => (canvasLevel = "pattern")}>Whole Pattern</button>
              <span aria-hidden="true">/</span>
              <button type="button" aria-pressed={canvasLevel === "stations"} onclick={() => (canvasLevel = "stations")}>Stations</button>
              <span class="loom-level-hint">{canvasLevel === "pattern" ? "Zoom in to reveal stations" : "Zoom out to fold the Pattern"}</span>
            </div>
            <div class="loom-flow-mount">
              {#if canvasGraph.nodes.length}
                <GraphCanvas projection={canvasGraph} selectedId={canvasSelectedId} onselect={selectCanvasNode} onzoom={zoomLevel} label={`${view.title} Pattern graph`} --graph-height="clamp(29rem, 59vh, 48rem)" />
              {:else}
                <p class="loom-empty-graph">No stations declared in this Pattern revision.</p>
              {/if}
            </div>
            <p class="loom-canvas-note">Read-only layout · Connections are declared permissions</p>
          </section>
          <details class="loom-outline" open={outlineOpen} ontoggle={(event) => {
            if (!event.currentTarget.isConnected) return;
            if (event.currentTarget.open !== outlineOpen) outlineMode = event.currentTarget.open ? "open" : "closed";
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
          <details class="loom-source">
            <summary>Identity &amp; source</summary>
            <dl>
              <dt>Checkpoint</dt><dd>{view.checkpoint_schema}</dd>
              <dt>Entry</dt><dd>{view.entry_node}</dd>
              <dt>Implementation</dt><dd>{view.implementation_revision}</dd>
              <dt>Digest</dt><dd><code>{view.digest}</code></dd>
              <dt>Trigger</dt><dd>{view.trigger_hint}</dd>
              <dt>Source</dt><dd><a href="/api/v1/loom/source/patterns/{view.pattern_id}/{view.revision}">Mermaid source →</a></dd>
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
  .loom-workspace { display: block; min-width: 0; }
  .loom-workspace :is(a, button, summary, h3):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 4px; }
  .loom-workspace :is(p, h2, h3, h4, code, strong, span, dd) { overflow-wrap: anywhere; }
  .loom-workspace button { cursor: pointer; font: inherit; }
  .loom-workspace a { color: var(--color-rune); }
  .loom-workspace-heading { display: flex; align-items: start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
  .loom-workspace-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem 1rem; }
  .loom-workspace-title h1 { color: var(--color-bone); font: 600 1.6rem/1.25 var(--font-body); }
  .loom-workspace-title > span { color: var(--color-parchment); font-size: 0.8125rem; }
  .loom-catalogue { position: relative; z-index: 5; flex: 0 0 auto; max-width: 100%; }
  .loom-catalogue summary { padding: 0.55rem 0.75rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); color: var(--color-bone); cursor: pointer; font-size: 0.8125rem; }
  .loom-catalogue summary span { margin-left: 0.4rem; color: var(--color-parchment); }
  .loom-catalogue nav { position: absolute; right: 0; top: calc(100% + 0.4rem); width: min(22rem, 80vw); max-height: 24rem; overflow-y: auto; display: grid; gap: 0.3rem; padding: 0.5rem; background: var(--color-obsidian); border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); }
  .loom-pattern { display: grid; gap: 0.3rem; min-width: 0; padding: 0.8rem; border: 1px solid transparent; border-radius: var(--radius-block); text-decoration: none; }
  .loom-pattern strong { font-size: 0.875rem; font-weight: 500; color: var(--color-bone); }
  .loom-pattern code, .loom-pattern span { color: var(--color-parchment); font-size: 0.75rem; }
  .loom-pattern:hover { background: var(--color-obsidian-2); }
  .loom-pattern[aria-current="page"] { border-color: var(--color-engraving); box-shadow: inset 3px 0 var(--color-rune); }
  .loom-reading, .loom-graph-column, .loom-detail-column { min-width: 0; }
  .loom-eyebrow { display: block; color: var(--color-parchment); font-size: 0.6875rem; letter-spacing: 0.12em; text-transform: uppercase; }
  .loom-identity { padding: 0 0 1rem; }
  .loom-title-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0.65rem; margin: 0.3rem 0 0.45rem; }
  .loom-title-row h2 { color: var(--color-bone); font: 600 1.45rem/1.2 var(--font-body); }
  .loom-read-only, .loom-kind { color: var(--color-parchment); border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); padding: 0.15rem 0.4rem; font-size: 0.6875rem; }
  .loom-description { color: var(--color-parchment); max-width: 64rem; font-size: 0.875rem; }
  .loom-exact-identity { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem 1rem; margin-top: 0.7rem; color: var(--color-parchment); font-size: 0.75rem; }
  .loom-exact-identity strong { color: var(--color-bone); font-weight: 500; }
  .loom-entry-row { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.5rem; margin-top: 0.4rem; font-size: 0.75rem; }
  .loom-entry-row p { color: var(--color-parchment); }
  .loom-entry-row code { margin-left: 0.4rem; color: var(--color-bone); }
  .loom-context-error { margin-top: 0.75rem; color: var(--color-parchment); border-left: 2px solid var(--color-heat); padding-left: 0.8rem; }
  .loom-score-layout { display: grid; grid-template-columns: minmax(0, 1fr) 18rem; align-items: start; gap: 0.8rem; }
  .loom-graph-column, .loom-detail-column { display: grid; gap: 0.8rem; }
  .loom-canvas-panel, .loom-outline, .loom-inspector, .loom-source { min-width: 0; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  .loom-canvas-panel { overflow: hidden; }
  .loom-section-head { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 0.4rem 1rem; padding: 0.9rem 1rem; border-bottom: 1px solid var(--color-engraving); }
  .loom-section-head h3 { color: var(--color-bone); font: 500 0.875rem/1.4 var(--font-body); }
  .loom-section-head p, .loom-score-guide, .loom-canvas-note { color: var(--color-parchment); font-size: 0.75rem; }
  .loom-levels { display: flex; align-items: center; flex-wrap: wrap; gap: 0.3rem; padding: 0.45rem 0.8rem; border-bottom: 1px solid var(--color-engraving); color: var(--color-parchment); font-size: 0.75rem; }
  .loom-levels button { border: 1px solid transparent; border-radius: var(--radius-glyph); background: transparent; padding: 0.35rem 0.5rem; color: var(--color-parchment); }
  .loom-levels button[aria-pressed="true"] { border-color: var(--color-rune); background: var(--color-obsidian-2); color: var(--color-rune); }
  .loom-level-hint { margin-left: auto; padding: 0.25rem 0.2rem; }
  .loom-flow-mount { min-width: 0; }
  .loom-empty-graph { display: grid; place-content: center; min-height: 29rem; padding: 2rem; text-align: center; color: var(--color-parchment); }
  .loom-canvas-note { padding: 0.65rem 1rem; border-top: 1px solid var(--color-engraving); }
  .loom-outline > summary, .loom-source summary { padding: 0.9rem 1rem; color: var(--color-bone); cursor: pointer; font-size: 0.8125rem; }
  .loom-outline > summary span { float: right; margin-left: 0.5rem; color: var(--color-parchment); font-size: 0.75rem; }
  .loom-score-guide { padding: 0.2rem 1rem 0.9rem; }
  .loom-stations { margin: 0; padding: 0; list-style: none; }
  .loom-station { padding: 0 1rem 0.9rem; border-top: 1px solid var(--color-engraving); }
  .loom-station[data-selected="true"] { background: color-mix(in srgb, var(--color-rune) 5%, var(--color-obsidian)); box-shadow: inset 3px 0 var(--color-rune); }
  .loom-station-select { display: flex; width: 100%; text-align: left; align-items: flex-start; gap: 0.7rem; padding: 0.9rem 0 0.6rem; border: 0; background: transparent; color: var(--color-bone); }
  .loom-station-select:hover .loom-station-identity strong { color: var(--color-rune); }
  .loom-station-number { padding-top: 0.2rem; color: var(--color-parchment); font: 0.75rem/1.5 var(--font-glyph); }
  .loom-station-identity { flex: 1; min-width: 0; }
  .loom-station-identity strong { display: block; font-size: 0.875rem; font-weight: 500; }
  .loom-station-identity code { display: block; margin-top: 0.15rem; font-size: 0.75rem; color: var(--color-parchment); }
  .loom-station-tags { display: flex; flex-direction: column; align-items: flex-end; gap: 0.35rem; max-width: 35%; color: var(--color-parchment); font-size: 0.75rem; }
  .loom-kind { display: inline-block; font-family: var(--font-glyph); }
  .loom-selection-mark { color: var(--color-rune); }
  .loom-successors { margin-left: 1.8rem; font-size: 0.8125rem; color: var(--color-parchment); }
  .loom-field-label { display: block; margin-bottom: 0.35rem; font-size: 0.75rem; }
  .loom-successors ul { display: flex; flex-wrap: wrap; gap: 0.35rem 1rem; list-style: none; padding: 0; }
  .loom-successors li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem; }
  .loom-loop { display: inline-block; color: var(--color-parchment); font-size: 0.6875rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); padding: 0 0.3rem; }
  .loom-inspector { padding: 1rem; }
  .loom-inspector h3 { margin: 0.6rem 0; color: var(--color-bone); font: 500 1.1rem/1.3 var(--font-body); scroll-margin-top: 1rem; }
  .loom-inspector-identity { display: flex; align-items: center; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 1rem; font-size: 0.75rem; }
  .loom-permissions { border-top: 1px solid var(--color-engraving); padding: 0.85rem 0; }
  .loom-permissions h4 { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.8125rem; font-weight: 500; color: var(--color-bone); }
  .loom-permissions h4 span { color: var(--color-parchment); font-weight: 400; }
  .loom-permissions ul { display: grid; gap: 0.65rem; list-style: none; padding: 0; margin-top: 0.65rem; }
  .loom-permissions li { min-width: 0; }
  .loom-permission-route { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.3rem 0.45rem; color: var(--color-bone); font-size: 0.8125rem; }
  .loom-permission-route button { background: none; border: 0; padding: 0.2rem 0; color: var(--color-rune); text-decoration: underline; text-underline-offset: 0.2em; text-align: left; overflow-wrap: anywhere; }
  .loom-permission-identity { display: flex; flex-wrap: wrap; gap: 0.3rem 0.6rem; color: var(--color-parchment); font-size: 0.6875rem; }
  .loom-no-permission { color: var(--color-parchment); font-size: 0.8125rem; }
  .loom-inspector-note { border-top: 1px solid var(--color-engraving); padding-top: 0.85rem; color: var(--color-parchment); font-size: 0.75rem; line-height: 1.6; }
  .loom-back { display: block; background: none; border: 0; padding: 0.75rem 0 0; text-align: left; color: var(--color-rune); font-size: 0.8125rem; }
  .loom-source dl { display: grid; gap: 0.4rem; padding: 0 1rem 1rem; font-size: 0.75rem; }
  .loom-source dt { margin-top: 0.5rem; color: var(--color-parchment); }
  .loom-source dd { min-width: 0; margin: 0; color: var(--color-bone); }
  .loom-button { min-height: 2.5rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); padding: 0.45rem 0.75rem; background: var(--color-void); color: var(--color-rune); }
  .loom-button:hover { border-color: var(--color-rune); }
  .loom-read-state { padding: 2rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  .loom-read-state h2 { margin: 0.5rem 0 1rem; font: 600 1.75rem/1.3 var(--font-body); }
  .loom-read-state p { color: var(--color-parchment); }
  .loom-read-state .loom-button { margin-top: 1rem; }
  .loom-empty-score { padding: 1.2rem; color: var(--color-parchment); }
  @media (max-width: 65rem) {
    .loom-score-layout { grid-template-columns: minmax(0, 1fr); }
    .loom-detail-column { grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); align-items: start; }
  }
  @media (max-width: 48rem) {
    .loom-workspace-heading { flex-wrap: wrap; }
    .loom-catalogue nav { right: auto; left: 0; }
    .loom-graph-column { display: flex; flex-direction: column; }
    .loom-outline { order: -1; }
    .loom-detail-column { grid-template-columns: minmax(0, 1fr); }
    .loom-outline > summary span { float: none; display: block; margin: 0.35rem 0 0; }
    .loom-station { padding-left: 0.75rem; padding-right: 0.75rem; }
    .loom-station-tags { max-width: 30%; }
    .loom-read-state { padding: 1.2rem; }
  }
</style>
