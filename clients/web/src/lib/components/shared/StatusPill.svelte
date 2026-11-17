<!--
  Small rounded status label: consent counts, lifecycle badges, read-only marks, live state.

  Tone carries meaning through colour *and* text; the optional dot is decorative.
  Use the global `.chip[data-state]` vocabulary only for Run and capability states
  that need its animation; everything else uses this pill.
-->
<script module lang="ts">
  export type PillTone = "neutral" | "attention" | "info" | "success" | "fault" | "muted";
</script>

<script lang="ts">
  import type { Snippet } from "svelte";

  let { tone = "neutral", dot = false, title, children }: {
    /** Semantic colour; never the only carrier of meaning. */
    tone?: PillTone;
    /** Leading decorative dot in the current colour. */
    dot?: boolean;
    /** Optional native tooltip. */
    title?: string;
    /** Pill text. */
    children: Snippet;
  } = $props();
</script>

<span class="status-pill" data-tone={tone} {title}>
  {#if dot}<span class="status-pill__dot" aria-hidden="true"></span>{/if}{@render children()}
</span>

<style>
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    max-width: 100%;
    padding: 0.05rem 0.55rem;
    border: 1px solid var(--color-engraving);
    border-radius: 999px;
    color: var(--color-parchment);
    font-size: var(--text-xs);
    font-weight: 500;
    line-height: 1.6;
    white-space: nowrap;
  }
  .status-pill[data-tone="attention"] {
    border-color: color-mix(in srgb, var(--color-accent) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent) 10%, transparent);
    color: var(--color-accent);
  }
  .status-pill[data-tone="info"] { border-color: color-mix(in srgb, var(--color-frost) 38%, transparent); color: var(--color-frost); }
  .status-pill[data-tone="success"] { border-color: color-mix(in srgb, var(--color-lich) 40%, transparent); color: var(--color-lich); }
  .status-pill[data-tone="fault"] { border-color: color-mix(in srgb, var(--color-ember) 40%, transparent); color: var(--color-ember); }
  .status-pill[data-tone="muted"] { border-style: dashed; color: var(--color-ash); }
  .status-pill__dot { flex: 0 0 auto; width: 0.4rem; height: 0.4rem; border-radius: 50%; background: currentColor; }
</style>
