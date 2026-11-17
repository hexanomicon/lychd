<!--
  Section title with optional muted metadata on the right ("Your projects · 9 recorded",
  "Pattern graph · 4 stations") and optional trailing controls.
-->
<script lang="ts">
  import type { Snippet } from "svelte";

  let { title, level = 2, meta, id, focusable = false, heading = $bindable(), actions }: {
    /** Heading text. */
    title: string;
    /** Heading level, matching the page outline. */
    level?: 2 | 3 | 4;
    /** Muted text aligned to the end, such as a count. */
    meta?: string;
    /** Heading id for `aria-labelledby`. */
    id?: string;
    /** Makes the heading a programmatic focus target (`tabindex="-1"`). */
    focusable?: boolean;
    /** Bindable reference to the heading element. */
    heading?: HTMLElement;
    /** Controls aligned to the end. */
    actions?: Snippet;
  } = $props();

  // Spread keeps the a11y lint from treating the programmatic target as a tab stop.
  const focusTarget = $derived(focusable ? { tabindex: -1 } : {});
</script>

<div class="section-heading">
  <svelte:element this={`h${level}`} class="section-heading__title" {id} {...focusTarget} bind:this={heading}>{title}</svelte:element>
  {#if meta}<span class="section-heading__meta">{meta}</span>{/if}
  {#if actions}<div class="section-heading__actions">{@render actions()}</div>{/if}
</div>

<style>
  .section-heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.25rem 1rem; min-width: 0; }
  .section-heading__title { flex: 1 1 auto; min-width: 0; margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.4 var(--font-body); }
  .section-heading__meta { color: var(--color-ash); font-size: var(--text-xs); white-space: nowrap; }
  .section-heading__actions { display: flex; align-items: center; gap: 0.5rem; }
  .section-heading__title:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
</style>
