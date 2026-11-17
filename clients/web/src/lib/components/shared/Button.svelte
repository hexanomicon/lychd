<!--
  The Altar's one button. Renders `<a>` when `href` is set, otherwise `<button>`.

  - primary: the single filled action in a region (Consecrate, New canvas, Offer).
  - secondary: bordered everyday action (Refresh, Retry, Cancel Run).
  - ghost: borderless toolbar action.
  `busy` sets `aria-busy` and disables the button so async actions cannot double-fire.
  Extra attributes (`onclick`, `aria-*`, `id`, …) pass through to the element.
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAnchorAttributes, HTMLButtonAttributes } from "svelte/elements";

  type Common = {
    /** Visual weight. */
    variant?: "primary" | "secondary" | "ghost";
    /** "md" meets the 44px target; "sm" is for dense toolbars and rails. */
    size?: "sm" | "md";
    /** Pending async work: disables and announces `aria-busy`. */
    busy?: boolean;
    /** Button content. */
    children: Snippet;
  };
  /** Navigation target: renders `<a>` instead of `<button>`. */
  type Props = Common & { href?: string } & Omit<HTMLButtonAttributes, "children">;

  let { variant = "secondary", size = "md", busy = false, href, children, ...rest }: Props = $props();
</script>

{#if href !== undefined}
  <a {...rest as HTMLAnchorAttributes} class="btn" data-variant={variant} data-size={size} {href}>{@render children()}</a>
{:else}
  <button
    {...rest}
    class="btn"
    data-variant={variant}
    data-size={size}
    type={rest.type ?? "button"}
    disabled={rest.disabled || busy}
    aria-busy={busy || undefined}
  >{@render children()}</button>
{/if}

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    min-height: 2.75rem;
    padding: 0.45rem 1rem;
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-glyph);
    background: var(--color-obsidian-2);
    color: var(--color-bone);
    font: 500 var(--text-sm)/1.2 var(--font-body);
    text-decoration: none;
    white-space: nowrap;
    cursor: pointer;
    transition: background-color var(--duration-whisper), border-color var(--duration-whisper), color var(--duration-whisper);
  }
  .btn[data-size="sm"] { min-height: 2.25rem; padding: 0.3rem 0.75rem; font-size: var(--text-xs); }
  .btn:hover:not(:disabled) { border-color: var(--color-rune); }
  .btn[data-variant="primary"] { border-color: var(--color-bone); background: var(--color-bone); color: var(--color-void); font-weight: 600; }
  .btn[data-variant="primary"]:hover:not(:disabled) { border-color: var(--color-parchment); background: var(--color-parchment); }
  .btn[data-variant="ghost"] { border-color: transparent; background: transparent; color: var(--color-parchment); }
  .btn[data-variant="ghost"]:hover:not(:disabled) { border-color: transparent; background: var(--color-obsidian-2); color: var(--color-bone); }
  .btn:disabled { opacity: 0.45; cursor: default; }
  .btn[aria-busy="true"] { cursor: progress; }
  .btn:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .btn { transition: none; } }
</style>
