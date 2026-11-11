<script lang="ts">
  import type { OrbRunSnapshot } from "$lib/api/models";

  let { summary }: { summary: OrbRunSnapshot["creation"] } = $props();

  function adoption(present: boolean, adopted: boolean): string {
    return adopted ? "Adopted" : present ? "Retained · not adopted" : "Not retained";
  }
</script>

{#if summary}
  <section class="creation-summary" aria-labelledby="creation-outcome-title">
    <header>
      <h2 id="creation-outcome-title">Creation outcome</h2>
      <span class="native-status">{summary.native_status.replaceAll("_", " ")}</span>
    </header>
    <p>Case outcome is separate from Run execution status. These are the latest fetched case details.</p>
    {#if !summary.admission_current}
      <p class="historical-admission">Historical admission: this Run is linked to an earlier attempt. The case outcome can include later admissions.</p>
    {/if}
    <dl class="judgments">
      <div><dt>Native verdict</dt><dd>{summary.native_disposition?.replaceAll("_", " ") ?? "No native verdict"}</dd></div>
      <div><dt>External assessment</dt><dd>{summary.external_disposition?.replaceAll("_", " ") ?? "No external assessment"}</dd></div>
      <div><dt>Owner disposition</dt><dd>{summary.current_decision_id ? summary.feedback_status.replaceAll("_", " ") : "No current decision"}</dd></div>
    </dl>
    <p class="feedback-state">Feedback: {summary.feedback_status.replaceAll("_", " ")}. An accepted native verdict does not establish external agreement or owner permission.</p>
    <dl class="custody">
      <div><dt>Constructor response</dt><dd>{adoption(summary.constructor_present, summary.constructor_adopted)}</dd></div>
      <div><dt>Verifier response</dt><dd>{adoption(summary.verifier_present, summary.verifier_adopted)}</dd></div>
      <div><dt>Candidate</dt><dd>{summary.candidate_present ? "Retained" : "Not retained"}</dd></div>
      <div><dt>Reason code</dt><dd>{summary.reason_code?.replaceAll("_", " ") ?? "None supplied"}</dd></div>
      <div><dt>Admission deadline</dt><dd><time datetime={summary.deadline}>{new Date(summary.deadline).toLocaleString()}</time> (local) · {summary.deadline_elapsed ? "elapsed" : "not elapsed at this read"}</dd></div>
      <div><dt>Execution slot</dt><dd>{summary.slot_encumbered ? "Encumbered" : "Not encumbered"}</dd></div>
    </dl>
    <details>
      <summary>Retained identities</summary>
      <dl class="identities">
        <div><dt>Case</dt><dd>{summary.case_id}</dd></div>
        <div><dt>Admission for this Run</dt><dd>{summary.admission_id}</dd></div>
        <div><dt>Current assessment</dt><dd>{summary.current_assessment_id ?? "None"}</dd></div>
        <div><dt>Current owner decision</dt><dd>{summary.current_decision_id ?? "None"}</dd></div>
      </dl>
    </details>
    <p>After the Run feed settles, use Refresh above to read later assessments or owner decisions. This view does not continue observing them after settlement.</p>
  </section>
{:else}
  <details class="creation-unavailable">
    <summary>Creation evidence unavailable</summary>
    <p>No Creation summary is available for this Run under current authority. This does not establish whether a case exists.</p>
  </details>
{/if}

<style>
  .creation-summary { min-width: 0; padding: 1rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  header { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 1rem; }
  h2 { color: var(--color-bone); font: 500 var(--text-lg)/1.4 var(--font-body); }
  .native-status { color: var(--color-bone); font-size: var(--text-base); text-transform: capitalize; }
  p, dl, details { font-size: var(--text-sm); line-height: 1.6; }
  p { margin-top: .6rem; color: var(--color-parchment); }
  .historical-admission { border-inline-start: 2px solid var(--color-rune); padding-inline-start: .75rem; }
  dl { display: grid; gap: .75rem; margin-top: 1rem; }
  .judgments { grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr)); }
  .custody { grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); }
  dl > div { min-width: 0; }
  dt { color: var(--color-parchment); }
  dd { margin: .2rem 0 0; color: var(--color-bone); overflow-wrap: anywhere; }
  .judgments dd { font-weight: 600; }
  details { margin-top: .8rem; color: var(--color-parchment); }
  summary { cursor: pointer; padding-block: .35rem; }
  summary:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .identities { font-family: var(--font-glyph); }
</style>
