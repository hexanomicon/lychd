<script lang="ts">
  import { resolve } from "$app/paths";
  import { untrack } from "svelte";
  import { getAtlasReferences } from "$lib/api/client";
  import type { AtlasSummary } from "$lib/api/models";
  import { atlasHref } from "$lib/atlas/navigation";

  let { kind, targetId, suggestedProject = null }: { kind: "session" | "run"; targetId: string; suggestedProject?: { id: string; title: string } | null } = $props();
  let projects = $state.raw<AtlasSummary[]>([]);
  let error = $state("");
  let generation = 0;
  let controller: AbortController | undefined;

  $effect(() => {
    const requestedKind = kind;
    const requestedId = targetId;
    untrack(() => {
      projects = [];
      void load(requestedKind, requestedId);
    });
    return () => {
      generation++;
      controller?.abort();
    };
  });

  async function load(requestedKind: "session" | "run", requestedId: string) {
    const version = ++generation;
    controller?.abort();
    controller = new AbortController();
    error = "";
    try {
      const next = await getAtlasReferences(requestedKind, requestedId, controller.signal);
      if (version === generation && kind === requestedKind && targetId === requestedId) projects = next;
    } catch {
      if (version === generation) error = "Atlas links could not be read.";
    }
  }
</script>

<svelte:window onfocus={() => load(kind, targetId)} />

<nav class="atlas-links" aria-label="Related Atlas projects">
  <span>Atlas</span>
  {#each projects as project (project.id)}
    <a href={resolve("/atlas/[project_id]", { project_id: project.id })}>{project.title}</a>
  {/each}
  {#if suggestedProject && !projects.some((project) => project.id === suggestedProject?.id)}
    <a href={atlasHref(suggestedProject.id, { kind, targetId })}>Link this conversation to {suggestedProject.title}</a>
  {/if}
  <a href={atlasHref(undefined, { kind, targetId })}>
    {projects.length ? "Link to another project" : "Link to project"}
  </a>
</nav>
{#if error}
  <div class="atlas-links" role="status">
    <span>{error}{projects.length ? " Showing earlier links; they may be out of date." : ""}</span>
    <button type="button" onclick={() => load(kind, targetId)}>Retry Atlas links</button>
  </div>
{/if}

<style>
  .atlas-links { display: flex; flex-wrap: wrap; gap: .6rem 1rem; align-items: center; padding: .75rem 1rem; overflow-wrap: anywhere; }
  .atlas-links > span { color: var(--color-ash); font-size: .85rem; }
  .atlas-links a { display: inline-flex; align-items: center; min-height: 2.75rem; color: var(--color-rune); text-underline-offset: .2em; }
  .atlas-links button { min-height: 2.75rem; padding: .45rem .7rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); background: var(--color-obsidian-2); color: var(--color-bone); font: inherit; cursor: pointer; }
  .atlas-links :is(a, button):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
</style>
