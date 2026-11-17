<script lang="ts">
  import { tick } from "svelte";
  import { availableFocusTarget } from "$lib/memory/focus";
  import type { MemoryPanelState, MemorySection } from "$lib/memory/panel.svelte";
  import type { SeancesWorkspace } from "$lib/seances/workspace.svelte";
  import WorkingMaterial from "./WorkingMaterial.svelte";
  import PublicNotes from "$lib/pages/bridge/components/PublicNotes.svelte";
  import PublicNoteRecall from "$lib/pages/bridge/components/PublicNoteRecall.svelte";

  let { state, work, liveSession }: { state: MemoryPanelState; work: SeancesWorkspace; liveSession?: string | null } = $props();
  let panel: HTMLElement | undefined;
  let closeButton: HTMLButtonElement | undefined;
  const sections: ReadonlyArray<{ id: MemorySection; label: string }> = [
    { id: "working", label: "Working material · this tab" }, { id: "notes", label: "Public notes" }, { id: "recall", label: "Recall" }
  ];
  function capturePanel(node: HTMLElement) { panel = node; return () => { panel = undefined; }; }
  function captureClose(node: HTMLButtonElement) { closeButton = node; return () => { closeButton = undefined; }; }
  $effect(() => {
    const open = state.isOpen;
    if (open) void tick().then(() => {
      if (state.isOpen && panel && !panel.contains(document.activeElement)) closeButton?.focus({ preventScroll: true });
    });
  });
  function keydown(event: KeyboardEvent) {
    if (!state.isOpen || !panel || event.defaultPrevented) return;
    if (event.key === "Escape") { event.preventDefault(); state.close(); }
    else if (event.key === "Tab") {
      const controls = [...panel.querySelectorAll<HTMLElement>("a[href],button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),summary,[tabindex='0']")]
        .filter((node) => node.tabIndex >= 0 && availableFocusTarget(node));
      const first = controls[0], last = controls.at(-1);
      if (!first) { event.preventDefault(); panel.focus(); }
      else if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    }
  }
</script>

<svelte:window onkeydown={keydown} />
<div class="memory-layer" hidden={!state.isOpen}>
  <button class="memory-backdrop" type="button" tabindex="-1" aria-label="Close Memory backdrop" onclick={() => state.close()}></button>
  <div id="memory-panel" class="memory-panel" role="dialog" aria-modal="true" aria-labelledby="memory-title" tabindex="-1" {@attach capturePanel}>
    <header><div><h2 id="memory-title">Memory</h2><p>Live Bridge Session: <code>{liveSession ?? "None selected"}</code>. Opening Memory does not change it.</p></div><button type="button" {@attach captureClose} onclick={() => state.close()}>Close Memory</button></header>
    <nav aria-label="Memory sections">{#each sections as section (section.id)}<button type="button" aria-pressed={state.section === section.id} onclick={() => state.open(section.id)}>{section.label}</button>{/each}</nav>
    <div class="memory-content">
      <div hidden={state.section !== "working"}>{#if state.initialized.working}<WorkingMaterial {work} />{/if}</div>
      <div hidden={state.section !== "notes"}>{#if state.initialized.notes}<PublicNotes selection={state.notesSelection} onSelect={(selection) => state.selectNotes(selection)} onSettled={(selection) => state.retainNotesSelection(selection)} registerSelectionGuard={(guard, apply) => state.registerNotesGuard(guard, apply)} embedded active={state.isOpen && state.section === "notes"} onClose={() => state.close()} />{/if}</div>
      <div hidden={state.section !== "recall"}>{#if state.initialized.recall}<PublicNoteRecall embedded active={state.isOpen && state.section === "recall"} onSelect={(selection) => state.selectNotes(selection)} onClose={() => state.close()} />{/if}</div>
    </div>
  </div>
</div>

<style>
  .memory-layer { position: fixed; inset: 0; z-index: 70; display: flex; justify-content: flex-end; }
  .memory-layer[hidden], .memory-content > [hidden] { display: none; }
  .memory-backdrop { position: absolute; inset: 0; border: 0; border-radius: 0; background: color-mix(in srgb, var(--color-void) 75%, transparent); }
  .memory-panel { position: relative; width: min(56rem, 100%); height: 100%; min-width: 0; display: flex; flex-direction: column; background: var(--color-void); color: var(--color-parchment); border-left: 1px solid var(--color-engraving); }
  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; }
  h2 { color: var(--color-bone); font: 600 var(--text-xl)/1.4 var(--font-body); }
  p { margin-top: .5rem; font-size: var(--text-xs); line-height: 1.6; color: var(--color-ash); }
  code { overflow-wrap: anywhere; }
  nav { display: flex; flex-wrap: wrap; gap: .5rem; padding: 0 1.25rem 1rem; border-bottom: 1px solid var(--color-engraving); }
  button { min-height: 2.75rem; padding: .5rem .75rem; font: inherit; font-size: var(--text-sm); color: var(--color-parchment); background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); cursor: pointer; }
  button[aria-pressed="true"] { color: var(--color-bone); border-color: var(--color-rune); }
  .memory-content { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
</style>
