<!--
  Bridge conversation history: pinned, the selected-but-unlisted conversation, and recent.

  One row implementation serves both placements:
  - sidebar: the Altar shell sidebar while the Bridge is the focused workspace.
  - disclosure: the Bridge's own collapsible list when it is docked beside an instrument
    or rendered standalone.
  It reads only the `BridgeHistory` interface; BridgeView owns the data and the intents.
  Pin buttons keep the `bridge-pin-{id}` id so BridgeView can return focus after a toggle.
-->
<script lang="ts">
  import type { BridgeHistory, BridgeHistoryEntry } from "$lib/navigation/instruments";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import Button from "$lib/components/shared/Button.svelte";
  import Disclosure from "$lib/components/shared/Disclosure.svelte";
  import Eyebrow from "$lib/components/shared/Eyebrow.svelte";
  import StatusPill from "$lib/components/shared/StatusPill.svelte";

  let { history, variant, open = $bindable(false), onselect }: {
    /** Conversation history projected by BridgeView. */
    history: BridgeHistory;
    /** Placement; see the header comment. */
    variant: "sidebar" | "disclosure";
    /** Disclosure variant: bindable open state. */
    open?: boolean;
    /** Called after a conversation link is activated (e.g. to close an overlay). */
    onselect?: () => void;
  } = $props();

  function select(event: MouseEvent, id: string) {
    history.select(event, id);
    onselect?.();
  }
</script>

