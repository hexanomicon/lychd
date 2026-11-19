<script lang="ts">
  import type { Snippet } from "svelte";
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";
  let {
    open = $bindable(true),
    width = $bindable(208),
    minimap,
    children,
    name,
    right = false,
  }: {
    open?: boolean;
    width?: number;
    minimap: Snippet;
    children: Snippet;
    name: string;
    right?: boolean;
  } = $props();
  const uid = $props.id();
</script>

<aside class={["map-rail", { folded: !open, right }]} aria-label={name}>
  <header>
    {#if open}<h2>Map</h2>{/if}
    <button
      type="button"
      aria-label={open ? "Collapse Map" : "Expand Map"}
      aria-controls={uid}
      aria-expanded={open}
      title={open ? "Collapse Map" : "Expand Map"}
      onclick={() => (open = !open)}>{open !== right ? "‹" : "›"}</button
    >
  </header>
  <div id={uid} class="map-body" hidden={!open}>
    <nav aria-label={`${name} objects`}>{@render children()}</nav>
    <div class="mini"><span>Minimap</span>{@render minimap()}</div>
  </div>
  {#if open}<PaneGrip
      bind:width
      name={`${name} width`}
      side={right ? "right" : "left"}
      min={156}
      max={352}
    />{/if}
</aside>

<style>
  .map-rail {
    min-width: 0;
    min-height: 0;
    position: relative;
    display: flex;
    flex-direction: column;
    z-index: 2;
    background: var(--color-obsidian);
    border-inline-end: 1px solid var(--color-engraving);
    overflow: hidden;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.55rem 0.5rem 0.8rem;
    gap: 0.25rem;
  }
  h2 {
    color: var(--color-bone);
    font: 600 0.95rem/1.4 var(--font-body);
  }
  button {
    width: 1.8rem;
    height: 1.8rem;
    border: 1px solid var(--color-control-border);
    background: var(--color-void);
    color: var(--color-bone);
    border-radius: var(--radius-rune);
    font: 1.1rem/1 var(--font-body);
    cursor: pointer;
  }
  button:focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 1px;
  }
  .folded header {
    padding: 0.45rem 0.1rem;
    justify-content: center;
  }
  .right {
    border-inline-start: 1px solid var(--color-engraving);
    border-inline-end: 0;
  }
  .map-body {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
  }
  .map-body[hidden] {
    display: none;
  }
  nav {
    padding: 0 0.55rem 0.45rem;
    flex: 1;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }
  .mini {
    margin: auto 0.5rem 0.45rem;
    padding-top: 0.4rem;
    border-block-start: 1px solid var(--color-engraving);
  }
  .mini span {
    display: block;
    margin-bottom: 0.3rem;
    color: var(--color-ash);
    font: var(--text-xs)/1.4 var(--font-body);
  }
  .mini :global(.svelte-flow__minimap) {
    max-width: 100%;
  }
  @media (max-height: 44rem) {
    .mini {
      max-width: 7rem;
    }
  }
</style>
