<script lang="ts">
  import { getLoomCatalogue } from "$lib/api/client";
  import type { LoomSummary } from "$lib/api/models";
  import { recipes } from "$lib/compositions/video";
  import { resolvePath } from "$lib/navigation/paths";
  import type { StudioKey } from "../studio/session";
  let { catalogue, current, patternPath }: { catalogue: readonly LoomSummary[]; current?: StudioKey; patternPath?: string } = $props();
  let localRows = $state.raw<LoomSummary[] | null>(null);
  let catalogueState = $state("");
  let request = 0;
  async function toggle(open: boolean) {
    const version = ++request;
    localRows = null;
    catalogueState = "";
    if (!open || !current) return;
    catalogueState = "Loading registered Patterns…";
    try {
      const rows = await getLoomCatalogue();
      if (request === version) { localRows = rows; catalogueState = ""; }
    } catch {
      if (request === version) catalogueState = "Registry unavailable.";
    }
  }
</script>

<details class="library" ontoggle={event => void toggle(event.currentTarget.open)}>
  <summary>Workflows</summary>
  <nav aria-label="Workflow library">
    <div class="section-title">Registered Patterns</div>
    {#each localRows ?? catalogue as pattern (pattern.detail_path)}
      <a href={pattern.detail_path} aria-current={patternPath === pattern.detail_path ? "page" : undefined}>
        <span>{pattern.title}<small>{pattern.pattern_id}@{pattern.revision}</small></span>
        <small>{pattern.binding && !pattern.binding.executable ? "Observation only" : pattern.default ? "Default" : pattern.route_rank != null ? `Route ${pattern.route_rank}` : pattern.active ? "Active route" : "Retained"}</small>
      </a>
    {:else}<p>{catalogueState || "No registered revisions loaded."}</p>{/each}
    <div class="section-title">Local blueprints</div>
    <a href={resolvePath("/loom") + "?studio=sdlc"} aria-current={current === "sdlc" ? "page" : undefined}>Agentic SDLC</a>
    {#each Object.entries(recipes) as [id, label] (id)}
      <a href={resolvePath("/loom") + "?composition=" + id} aria-current={current === id ? "page" : undefined}>
        <span>{label}</span><small>Atelier</small>
      </a>
    {/each}
  </nav>
</details>

<style>
  .library { margin:0 0 .6rem; padding:0 0 .55rem; border:0; border-bottom:1px solid var(--color-engraving); }
  summary { cursor:pointer; padding:.4rem .2rem; font:600 13px var(--font-body); color:var(--color-bone); }
  nav { display:grid; gap:2px; }
  .section-title { margin:.6rem .2rem .25rem; color:var(--color-ash); font:10px var(--font-glyph); }
  a { display:flex; align-items:baseline; justify-content:space-between; gap:.35rem; padding:.35rem; color:var(--color-parchment); text-decoration:none; border-radius:4px; font:12px/1.35 var(--font-body); }
  a:hover,a[aria-current="page"] { background:var(--color-obsidian-2); color:var(--color-bone); }
  a span small { display:block; margin-top:2px; overflow-wrap:anywhere; }
  small,p { color:var(--color-ash); font:10px var(--font-glyph); }
</style>
