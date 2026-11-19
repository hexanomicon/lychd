<script lang="ts">
  import GraphCanvas from "$lib/graph/components/GraphCanvas.svelte";
  import type { GraphProjection } from "$lib/graph/model";
  import { evidenceCases, type EvidenceCase, type exampleDisposition } from "../state/affect-example";

  let { evidence, result }: { evidence: EvidenceCase; result: ReturnType<typeof exampleDisposition> } =
    $props();
  let selected = $state("appraisal");
  let focusRevision = $state(0);
  const uid = $props.id();
  const edges = [
    ["ground", "appraisal", "Positive baseline"],
    ["read", "appraisal", "Observed evidence"],
    ["appraisal", "next", "Question and limits"],
    ["next", "advocate", "Proposal"],
    ["next", "challenge", "Counterexample"],
    ["advocate", "reconcile", "Supporting claim"],
    ["challenge", "reconcile", "Challenge"],
    ["reconcile", "edit", "Proposed repair"],
  ] as const;
  let sample = $derived(evidenceCases[evidence]);
  let graph = $derived<GraphProjection>({
    identity: "worked-example:import-retry",
    nodes: [
      {
        id: "ground",
        label: "Ecstatic Harmonizer",
        kind: "source",
        state: "Positive baseline",
        detail: "Default enabling enjoyment through exploration, rest or a stop.",
      },
      {
        id: "read",
        label: "Read · receipts.log",
        kind: "file",
        state: "Source excerpt",
        detail: sample.observation,
      },
      {
        id: "appraisal",
        label: "Appraise the evidence",
        kind: "step",
        state: sample.emotion,
        detail: sample.appraisal,
      },
      {
        id: "next",
        label: result.title,
        kind: "gate",
        state: "Worked recommendation",
        detail: result.reason,
      },
      {
        id: "advocate",
        label: "+ Advocate",
        kind: "step",
        state: "Crucible · support",
        detail:
          "A document-specific retry could spare the successful imports. Its case depends on identifying the earlier write.",
      },
      {
        id: "challenge",
        label: "− Challenger",
        kind: "step",
        state: "Crucible · objection",
        detail:
          "A lost acknowledgement can hide a committed write. An unconditional retry could duplicate the import.",
      },
      {
        id: "reconcile",
        label: "Reconciler",
        kind: "gate",
        state: "Crucible · dossier",
        detail:
          "Preserve the duplicate-write objection. Require evidence of the earlier outcome before resubmitting.",
      },
      {
        id: "edit",
        label: "Edit · retry.py",
        kind: "file",
        state: "Candidate diff",
        detail: "Inspect the suggested edit and the verification it still needs.",
      },
    ],
    edges: edges.map(([source, target, label]) => ({
      id: `${source}-${target}`,
      source,
      target,
      label,
      relation: "declared",
    })),
  });
  let node = $derived(graph.nodes.find((item) => item.id === selected));
  let successors = $derived(
    graph.edges
      .filter((edge) => edge.source === selected)
      .map((edge) => graph.nodes.find((item) => item.id === edge.target)!),
  );
  function inspect(id: string) {
    selected = id;
    focusRevision++;
    document.getElementById(`${uid}-inspection`)?.focus({ preventScroll: true });
  }
  const excerpts: Record<EvidenceCase, string> = {
    key: "doc=3  write=timeout  receipt_key=r17",
    repeat: "doc=3  write=timeout\ndoc=3  write=timeout",
    conflict: "doc=3  write=w12  receipt=r17\ndoc=3  write=w19  receipt=r17",
    confirmed: "doc=3  write=w12  receipt=r17  status=committed",
  };
</script>

<section class="worked-graph" aria-label="Worked inquiry graph">
  <div class="diagram">
    <GraphCanvas
      projection={graph}
      selectedId={selected}
      onselect={inspect}
      focusId={selected}
      {focusRevision}
      label="Illustrated affect and Crucible graph"
      --graph-height="clamp(16rem,32vh,24rem)"
    />
  </div>
  <div class="inspection">
    <label
      >Inspect a worked node
      <select value={selected} onchange={(event) => inspect(event.currentTarget.value)}>
        {#each graph.nodes as item (item.id)}<option value={item.id}>{item.label}</option>{/each}
      </select>
    </label>
    <h4 id={`${uid}-inspection`} tabindex="-1">{node?.label}</h4>
    <p class="node-state">{node?.state}</p>
    <p>{node?.detail}</p>
    {#if selected === "read"}
      <pre aria-label="Illustrative file excerpt">{excerpts[evidence]}</pre>
    {:else if selected === "edit"}
      <pre aria-label="Illustrative file diff"><del>− submit(document)</del>
<ins
          >+ if prior_write == "confirmed_failed":
+     submit(document)
+ else:
+     return review(prior_write)</ins
        ></pre>
      <p>
        <strong>Open finding</strong> A lost acknowledgement can duplicate a write. Verify the repair against a
        committed write and an unknown outcome.
      </p>
    {:else if selected === "reconcile"}
      <p>
        <strong>Return for review</strong> The positive case survives for confirmed failures. An unknown outcome
        still needs a receipt or an owner decision.
      </p>
    {:else if selected === "advocate"}
      <p>
        <strong>After the challenge</strong> Concede the lost-acknowledgement case. Limit automatic retries to confirmed
        failures.
      </p>
    {:else if selected === "challenge"}
      <p>
        <strong>After the advocate's reply</strong> Accept the narrower retry. Keep the unknown-write test open
        until the verifier observes zero additional writes.
      </p>
    {/if}
    {#if successors.length}
      <nav aria-label="Follow worked connections">
        {#each successors as item (item.id)}<button type="button" onclick={() => inspect(item.id)}
            >{item.label} →</button
          >{/each}
      </nav>
    {/if}
  </div>
</section>

<style>
  .worked-graph {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(13rem, 1fr);
    gap: 1rem;
    margin-bottom: 1.2rem;
    border-block: 1px solid var(--color-engraving);
    padding-block: 0.7rem;
  }
  .diagram {
    min-width: 0;
  }
  .inspection {
    min-width: 0;
    font-size: var(--text-sm);
    color: var(--color-parchment);
  }
  label {
    display: grid;
    gap: 0.25rem;
    font-size: var(--text-xs);
  }
  nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.6rem;
  }
  button {
    padding: 0.25rem 0.45rem;
    font: inherit;
    font-size: var(--text-xs);
    color: var(--color-bone);
    background: var(--color-obsidian);
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-rune);
    cursor: pointer;
  }
  select {
    width: 100%;
    min-height: 2.4rem;
    color: var(--color-bone);
    background: var(--color-obsidian);
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-rune);
    padding: 0.4rem;
  }
  h4 {
    color: var(--color-bone);
    margin: 0.75rem 0 0.15rem;
  }
  .node-state {
    color: var(--color-rune);
    font-size: var(--text-xs);
    margin-bottom: 0.45rem;
  }
  p + p {
    margin-top: 0.45rem;
  }
  pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    padding: 0.55rem;
    margin: 0.4rem 0;
    background: var(--color-obsidian);
    border: 1px solid var(--color-engraving);
    font: var(--text-xs)/1.55 var(--font-glyph);
  }
  del,
  ins {
    text-decoration: none;
  }
  del {
    color: var(--color-heat);
  }
  ins {
    color: var(--color-rune);
  }
  :is(select, h4, button):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 2px;
  }
  @container work-area (max-width:50rem) {
    .worked-graph {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 48rem) {
    .worked-graph {
      grid-template-columns: 1fr;
    }
  }
</style>
