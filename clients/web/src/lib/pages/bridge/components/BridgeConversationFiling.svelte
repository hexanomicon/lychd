<script lang="ts">
  import { onMount, type Snippet } from "svelte";
  import { navigationId } from "$lib/navigation/instruments";

  type Placement = { id: string; archive: boolean; groups: string[] };
  type Folder = { label: string; children: Folder[]; sessions: string[] };
  let {
    pinned,
    recent,
    selected,
    selectedIsOffPage,
    attention,
    ready,
    row,
  }: {
    pinned: readonly string[];
    recent: readonly string[];
    selected: string | null;
    selectedIsOffPage: boolean;
    attention: boolean;
    ready: boolean;
    row: Snippet<[string]>;
  } = $props();

  const storageKey = "lychd.bridge-conversation-filing.v1";
  let placements = $state.raw<Placement[]>([]);
  let archived = $state(false);
  let editing = $state(false);
  let folderInput = $state("");
  let notice = $state("");
  const byId = $derived(new Map(placements.map((record) => [record.id, record])));
  const visible = (id: string) => attention || (byId.get(id)?.archive ?? false) === archived;
  const visiblePins = $derived(pinned.filter(visible));
  const offPage = $derived(
    selected && selectedIsOffPage && visible(selected) && !pinned.includes(selected) ? selected : null,
  );
  const tree = $derived.by(() => {
    const root: Folder = { label: "", children: [], sessions: [] };
    const ids = new Set([...recent, ...(ready && !attention ? placements.map((record) => record.id) : [])]);
    for (const id of ids) {
      if (pinned.includes(id) || offPage === id || !visible(id)) continue;
      let parent = root;
      for (const label of attention ? [] : (byId.get(id)?.groups ?? [])) {
        let child = parent.children.find((item) => item.label === label);
        if (!child) {
          child = { label, children: [], sessions: [] };
          parent.children.push(child);
        }
        parent = child;
      }
      parent.sessions.push(id);
    }
    return root;
  });

  function validGroup(value: unknown): value is string {
    return (
      typeof value === "string" &&
      value.length > 0 &&
      value.length <= 40 &&
      value.trim() === value &&
      !value.includes("/") &&
      ![...value].some((char) => char.charCodeAt(0) < 32)
    );
  }

  function loadFiling() {
    try {
      const raw = localStorage.getItem(storageKey);
      const value: unknown = raw && raw.length <= 131072 ? JSON.parse(raw) : [];
      placements =
        Array.isArray(value) && value.length <= 256
          ? value.filter(
              (record) =>
                record &&
                typeof record.id === "string" &&
                navigationId(record.id) &&
                typeof record.archive === "boolean" &&
                Array.isArray(record.groups) &&
                record.groups.length <= 3 &&
                record.groups.every(validGroup),
            )
          : [];
    } catch {
      placements = [];
    }
  }
  onMount(() => {
    loadFiling();
    const sync = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) loadFiling();
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  });

  function storePlacement(id: string, archive: boolean, groups: string[]) {
    if (!navigationId(id)) return;
    const other = placements.filter((record) => record.id !== id);
    if ((archive || groups.length > 0) && other.length >= 256) {
      notice = "Filing is full. Return a conversation to Active without a group to make room.";
      return;
    }
    placements = archive || groups.length ? [...other, { id, archive, groups }] : other;
    notice = "";
    try {
      localStorage.setItem(storageKey, JSON.stringify(placements));
    } catch {
      notice = "Filing kept in this view. Browser storage is unavailable.";
    }
    editing = false;
    archived = archive;
  }

  function saveGroup(id: string) {
    const groups = folderInput.trim() ? folderInput.split("/").map((label) => label.trim()) : [];
    if (groups.length > 3 || !groups.every(validGroup)) {
      notice = "Use up to three group names, each 1–40 characters, separated by a slash.";
      return;
    }
    storePlacement(id, byId.get(id)?.archive ?? false, groups);
  }
</script>

