<script lang="ts">
  import { onMount } from "svelte";
  import { accentOptions, appearanceStorageKey, defaultAccent, parseAppearance, serializeAppearance, type AccentId } from "$lib/appearance/preferences";

  let accent = $state<AccentId>(defaultAccent);
  let notice = $state("");
  let disclosure: HTMLDetailsElement | undefined;
  const uid = $props.id();

  function attachDisclosure(node: HTMLDetailsElement) {
    disclosure = node;
    return () => { if (disclosure === node) disclosure = undefined; };
  }

  function apply(next: AccentId) {
    accent = next;
    document.documentElement.dataset.altarAccent = next;
  }
  function choose(next: AccentId) {
    apply(next);
    try { localStorage.setItem(appearanceStorageKey, serializeAppearance(next)); notice = ""; }
    catch { notice = "Kept for this tab. Browser storage is unavailable."; }
  }
  function reset() {
    apply(defaultAccent);
    try { localStorage.removeItem(appearanceStorageKey); notice = ""; }
    catch { notice = "Default restored for this tab. Browser storage is unavailable."; }
  }
  function storageChanged(event: StorageEvent) {
    if (event.key !== appearanceStorageKey && event.key !== null) return;
    if (event.storageArea) {
      try { if (event.storageArea !== localStorage) return; } catch { return; }
    }
    apply(parseAppearance(event.newValue));
    notice = "";
  }
  function closeOutside(event: MouseEvent) {
    if (disclosure?.open && !event.composedPath().includes(disclosure)) disclosure.open = false;
  }
  function escape(event: KeyboardEvent) {
    if (event.key !== "Escape" || event.defaultPrevented || !disclosure?.open) return;
    disclosure.open = false;
    disclosure.querySelector("summary")?.focus();
    event.preventDefault();
  }
  onMount(() => {
    try { apply(parseAppearance(localStorage.getItem(appearanceStorageKey))); }
    catch { apply(defaultAccent); notice = "Kept for this tab. Browser storage is unavailable."; }
    return () => { delete document.documentElement.dataset.altarAccent; };
  });
</script>

<svelte:window onclick={closeOutside} onkeydown={escape} onstorage={storageChanged} />
<details class="appearance" {@attach attachDisclosure} onfocusout={(event) => {
  if (disclosure && (!(event.relatedTarget instanceof Node) || !disclosure.contains(event.relatedTarget))) disclosure.open = false;
}}>
  <summary>Appearance</summary>
  <div class="appearance-panel">
    <h2>Appearance</h2>
    <p>LychD Dark · choose the decorative accent for this browser.</p>
    <fieldset><legend>Accent</legend>
      {#each accentOptions as option (option.id)}
        <label>
          <input type="radio" name={`${uid}-accent`} value={option.id} checked={accent === option.id} onchange={() => choose(option.id)} />
          <span class="swatch" style:background-color={option.color} aria-hidden="true"></span>
          {option.label}
        </label>
      {/each}
    </fieldset>
    <p>Focus, activity and status colours keep their meaning.</p>
    <button type="button" onclick={reset}>Reset to LychD Dark</button>
    {#if notice}<p role="status">{notice}</p>{/if}
  </div>
</details>

<style>
  .appearance { position: relative; font-family: var(--font-body); }
  summary { padding: .65rem .75rem; min-height: 2.75rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); color: var(--color-parchment); cursor: pointer; font-size: var(--text-sm); }
  summary:hover { background: var(--color-obsidian-2); }
  .appearance-panel { position: absolute; right: 0; top: calc(100% + .5rem); z-index: 50; width: min(20rem, calc(100vw - 2rem)); max-height: calc(100dvh - 6rem); overflow-y: auto; padding: 1rem; background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-panel); box-shadow: 0 .5rem 1.5rem #0008; }
  h2 { margin: 0 0 .65rem; font-size: var(--text-lg); color: var(--color-bone); }
  p { margin: .65rem 0; color: var(--color-ash); font-size: var(--text-sm); line-height: 1.5; }
  fieldset { display: grid; gap: .5rem; margin: .8rem 0; padding: .65rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); }
  legend { padding: 0 .3rem; color: var(--color-parchment); font-size: var(--text-sm); }
  label { display: flex; align-items: center; gap: .65rem; min-height: 2.75rem; color: var(--color-parchment); cursor: pointer; font-size: var(--text-sm); }
  input { accent-color: var(--color-rune); }
  .swatch { width: 1.2rem; height: 1.2rem; border: 1px solid var(--color-control-border); border-radius: 50%; }
  button { padding: .6rem .75rem; min-height: 2.75rem; background: var(--color-obsidian-2); color: var(--color-bone); border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); cursor: pointer; font-size: var(--text-sm); }
  :is(summary, input, button):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (forced-colors: active) { .swatch { forced-color-adjust: none; } }
</style>
