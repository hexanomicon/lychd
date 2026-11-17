<!--
  Centred placeholder for an empty region ("No séance yet", "Choose a conversation").

  The title is a real heading when it names the region; body copy and an optional
  action render beneath it.
-->
<script lang="ts">
  import type { Snippet } from "svelte";

  let { title, level = 2, glyph, children, action }: {
    /** Short title for the empty region. */
    title?: string;
    /** Heading level for the title. */
    level?: 2 | 3;
    /** Decorative mark above the title. */
    glyph?: string;
    /** Explanation. */
    children?: Snippet;
    /** One next step. */
    action?: Snippet;
  } = $props();
</script>

<div class="empty-state">
  {#if glyph}<span class="empty-state__glyph" aria-hidden="true">{glyph}</span>{/if}
  {#if title}<svelte:element this={`h${level}`} class="empty-state__title">{title}</svelte:element>{/if}
  {#if children}<div class="empty-state__body">{@render children()}</div>{/if}
  {#if action}<div class="empty-state__action">{@render action()}</div>{/if}
</div>

<style>
  .empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; margin: auto; padding: 2.5rem 1rem; text-align: center; color: var(--color-parchment); }
  .empty-state__glyph { color: var(--color-accent); font-size: 1.6rem; }
  .empty-state__title { margin: 0; color: var(--color-bone); font: 600 var(--text-lg)/1.35 var(--font-body); }
  .empty-state__body { max-width: 36rem; font-size: var(--text-sm); line-height: 1.65; }
  .empty-state__body :global(p) { margin: 0; }
  .empty-state__body :global(p + p) { margin-top: 0.5rem; }
  .empty-state__action { margin-top: 0.75rem; }
</style>