{#snippet folder(node: Folder)}
  <details class="folder" open>
    <summary>{node.label}</summary>
    {#each node.children as child (child.label)}{@render folder(child)}{/each}
    {#each node.sessions as id (id)}{@render row(id)}{/each}
  </details>
{/snippet}

{#if !attention}
  <div class="tabs" role="group" aria-label="Conversation filing in this browser">
    <button
      type="button"
      aria-pressed={!archived}
      onclick={() => {
        archived = false;
        editing = false;
      }}>Active</button
    >
    <button
      type="button"
      aria-pressed={archived}
      onclick={() => {
        archived = true;
        editing = false;
      }}>Archive</button
    >
  </div>
{/if}

{#if visiblePins.length}
  <h2>Pinned</h2>
  {#each visiblePins as id (id)}{@render row(id)}{/each}
{/if}
{#if offPage}<h2>Selected conversation</h2>
  {@render row(offPage)}{/if}
{#each tree.children as child (child.label)}{@render folder(child)}{/each}
{#if tree.sessions.length}
  <h2>{archived && !attention ? "Archived conversations" : "Recent conversations"}</h2>
  {#each tree.sessions as id (id)}{@render row(id)}{/each}
{:else if !tree.children.length && !visiblePins.length && !offPage && ready}
  <p>
    {archived && !attention
      ? "No conversations filed in Archive."
      : attention
        ? "No pending conversations on this page."
        : "No recent conversations on this page."}
  </p>
{/if}

{#if selected && ready && !attention}
  {#key selected}
    <details
      class="organize"
      ontoggle={(event) => {
        if (!event.currentTarget.open) editing = false;
      }}
    >
      <summary>Organize selected séance</summary>
      <p>Filing uses this browser. A conversation keeps its history and pending requests in either tab.</p>
      <button
        type="button"
        onclick={() => {
          if (selected)
            storePlacement(selected, !byId.get(selected)?.archive, byId.get(selected)?.groups ?? []);
        }}>{byId.get(selected)?.archive ? "Move to Active" : "Move to Archive"}</button
      >
      <button
        type="button"
        onclick={() => {
          folderInput = selected ? (byId.get(selected)?.groups ?? []).join(" / ") : "";
          editing = true;
        }}>Set group</button
      >
      {#if editing}
        <form
          onsubmit={(event) => {
            event.preventDefault();
            if (selected) saveGroup(selected);
          }}
        >
          <label
            >Group path<input
              bind:value={folderInput}
              maxlength="126"
              placeholder="Research / Writing"
            /></label
          >
          <p>Leave empty to remove the grouping.</p>
          <button type="submit">Save group</button>
        </form>
      {/if}
    </details>
  {/key}
{/if}
{#if notice}<p role="status">{notice}</p>{/if}

<style>
  .tabs {
    display: flex;
    gap: 0.15rem;
    padding: 0.15rem;
    border: 1px solid var(--color-engraving);
    border-radius: var(--radius-glyph);
    background: var(--color-void);
  }
  button,
  input {
    color: var(--color-parchment);
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-glyph);
    background: transparent;
    font: inherit;
    font-size: var(--text-xs);
  }
  button {
    padding: 0.3rem 0.55rem;
    min-height: 2.1rem;
    cursor: pointer;
  }
  .tabs button {
    flex: 1;
    border-color: transparent;
  }
  .tabs button[aria-pressed="true"] {
    border-color: var(--color-control-border);
    background: var(--color-obsidian-2);
    color: var(--color-bone);
    font-weight: 600;
  }
  h2,
  summary {
    font: 600 var(--text-xs)/1.5 var(--font-body);
    color: var(--color-parchment);
  }
  h2 {
    margin: 0.95rem 0.35rem 0.3rem;
  }
  p {
    color: var(--color-ash);
    font-size: var(--text-xs);
    line-height: 1.5;
    margin: 0.35rem 0 0.5rem;
    overflow-wrap: anywhere;
  }
  .folder {
    margin: 0.4rem 0 0 0.25rem;
    padding-inline-start: 0.4rem;
    border-inline-start: 1px solid var(--color-engraving);
  }
  summary {
    overflow-wrap: anywhere;
    min-height: 2rem;
    align-content: center;
    cursor: pointer;
  }
  .organize {
    margin-top: 1rem;
    padding-top: 0.45rem;
    border-top: 1px solid var(--color-engraving);
  }
  .organize button {
    margin: 0.1rem 0.15rem 0.1rem 0;
  }
  form label {
    display: grid;
    gap: 0.2rem;
    color: var(--color-parchment);
    font-size: var(--text-xs);
  }
  input {
    width: 100%;
    min-width: 0;
    min-height: 2.25rem;
    padding: 0.35rem;
    background: var(--color-void);
  }
  :is(button, input, summary):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 1px;
  }
</style>
