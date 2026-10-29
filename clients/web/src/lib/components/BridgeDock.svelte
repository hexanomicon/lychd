<script lang="ts">
  import { onMount, tick, type Snippet } from "svelte";
  import { boundedDockWidth, bridgeDockStorageKey, defaultDockLayout, dockMaximumWidth, dockMinimumWidth, parseDockLayout } from "$lib/navigation/dock";

  let { open = $bindable(true), narrow = $bindable(false), forceOpen = false, available = true, viewing = "Altar", onconnect, children }: {
    open?: boolean; narrow?: boolean; forceOpen?: boolean; available?: boolean;
    viewing?: string; onconnect?: () => void; children: Snippet;
  } = $props();
  let width = $state(defaultDockLayout.width);
  let side = $state<"left" | "right">("right");
  let viewportWidth = $state(1280);
  const maximumWidth = $derived(Math.max(dockMinimumWidth, Math.min(dockMaximumWidth, Math.floor(viewportWidth * .6))));
  const effectiveWidth = $derived(Math.min(width, maximumWidth));
  let panel: HTMLElement | undefined;
  function capturePanel(element: HTMLElement) {
    panel = element;
    return () => { if (panel === element) panel = undefined; };
  }
  let mounted = $state(false);
  let opener: HTMLElement | null = null;
  let wasModal = false;
  let dragging: { x: number; width: number; pointer: number } | null = null;

  onMount(() => {
    const media = window.matchMedia?.("(max-width: 56rem)");
    narrow = media?.matches ?? false;
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(bridgeDockStorageKey);
      const saved = parseDockLayout(stored);
      width = saved.width;
      side = saved.side;
      if (!forceOpen) open = stored === null && narrow ? false : saved.open;
    } catch {
      if (!forceOpen && narrow) open = false;
    }
    const changed = (event: MediaQueryListEvent) => { narrow = event.matches; };
    media?.addEventListener?.("change", changed);
    mounted = true;
    return () => media?.removeEventListener?.("change", changed);
  });

  $effect(() => {
    if (!mounted) return;
    try { localStorage.setItem(bridgeDockStorageKey, JSON.stringify({ width, side, open })); }
    catch { /* Layout preferences are optional. */ }
  });

  // Synchronize the modal's DOM focus without remounting the conversation.
  $effect(() => {
    const modal = narrow && open;
    const target = panel;
    if (modal && !wasModal && target) {
      opener = document.activeElement instanceof HTMLElement && document.activeElement !== document.body
        ? document.activeElement : document.getElementById("bridge-toggle");
      void tick().then(() => {
        if (narrow && open && !target.contains(document.activeElement)) {
          target.querySelector<HTMLButtonElement>("[data-dock-close]")?.focus();
        }
      });
    } else if (!modal && wasModal) {
      if (opener?.isConnected) opener.focus({ preventScroll: true });
      opener = null;
    }
    wasModal = modal;
  });

  function keydown(event: KeyboardEvent) {
    if (!open || !narrow || !panel) return;
    if (event.key === "Escape" && !event.defaultPrevented) {
      event.preventDefault();
      collapse();
    } else if (event.key === "Tab") {
      const focusable = [...panel.querySelectorAll<HTMLElement>("a[href], button:not(:disabled), textarea:not(:disabled), input:not(:disabled), select:not(:disabled), summary, [tabindex='0']")]
        .filter((node) => !node.closest("[hidden], [inert]") && node.getClientRects().length > 0);
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first) { event.preventDefault(); panel.focus(); }
      else if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }
  }

  function collapse() {
    open = false;
    void tick().then(() => document.getElementById("bridge-toggle")?.focus({ preventScroll: true }));
  }

  function resizeStart(event: PointerEvent) {
    if (event.button !== 0 || narrow) return;
    dragging = { x: event.clientX, width: effectiveWidth, pointer: event.pointerId };
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }
  function resizeMove(event: PointerEvent) {
    if (!dragging || event.pointerId !== dragging.pointer) return;
    width = Math.min(maximumWidth, boundedDockWidth(dragging.width + (event.clientX - dragging.x) * (side === "left" ? 1 : -1)));
  }
  function resizeEnd(event: PointerEvent) {
    if (dragging?.pointer !== event.pointerId) return;
    dragging = null;
  }
  function resizeKey(event: KeyboardEvent) {
    if (event.key === "Home") width = dockMinimumWidth;
    else if (event.key === "End") width = maximumWidth;
    else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      width = Math.min(maximumWidth, boundedDockWidth(effectiveWidth + (event.key === "ArrowRight" ? 24 : -24) * (side === "left" ? 1 : -1)));
    } else return;
    event.preventDefault();
  }
</script>