{#snippet row(entry: BridgeHistoryEntry)}
  {@const pinned = history.isPinned(entry.id)}
  <div class="conversation-row">
    <a class="conversation-row__link" href={history.href(entry.id)} aria-current={history.selectedId === entry.id ? "page" : undefined} onclick={(event) => select(event, entry.id)}>
      <span class="conversation-row__title"><AltarIcon name="conversation" size={16} /><span class="t">{entry.title}</span></span>
      {#if entry.pending || entry.marker || !entry.loaded}
        <span class="conversation-row__marks">
          {#if entry.pending}<StatusPill tone="attention">{entry.pending} awaiting consent</StatusPill>{/if}
          {#if entry.marker}<StatusPill>{entry.marker}</StatusPill>{/if}
          {#if !entry.loaded}<StatusPill tone="muted">Details not loaded</StatusPill>{/if}
        </span>
      {/if}
    </a>
    <button
      id={`bridge-pin-${entry.id}`}
      class="conversation-row__pin"
      type="button"
      aria-label={`${pinned ? "Unpin" : "Pin"} conversation: ${entry.loaded ? entry.title : entry.id}`}
      aria-pressed={pinned}
      title={pinned ? "Unpin conversation" : "Pin conversation"}
      onclick={() => history.togglePin(entry.id)}
    ><AltarIcon name="pin" size={14} /></button>
  </div>
{/snippet}

{#snippet footer()}
  {#if history.hasMore}
    <Button size="sm" busy={history.loadingMore} onclick={() => history.loadMore()}>
      {history.loadingMore ? "Loading conversations…" : "Load more conversations"}
    </Button>
  {/if}
  {#if history.notice}<p class="conversation-list__empty" role="status">{history.notice}</p>{/if}
{/snippet}

{#if variant === "sidebar"}
  <nav class="conversation-list" data-variant="sidebar" aria-label="Conversations">
    <div class="conversation-list__heading">
      <Eyebrow as="h2">Pinned</Eyebrow>
      {#if history.selectedId && !history.isPinned(history.selectedId)}
        {@const current = history.selectedId}
        <button class="conversation-list__add" type="button" aria-label="Pin current conversation" title="Pin current conversation" onclick={() => history.togglePin(current)}><AltarIcon name="plus" size={14} /></button>
      {/if}
    </div>
    {#each history.pinned as entry (entry.id)}{@render row(entry)}{:else}<p class="conversation-list__empty">No pinned conversations.</p>{/each}
    <div class="conversation-list__heading">
      <Eyebrow as="h2">Recent</Eyebrow>
      <button class="conversation-list__add" type="button" aria-label="Open a new séance" title="New Séance" disabled={history.creating} onclick={() => history.create()}><AltarIcon name="plus" size={14} /></button>
    </div>
    {#if history.unlisted}{@render row(history.unlisted)}{/if}
    {#each history.recent as entry (entry.id)}{@render row(entry)}{:else}
      {#if history.ready && !history.unlisted && !history.pinned.length}<p class="conversation-list__empty">No séance yet.</p>{/if}
    {/each}
    {@render footer()}
  </nav>
{:else}
  <div class="conversation-list" data-variant="disclosure">
    <Disclosure bind:open>
      {#snippet summary()}<Eyebrow>Conversations</Eyebrow>{/snippet}
      <Button variant="primary" busy={history.creating} data-new-seance onclick={() => history.create()}>
        <span aria-hidden="true">✦</span>{history.creating ? "Opening…" : "New Séance"}
      </Button>
      <nav aria-label="Conversations">
        <div class="conversation-list__heading"><Eyebrow as="h2">Pinned</Eyebrow></div>
        {#each history.pinned as entry (entry.id)}{@render row(entry)}{:else}<p class="conversation-list__empty">No pinned conversations.</p>{/each}
        {#if history.unlisted}
          <div class="conversation-list__heading"><Eyebrow as="h2">Selected conversation</Eyebrow></div>
          {@render row(history.unlisted)}
        {/if}
        <div class="conversation-list__heading"><Eyebrow as="h2">Recent conversations</Eyebrow></div>
        <p class="conversation-list__order">Newest created first</p>
        {#each history.recent as entry (entry.id)}{@render row(entry)}{:else}
          {#if history.ready && !history.unlisted && !history.pinned.length}<p class="conversation-list__empty glyph">No séance yet — open one to speak.</p>{/if}
        {/each}
        {@render footer()}
      </nav>
    </Disclosure>
  </div>
{/if}

<style>
  .conversation-list { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
  .conversation-list nav { display: flex; flex-direction: column; gap: 0.1rem; margin-top: 0.5rem; }
  .conversation-list__heading { display: flex; align-items: center; justify-content: space-between; min-height: 2rem; margin-top: 0.6rem; padding-inline-start: 0.7rem; }
  .conversation-list__add, .conversation-row__pin {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 2rem;
    height: 2rem;
    padding: 0;
    border: 0;
    border-radius: var(--radius-rune);
    background: transparent;
    color: var(--color-ash);
    cursor: pointer;
  }
  .conversation-list__add:hover:not(:disabled), .conversation-row__pin:hover { background: var(--color-obsidian-2); color: var(--color-bone); }
  .conversation-list__add:disabled { opacity: 0.45; cursor: default; }
  .conversation-list__empty, .conversation-list__order { margin: 0; padding: 0.25rem 0.7rem; color: var(--color-ash); font-size: var(--text-xs); line-height: 1.6; }
  .conversation-list :global(.btn) { margin-top: 0.5rem; }
  .conversation-row { position: relative; display: flex; align-items: center; min-width: 0; }
  .conversation-row__link {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    flex: 1 1 auto;
    min-width: 0;
    min-height: 2.5rem;
    justify-content: center;
    padding: 0.4rem 2.4rem 0.4rem 0.7rem;
    border: 1px solid transparent;
    border-radius: var(--radius-rune);
    color: var(--color-parchment);
    font-size: var(--text-sm);
    text-decoration: none;
  }
  .conversation-row__link:hover { background: var(--color-obsidian-2); color: var(--color-bone); }
  .conversation-row__link[aria-current="page"] { border-color: var(--color-engraving); background: var(--color-obsidian-2); color: var(--color-bone); font-weight: 600; }
  .conversation-row__link:focus-visible, .conversation-row__pin:focus-visible, .conversation-list__add:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
  .conversation-row__title { display: flex; align-items: center; gap: 0.6rem; min-width: 0; }
  .conversation-row__title :global(svg) { flex: 0 0 auto; color: var(--color-ash); }
  .conversation-row__title .t { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .conversation-row__marks { display: flex; flex-wrap: wrap; gap: 0.3rem; padding-inline-start: 1.6rem; }
  .conversation-row__pin { position: absolute; inset-inline-end: 0.2rem; inset-block-start: 0.25rem; opacity: 0; }
  .conversation-row:hover .conversation-row__pin, .conversation-row__pin:focus-visible, .conversation-row__pin[aria-pressed="true"] { opacity: 1; }
  .conversation-row__pin[aria-pressed="true"] { color: var(--color-accent); }
  @media (hover: none) { .conversation-row__pin { opacity: 1; } }
</style>
