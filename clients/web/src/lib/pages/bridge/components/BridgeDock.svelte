<script lang="ts">
  import { onMount, tick, type Snippet } from "svelte";
  import { boundedDockWidth, bridgeDockStorageKey, defaultDockLayout, dockMaximumWidth, dockMinimumWidth, parseDockLayout } from "$lib/pages/bridge/state/dock";

  import WorkTools from "$lib/shell/components/WorkTools.svelte";
  import { createLocalFiles } from "$lib/shell/state/local-files.svelte";
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";

  let { tool = $bindable("bridge"), open = $bindable(true), narrow = $bindable(false), forceOpen = false, canvasFirst = false, focused = false, suspended = false, focusHref = "/seances", focusLabel = "Open Séance", browseHref = "/seances", workHref = "/orb", available = true, viewing = "Altar", onconnect, onexpand, onsuspend, children }: {
    tool?: string; open?: boolean; narrow?: boolean; forceOpen?: boolean; canvasFirst?: boolean; available?: boolean;
    focused?: boolean; suspended?: boolean; focusHref?: string; focusLabel?: string; browseHref?: string; workHref?: string;
    viewing?: string; onconnect?: () => void; onexpand?: () => void; onsuspend?: () => void; children: Snippet;
  } = $props();
  const files = createLocalFiles();
  let webPages = $state<string[]>([]);
  let focusedTool=$state("files"), workOpen=$state(false), workWidth=$state(480);
  let width = $state(defaultDockLayout.width);
  let side = $state(defaultDockLayout.side);
  let preferredOpen = $state(defaultDockLayout.open);
  let savedPreference = $state(false);
  let viewportWidth = $state(1280);
  const maximumWidth = $derived(Math.max(dockMinimumWidth, Math.min(dockMaximumWidth, Math.floor(viewportWidth * .6))));
  const effectiveWidth = $derived(Math.min(width, maximumWidth));
  const modal = $derived(narrow && open && !focused && !suspended);
  const visible = $derived(open || focused);
  let panel: HTMLElement | undefined;
  function capturePanel(element: HTMLElement) {
    panel = element;
    return () => { if (panel === element) panel = undefined; };
  }
  let mounted = $state(false);
  let opener: HTMLElement | null = null;
  let wasModal = false;
  let wasSuspended = false;
  let dragging: { x: number; width: number; pointer: number } | null = null;

  function setOpen(value: boolean) {
    // Suspend while controls are still visible; full focus remains visible when open is false.
    if (open && !value && !focused) onsuspend?.();
    open = value;
  }

  onMount(() => {
    const media = window.matchMedia?.("(max-width: 56rem)");
    narrow = media?.matches ?? false;
    workOpen = !narrow && (window.matchMedia?.("(min-width: 76rem)").matches ?? false);
    if (workOpen) workWidth = Math.min(620, Math.round(window.innerWidth * .34));
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(bridgeDockStorageKey);
      const saved = parseDockLayout(stored);
      width = saved.width;
      savedPreference = stored !== null;
      side = stored === null && canvasFirst ? "right" : saved.side;
      preferredOpen = stored === null && (narrow || canvasFirst) ? false : saved.open;
      if (!forceOpen) setOpen(preferredOpen);
    } catch {
      if (narrow) { preferredOpen = false; if (!forceOpen) setOpen(false); }
    }
    const changed = (event: MediaQueryListEvent) => { narrow = event.matches; };
    media?.addEventListener?.("change", changed);
    mounted = true;
    return () => media?.removeEventListener?.("change", changed);
  });

  $effect(() => {
    if (!mounted || !savedPreference) return;
    try { localStorage.setItem(bridgeDockStorageKey, JSON.stringify({ width, side, open: preferredOpen })); }
    catch { /* Layout preferences are optional. */ }
  });

  // Synchronize the modal's DOM focus without remounting the conversation.
  $effect(() => {
    const target = panel;
    if (modal && !wasModal && !wasSuspended && target) {
      opener = document.activeElement instanceof HTMLElement && document.activeElement !== document.body
        ? document.activeElement : document.getElementById("bridge-toggle");
      void tick().then(() => {
        if (narrow && open && !focused && !suspended && !target.contains(document.activeElement)) {
          target.querySelector<HTMLButtonElement>("[data-dock-close]")?.focus();
        }
      });
    } else if (!modal && wasModal) {
      if (!suspended && !focused && opener?.isConnected) opener.focus({ preventScroll: true });
      opener = null;
    }
    wasModal = modal;
    wasSuspended = suspended;
  });

  function keydown(event: KeyboardEvent) {
    if (!modal || !panel) return;
    if (event.key === "Escape" && !event.defaultPrevented) {
      event.preventDefault();
      collapse();
    } else if (event.key === "Tab") {
      const focusable = [...panel.querySelectorAll<HTMLElement>("a[href], button:not(:disabled), textarea:not(:disabled), input:not(:disabled), select:not(:disabled), summary, [tabindex='0']")]
        .filter((node) => node.tabIndex >= 0 && !node.closest("[hidden], [inert]") && node.getClientRects().length > 0);
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

  // Navigation can request the open canvas until an operator chooses a dock layout.
  export function applyCanvasDefault() {
    if (savedPreference || forceOpen) return;
    side = "right";
    setOpen(false);
  }
  function toggle() {
    savedPreference = true;
    if (open) collapse();
    else {
      preferredOpen = true;
      if (onexpand) onexpand();
      else open = true;
    }
  }

  function collapse() {
    savedPreference = true;
    preferredOpen = false;
    setOpen(false);
    void tick().then(() => document.getElementById("bridge-toggle")?.focus({ preventScroll: true }));
  }

  function resizeStart(event: PointerEvent) {
    if (event.button !== 0 || narrow) return;
    savedPreference = true;
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
    savedPreference = true;
    event.preventDefault();
  }
</script>

<svelte:window bind:innerWidth={viewportWidth} onkeydown={keydown} />
<div id={focused ? "altar-main" : undefined} class={["dock-shell", { "dock-left": side === "left", "dock-modal": narrow && !focused && !suspended, "dock-collapsed": !visible, "dock-focused": focused, "canvas-dock": canvasFirst }]} role={focused ? "main" : modal ? "dialog" : undefined} aria-label={focused ? "Bridge workspace" : undefined} aria-modal={modal ? true : undefined} aria-labelledby={modal ? "bridge-dock-title" : undefined} inert={suspended} tabindex="-1" style:--dock-width={`${effectiveWidth}px`} {@attach capturePanel}>
  {#if !focused}<button id="bridge-toggle" class="dock-toggle" type="button" data-dock-close aria-label={open ? "Collapse Bridge" : "Expand Bridge"} aria-expanded={open} aria-controls="bridge-dock" title={open ? "Collapse Bridge" : "Expand Bridge"} onclick={toggle}><span aria-hidden="true">{(side === "left") === open ? "<<" : ">>"}</span>{#if !open && !canvasFirst}<span class="edge-label">Bridge</span>{/if}</button>{/if}
  <div class="dock-frame" hidden={!visible}>
    {#if modal}<button class="dock-backdrop" type="button" tabindex="-1" aria-label="Close Bridge overlay" onclick={collapse}></button>{/if}
    <section id="bridge-dock" class="bridge-dock" role={narrow || focused ? undefined : "complementary"} aria-labelledby={!focused ? "bridge-dock-title" : undefined}>
      {#if focused}
        <nav class="focus-heading" aria-label="Bridge workspace">
          <a href={workHref}>← Back to workspace</a>
          <a href={browseHref}>Browse séances</a>
          <button class="open-work" type="button" aria-expanded={workOpen} onclick={()=>workOpen=!workOpen}>{workOpen?"Hide tools":"Open tools"}</button>
        </nav>
      {:else}
      <header class="dock-heading">
        <div class="dock-location"><h2 id="bridge-dock-title">Bridge</h2><span class="dock-view"><span class="visually-hidden">Viewing: </span>{viewing}</span></div>
        <div class="dock-actions">
          <a href={focusHref} aria-label={focusLabel} title={focusLabel}><span aria-hidden="true">↗</span><span class="visually-hidden">{focusLabel}</span></a>
          <button type="button" onclick={() => { savedPreference = true; side = side === "left" ? "right" : "left"; }} aria-label={`Dock Bridge ${side === "left" ? "right" : "left"}`} title={`Dock Bridge ${side === "left" ? "right" : "left"}`}><span aria-hidden="true">⇄</span></button>
        </div>
      </header>
      <WorkTools bind:pages={webPages} {files} bind:active={() => tool, (next) => { if(tool==="bridge" && next!=="bridge")onsuspend?.();tool=next; }}/>
      {/if}
      {#if !available && (focused || tool==="bridge")}
        <div class="dock-offline">
          <h3>Bridge is offline</h3>
          <p>This development workbench has not connected to LychD. Conversations and consent status are unavailable.</p>
          <button type="button" onclick={onconnect}>Connect to LychD</button>
        </div>
      {/if}
      <div class="dock-conversation" hidden={!available || (!focused && tool!=="bridge")}>{@render children()}</div>
    </section>
    {#if focused && workOpen}<aside class="focus-work" style:--work-width={workWidth+"px"} aria-label="Local work tools"><PaneGrip bind:width={workWidth} name="Work tools width"/><button type="button" class="work-close" aria-label="Close work tools" title="Close work tools" onclick={()=>workOpen=false}>»</button><WorkTools focused bind:pages={webPages} {files} bind:active={focusedTool}/></aside>{/if}
    {#if !narrow && !focused}
      <!-- The focusable separator owns width only; it never changes conversation state. -->
      <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
      <div class="dock-resizer" role="separator" aria-label="Bridge width" aria-orientation="vertical" aria-valuemin={dockMinimumWidth} aria-valuemax={maximumWidth} aria-valuenow={effectiveWidth} aria-controls="bridge-dock" tabindex="0" onpointerdown={resizeStart} onpointermove={resizeMove} onpointerup={resizeEnd} onpointercancel={resizeEnd} onlostpointercapture={() => { dragging = null; }} onkeydown={resizeKey}><span aria-hidden="true">⋮</span></div>
    {/if}
  </div>
</div>

<style>
  .open-work {margin-left:auto}
  .focus-work{position:relative;display:flex;flex-direction:column;width:min(var(--work-width),58%);min-width:0;flex:none;background:var(--color-obsidian);border-left:1px solid var(--color-engraving)}
  .focus-work :global(.work-tabs){padding-inline-start:3rem}
  .work-close{position:absolute;top:.35rem;left:.5rem;z-index:2;min-height:2rem}
  @media(max-width:42rem){.focus-work{position:absolute;inset:0 0 0 auto;width:min(100%,25rem);z-index:22;box-shadow:-.5rem 0 1rem #0005}}
  .dock-shell { order: 1; position: relative; z-index:20; display: flex; flex: 0 0 min(var(--dock-width), 60vw); width: min(var(--dock-width), 60vw); min-width: 0; min-height: 0; }
  .dock-shell.dock-left { order: -1; }
  .dock-shell.dock-collapsed { flex-basis: 0; width: 0; }
  .dock-focused .bridge-dock{flex:1;min-width:0}
  .dock-shell.dock-focused { flex: 1 1 0; width: 100%; order: 0; overflow: hidden; }
  .dock-focused .dock-frame { border: 0; }
  .focus-heading { display: flex; flex-wrap: wrap; gap: .25rem 1rem; padding: .35rem 1rem; border-bottom: 1px solid var(--color-engraving); }
  .focus-heading a, .dock-actions a { display: inline-flex; align-items: center; min-height: 2rem; font-size: var(--text-xs); color: var(--color-parchment); }
  a:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
  .dock-frame { position: relative; display: flex; width: 100%; min-width: 0; min-height: 0; background: var(--color-obsidian); border-left: 1px solid var(--color-engraving); }
  .dock-frame[hidden] { display: none; }
  .dock-left .dock-frame { border-left: 0; border-right: 1px solid var(--color-engraving); }
  .bridge-dock { display: flex; flex-direction: column; width: 100%; min-width: 0; min-height: 0; }
  .dock-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .35rem; min-height:3.5rem; padding: .6rem 1rem .35rem; border-bottom: 0; background: var(--color-obsidian); }
  .dock-heading h2 { font: 600 var(--text-lg)/1.4 var(--font-body); letter-spacing:-.025em; color: var(--color-bone); }
  .dock-location { display: flex; align-items: baseline; flex-wrap: wrap; gap: .35rem .6rem; min-width: 0; }
  .dock-view { font-size: var(--text-xs); color: var(--color-ash); overflow-wrap: anywhere; }
  .dock-actions button, .dock-actions a { min-height:2rem; min-width:2rem; display:grid; place-items:center; border:0; background:transparent; border-radius:var(--radius-rune); text-decoration:none; font-size:1.15rem; }
  .dock-actions button:hover, .dock-actions a:hover { background:var(--color-obsidian-2); }
  .dock-actions { display: flex; gap: .125rem; }
  button { min-height: 2.5rem; padding: .4rem .65rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); background: var(--color-obsidian); color: var(--color-bone); font: inherit; font-size: var(--text-xs); cursor: pointer; }
  button:hover { border-color: var(--color-rune); }
  button:focus-visible, .dock-resizer:focus-visible { outline: 2px solid var(--color-rune); outline-offset: -2px; }
  .dock-toggle { position: absolute; inset-block-start: calc(50% - 1.375rem); right: 100%; z-index: 3; display: grid; place-items: center; width: 2rem; min-height: 2.75rem; padding: .25rem; border-radius: var(--radius-glyph) 0 0 var(--radius-glyph); font: 600 var(--text-sm)/1 var(--font-body); }
  .dock-toggle:has(.edge-label) { width: 2rem; padding-block: .5rem; gap: .35rem; }
  .edge-label { writing-mode: vertical-rl; font-size: var(--text-xs); }
  .dock-left .dock-toggle { right: auto; left: 100%; border-radius: 0 var(--radius-glyph) var(--radius-glyph) 0; }
  .dock-conversation { flex: 1; display: flex; min-height: 0; min-width: 0; overflow: hidden; }
  .dock-conversation[hidden] { display: none; }
  .dock-offline { padding: 1.5rem; color: var(--color-parchment); }
  .dock-offline h3 { color: var(--color-bone); margin-bottom: .75rem; }
  .dock-offline p { line-height: 1.7; margin-bottom: 1rem; }
  .dock-resizer { position: absolute; inset-block: 0; left: -5px; z-index: 2; width: 10px; cursor: col-resize; touch-action: none; display: grid; place-items: center; }
  .dock-left .dock-resizer { left: auto; right: -5px; }
  .dock-resizer span { visibility:hidden; }
  .dock-resizer:hover, .dock-resizer:focus-visible { background: color-mix(in srgb, var(--color-rune) 25%, transparent); }
  .dock-shell.dock-modal { position: absolute; inset: 0; z-index: 30; width: auto; }
  .dock-modal .dock-frame { border: 0; background: transparent; justify-content: flex-end; }
  .dock-modal .dock-toggle { inset-block-start:.75rem; }
  .dock-modal.dock-collapsed .dock-toggle { inset-block-start:calc(50% - 1.375rem); }
  .dock-shell.dock-modal.dock-collapsed { left: auto; width: 0; }
  .dock-shell.dock-modal.dock-left.dock-collapsed { left: 0; right: auto; }
  .dock-modal.dock-left .dock-frame { justify-content: flex-start; }
  .dock-modal:not(.dock-collapsed) .dock-toggle { right: calc(min(var(--dock-width), 100%) - 2rem); }
  .dock-modal.dock-left:not(.dock-collapsed) .dock-toggle { right: auto; left: calc(min(var(--dock-width), 100%) - 2rem); }
  .dock-modal:not(.dock-left) .dock-heading { padding-left: 2.5rem; }
  .dock-modal.dock-left .dock-heading { padding-right: 2.5rem; }
  .dock-modal .bridge-dock { position: relative; z-index: 1; width: min(var(--dock-width), 100%); background: var(--color-obsidian); border: 1px solid var(--color-engraving); }
  .dock-backdrop { position: absolute; inset: 0; padding: 0; border: 0; border-radius: 0; background: color-mix(in srgb, var(--color-void) 75%, transparent); }
  /* Keep the reopen handle reachable without covering the first canvas or form control. */
  .dock-shell.dock-collapsed, .dock-shell.dock-modal.dock-collapsed {
    position: relative;
    inset: auto;
    align-self: stretch;
    flex: 0 0 1.55rem;
    width: 1.55rem;
  }
  .dock-shell.dock-collapsed .dock-toggle { inset-inline: 0; width: 1.55rem; }
  .dock-shell.canvas-dock.dock-collapsed { flex-basis:0; width:0; }
  .canvas-dock.dock-collapsed .dock-toggle { inset:.6rem 0 auto auto; width:2rem; height:2rem; min-height:0; border-color:transparent; background:transparent; font-size:1.15rem; color:var(--color-parchment); }
  .canvas-dock.dock-collapsed .dock-toggle:hover { background:var(--color-obsidian-2); }
  .canvas-dock.dock-left.dock-collapsed .dock-toggle { inset:auto auto 1rem 0; background:var(--color-obsidian); }
</style>
