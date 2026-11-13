<script lang="ts">
  import type { RuntimeReadState } from "$lib/pages/orb/state/runtime";
  import { activityKey, projectRuntime, type RuntimeSelection } from "$lib/pages/orb/state/runtime-projection";
  let { state, field, selected, onselect, onrefresh }: {
    state: RuntimeReadState;
    field: ReturnType<typeof projectRuntime>;
    selected: RuntimeSelection | undefined;
    onselect: (id: string, opener?: HTMLElement) => void;
    onrefresh: () => void;
  } = $props();
  let component = $derived(selected && "component" in selected ? selected.component : null);
  let activities = $derived(selected && "activities" in selected ? selected.activities : []);
  let snapshot = $derived(state.snapshot);
</script>

<div class="runtime-evidence">
  <header><h3>Runtime topology &amp; activity</h3><button type="button" onclick={onrefresh} disabled={state.loading}>{state.loading ? "Reading…" : "Refresh runtime"}</button></header>
  <p>Declared components and connections; actual operation observations are separate. Run correlation is optional.</p>
  {#if state.error}<p role="alert">{state.error}</p>{/if}
  {#if snapshot}
    {#if state.received.size}<p role="status">{state.received.size} newly received runtime observations.</p>{/if}
    <p class="coverage">Read <time datetime={snapshot.read_at}>{new Date(snapshot.read_at).toLocaleString()}</time> · {state.stale ? "stale browser window" : "last received window"} · refreshes every 3 seconds while visible.</p>
    <p class="coverage">At most {snapshot.coverage.component_limit} components, {snapshot.coverage.activity_limit} observations and {snapshot.coverage.source_limit} sources. Process-local capture; completeness is not established.</p>
    <p class="coverage">Omitted: {snapshot.coverage.omitted_sources} sources · {snapshot.coverage.omitted_components} components · {snapshot.coverage.omitted_relations} relations · {snapshot.coverage.omitted_activities} observations · {snapshot.coverage.omitted_patterns} Patterns. Display limit: {field.omittedNodes} nodes and {field.omittedEdges} edges omitted.</p>
    <details open><summary>Sources &amp; coverage ({snapshot.sources.length})</summary>
      <ul class="sources">{#each snapshot.sources as source (source.source_id)}<li>
        <strong>{source.source_id}</strong> · {source.status}{#if source.generation_changed} · generation changed, historical baseline{/if}
        <dl><dt>Registrant</dt><dd>{source.registrant_id ?? "Unresolved custody"}</dd><dt>Generation</dt><dd>{source.generation ?? "Unavailable"}</dd><dt>Profile</dt><dd>{source.profile_id ?? "Unavailable"}@{source.profile_revision ?? "?"}</dd><dt>Source timestamp</dt><dd>{source.generated_at ?? "Unavailable"}</dd><dt>Sequence window</dt><dd>{source.coverage.first_seq ?? "None"}–{source.coverage.last_seq ?? "None"}</dd><dt>Capture loss</dt><dd>{source.coverage.dropped} dropped · {source.coverage.gaps} gaps · {source.coverage.omitted_activities} omitted observations</dd><dt>Other omissions</dt><dd>{source.coverage.omitted_components} components · {source.coverage.omitted_relations} relations · {source.coverage.omitted_patterns} Patterns</dd></dl>
        {#if source.coverage.limitations.length}<ul>{#each source.coverage.limitations as limitation (limitation)}<li>{limitation.replaceAll("_", " ")}</li>{/each}</ul>{/if}
      </li>{/each}</ul>
    </details>
    <details open><summary>Semantic runtime list ({field.projection.nodes.length})</summary>
      <ul class="nodes">{#each field.projection.nodes as node (node.id)}<li><button type="button" onclick={(event) => onselect(node.id, event.currentTarget)}>
        {#if node.icon}<img src={node.icon} alt="" width="18" height="18" />{/if}<strong>{node.label}</strong><span>{node.kind} · {node.state ?? "unknown"}</span><small>{node.detail}</small>{#if node.attention === "received"}<small>Newly received observation</small>{/if}
      </button></li>{/each}</ul>
    </details>
    <details><summary>Declared and observed connections ({field.projection.edges.length})</summary><ul>{#each field.projection.edges as edge (edge.id)}<li>{edge.label} · {edge.relation}</li>{/each}</ul></details>
    {#if component}<section aria-label="Selected runtime component"><h4>{component.label}</h4><dl>
      <dt>Component</dt><dd>{component.key}</dd><dt>Kind</dt><dd>{component.kind}</dd><dt>Revision</dt><dd>{component.revision}</dd><dt>Owner</dt><dd>{component.owner}</dd><dt>Instance</dt><dd>{component.instance_id ?? "Not supplied"}</dd><dt>Lifecycle observation</dt><dd>{component.lifecycle}</dd><dt>Activity coverage</dt><dd>{component.activity_coverage}</dd><dt>Source</dt><dd>{component.source_id}</dd><dt>Generation</dt><dd>{component.source_generation}</dd><dt>Registrant</dt><dd>{component.registrant_id ?? "Not supplied"}</dd>
    </dl><p>A declaration does not establish running state or health.</p></section>{/if}
    {#if activities.length}<section aria-label="Selected runtime activity"><h4>Observed operation</h4><p>HTTP response and effect outcome are separate. Missing finish remains unknown.</p>
      {#each activities as event (activityKey(event))}<article><h5>{event.operation} · {event.kind}</h5><dl>
        <dt>Direction</dt><dd>{event.source} → {event.target}</dd><dt>Phase</dt><dd>{event.phase}</dd><dt>Event</dt><dd>{event.event_id}</dd><dt>Operation</dt><dd>{event.operation_id}</dd><dt>Attempt</dt><dd>{event.attempt_id ?? "Not supplied"}</dd><dt>Producer</dt><dd>{event.producer_id}</dd><dt>Source generation</dt><dd>{event.source_id} / {event.source_generation}</dd><dt>Registrant</dt><dd>{event.registrant_id}</dd><dt>Sequence</dt><dd>{event.seq}</dd><dt>Observed</dt><dd>{event.observed_at}</dd><dt>Received</dt><dd>{event.received_at}</dd><dt>HTTP status</dt><dd>{event.http_status ?? "Not observed"}</dd><dt>Error category</dt><dd>{event.error_category ?? "Not supplied"}</dd><dt>Elapsed</dt><dd>{event.elapsed_ms == null ? "Not supplied" : `${event.elapsed_ms} ms`}</dd><dt>Owner effect outcome</dt><dd>{event.effect_outcome ?? "Not supplied"}</dd><dt>Receipt</dt><dd>{event.receipt_id ?? "Not supplied"}</dd><dt>Run</dt><dd>{#if event.run_id}{event.run_id} · attributed to {event.source_id}{:else}No Run correlation supplied{/if}</dd><dt>Station attempt</dt><dd>{event.station_attempt_id ?? "Not supplied"}</dd><dt>Request</dt><dd>{event.request_id ?? "Not supplied"}</dd><dt>Job</dt><dd>{event.job_id ?? "Not supplied"}</dd><dt>Capture</dt><dd>{event.capture}</dd>
        {#if event.producer_generation}<dt>Producer generation</dt><dd>{event.producer_generation}</dd>{/if}
        {#if event.producer_seq != null}<dt>Producer sequence</dt><dd>{event.producer_seq}</dd>{/if}
        {#if event.station_key}<dt>Station key</dt><dd>{event.station_key}</dd>{/if}
        {#if event.step_id}<dt>Entered Step</dt><dd>{event.step_id}</dd>{/if}
        {#if event.native_event_id}<dt>Native event</dt><dd>{event.native_event_id}</dd>{/if}
        {#if event.native_seq != null}<dt>Native event sequence</dt><dd>{event.native_seq}</dd>{/if}
      </dl>
      {#if event.pattern_id}
        {@const pattern = snapshot.patterns.find(entry => entry.binding.source_id === event.source_id && entry.binding.source_generation === event.source_generation && entry.descriptor.pattern_id === event.pattern_id && entry.descriptor.revision === event.pattern_revision)}
        {#if pattern}<a href={pattern.detail_path}>Inspect exact Pattern {event.pattern_id}@{event.pattern_revision} →</a>{:else}<p>Exact Pattern {event.pattern_id}@{event.pattern_revision} is outside this inspection window.</p>{/if}
      {/if}
      </article>{/each}
    </section>{/if}
    <details><summary>Exact inspection Patterns ({snapshot.patterns.length})</summary><ul>{#each snapshot.patterns as pattern (pattern.detail_path)}<li><a href={pattern.detail_path}>{pattern.descriptor.title} · {pattern.descriptor.pattern_id}@{pattern.descriptor.revision}</a><p>{pattern.binding.executable ? "Executable in this Vessel" : "Observation only · not executable in this Vessel"} · {pattern.binding.profile_id}@{pattern.binding.profile_revision} · {pattern.binding.source_generation}</p></li>{/each}</ul></details>
  {:else if !state.loading}<p>No runtime window is available.</p>{/if}
</div>

<style>
  .runtime-evidence { font-size:12px; min-width:0; }
  header { display:flex; justify-content:space-between; align-items:start; gap:.5rem; }
  h3,h4 { font:500 14px/1.4 var(--font-body); color:var(--color-bone); }
  h5 { font:500 12px/1.5 var(--font-body); }
  p { color:var(--color-parchment); margin:.65rem 0; line-height:1.5; }
  details,section,article { border-top:1px solid var(--color-engraving); padding-top:.6rem; margin-top:.75rem; }
  summary { cursor:pointer; padding:.3rem 0; color:var(--color-bone); }
  ul { padding-left:1rem; }
  li { margin:.6rem 0; overflow-wrap:anywhere; }
  dl { display:grid; grid-template-columns:minmax(5rem,1fr) minmax(0,2fr); gap:.3rem .5rem; margin:.6rem 0; }
  dt { color:var(--color-parchment); } dd { margin:0; overflow-wrap:anywhere; }
  .nodes,.sources { list-style:none; padding:0; }
  button { border:1px solid var(--color-engraving); border-radius:var(--radius-glyph); background:var(--color-obsidian); color:var(--color-bone); padding:.5rem; cursor:pointer; font:inherit; }
  .nodes button { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; width:100%; text-align:left; }
  .nodes button small { flex-basis:100%; color:var(--color-parchment); }
  img { filter:invert(1); }
  a { color:var(--color-rune); }
  :is(button,a,summary):focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
</style>
