<script lang="ts">
  import { onMount } from "svelte";
  import type { BridgeTurnView } from "$lib/api/models";
  import type { LiveTurn } from "../state/projection";
  import { navigationId } from "$lib/navigation/instruments";

  type Exchange = {
    key: string;
    run: string | null;
    position: number | null;
    question: string;
    reply: string;
    status: string;
  };
  let {
    session,
    turns,
    live,
    onjump,
  }: {
    session: string;
    turns: readonly BridgeTurnView[];
    live: readonly LiveTurn[];
    onjump: (position: number | null, run: string | null) => void;
  } = $props();
  const storageKey = "lychd.bridge-exchange-bookmarks.v1";
  let bookmarks = $state.raw<string[][]>([]);
  let previewKey = $state<string | null>(null);
  let current = $state<string | null>(null);
  let notice = $state("");
  const previewId = $props.id();
  const exchanges = $derived.by(() => {
    const result = new Map<string, Exchange>();
    for (const [position, turn] of turns.entries()) {
      const run = turn.run_id ?? null;
      // Without a Run identity this mark points only into the current retained read.
      const key = run ? `run:${run}` : `turn:${position}:${turn.created_at}`;
      const item = result.get(key) ?? { key, run, position, question: "", reply: "", status: "" };
      if (turn.role === "user") {
        item.question = turn.content;
        item.position = position;
      } else {
        item.reply = turn.content;
        item.status = turn.state ?? "";
      }
      result.set(key, item);
    }
    for (const turn of live) {
      const key = `run:${turn.runId}`;
      const item = result.get(key) ?? {
        key,
        run: turn.runId,
        position: null,
        question: "",
        reply: "",
        status: "",
      };
      item.reply = turn.content;
      item.status = turn.runStatus;
      result.set(key, item);
    }
    return [...result.values()];
  });
  const preview = $derived(exchanges.find((item) => item.key === previewKey));
  const selected = $derived(exchanges.find((item) => item.key === current) ?? exchanges.at(-1));

  function readBookmarks() {
    try {
      const raw = localStorage.getItem(storageKey);
      const saved: unknown = raw && raw.length <= 65536 ? JSON.parse(raw) : [];
      bookmarks =
        Array.isArray(saved) && saved.length <= 200
          ? saved.filter(
              (pair) =>
                Array.isArray(pair) &&
                pair.length === 2 &&
                pair.every((value) => typeof value === "string" && navigationId(value)),
            )
          : [];
    } catch {
      bookmarks = [];
    }
  }

  onMount(() => {
    readBookmarks();
    const sync = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) readBookmarks();
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  });

  function marked(run: string | null) {
    return run !== null && bookmarks.some(([owner, id]) => owner === session && id === run);
  }

  function bookmark(run: string) {
    if (!navigationId(session) || !navigationId(run)) return;
    if (marked(run)) bookmarks = bookmarks.filter(([owner, id]) => owner !== session || id !== run);
    else if (bookmarks.length < 200) bookmarks = [...bookmarks, [session, run]];
    else {
      notice = "Bookmark limit reached. Remove a bookmark first.";
      return;
    }
    notice = "";
    try {
      localStorage.setItem(storageKey, JSON.stringify(bookmarks));
    } catch {
      notice = "Bookmark kept in this view. Browser storage is unavailable.";
    }
  }

  function move(event: KeyboardEvent) {
    const button = event.currentTarget as HTMLButtonElement;
    const marks = Array.from(button.parentElement?.querySelectorAll<HTMLButtonElement>("button") ?? []);
    if (event.key === "Escape") {
      previewKey = null;
      return;
    }
    const index = marks.indexOf(button);
    const target =
      event.key === "ArrowDown"
        ? Math.min(index + 1, marks.length - 1)
        : event.key === "ArrowUp"
          ? Math.max(index - 1, 0)
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? marks.length - 1
              : -1;
    if (target < 0) return;
    event.preventDefault();
    marks[target]?.focus();
  }

  function jump(item: Exchange) {
    current = item.key;
    previewKey = null;
    onjump(item.position, item.run);
  }
</script>

