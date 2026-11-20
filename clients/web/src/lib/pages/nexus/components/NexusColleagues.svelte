<script lang="ts">
  import { onMount } from "svelte";
  import { setNexusPresence } from "$lib/api/client";
  import type { NexusSnapshot } from "$lib/api/models";

  type Board = NonNullable<NexusSnapshot["presence"]>;
  let { board, stale, onrefresh }: { board: Board; stale: boolean; onrefresh: () => Promise<void> } = $props();
  let saving = $state(false);
  let notice = $state("");
  let now = $state(Date.now());
  onMount(() => {
    const clock = window.setInterval(() => { now = Date.now(); }, 1000);
    return () => window.clearInterval(clock);
  });

  const labels = { ready: "Ready", busy: "Busy", unknown: "Availability unknown", hidden: "Hidden" };
  const sharing = $derived(board.sharing_until && Date.parse(board.sharing_until) > now ? board.sharing : "hidden");

  async function choose(choice: Board["sharing"]) {
    if (saving) return;
    saving = true;
    notice = "";
    try {
      const result = await setNexusPresence(board.audience_id, choice);
      if (result.sharing !== choice) {
        notice = "The requested sharing choice is no longer active.";
      } else {
        notice = choice === "hidden" ? "Sharing stopped on this Vessel." : "Sharing preference saved.";
      }
    } catch {
      notice = "Change could not be confirmed. Check the refreshed preference.";
    }
    try {
      await onrefresh();
    } finally {
      saving = false;
    }
  }
</script>

<section class="panel colleagues" aria-label="Paired availability">
  <h2 class="rune-head">Paired availability</h2>
  <ul>
    {#each board.peers as peer (peer.name)}
      {@const availability = !stale && peer.expires_at && Date.parse(peer.expires_at) > now ? peer.availability : "unknown"}
      <li>
        <strong>{peer.name}</strong>
        <span class="availability" data-availability={availability}>{labels[availability]}</span>
        {#if peer.observed_at}
          <time datetime={peer.observed_at}>Last report {new Date(peer.observed_at).toLocaleString()}</time>
        {:else}<small>No report received</small>{/if}
        {#if peer.publication === "unavailable"}<small>Local publication failed</small>{/if}
      </li>
    {/each}
  </ul>
  <p class="preference"><strong>Your availability</strong> · {stale ? "Unknown" : labels[sharing]}
    {#if !stale && sharing !== "hidden" && board.sharing_until}
      until <time datetime={board.sharing_until}>{new Date(board.sharing_until).toLocaleTimeString()}</time>
    {/if}
  </p>
  <p>Share for one hour with {board.peers.map((peer) => peer.name).join(", ")}. Ready means you welcome requests. Each task needs separate admission.</p>
  <div class="choices" role="group" aria-label="Share your availability">
    <button type="button" disabled={saving || stale || sharing === "ready"} onclick={() => void choose("ready")}>Share ready</button>
    <button type="button" disabled={saving || stale || sharing === "busy"} onclick={() => void choose("busy")}>Share busy</button>
    <button type="button" disabled={saving || (!stale && sharing === "hidden" && !notice && !board.peers.some((p) => p.publication === "unavailable"))} onclick={() => void choose("hidden")}>Stop sharing</button>
  </div>
  <span role="status">{saving ? "Updating…" : notice}</span>
</section>

<style>
  .colleagues { padding: 1.125rem; }
  h2, p { margin: 0 0 .6rem; }
  p { font-size: var(--text-sm); line-height: 1.5; }
  ul { list-style: none; padding: 0; margin: .85rem 0 1rem; border-bottom: 1px solid var(--color-engraving); }
  li { display: grid; grid-template-columns: minmax(5rem, 1fr) minmax(6rem, 1fr) 2fr;
    align-items: center; gap: .35rem 1rem; border-top: 1px solid var(--color-engraving);
    padding: .65rem 0; overflow-wrap: anywhere; }
  .availability { justify-self: start; font-size: var(--text-sm); }
  .availability[data-availability="ready"] { color: var(--color-secondary); }
  .availability[data-availability="busy"] { color: var(--color-heat); }
  li time, li small { color: var(--color-ash); font-size: var(--text-xs); }
  .preference { font-size: inherit; }
  .choices { display: flex; flex-wrap: wrap; gap: .5rem; }
  button { min-height: 2.5rem; padding: .4rem .85rem; border: 1px solid var(--color-control-border);
    border-radius: var(--radius-glyph); background: var(--color-obsidian-2); color: var(--color-parchment); cursor: pointer; }
  button:hover:enabled { border-color: var(--color-primary); }
  button:disabled { background: var(--color-obsidian); color: var(--color-ash); cursor: default; }
  @media (max-width: 36rem) {
    li { grid-template-columns: minmax(0, 1fr) auto; }
    li time, li small { grid-column: 1 / -1; }
  }
</style>
