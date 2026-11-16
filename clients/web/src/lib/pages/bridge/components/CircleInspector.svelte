<script lang="ts">
  import type { LiveTurn } from "$lib/pages/bridge/state/projection";
  import { runEvidenceHref, runScoreHref } from "$lib/pages/bridge/state/run-links";

  let { runId, turn, pending = 0 }: {
    runId: string;
    turn?: LiveTurn;
    pending?: number;
  } = $props();

  // Shows only served Run fields; station progress has no served contract, so none is inferred here.
  const status = $derived(pending > 0 ? "Waiting for consent" : turn ? label(turn.runStatus) : "Retained reply");
  const evidenceHref = $derived(runEvidenceHref(runId, turn));
  const scoreHref = $derived(runScoreHref(runId, turn));

  function label(value: string): string {
    if (value === "awaiting_hardware") return "Awaiting animators";
    if (value === "awaiting_delegate") return "Delegated labor";
    const text = value.replaceAll("_", " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }
</script>

<aside class="circle-inspector" aria-labelledby="circle-inspector-title">
  <h2 id="circle-inspector-title">Circle</h2>
  <p class="inspector-status" data-status={pending > 0 ? "awaiting_consent" : turn?.runStatus ?? "retained"}>
    <span class="dot" aria-hidden="true"></span>{status}
  </p>
  <p class="inspector-run">Run · <code>{runId}</code></p>
  <dl>
    {#if turn}
      <dt>Pattern</dt><dd><code>{turn.patternId ? `${turn.patternId}${turn.patternRevision ? `@${turn.patternRevision}` : ""}` : "Not available"}</code></dd>
      <dt>Capability</dt><dd><code>{turn.capabilityKey ?? "Not available"}</code></dd>
    {/if}
    <dt>Sigil</dt><dd>Local · Magus</dd>
    {#if turn}<dt>Capture</dt><dd><code>{turn.evidenceCapture.replaceAll("_", "-")}</code></dd>{/if}
  </dl>
  <nav class="inspector-links" aria-label="Run inspection">
    {#if scoreHref}<a href={scoreHref}>Open score in Loom <span aria-hidden="true">↗</span></a>{/if}
    {#if evidenceHref}<a href={evidenceHref}>Inspect Run in Orb <span aria-hidden="true">↗</span></a>{/if}
  </nav>
</aside>

<style>
  .circle-inspector { display: flex; flex-direction: column; gap: 1rem; min-width: 0; min-height: 0; padding: 1rem 1.25rem; overflow-y: auto; border-inline-start: 1px solid var(--color-engraving); background: var(--color-obsidian); color: var(--color-parchment); font-size: var(--text-sm); }
  h2 { margin: 0 0 .5rem; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-body); }
  .inspector-status { display: flex; align-items: center; gap: .5rem; margin: 0; color: var(--color-bone); }
  .inspector-status[data-status="awaiting_consent"] { color: var(--color-accent); }
  .inspector-status[data-status="failed"] { color: var(--color-ember); }
  .dot { width: .5rem; height: .5rem; border-radius: 50%; background: currentColor; }
  .inspector-run { margin: -.6rem 0 0; padding-bottom: 1rem; border-bottom: 1px solid var(--color-engraving); }
  dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .6rem 1.25rem; margin: 0; padding-bottom: 1rem; border-bottom: 1px solid var(--color-engraving); }
  dt { color: var(--color-parchment); }
  dd { min-width: 0; margin: 0; color: var(--color-bone); overflow-wrap: anywhere; }
  code { color: inherit; font: var(--text-sm)/1.5 var(--font-glyph); }
  .inspector-links { display: flex; flex-direction: column; }
  .inspector-links a { display: flex; align-items: center; justify-content: space-between; min-height: 2.75rem; color: var(--color-bone); text-decoration: none; cursor: pointer; }
  .inspector-links a:hover { color: var(--color-rune); }
  a:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
