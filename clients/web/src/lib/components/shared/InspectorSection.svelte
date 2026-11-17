<!--
  One divided section inside an `InspectorPanel` (Stations, Incoming permissions,
  Identity & source). Untitled sections are plain dividers.

  `focusable` + `element` let the owner move focus into the section after a selection.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import SectionHeading from "./SectionHeading.svelte";

  const generatedId = $props.id();
  let { title, meta, level = 3, focusable = false, element = $bindable(), children }: {
    /** Section heading; omit for a plain divider. */
    title?: string;
    /** Muted text beside the heading, such as a count. */
    meta?: string;
    /** Heading level below the panel's title. */
    level?: 3 | 4;
    /** Makes the section a programmatic focus target. */
    focusable?: boolean;
    /** Bindable reference to the section element. */
    element?: HTMLElement;
    /** Section body. */
    children: Snippet;
  } = $props();

  const headingId = `${generatedId}-heading`;
  const focusTarget = $derived(focusable ? { tabindex: -1 } : {});
</script>

<section class="inspector-section" aria-labelledby={title ? headingId : undefined} {...focusTarget} bind:this={element}>
  {#if title}<SectionHeading {title} {meta} {level} id={headingId} />{/if}
  {@render children()}
</section>

<style>
  .inspector-section { display: flex; flex-direction: column; gap: 0.65rem; min-width: 0; padding-block: 0.9rem; border-top: 1px solid var(--color-engraving); }
  .inspector-section:focus-visible { outline: 2px solid var(--color-rune); outline-offset: -2px; }
  .inspector-section :global(.section-heading__title) { font-size: var(--text-sm); }
</style>
