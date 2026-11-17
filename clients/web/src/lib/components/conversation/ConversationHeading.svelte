<!--
  The conversation's heading row: pin toggle, title, consent pill, optional "Browse
  séances" link, and a tools slot. Used by the focused Bridge and the docked Bridge.

  `heading` is the page's level-one heading; it is visually hidden when a conversation
  title is shown, so the outline still names the instrument.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import StatusPill from "$lib/components/shared/StatusPill.svelte";

  let { heading, headingHidden = false, title, pending = 0, pinned, onpin, browseHref, tools }: {
    /** Level-one heading text ("Bridge"). */
    heading: string;
    /** Keep the heading for assistive technology only. */
    headingHidden?: boolean;
    /** Visible conversation title. */
    title?: string;
    /** Pending consent count for the pill. */
    pending?: number;
    /** Pin state; omit to hide the pin toggle. */
    pinned?: boolean;
    /** Toggles the pin. */
    onpin?: () => void;
    /** Shows a "Browse séances" link when supplied. */
    browseHref?: string;
    /** Trailing tools disclosure. */
    tools?: Snippet;
  } = $props();
</script>

<header class="conversation-heading">
  <div class="conversation-heading__identity">
    {#if pinned !== undefined && onpin}
      <button class="conversation-heading__pin" type="button" aria-label={pinned ? "Unpin this conversation" : "Pin this conversation"} aria-pressed={pinned} title={pinned ? "Unpin conversation" : "Pin conversation"} onclick={onpin}><AltarIcon name="pin" size={16} /></button>
    {/if}
    <h1 class="conversation-heading__h1" class:visually-hidden={headingHidden}>{heading}</h1>
    {#if title}<p class="conversation-title">{title}</p>{/if}
    {#if pending}<StatusPill tone="attention">{pending} awaiting consent</StatusPill>{/if}
  </div>
  {#if browseHref}<a class="conversation-heading__browse" href={browseHref}><AltarIcon name="seances" size={16} />Browse séances</a>{/if}
  {@render tools?.()}
</header>

<style>
  .conversation-heading { position: relative; display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 1.25rem; min-height: 3.5rem; padding: 0.35rem clamp(1rem, 2vw, 1.5rem); border-bottom: 1px solid var(--color-engraving); }
  .conversation-heading__identity { display: flex; align-items: center; flex: 1 1 12rem; gap: 0.65rem; min-width: 0; }
  .conversation-heading__h1 { margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-body); }
  .conversation-title { min-width: 0; margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-body); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .conversation-heading__pin {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 2.25rem;
    height: 2.25rem;
    padding: 0;
    border: 1px solid var(--color-engraving);
    border-radius: var(--radius-glyph);
    background: transparent;
    color: var(--color-ash);
    cursor: pointer;
  }
  .conversation-heading__pin:hover { background: var(--color-obsidian-2); color: var(--color-bone); }
  .conversation-heading__pin[aria-pressed="true"] { color: var(--color-accent); }
  .conversation-heading__browse { display: inline-flex; align-items: center; gap: 0.45rem; min-height: 2.75rem; color: var(--color-parchment); font-size: var(--text-sm); text-decoration: none; }
  .conversation-heading__browse:hover { color: var(--color-bone); }
  .conversation-heading :is(a, button):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
