<script lang="ts">
  import SchemaFields from "$lib/components/shared/SchemaFields.svelte";
  import type { OrbRunSnapshot } from "$lib/api/models";
  let { schema, jobs = [], historical = false }: { schema?: string | null; jobs?: OrbRunSnapshot["delegated_jobs"]; historical?: boolean } = $props();
</script>
<div class="result">
  {#if schema}<SchemaFields source={schema} title="Declared output schema" />{/if}
  {#if historical}<p>Historical output values are unavailable at this cursor.</p>
  {:else if jobs.length}
    <h4>Recorded output</h4>
    {#each jobs as job (job.job_id)}<dl><dt>Job</dt><dd>{job.job_id}</dd><dt>Text</dt><dd>{job.output_present ? "Retained" : "Absent"}</dd><dt>Artifacts</dt><dd>{job.artifact_count}</dd></dl>{/each}
  {:else}<p>The installed station declares this result type. The Run supplies no public output values here.</p>{/if}
</div>
<style>
  .result{padding:.8rem 0;border-block-start:1px solid var(--color-engraving)}
  p,dt{font:11px/1.5 var(--font-body);color:var(--color-ash)} h4{margin:.7rem 0;font-size:.85rem}
  dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:.25rem .65rem}dd{margin:0;overflow-wrap:anywhere}
</style>
