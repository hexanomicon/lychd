<!--
  Native `<details>` disclosure in two shapes:
  - section: expands in place (Graph outline, Séance details, Coverage).
  - popover: floats below its summary and closes on Escape or outside click
    (Pattern library, Tools, filters).
  Keyboard and screen-reader behaviour is the browser's own; nothing is re-implemented.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import type { Attachment } from "svelte/attachments";
  import { dismissibleDetails } from "./dismissible";

  let {
    variant = "section",
    open = $bindable(false),
    align = "end",
    summaryLabel,
    summaryAttach,
    ontoggle,
    summary,
    children
  }: {
    /** In-place section or floating popover. */
    variant?: "section" | "popover";
    /** Bindable open state. */
    open?: boolean;
    /** Popover edge alignment. */
    align?: "start" | "end";
    /** Accessible name when the visible summary is terse. */
    summaryLabel?: string;
    /** Attachment on the summary, e.g. to keep it as a focus-return target. */
    summaryAttach?: Attachment<HTMLElement>;
    /** Fires after the browser toggles the disclosure (never after unmount). */
    ontoggle?: (open: boolean) => void;
    /** Visible summary content. */
    summary: Snippet;
    /** Disclosed content. */
    children: Snippet;
  } = $props();
</script>

<details
  class="disclosure"
  data-variant={variant}
  data-align={align}
  bind:open
  ontoggle={(event) => { if (event.currentTarget.isConnected) ontoggle?.(event.currentTarget.open); }}
  {@attach variant === "popover" && dismissibleDetails}
>
  <summary aria-label={summaryLabel} {@attach summaryAttach}>
    {@render summary()}<span class="disclosure__chevron" aria-hidden="true"></span>
  </summary>
  <div class="disclosure__body">{@render children()}</div>
</details>

<style>
  .disclosure { position: relative; min-width: 0; }
  summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.75rem;
    color: var(--color-text-body);
    font-size: var(--text-sm);
    list-style: none;
    cursor: pointer;
  }
  summary::-webkit-details-marker { display: none; }
  summary:hover { color: var(--color-text-strong); }
  summary:focus-visible { outline: 2px solid var(--color-interactive); outline-offset: 2px; border-radius: var(--radius-rune); }
  .disclosure__chevron {
    width: 0.45rem;
    height: 0.45rem;
    border-inline-end: 1.5px solid currentColor;
    border-block-end: 1.5px solid currentColor;
    transform: rotate(-45deg);
    transition: transform var(--duration-drift, 160ms) ease;
  }
  .disclosure[open] > summary .disclosure__chevron { transform: rotate(45deg); }
  .disclosure[data-variant="section"] > .disclosure__body { padding-block: 0.25rem 0.75rem; }
  .disclosure[data-variant="popover"] > .disclosure__body {
    position: absolute;
    inset-block-start: calc(100% + 0.35rem);
    z-index: 30;
    width: max-content;
    min-width: 14rem;
    max-width: min(26rem, 90vw);
    max-height: min(28rem, 60dvh);
    overflow-y: auto;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border-context, var(--color-border-subtle));
    border-radius: var(--radius-glyph);
    background: var(--color-surface-context, var(--color-surface-panel));
    box-shadow: 0 0.75rem 2rem color-mix(in srgb, var(--color-shadow) 35%, transparent);
  }
  .disclosure[data-align="end"] > .disclosure__body { inset-inline-end: 0; }
  .disclosure[data-align="start"] > .disclosure__body { inset-inline-start: 0; }
  @media (prefers-reduced-motion: reduce) { .disclosure__chevron { transition: none; } }
</style>