{#if exchanges.length}
  <nav
    class="exchange-rail"
    aria-label="Conversation exchanges"
    onpointerleave={(event) => {
      if (!event.currentTarget.contains(document.activeElement)) previewKey = null;
    }}
    onfocusout={(event) => {
      if (!(event.relatedTarget instanceof Node) || !event.currentTarget.contains(event.relatedTarget))
        previewKey = null;
    }}
  >
    <div class="marks">
      {#each exchanges as item, index (item.key)}
        <button
          type="button"
          class="mark"
          data-exchange-key={item.key}
          class:current={selected?.key === item.key}
          class:marked={marked(item.run)}
          aria-label={`Jump to exchange ${index + 1}${marked(item.run) ? ", bookmarked" : ""}`}
          aria-describedby={previewKey === item.key ? previewId : undefined}
          aria-current={current === item.key ? "location" : undefined}
          tabindex={(previewKey ?? selected?.key) === item.key ? 0 : -1}
          onpointerenter={() => {
            previewKey = item.key;
          }}
          onfocus={() => {
            previewKey = item.key;
          }}
          onkeydown={move}
          onclick={() => jump(item)}><span></span></button
        >
      {/each}
    </div>
    {#if preview}
      <div class="exchange-preview" id={previewId}>
        <strong>Exchange {exchanges.indexOf(preview) + 1}</strong>
        {#if preview.question}<div>
            <small>You</small>
            <p>{preview.question.slice(0, 200)}</p>
          </div>{/if}
        {#if preview.reply}<div>
            <small>LychD</small>
            <p>{preview.reply.slice(0, 240)}</p>
          </div>
        {:else}<p>{preview.status ? preview.status.replaceAll("_", " ") : "No reply retained."}</p>{/if}
        {#if preview.run && navigationId(preview.run) && navigationId(session)}
          <button
            class="bookmark"
            type="button"
            aria-pressed={marked(preview.run)}
            onkeydown={(event) => {
              if (event.key !== "Escape") return;
              const buttons = event.currentTarget
                .closest("nav")
                ?.querySelectorAll<HTMLButtonElement>(".mark");
              Array.from(buttons ?? [])
                .find((button) => button.dataset.exchangeKey === previewKey)
                ?.focus();
              previewKey = null;
            }}
            onclick={() => {
              if (preview?.run) bookmark(preview.run);
            }}
          >
            {marked(preview.run) ? "Remove bookmark" : "Bookmark exchange"}
          </button>
        {/if}
        {#if notice}<p role="status">{notice}</p>{/if}
      </div>
    {/if}
  </nav>
{/if}

<style>
  .exchange-rail {
    position: absolute;
    z-index: 3;
    inset-inline-start: 0.1rem;
    top: 50%;
    transform: translateY(-50%);
    max-height: calc(100% - 1rem);
    display: flex;
    align-items: center;
  }
  .marks {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    max-height: min(15rem, 36dvh);
    padding: 0.2rem;
    overflow-y: auto;
    scrollbar-width: thin;
  }
  .mark {
    display: flex;
    align-items: center;
    justify-content: start;
    width: 1.65rem;
    min-height: 1.45rem;
    padding: 0 0.18rem;
    background: transparent;
    border: 0;
    cursor: pointer;
  }
  .mark span {
    width: 0.65rem;
    height: 2px;
    border-radius: 2px;
    background: var(--color-ash);
  }
  .mark.current span,
  .mark:focus-visible span,
  .mark:hover span {
    width: 1.05rem;
    height: 3px;
    background: var(--color-bone);
  }
  .mark.marked span::after {
    content: "";
    display: block;
    width: 0.3rem;
    height: 0.3rem;
    transform: translate(-0.13rem, -0.08rem) rotate(45deg);
    background: var(--color-rune);
  }
  .exchange-preview {
    position: absolute;
    inset-inline-start: calc(100% - 0.15rem);
    width: min(17rem, 63vw);
    max-height: 38dvh;
    overflow-y: auto;
    padding: 0.7rem 0.85rem;
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-panel);
    background: var(--color-obsidian);
    color: var(--color-parchment);
    overflow-wrap: anywhere;
  }
  .exchange-preview strong {
    color: var(--color-bone);
    font-size: var(--text-sm);
  }
  small {
    display: block;
    margin-top: 0.5rem;
    color: var(--color-ash);
    font-size: var(--text-xs);
  }
  p {
    display: -webkit-box;
    line-clamp: 3;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin: 0.15rem 0;
    font-size: var(--text-sm);
    line-height: 1.45;
  }
  .bookmark {
    min-height: 2rem;
    margin-top: 0.45rem;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-glyph);
    background: var(--color-obsidian-2);
    color: var(--color-rune);
    cursor: pointer;
    font: inherit;
    font-size: var(--text-xs);
  }
  button:focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: -1px;
  }
</style>
