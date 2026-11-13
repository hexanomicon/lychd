<script lang="ts">
  import type { OrbRunSnapshot } from "$lib/api/models";

  type Preference = NonNullable<OrbRunSnapshot["bridge_preference"]>;
  type Route = Preference["routes"][number];
  let { summary }: { summary: OrbRunSnapshot["bridge_preference"] } = $props();

  const phases: Record<NonNullable<Route["phase"]>, string> = {
    cold: "Cold", activatable: "Activatable", warming: "Warming",
    warm: "Warm", error: "Error", unknown: "Unknown"
  };
  const exclusions: Record<NonNullable<Route["exclusion_code"]>, string> = {
    disabled: "Disabled · ineligible",
    not_warm: "Not warm",
    admission_closed: "Admission closed",
    readiness_changed: "Readiness changed before admission"
  };
</script>

{#if summary}
  <section class="routing-preference" aria-labelledby="routing-preference-title">
    <h2 id="routing-preference-title">Routing preference</h2>
    <p>Selected at admission: <code>{summary.selected_capability_key}</code></p>
    <p>This immutable admission observation is retained with the Run. Later readiness may differ.</p>
    <!-- Keyboard users need focus to scroll this bounded table region. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="route-table" role="region" aria-label="Routing preference routes" tabindex="0">
      <table>
        <caption>Routes observed at admission</caption>
        <thead>
          <tr><th scope="col">Route</th><th scope="col">Preference (unitless)</th><th scope="col">Observation</th></tr>
        </thead>
        <tbody>
          {#each summary.routes as route (route.capability_key)}
            <tr>
              <th scope="row">
                <code>{route.capability_key}</code>
                {#if route.capability_key === summary.selected_capability_key}
                  <span class="selected-label">Selected at admission</span>
                {/if}
              </th>
              <td>{route.weight}</td>
              <td>
                <span>{route.phase === null ? "No retained observation" : phases[route.phase]}</span>
                <span>{route.admission_open ? "Admission open" : "Admission closed"}</span>
                <span>{route.exclusion_code === null ? "Not excluded" : exclusions[route.exclusion_code]}</span>
                {#if route.observed_at}
                  <time datetime={route.observed_at}>{new Date(route.observed_at).toLocaleString()} (local)</time>
                {:else}
                  <span>No retained observation time</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p>Settings affect new admissions. Replay and restart keep the selected key; fallback is unavailable.</p>
    <details>
      <summary>Admission identities and observation window</summary>
      <dl>
        <div><dt>Policy digest</dt><dd><code>{summary.policy_digest}</code></dd></div>
        <div><dt>Batch started</dt><dd><time datetime={summary.batch_started_at}>{new Date(summary.batch_started_at).toLocaleString()} (local)</time></dd></div>
        <div><dt>Batch finished</dt><dd><time datetime={summary.batch_finished_at}>{new Date(summary.batch_finished_at).toLocaleString()} (local)</time></dd></div>
      </dl>
    </details>
  </section>
{/if}

<style>
  .routing-preference { min-width: 0; padding: 1rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  h2 { color: var(--color-bone); font: 500 var(--text-lg)/1.4 var(--font-body); }
  p, table, details { font-size: var(--text-sm); line-height: 1.6; }
  p { margin-top: .6rem; color: var(--color-parchment); }
  code { font-family: var(--font-glyph); overflow-wrap: anywhere; }
  .route-table { overflow-x: auto; margin-top: .8rem; }
  table { width: 100%; min-width: 22rem; table-layout: fixed; border-collapse: collapse; }
  caption { text-align: start; color: var(--color-parchment); padding-bottom: .5rem; }
  th, td { text-align: start; vertical-align: top; padding: .6rem .4rem; border-bottom: 1px solid var(--color-engraving); overflow-wrap: anywhere; }
  th { color: var(--color-bone); font-weight: 500; }
  td { color: var(--color-parchment); }
  th:first-child { width: 36%; }
  th:nth-child(2) { width: 22%; }
  td span, td time, .selected-label { display: block; }
  .selected-label { margin-top: .4rem; color: var(--color-bone); font: 600 var(--text-sm)/1.5 var(--font-body); }
  details { margin-top: .8rem; color: var(--color-parchment); }
  summary { cursor: pointer; padding-block: .35rem; }
  summary:focus-visible, .route-table:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  dl { display: grid; gap: .75rem; margin-top: .6rem; }
  dd { margin: .2rem 0 0; color: var(--color-bone); overflow-wrap: anywhere; }
</style>
