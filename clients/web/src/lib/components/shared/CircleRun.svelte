<script lang="ts">
  import type { LiveTurn } from "$lib/bridge/projection";
  import { loomOriginHref, orbReturnHref, selectedOrbHref } from "$lib/navigation/instruments";

  let { runId, turn: suppliedTurn, cancelling = false, oncancel }: {
    runId: string;
    turn?: LiveTurn;
    cancelling?: boolean;
    oncancel?: () => void;
  } = $props();

  const identityId = $props.id();
  let expanded = $state(false);
  let identityMismatch = $derived(!!suppliedTurn && suppliedTurn.runId !== runId);
  let turn = $derived(identityMismatch ? undefined : suppliedTurn);
  let selection = $derived(turn?.delegatedJobId ? new URLSearchParams({ job: turn.delegatedJobId }).toString() : "");
  let evidenceHref = $derived(
    !identityMismatch && (!turn || selectedOrbHref(turn.orbPath, "") === orbReturnHref(runId))
      ? orbReturnHref(runId, selection)
      : null
  );
  let scoreHref = $derived.by(() => {
    if (!turn?.loomPath || !turn.patternId || !turn.patternRevision) return null;
    const supplied = loomOriginHref(turn.loomPath, runId, selection);
    const exact = loomOriginHref(`/loom/${encodeURIComponent(turn.patternId)}/${encodeURIComponent(turn.patternRevision)}`, runId, selection);
    return supplied === exact ? supplied : null;
  });
  let canCancel = $derived(!!oncancel && !!turn && !["done", "failed", "cancelled"].includes(turn.state));
  let active = $derived(turn?.runStatus === "running" && turn.state === "streaming");

  function label(value: string): string {
    if (value === "awaiting_hardware") return "awaiting animators";
    if (value === "awaiting_delegate") return "delegated labor";
    return value.replaceAll("_", " ");
  }
</script>

<div class="circle-run">
  <div class="circle-overview">
    <button class="circle-toggle" type="button" aria-expanded={expanded} aria-controls={identityId} onclick={() => expanded = !expanded}>
      <span class="circle-mark" aria-hidden="true"></span>
      Circle <span class="visually-hidden">details for Run {runId}</span>
      <span class="circle-chevron" aria-hidden="true">{expanded ? "⌃" : "⌄"}</span>
    </button>
    <div class="circle-status" aria-live="polite" data-active={active} data-status={turn?.runStatus}>
      <span>{identityMismatch ? "Run details unavailable" : turn ? label(turn.runStatus) : "Retained reply"}</span>
      {#if turn?.activity && turn.activity !== turn.runStatus}
        <span class="circle-activity">{label(turn.activity)}</span>
      {/if}
    </div>
    <nav class="circle-actions" aria-label="Run links">
      {#if evidenceHref}
        <a href={evidenceHref}>Look into the Orb <span aria-hidden="true">↗</span></a>
      {:else}
        <span class="circle-unavailable">Evidence link unavailable</span>
      {/if}
      {#if canCancel}
        <button class="circle-cancel" type="button" disabled={cancelling} aria-busy={cancelling} aria-label={`Cancel run ${runId}`} onclick={oncancel}>
          {cancelling ? "Cancelling…" : "Cancel Run"}
        </button>
      {/if}
    </nav>
  </div>
  {#if identityMismatch}<p class="circle-unavailable">The supplied projection belongs to another Run.</p>{/if}
  <div class="circle-identity" id={identityId} hidden={!expanded}>
    <dl>
      <dt>Run</dt><dd><code>{runId}</code></dd>
      {#if turn}
        <dt>Pattern</dt><dd>{turn.patternId || "Not available"}</dd>
        <dt>Revision</dt><dd><code>{turn.patternRevision || "Not available"}</code></dd>
      {:else}
        <dt>Run status</dt><dd class="circle-unavailable">{identityMismatch ? "Not available" : "Not retained in this reply"}</dd>
        <dt>Declared score</dt><dd class="circle-unavailable">{identityMismatch ? "Not available" : "Not retained in this reply"}</dd>
      {/if}
      {#if turn?.delegatedJobId}
        <dt>Delegated job</dt><dd><code>{turn.delegatedJobId}</code></dd>
      {/if}
    </dl>
    {#if scoreHref}
      <a class="circle-score" href={scoreHref}>View declared score <span aria-hidden="true">↗</span></a>
    {:else if turn}
      <p class="circle-unavailable">Declared score link unavailable</p>
    {/if}
  </div>
</div>

<style>
  .circle-run { min-width: 0; margin: .3rem 0 .75rem; border-block: 1px solid var(--color-engraving); color: var(--color-parchment); font: .875rem/1.5 var(--font-body); }
  .circle-overview { display: flex; align-items: center; flex-wrap: wrap; gap: .15rem .8rem; padding: .35rem 0; }
  .circle-toggle { display: inline-flex; align-items: center; flex: 0 0 auto; gap: .5rem; min-height: 2.75rem; padding: .25rem .15rem; border: 0; background: none; color: var(--color-bone); font: inherit; cursor: pointer; }
  .circle-mark { width: .8rem; height: .8rem; border: 1px solid currentColor; border-radius: 50%; }
  .circle-chevron { margin-left: .2rem; color: var(--color-parchment); }
  .circle-status { display: flex; flex: 1 1 9rem; align-items: baseline; flex-wrap: wrap; gap: .1rem .75rem; min-width: 0; overflow-wrap: anywhere; }
  .circle-status > span:first-child { color: var(--color-bone); }
  .circle-status[data-active="true"] > span:first-child::before { content: ""; display: inline-block; width: .35rem; height: .35rem; margin: 0 .4rem .1rem 0; border-radius: 50%; background: var(--color-lich); }
  .circle-status[data-status="failed"] > span:first-child { color: var(--color-ember); }
  .circle-actions { display: flex; align-items: center; flex-wrap: wrap; gap: .3rem 1rem; margin-left: auto; }
  .circle-run a { display: inline-flex; align-items: center; gap: .3rem; min-height: 2.75rem; color: var(--color-rune); text-decoration: underline; text-underline-offset: .2em; }
  .circle-cancel { min-height: 2.75rem; padding: .35rem .75rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); background: transparent; color: var(--color-bone); font: inherit; cursor: pointer; }
  .circle-cancel:hover:not(:disabled) { border-color: var(--color-ember); }
  .circle-cancel:disabled { cursor: wait; color: var(--color-parchment); }
  .circle-identity { padding: .8rem 0; border-top: 1px solid var(--color-engraving); }
  dl { display: grid; grid-template-columns: minmax(6.5rem, auto) minmax(0, 1fr); gap: .55rem 1.25rem; margin: 0; }
  dt { color: var(--color-parchment); }
  dd { min-width: 0; margin: 0; color: var(--color-bone); overflow-wrap: anywhere; }
  code { color: inherit; font: .875rem/1.5 var(--font-glyph); white-space: normal; }
  .circle-score { margin-top: .45rem; }
  .circle-unavailable { color: var(--color-parchment); }
  p.circle-unavailable { margin: .65rem 0 0; }
  button:focus-visible, a:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 40rem) {
    .circle-status { flex-basis: 8rem; }
    .circle-actions { flex-basis: 100%; margin-left: 0; justify-content: space-between; }
    dl { grid-template-columns: minmax(0, 1fr); gap: .2rem; }
    dd + dt { margin-top: .65rem; }
  }
</style>
