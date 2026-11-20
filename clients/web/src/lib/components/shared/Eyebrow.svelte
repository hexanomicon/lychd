<!--
  Small uppercase context label above a title or section ("Pattern topology", "Selected station").

  `as` picks the element: a heading when the label names a section for assistive
  technology, otherwise a span or paragraph.
-->
<script lang="ts">
  import type { Snippet } from "svelte";

  let { as = "span", id, children }: {
    /** Rendered element; use "h2"/"h3" only when the label is the section's heading. */
    as?: "span" | "p" | "h2" | "h3";
    /** Id for `aria-labelledby`. */
    id?: string;
    /** Label text. */
    children: Snippet;
  } = $props();
</script>

<svelte:element this={as} class="eyebrow-label" {id}>{@render children()}</svelte:element>

<style>
  .eyebrow-label {
    display: block;
    margin: 0;
    color: var(--color-text-muted);
    font: 600 var(--text-2xs)/1.5 var(--font-body);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
</style>
