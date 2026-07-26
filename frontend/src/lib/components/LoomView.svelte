<script lang="ts">
  import { goto } from "$app/navigation";

  import { getLoomCatalogue, getLoomWorkflow } from "$lib/api/client";
  import type { LoomSummary, LoomView as LoomProjection } from "$lib/api/models";
  import MermaidGraph from "./MermaidGraph.svelte";

  let { workflowName }: { workflowName?: string } = $props();
  let catalogue = $state<LoomSummary[]>([]);
  let view = $state<LoomProjection | null>(null);
  let loading = $state(true);
  let error = $state("");
  let loadVersion = 0;

  $effect(() => {
    const requested = workflowName;
    void load(requested);
  });

  async function load(requested?: string) {
    const version = ++loadVersion;
    loading = true;
    try {
      const patterns = await getLoomCatalogue();
      if (version !== loadVersion) return;
      catalogue = patterns;
      const name = requested ?? patterns[0]?.name;
      if (!name) {
        view = null;
        return;
      }
      view = await getLoomWorkflow(name);
      if (!requested) await goto(`/loom/${name}`, { replaceState: true });
      error = "";
    } catch (cause) {
      if (version === loadVersion) error = cause instanceof Error ? cause.message : "The Loom cannot be read.";
    } finally {
      if (version === loadVersion) loading = false;
    }
  }
</script>

<svelte:head><title>Loom — LychD</title></svelte:head>
<div class="instrument-deck" aria-label="Loom">
  <aside class="loom-rail">
    {#each catalogue as pattern}
      <a class:current={view?.name === pattern.name} class="pattern" href="/loom/{pattern.name}">
        <span class="t">{pattern.title}</span>
        <span class="m">{pattern.trigger_hint}</span>
      </a>
    {/each}
  </aside>

  <div class="loom-canvas">
    {#if loading}
      <div class="mist"></div>
    {:else if view}
      <section data-fragment="loom.graph" data-workflow={view.name}>
        <div class="panel graph-stage">
          <MermaidGraph source={view.mermaid_source} />
        </div>
        <div class="loom-meta">
          <div class="panel">
            <div class="panel-head"><span class="rune-head">Pattern</span></div>
            <dl class="kv">
              <dt>name</dt><dd class="glyph">{view.name}</dd>
              <dt>title</dt><dd>{view.title}</dd>
              <dt>trigger</dt><dd>{view.trigger_hint}</dd>
              <dt>nodes</dt><dd class="glyph">{view.node_names.join(" → ")}</dd>
              <dt>source</dt><dd><a href="/api/v1/loom/{view.name}/source">stateDiagram-v2 ↗</a></dd>
            </dl>
          </div>
          <div class="panel">
            <div class="panel-head"><span class="rune-head">Description</span></div>
            <div class="loom-desc">{view.description}</div>
          </div>
        </div>
      </section>
    {:else}
      <div class="turn__fault">{error || "No workflow patterns are registered."}</div>
    {/if}
  </div>
</div>
