<!--
  Shared page header for Altar instruments and workspaces.

  Owns the layout and typography of the opening block (back link, kicker,
  title, description, actions) so every page reads the same. Page-specific
  extras render through the `children` snippet beneath the description, and
  controls render through the `actions` snippet; both keep the caller's
  scoped styles because snippets belong to the component that declares them.
-->
<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    kicker,
    description,
    back,
    titleId,
    titleFocusable = false,
    heading = $bindable(),
    children,
    actions
  }: {
    /** Visible level-one heading text. */
    title: string;
    /** Short uppercase context label above the title. */
    kicker?: string;
    /** One-sentence explanation below the title. */
    description?: string;
    /** Optional return link rendered above the kicker. */
    back?: { href: string; label: string };
    /** Id for the heading, for `aria-labelledby` and programmatic focus. */
    titleId?: string;
    /** Makes the heading a programmatic focus target (`tabindex="-1"`). */
    titleFocusable?: boolean;
    /** Bindable reference to the rendered heading element. */
    heading?: HTMLHeadingElement;
    /** Extra identity content rendered beneath the description. */
    children?: Snippet;
    /** Controls aligned to the end of the header. */
    actions?: Snippet;
  } = $props();

  // A spread keeps the a11y lint from treating the dynamic value as a tab stop;
  // the heading is only ever a programmatic (-1) focus target.
  let focusTarget = $derived(titleFocusable ? { tabindex: -1 } : {});
</script>

<header class="page-header">
  <div class="page-header__identity">
    {#if back}<a class="page-header__back" href={back.href}>{back.label}</a>{/if}
    {#if kicker}<span class="instrument-kicker">{kicker}</span>{/if}
    <h1 class="page-header__title" id={titleId} {...focusTarget} bind:this={heading}>{title}</h1>
    {#if description}<p class="page-header__description">{description}</p>{/if}
    {@render children?.()}
  </div>
  {#if actions}<div class="page-header__actions">{@render actions()}</div>{/if}
</header>

<style>
  .page-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem 2rem;
    min-width: 0;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--color-engraving);
  }
  .page-header__identity { flex: 1 1 24rem; min-width: 0; }
  .page-header__back {
    display: inline-block;
    margin-bottom: 0.6rem;
    padding-block: 0.2rem;
    color: var(--color-ash);
    font-size: var(--text-xs);
    text-underline-offset: 0.2em;
  }
  .page-header__back:hover { color: var(--color-rune); }
  .instrument-kicker { margin-bottom: 0.35rem; }
  .page-header__title {
    margin: 0;
    color: var(--color-bone);
    font: 600 clamp(1.5rem, 2.4vw, 2rem)/1.2 var(--font-body);
    font-variant: normal;
    letter-spacing: -0.03em;
    overflow-wrap: anywhere;
  }
  .page-header__description {
    max-width: 48rem;
    margin: 0.6rem 0 0;
    color: var(--color-parchment);
    font-size: var(--text-sm);
    line-height: 1.6;
  }
  .page-header__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }
  .page-header :is(a, h1):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
</style>
