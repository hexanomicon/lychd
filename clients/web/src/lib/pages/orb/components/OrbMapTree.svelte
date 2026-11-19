<script lang="ts">
  import type { OrbRunSnapshot } from "$lib/api/models";
  import type { GraphProjection } from "$lib/graph/model";
  import type { OrbFieldLens } from "../state/orb";
  import { loadedSubjects, attemptIdentity, stationDurations, durationLabel } from "../state/orb-evidence";

  let {
    runs,
    lenses,
    runtime,
    selectedRun,
    selectedEvent,
    selectedNode,
    onrun,
    onevent,
    onruntime,
  }: {
    runs: readonly OrbRunSnapshot["run"][];
    lenses: ReadonlyMap<string, OrbFieldLens>;
    runtime: GraphProjection;
    selectedRun: string | null;
    selectedEvent: string | null;
    selectedNode: string | null;
    onrun: (id: string, opener: HTMLElement) => void;
    onevent: (run: string, id: string, opener: HTMLElement) => void;
    onruntime: (id: string, opener: HTMLElement) => void;
  } = $props();
  let rows = $derived(
    runs.map((run) => ({
      run,
      durations: stationDurations(lenses.get(run.run_id)?.snapshot.evidence ?? []),
      subjects: loadedSubjects(lenses.get(run.run_id)?.snapshot.evidence ?? []),
    })),
  );
</script>

{#snippet records(runId: string, events: OrbRunSnapshot["evidence"])}
  {#each events as event (event.event_id)}
    <button
      type="button"
      class="record"
      aria-pressed={selectedRun === runId && selectedEvent === event.event_id}
      onclick={(click) => onevent(runId, event.event_id, click.currentTarget)}
      >#{event.seq} · {event.summary}</button
    >
  {/each}
{/snippet}

{#each rows as row (row.run.run_id)}
  <div class="run">
    <button
      type="button"
      class="run-name"
      title={row.run.run_id}
      aria-pressed={selectedRun === row.run.run_id && !selectedEvent}
      onclick={(event) => onrun(row.run.run_id, event.currentTarget)}
      >{row.run.workflow_name}<small>{row.run.status}</small></button
    >
    {#if row.subjects.length}
      <details open={selectedRun === row.run.run_id}>
        <summary>Subjects · {row.subjects.length}</summary>
        {#each row.subjects as subject (subject.key)}
          <details
            class="subject"
            open={selectedRun === row.run.run_id &&
              subject.records.some((item) => item.event_id === selectedEvent)}
          >
            <summary
              >{subject.subject ?? subject.kind}
              <small>{subject.records.length}</small
              >{#if subject.kind === "node" && subject.subject && row.durations.has(subject.subject)}
                <small title="Total recorded duration of completed attempts"
                  >{durationLabel(row.durations.get(subject.subject)!)}</small
                >{/if}</summary
            >
            {#if subject.attempts.length}
              {#each subject.attempts as attempt (attempt.key)}
                {@const occurrences = subject.records.filter(
                  (event) => attemptIdentity(event) === attempt.key,
                )}
                <details
                  class="attempt"
                  open={selectedRun === row.run.run_id &&
                    occurrences.some((item) => item.event_id === selectedEvent)}
                >
                  <summary>{attempt.label}</summary>
                  {@render records(row.run.run_id, occurrences)}
                </details>
              {/each}
            {:else}
              {@render records(row.run.run_id, subject.records)}
            {/if}
          </details>
        {/each}
      </details>
    {:else}<small class="empty">No loaded records</small>{/if}
  </div>
{/each}
{#if runtime.nodes.length}
  <details class="runtime" open={!runs.length || runtime.nodes.some((item) => item.id === selectedNode)}>
    <summary>Runtime · latest window</summary>
    {#each runtime.nodes as item (item.id)}<button
        type="button"
        class="record"
        aria-pressed={selectedNode === item.id}
        onclick={(event) => onruntime(item.id, event.currentTarget)}>{item.label}</button
      >{/each}
  </details>
{/if}

<style>
  .run,
  .runtime {
    padding: 0.35rem 0;
    border-top: 1px solid var(--color-engraving);
  }
  button,
  summary {
    color: var(--color-parchment);
    font: var(--text-xs)/1.5 var(--font-body);
    cursor: pointer;
    overflow-wrap: anywhere;
  }
  button {
    padding: 0.25rem 0.35rem;
    text-align: start;
    width: 100%;
    border: 1px solid transparent;
    border-radius: 3px;
    background: transparent;
  }
  button[aria-pressed="true"] {
    color: var(--color-rune);
    border-color: var(--color-control-border);
    background: var(--color-obsidian-2);
  }
  .run-name {
    display: flex;
    justify-content: space-between;
    gap: 0.25rem;
    font-weight: 600;
  }
  summary {
    padding: 0.22rem 0;
  }
  small {
    color: var(--color-ash);
    font-weight: 400;
    font-size: 11px;
  }
  .subject,
  .attempt {
    margin-inline-start: 0.45rem;
    padding-inline-start: 0.35rem;
    border-inline-start: 1px solid var(--color-engraving);
  }
  .empty {
    padding-inline: 0.35rem;
  }
  :is(summary, button):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: -1px;
  }
</style>
