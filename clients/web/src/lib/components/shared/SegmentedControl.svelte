<!--
  A labelled group of mutually exclusive toggle buttons (Whole Pattern / Stations,
  Map / List, view filters). Each button reports its state with `aria-pressed`.
  Bind `value`, or listen with `onchange` when the owner keeps the state.
-->
<script module lang="ts">
  export interface SegmentOption<T extends string = string> {
    value: T;
    label: string;
    /** Optional count shown after the label. */
    count?: number | string;
    disabled?: boolean;
  }
</script>

<script lang="ts" generics="T extends string">
  import type { Snippet } from "svelte";

  let { label, options, value = $bindable(), separator, onchange, hint }: {
    /** Accessible group name. */
    label: string;
    /** Choices, in order. */
    options: readonly SegmentOption<T>[];
    /** Selected value. */
    value?: T;
    /** Decorative separator rendered between buttons (e.g. "/"). */
    separator?: string;
    /** Called after a choice; `value` is already updated. */
    onchange?: (value: T) => void;
    /** Muted text after the buttons. */
    hint?: Snippet;
  } = $props();

  function choose(next: T) {
    value = next;
    onchange?.(next);
  }
</script>

<div class="segmented" role="group" aria-label={label}>
  {#each options as option, index (option.value)}
    {#if separator && index > 0}<span class="segmented__separator" aria-hidden="true">{separator}</span>{/if}
    <button type="button" aria-pressed={value === option.value} disabled={option.disabled} onclick={() => choose(option.value)}>
      {option.label}{#if option.count !== undefined} <strong class="segmented__count">{option.count}</strong>{/if}
    </button>
  {/each}
  {#if hint}<span class="segmented__hint">{@render hint()}</span>{/if}
</div>

<style>
  .segmented {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem;
    min-width: 0;
    padding: 0.25rem;
    border: 1px solid var(--color-border-subtle);
    border-radius: var(--radius-glyph);
    background: var(--color-surface-raised);
  }
  button {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 2.25rem;
    padding: 0.3rem 0.85rem;
    border: 0;
    border-radius: var(--radius-rune);
    background: transparent;
    color: var(--color-text-body);
    font: 500 var(--text-sm)/1.2 var(--font-body);
    cursor: pointer;
  }
  button:hover:not(:disabled) { color: var(--color-text-strong); }
  button[aria-pressed="true"] { background: var(--color-action); color: var(--color-on-action); }
  button:disabled { opacity: 0.45; cursor: default; }
  button:focus-visible { outline: 2px solid var(--color-interactive); outline-offset: 2px; }
  .segmented__count { font-weight: 600; }
  .segmented__separator { color: var(--color-text-muted); }
  .segmented__hint { margin-inline-start: auto; padding-inline: 0.5rem; color: var(--color-text-muted); font-size: var(--text-xs); }
</style>
