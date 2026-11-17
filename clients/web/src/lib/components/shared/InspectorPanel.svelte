<!--
  Side inspector for the selected object: Circle (Run), Loom (station), Orb (evidence),
  Nexus (object). An eyebrow and title head it; `InspectorSection`s divide the body.

  The title labels the landmark. Pass `titleFocusable` + `heading` when the owner
  moves focus to the inspector after a selection; pass `ondismiss` for a close button.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import Eyebrow from "./Eyebrow.svelte";

  const generatedId = $props.id();
  let {
    title,
    titleId = `${generatedId}-title`,
    id,
    label,
    level = 2,
    eyebrow,
    as = "aside",
    titleFocusable = false,
    heading = $bindable(),
    sticky = false,
    framed = true,
    ondismiss,
    dismissLabel = "Close inspector",
    meta,
    children
  }: {
    /** Inspector title; names the landmark. */
    title: string;
    /** Heading id; generated when omitted. */
    titleId?: string;
    /** Landmark id, e.g. for `aria-controls` from the selecting controls. */
    id?: string;
    /** Stable landmark name; otherwise the landmark is named by its title. */
    label?: string;
    /** Title heading level, matching the page outline. */
    level?: 2 | 3;
    /** Small label above the title ("Selected station"). */
    eyebrow?: string;
    /** Landmark element. */
    as?: "aside" | "section";
    /** Makes the title a programmatic focus target. */
    titleFocusable?: boolean;
    /** Bindable reference to the title element. */
    heading?: HTMLElement;
    /** Stick to the top of the scrolling work area. */
    sticky?: boolean;
    /** Draw its own divider, padding and surface; false when a page column already frames it. */
    framed?: boolean;
    /** Renders a close button when supplied. */
    ondismiss?: () => void;
    dismissLabel?: string;
    /** Content beside the title, such as a status pill. */
    meta?: Snippet;
    /** Inspector body, usually `InspectorSection`s. */
    children: Snippet;
  } = $props();

  const focusTarget = $derived(titleFocusable ? { tabindex: -1 } : {});
</script>

<svelte:element this={as} {id} class="inspector-panel" class:inspector-panel--sticky={sticky} class:inspector-panel--framed={framed} aria-label={label} aria-labelledby={label ? undefined : titleId}>
  <header class="inspector-panel__head">
    <div class="inspector-panel__identity">
      {#if eyebrow}<Eyebrow>{eyebrow}</Eyebrow>{/if}
      <svelte:element this={`h${level}`} class="inspector-panel__title" id={titleId} {...focusTarget} bind:this={heading}>{title}</svelte:element>
      {@render meta?.()}
    </div>
    {#if ondismiss}
      <button class="inspector-panel__dismiss" type="button" aria-label={dismissLabel} title={dismissLabel} onclick={ondismiss}>×</button>
    {/if}
  </header>
  {@render children()}
</svelte:element>

<style>
  .inspector-panel {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    color: var(--color-parchment);
    font-size: var(--text-sm);
    container-type: inline-size;
  }
  .inspector-panel--framed { padding: 1rem 1.25rem; overflow-y: auto; border-inline-start: 1px solid var(--color-engraving); background: var(--color-obsidian); }
  .inspector-panel--sticky { position: sticky; inset-block-start: 0; max-height: 100dvh; }
  .inspector-panel__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; padding-bottom: 0.85rem; }
  .inspector-panel__identity { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
  .inspector-panel__title { margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.4 var(--font-body); overflow-wrap: anywhere; }
  .inspector-panel__title:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .inspector-panel__dismiss {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 2.25rem;
    height: 2.25rem;
    padding: 0;
    border: 0;
    border-radius: var(--radius-rune);
    background: transparent;
    color: var(--color-ash);
    font-size: 1.25rem;
    cursor: pointer;
  }
  .inspector-panel__dismiss:hover { background: var(--color-obsidian-2); color: var(--color-bone); }
  .inspector-panel__dismiss:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
