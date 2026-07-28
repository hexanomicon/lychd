<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";

  import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
  import type {
    LoomSummary,
    LoomView as LoomProjection,
    OrbRunSnapshot
  } from "$lib/api/models";
  import MermaidGraph from "./MermaidGraph.svelte";

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
  let sourceRunId = $derived(page.url.searchParams.get("run"));

  $effect(() => {
    void load(patternId, revision, sourceRunId);
  });

  async function load(
    requestedPattern?: string,
    requestedRevision?: string,
    requestedRun?: string | null
  ) {
    const version = ++loadVersion;
    loading = true;
    error = "";
    view = null;
    sourceRun = null;
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
          : patterns[0];
      if (!selected) return;
      const next = await getLoomPatternRevision(selected.pattern_id, selected.revision);
      if (version !== loadVersion) return;
      view = next;
      const originMatches =
        origin?.pattern.exact === true &&
        origin.pattern.pattern_id === next.pattern_id &&
        origin.pattern.revision === next.revision;
      sourceRun = originMatches ? origin : null;
      if (!requestedPattern || !requestedRevision || (requestedRun && !originMatches)) {
        const exactPath = `/loom/${next.pattern_id}/${next.revision}`;
        await goto(
          originMatches && requestedRun
            ? `${exactPath}?run=${encodeURIComponent(requestedRun)}`
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
    <p class="instrument-kicker">Published Patterns</p>
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
          <span class="m">{pattern.pattern_id}@{pattern.revision}</span>
        </a>
      {/each}
    </nav>
  </aside>

  <section class="loom-canvas" aria-label="Published Pattern">
    {#if loading}
      <div class="mist"></div>
    {:else if error}
      <div class="turn__fault" role="alert">{error}</div>
    {:else if view}
      <header class="pattern-identity">
        <div>
          <span class="eyebrow">Published Pattern</span>
          <h2>{view.title}</h2>
          <p>{view.description}</p>
          {#if sourceRun}
            <nav class="context-links" aria-label="Run context">
              <a href={`/orb/${encodeURIComponent(sourceRun.run.run_id)}`}>
                Return to Run in Orb →
              </a>
            </nav>
          {/if}
        </div>
        <div class="identity-seal">
          <strong>{view.pattern_id}@{view.revision}</strong>
          <span>{view.publication}</span>
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
                <strong>{node.label}</strong>
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
        <section class="panel">
          <div class="panel-head"><h3 class="rune-head">Immutable identity</h3></div>
          <dl class="kv">
            <dt>checkpoint</dt><dd>{view.checkpoint_schema}</dd>
            <dt>digest</dt><dd class="glyph digest">{view.digest}</dd>
            <dt>trigger</dt><dd>{view.trigger_hint}</dd>
            <dt>source</dt>
            <dd>
              <a href="/api/v1/loom/{view.pattern_id}/{view.revision}/source">Mermaid source →</a>
            </dd>
          </dl>
        </section>
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
      </aside>
    {:else}
      <div class="shell-placeholder">
        <span class="glyph-big">◇</span>
        <h2 class="rune-head">No Pattern revisions are registered</h2>
      </div>
    {/if}
  </section>
</div>
