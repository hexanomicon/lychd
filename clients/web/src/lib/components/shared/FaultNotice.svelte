<!--
  A read or action failure, with an optional retry.

  severity "alert" interrupts (blocking failures); "status" is announced politely
  (soft notices such as an unavailable link target). The live region is the message
  itself, or, with a title or guidance, the block holding all of them; it carries the
  `id`, so controls can point at it with `aria-describedby`.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import Button from "./Button.svelte";

  let {
    title,
    message,
    severity = "alert",
    id,
    onretry,
    retrying = false,
    retryDisabled = false,
    retryLabel = "Retry",
    retryingLabel = "Retrying…",
    children
  }: {
    /** Short summary above the message ("Atlas could not be loaded."). */
    title?: string;
    /** Operator-readable failure text. */
    message: string;
    /** Live-region politeness. */
    severity?: "alert" | "status";
    /** Id of the live region, for `aria-describedby`. */
    id?: string;
    /** Shows a retry button when supplied. */
    onretry?: () => void;
    /** Retry in flight: disables and labels the button. */
    retrying?: boolean;
    /** Retry unavailable for another reason (e.g. an open editor). */
    retryDisabled?: boolean;
    retryLabel?: string;
    retryingLabel?: string;
    /** Extra guidance below the message. */
    children?: Snippet;
  } = $props();
</script>

<div class="fault-notice" data-titled={!!title}>
  {#if title || children}
    <div class="fault-notice__message" role={severity} {id}>
      {#if title}<strong class="fault-notice__title">{title}</strong>{/if}
      <p>{message}</p>
      {@render children?.()}
    </div>
  {:else}
    <p class="fault-notice__message" role={severity} {id}>{message}</p>
  {/if}
  {#if onretry}
    <Button size="sm" busy={retrying} disabled={retryDisabled} onclick={onretry}>{retrying ? retryingLabel : retryLabel}</Button>
  {/if}
</div>

<style>
  .fault-notice { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1rem; min-width: 0; }
  .fault-notice[data-titled="true"] { flex-direction: column; align-items: flex-start; }
  .fault-notice__message {
    flex: 1 1 16rem;
    min-width: 0;
    padding-inline-start: 0.75rem;
    border-inline-start: 2px solid var(--color-ember);
    color: var(--color-ember);
    font: var(--text-sm)/1.6 var(--font-body);
    overflow-wrap: anywhere;
  }
  .fault-notice__message, .fault-notice__message p { margin: 0; }
  .fault-notice__message :global(p + p) { margin-top: 0.35rem; }
  .fault-notice__title { display: block; margin-bottom: 0.2rem; font-weight: 600; }
  .fault-notice[data-titled="true"] .fault-notice__message :global(p) { color: var(--color-parchment); }
</style>
