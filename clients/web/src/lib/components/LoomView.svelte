<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { resolve } from "$app/paths";
  import { navigationId, orbReturnHref, loomOriginHref } from "$lib/navigation/instruments";
  import { onDestroy } from "svelte";

  import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
  import type {
    LoomSummary,
    LoomView as LoomProjection,
    OrbRunSnapshot
  } from "$lib/api/models";
  import MermaidGraph from "./MermaidGraph.svelte";
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
  let showDiagram = $state(false);
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
      const originMatches =
        origin?.run.run_id === requestedRun &&
        origin?.pattern.exact === true &&
        origin.pattern.loom_path !== null &&
        origin.pattern.pattern_id === next.pattern_id &&
        origin.pattern.revision === next.revision &&
        origin.pattern.digest === next.digest;
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

<svelte:head><title>Loom — LychD</title></svelte:head>
<div class="instrument-deck instrument-deck--loom">
  <aside class="loom-rail">
    <h1 class="instrument-title rune-head">Loom</h1>
    <p class="instrument-kicker">Registered Patterns</p>
    <nav aria-label="Pattern revisions">
      {#each catalogue as pattern (`${pattern.pattern_id}@${pattern.revision}`)}
        <a
          aria-current={
            view?.pattern_id === pattern.pattern_id && view?.revision === pattern.revision
              ? "page"
              : undefined
          }
          class="pattern"
          href={pattern.detail_path}
        >
          <span class="t">{pattern.title}</span>
          <span class="m">
            {pattern.pattern_id}@{pattern.revision}
            · {pattern.default
              ? "default"
              : pattern.route_rank != null
                ? `route ${pattern.route_rank}`
                : "retained"}
          </span>
        </a>
      {/each}
    </nav>
  </aside>

  <section class="loom-canvas" aria-label="Registered Pattern">
    {#if loading}
      <div class="mist"></div>
    {:else if error}
      <div class="turn__fault" role="alert">{error}</div>
    {:else if view}
      <header class="pattern-identity">
        <div>
          <span class="eyebrow">Registered Pattern</span>
          <h2>{view.title}</h2>
          <p>{view.description}</p>
          <p class="pattern-entry">Entry <code>{view.entry_node}</code></p>
          {#if returnHref}
            <nav class="context-links" aria-label="Run context">
              <a href={resolve(returnHref)}>
                Return to Run in Orb →
              </a>
            </nav>
          {/if}
          {#if sourceContextError}<p class="context-unavailable" role="status">{sourceContextError}</p>{/if}
        </div>
        <div class="identity-seal">
          <strong>{view.pattern_id}@{view.revision}</strong>
          <span>Registered from source</span>
        </div>
      </header>

      <section class="pattern-score panel" aria-labelledby="score-title">
        <div class="panel-head">
          <h3 id="score-title" class="rune-head">Semantic score</h3>
          <span class="score-count">{view.nodes.length} stations · {view.edges.length} permissions</span>
        </div>
        <ol class="station-list">
          {#each view.nodes as node, index (node.key)}
            <li class="station" data-kind={node.kind}>
              <span class="station__index">{String(index + 1).padStart(2, "0")}</span>
              <span class="station__body">
                <strong>
                  {#if node.kind === "delegate"}<DelegateMark />{/if}
                  {node.label}
                </strong>
                <code>{node.key}</code>
              </span>
              <span class="declaration-kind" data-kind={node.kind}>{node.kind}</span>
              <ul class="permission-list" aria-label="Permitted next stations">
                {#each view.edges.filter((edge) => edge.source === node.key) as edge (edge.key)}
                  <li><span aria-hidden="true">→</span> {edge.target}</li>
                {/each}
              </ul>
            </li>
          {/each}
        </ol>
      </section>

      <aside class="loom-meta">
        <details class="panel pattern-details">
          <summary>Identity &amp; source</summary>
          <dl class="kv">
            <dt>checkpoint</dt><dd>{view.checkpoint_schema}</dd>
            <dt>entry</dt><dd>{view.entry_node}</dd>
            <dt>implementation</dt><dd>{view.implementation_revision}</dd>
            <dt>digest</dt><dd class="glyph digest">{view.digest}</dd>
            <dt>trigger</dt><dd>{view.trigger_hint}</dd>
            <dt>source</dt>
            <dd>
              <a href="/api/v1/loom/source/patterns/{view.pattern_id}/{view.revision}">Mermaid source →</a>
            </dd>
          </dl>
        </details>
      </aside>
      <section class="panel diagram-lens">
        <div class="panel-head">
          <h3 class="rune-head">Diagram lens</h3>
          <button class="text-action" type="button" onclick={() => (showDiagram = !showDiagram)}>
            {showDiagram ? "Hide" : "Reveal"}
          </button>
        </div>
        {#if showDiagram}
          <MermaidGraph source={view.mermaid_source} label={`${view.title} Pattern diagram`} />
        {:else}
          <p class="inspector-copy">Optional visual projection. The semantic score remains primary.</p>
        {/if}
      </section>
    {:else}
      <div class="shell-placeholder">
        <span class="glyph-big">⬡</span>
        <h2 class="rune-head">No Pattern revisions are registered</h2>
      </div>
    {/if}
  </section>
</div>
