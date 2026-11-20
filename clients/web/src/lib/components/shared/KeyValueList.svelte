<!--
  Definition list for identity and property facts (Run, Pattern, capability, source).

  Pass `items` for plain text facts, or `children` with your own `<dt>`/`<dd>` pairs
  (optionally wrapped in `<div>`) when a value needs markup such as links or pills.
  `dd.glyph` renders machine identifiers in the glyph font.
-->
<script module lang="ts">
  export interface KeyValueItem {
    term: string;
    value: string | number;
    /** Machine identifier: render in the glyph font. */
    glyph?: boolean;
  }
</script>

<script lang="ts">
  import type { Snippet } from "svelte";

  let { items, layout = "columns", termWidth, label, children }: {
    /** Plain facts; ignored when `children` is supplied. */
    items?: readonly KeyValueItem[];
    /** "columns": term beside value. "stacked": term above value. */
    layout?: "columns" | "stacked";
    /** CSS width for the term column in "columns" layout. */
    termWidth?: string;
    /** Accessible name when the list stands alone. */
    label?: string;
    /** Custom `<dt>`/`<dd>` content. */
    children?: Snippet;
  } = $props();
</script>

<dl class="kv-list" data-layout={layout} aria-label={label} style:--kv-term-width={termWidth}>
  {#if children}
    {@render children()}
  {:else}
    {#each items ?? [] as item (item.term)}
      <div><dt>{item.term}</dt><dd class:glyph={item.glyph}>{item.value}</dd></div>
    {/each}
  {/if}
</dl>

<style>
  .kv-list {
    display: grid;
    grid-template-columns: var(--kv-term-width, minmax(6rem, auto)) minmax(0, 1fr);
    gap: 0.55rem 1.25rem;
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.5;
  }
  .kv-list[data-layout="stacked"] { grid-template-columns: minmax(0, 1fr); gap: 0.75rem; }
  .kv-list > :global(div) { display: contents; }
  .kv-list[data-layout="stacked"] > :global(div) { display: block; }
  .kv-list :global(dt) { color: var(--color-text-muted); }
  .kv-list[data-layout="stacked"] :global(dt) { margin-bottom: 0.15rem; font-size: var(--text-xs); }
  .kv-list :global(dd) { min-width: 0; margin: 0; color: var(--color-text-strong); overflow-wrap: anywhere; }
  .kv-list :global(:is(dd.glyph, code)) { font-family: var(--font-glyph); font-size: var(--text-sm); }
  .kv-list :global(dd.glyph) { color: var(--color-status-ready); }
  @container (max-width: 22rem) {
    .kv-list[data-layout="columns"] { grid-template-columns: minmax(0, 1fr); gap: 0.15rem; }
    .kv-list[data-layout="columns"] :global(dd) { margin-bottom: 0.4rem; }
  }
</style>
