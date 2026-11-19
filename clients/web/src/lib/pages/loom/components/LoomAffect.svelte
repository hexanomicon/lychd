<script lang="ts">
  import type { LoomView } from "$lib/api/models";
  import { resolvePath } from "$lib/navigation/paths";
  import LoomInquiryGraph from "./LoomInquiryGraph.svelte";
  import {
    evidenceCases,
    exampleDisposition,
    type EvidenceCase,
    type LookupPermission,
    type ProbeAllowance,
  } from "../state/affect-example";

  let { score, stationKey }: { score: LoomView; stationKey: string | null } = $props();
  let station = $derived(stationKey ?? score.entry_node);
  let exits = $derived(score.edges.filter((edge) => edge.source === station));
  let evidence = $state<EvidenceCase>("key");
  let allowance = $state<ProbeAllowance>("one");
  let permission = $state<LookupPermission>("permitted");
  let result = $derived(exampleDisposition(evidence, allowance, permission));
  const uid = $props.id();
</script>

<section class="affect-policy" aria-labelledby={`${uid}-title`}>
  <header>
    <p class="kicker">Worked policy · Import retry</p>
    <h3 id={`${uid}-title`}>What earns another probe?</h3>
    <p>
      A document write timed out. Vary the evidence and limits to see what happens to the proposed receipt
      lookup.
    </p>
  </header>
  <LoomInquiryGraph {evidence} {result} />
  <div class="policy-grid">
    <div class="experiment">
      <div class="baseline">
        <strong>Ecstatic Harmonizer</strong>
        <p>
          The proposed positive baseline reaches every eligible station, including those at rest. It stays
          positive across these outcomes.
        </p>
      </div>
      <p>
        The dopamine-like signal here tracks useful surprise. A clue earns attention when it can change the
        decision about this write.
      </p>
      <label
        >Evidence returned
        <select bind:value={evidence}>
          {#each Object.entries(evidenceCases) as [key, item] (key)}<option value={key}>{item.label}</option
            >{/each}
        </select>
      </label>
      <div class="limits">
        <label
          >Remaining allowance
          <select bind:value={allowance}
            ><option value="one">One read-only probe</option><option value="spent">Budget exhausted</option
            ></select
          >
        </label>
        <label
          >Lookup permission
          <select bind:value={permission}
            ><option value="permitted">Authorized for this read</option><option value="needs_review"
              >Owner decision required</option
            ></select
          >
        </label>
      </div>
      <div class="outcome" aria-live="polite">
        <dl>
          <dt>Evidence</dt>
          <dd>{evidenceCases[evidence].observation}</dd>
          <dt>Appraisal</dt>
          <dd>{evidenceCases[evidence].appraisal}</dd>
        </dl>
        <div class="decision" data-kind={result.kind}>
          <strong>{result.title}</strong>
          <p>{result.reason}</p>
        </div>
      </div>
    </div>
    <aside aria-label="Revision coverage">
      <h4>Revision coverage</h4>
      <code>{score.pattern_id}@{score.revision}</code>
      {#if score.nodes.length}
        <label
          >Station definition
          <select bind:value={station}
            >{#each score.nodes as node (node.key)}<option value={node.key}>{node.label} · {node.key}</option
              >{/each}</select
          >
        </label>
        <p>Permitted successors</p>
        {#if exits.length}
          <ul>
            {#each exits as edge (edge.key)}<li><code>{edge.target}</code> · {edge.relation}</li>{/each}
          </ul>
        {:else}<p>No outgoing permission declared.</p>{/if}
      {/if}
      <p>
        The revision supplies no affect policy or signal binding. Changes to the worked example last only in
        this view.
      </p>
      <h4>Network scope</h4>
      <p>
        A consuming station needs a declared input. A peer needs a separately authorized route. The example
        sends no signal.
      </p>
      <a href={resolvePath("/nexus?area=affect")}>Inspect affect routing in Nexus →</a>
    </aside>
  </div>
</section>

<style>
  .affect-policy {
    max-width: 76rem;
    color: var(--color-parchment);
    font: var(--text-sm)/1.55 var(--font-body);
  }
  header {
    margin: 0 0 1.2rem;
    max-width: 47rem;
  }
  .kicker,
  dt {
    color: var(--color-ash);
    font: var(--text-xs)/1.5 var(--font-body);
  }
  h3,
  h4,
  strong {
    color: var(--color-bone);
  }
  h3 {
    margin: 0.25rem 0 0.5rem;
    font: 600 clamp(1.25rem, 2vw, 1.65rem)/1.2 var(--font-body);
  }
  h4 {
    margin: 0 0 0.6rem;
    font-size: 1rem;
  }
  .policy-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(13rem, 1fr);
    gap: clamp(1rem, 3%, 2.5rem);
  }
  .experiment,
  aside {
    display: grid;
    min-width: 0;
    gap: 0.9rem;
    align-content: start;
  }
  .baseline {
    padding: 0.6rem 0.85rem;
    border-inline-start: 3px solid var(--color-rune);
    background: var(--color-obsidian);
  }
  .limits {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.7rem;
  }
  label {
    display: grid;
    gap: 0.3rem;
    color: var(--color-parchment);
    font-size: 0.8rem;
  }
  select {
    width: 100%;
    min-height: 2.6rem;
    min-width: 0;
    padding: 0.45rem;
    background: var(--color-obsidian);
    color: var(--color-bone);
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-rune);
    font: inherit;
  }
  :is(select, a):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 3px;
  }
  dl {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: baseline;
    gap: 0.5rem 1rem;
  }
  .decision {
    margin-top: 0.9rem;
    padding: 0.65rem 0.85rem;
    border: 1px solid var(--color-engraving);
    border-inline-start: 3px solid var(--color-ash);
  }
  .decision[data-kind="probe"] {
    border-inline-start-color: var(--color-rune);
  }
  .decision[data-kind="review"] {
    border-inline-start-color: var(--color-heat);
  }
  aside {
    padding-inline-start: 1.2rem;
    border-inline-start: 1px solid var(--color-engraving);
  }
  aside :is(code, li) {
    overflow-wrap: anywhere;
  }
  aside ul {
    padding: 0 0 0 1rem;
  }
  aside h4:not(:first-child) {
    margin: 0.6rem 0 0;
  }
  @container work-area (max-width:50rem) {
    .policy-grid {
      grid-template-columns: 1fr;
    }
    aside {
      padding: 0.8rem 0;
      border-inline-start: 0;
      border-top: 1px solid var(--color-engraving);
    }
  }
  @media (max-width: 48rem) {
    .policy-grid,
    .limits {
      grid-template-columns: 1fr;
    }
    aside {
      padding: 0.8rem 0;
      border-inline-start: 0;
      border-top: 1px solid var(--color-engraving);
    }
  }
</style>
