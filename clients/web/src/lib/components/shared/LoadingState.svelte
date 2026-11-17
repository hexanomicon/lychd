<!--
  Labelled loading placeholder. The label is a polite status for assistive
  technology (visible unless `hideLabel`); the mist bars are decorative.
-->
<script lang="ts">
  let { label, lines = 2, hideLabel = false }: {
    /** What is loading, e.g. "Loading conversation…". */
    label: string;
    /** Number of decorative mist bars. */
    lines?: number;
    /** Keep the label for screen readers only. */
    hideLabel?: boolean;
  } = $props();
</script>

<div class="loading-state">
  <p class="loading-state__label" class:visually-hidden={hideLabel} role="status">{label}</p>
  {#each { length: lines }, index (index)}<div class="mist" aria-hidden="true"></div>{/each}
</div>

<style>
  .loading-state { display: flex; flex-direction: column; gap: 0.6rem; min-width: 0; }
  .loading-state__label { margin: 0; color: var(--color-parchment); font-size: var(--text-sm); }
</style>