<svelte:window bind:innerWidth={viewportWidth} onkeydown={keydown} />
<div class={["dock-frame", { "dock-left": side === "left", "dock-modal": narrow }]} hidden={!open} style:--dock-width={`${effectiveWidth}px`}>
  {#if narrow}<button class="dock-backdrop" type="button" tabindex="-1" aria-label="Close Bridge overlay" onclick={collapse}></button>{/if}
  <section id="bridge-dock" class="bridge-dock" role={narrow ? "dialog" : "complementary"} aria-modal={narrow ? true : undefined} aria-labelledby="bridge-dock-title" tabindex="-1" {@attach capturePanel}>
    <header class="dock-heading">
      <h2 id="bridge-dock-title">Bridge</h2>
      <div class="dock-actions">
        <button type="button" onclick={() => { side = side === "left" ? "right" : "left"; }} aria-label={`Dock Bridge ${side === "left" ? "right" : "left"}`}>Dock {side === "left" ? "right" : "left"}</button>
        <button type="button" data-dock-close onclick={collapse} aria-label="Collapse Bridge">− <span>Collapse</span></button>
      </div>
    </header>
    <p class="dock-context">Viewing: <strong>{viewing}</strong><span>Page content is not attached to messages.</span></p>
    {#if !available}
      <div class="dock-offline">
        <h3>Bridge is offline</h3>
        <p>This development workbench has not connected to LychD. Conversations and consent status are unavailable.</p>
        <button type="button" onclick={onconnect}>Connect to LychD</button>
      </div>
    {/if}
    <div class="dock-conversation" hidden={!available}>{@render children()}</div>
  </section>
  {#if !narrow}
    <!-- The focusable separator owns width only; it never changes conversation state. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <div class="dock-resizer" role="separator" aria-label="Bridge width" aria-orientation="vertical" aria-valuemin={dockMinimumWidth} aria-valuemax={maximumWidth} aria-valuenow={effectiveWidth} aria-controls="bridge-dock" tabindex="0" onpointerdown={resizeStart} onpointermove={resizeMove} onpointerup={resizeEnd} onpointercancel={resizeEnd} onlostpointercapture={() => { dragging = null; }} onkeydown={resizeKey}><span aria-hidden="true">⋮</span></div>
  {/if}
</div>

<style>
  .dock-frame { order: 1; position: relative; display: flex; flex: 0 0 min(var(--dock-width), 60vw); width: min(var(--dock-width), 60vw); min-width: 0; min-height: 0; background: var(--color-obsidian); border-left: 1px solid var(--color-engraving); }
  .dock-frame[hidden] { display: none; }
  .dock-left { order: -1; border-left: 0; border-right: 1px solid var(--color-engraving); }
  .bridge-dock { display: flex; flex-direction: column; width: 100%; min-width: 0; min-height: 0; }
  .dock-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .5rem; padding: .75rem 1rem; border-bottom: 1px solid var(--color-engraving); }
  .dock-heading h2 { font: 600 var(--text-lg)/1.4 var(--font-body); color: var(--color-bone); }
  .dock-actions { display: flex; gap: .5rem; }
  .dock-context { padding: .55rem 1rem; border-bottom: 1px solid var(--color-engraving); color: var(--color-ash); font-size: var(--text-xs); }
  .dock-context strong { color: var(--color-rune); font-weight: 500; }
  .dock-context span { display: block; margin-top: .2rem; font-size: var(--text-2xs); }
  button { min-height: 2.5rem; padding: .4rem .65rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); background: var(--color-obsidian); color: var(--color-bone); font: inherit; font-size: var(--text-xs); cursor: pointer; }
  button:hover { border-color: var(--color-rune); }
  button:focus-visible, .dock-resizer:focus-visible { outline: 2px solid var(--color-rune); outline-offset: -2px; }
  .dock-conversation { flex: 1; display: flex; min-height: 0; min-width: 0; overflow: hidden; }
  .dock-conversation[hidden] { display: none; }
  .dock-offline { padding: 1.5rem; color: var(--color-parchment); }
  .dock-offline h3 { color: var(--color-bone); margin-bottom: .75rem; }
  .dock-offline p { line-height: 1.7; margin-bottom: 1rem; }
  .dock-resizer { position: absolute; inset-block: 0; left: -5px; z-index: 2; width: 10px; cursor: col-resize; touch-action: none; display: grid; place-items: center; }
  .dock-left .dock-resizer { left: auto; right: -5px; }
  .dock-resizer span { background: var(--color-obsidian-2); border: 1px solid var(--color-engraving); color: var(--color-parchment); padding: .35rem 0; border-radius: var(--radius-glyph); }
  .dock-resizer:hover, .dock-resizer:focus-visible { background: color-mix(in srgb, var(--color-rune) 25%, transparent); }
  .dock-modal { position: absolute; inset: 0; z-index: 30; width: auto; border: 0; background: transparent; justify-content: flex-end; }
  .dock-modal.dock-left { justify-content: flex-start; }
  .dock-modal .bridge-dock { position: relative; z-index: 1; width: min(var(--dock-width), 100%); background: var(--color-obsidian); border: 1px solid var(--color-engraving); }
  .dock-backdrop { position: absolute; inset: 0; padding: 0; border: 0; border-radius: 0; background: color-mix(in srgb, var(--color-void) 75%, transparent); }
</style>
