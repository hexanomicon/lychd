<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import type { LoomView } from "$lib/api/models";
  import { exportJson, exportMarkdown, scoreKey, verdicts, type Criterion, type Judgment, type ReviewRecord, type Verdict } from "$lib/pages/loom/state/evaluation/review";
  import { createEvaluationWorkspace, getEvaluationWorkspace, hasEvaluationWorkspace } from "$lib/pages/loom/state/evaluation/workspace.svelte";

  let { score, linkedRunId = null }: { score: LoomView; linkedRunId?: string | null } = $props();
  const workspace = hasEvaluationWorkspace() ? getEvaluationWorkspace() : createEvaluationWorkspace();
  const uid = $props.id();
  let review = $derived(workspace.active);
  let record = $derived(review?.record);
  let sameScore = $derived(review ? scoreKey(review.score) === scoreKey(score) : true);
  let contract = $derived(record?.contract ?? review?.contract);
  let source = $derived(record?.source ?? review?.source);
  let judgments = $derived(record?.judgments ?? review?.judgments ?? []);
  let discardId = $state<string | null>(null);
  let criterionSequence = 1;

  onDestroy(() => { for (const entry of workspace.entries) if (entry.loading) workspace.cancelRead(entry.id); });
  $effect(() => {
    const displayedKey = scoreKey(score);
    untrack(() => { for (const entry of workspace.entries) if (entry.loading && scoreKey(entry.score) !== displayedKey) workspace.cancelRead(entry.id); });
  });

  function input(event: Event & { currentTarget: HTMLInputElement | HTMLTextAreaElement }, change: (value: string) => void, read: () => string) {
    change(event.currentTarget.value);
    event.currentTarget.value = read();
  }
  function editCriterion(id: string, field: keyof Omit<Criterion, "id">, text: string) {
    if (review) workspace.editContract(review.id, { criteria: review.criteria.map(item => item.id === id ? { ...item, [field]: text } : item) });
  }
  function criterionValue(id: string, field: keyof Omit<Criterion, "id">) { return workspace.active?.criteria.find(item => item.id === id)?.[field] ?? ""; }
  function editJudgment(id: string, field: keyof Omit<Judgment, "criterionId" | "verdict">, text: string) {
    if (review) workspace.editJudgment(review.id, id, { [field]: text });
  }
  function judgmentValue(id: string, field: keyof Omit<Judgment, "criterionId" | "verdict">) { return workspace.active?.judgments.find(item => item.criterionId === id)?.[field] ?? ""; }
  function addCriterion() {
    if (!review) return;
    let id: string;
    do { id = `criterion-${++criterionSequence}`; } while (review.criteria.some(item => item.id === id));
    workspace.editContract(review.id, { criteria: [...review.criteria, { id, statement: "", evidence: "", missing: "Missing evidence remains UNKNOWN." }] });
  }
  function download(value: ReviewRecord, format: "json" | "md") {
    const content = format === "json" ? exportJson(value) : exportMarkdown(value);
    const url = URL.createObjectURL(new Blob([content], { type: format === "json" ? "application/json;charset=utf-8" : "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `loom-${value.id}-revision-${value.revision}.${format}`;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
</script>

<section class="evaluation" aria-label="Manual output review">
  <header>
    <span class="eyebrow">Evaluation</span>
    <h3>Manual output review</h3>
    <p class="boundary">Retrospective · Retained output · No new execution · Not saved to Vessel</p>
    <p>Declare a goal, freeze criteria, then read an exact Run's retained agent output. Historical execution predates these criteria. Completion records your judgment; Run status does not grade the output.</p>
    <p class="muted">Reviews stay in this browser document through navigation. Reload or exit loses them. Export completed records before leaving. Up to 4 reviews and 256,000 characters total; oversized input is refused without truncation.</p>
  </header>
  <div class="actions"><button type="button" onclick={() => { workspace.start(score); discardId = null; }}>New review for this score</button><span>{workspace.entries.length} / 4 reviews</span></div>
  {#if workspace.notice}<p role="status" class="notice">{workspace.notice}</p>{/if}
  {#if workspace.entries.length}
    <nav class="review-list" aria-label="Local reviews">
      {#each workspace.entries as entry (entry.id)}
        <button type="button" aria-pressed={entry.id === workspace.activeId} onclick={() => { workspace.select(entry.id); discardId = null; }}>
          {entry.id} · revision {entry.revision} · {entry.score.pattern_id}@{entry.score.revision} · {entry.record ? "Completed" : "Draft"}
        </button>
      {/each}
    </nav>
  {/if}
  {#if review}
    <article aria-label={`Review ${review.id}`} aria-busy={review.loading}>
      <div class="review-title"><h4>{review.id} · revision {review.revision}</h4><button type="button" onclick={() => discardId = review!.id}>Discard review</button></div>
      <p>Exact score: <code>{review.score.pattern_id}@{review.score.revision}</code> · <code>{review.score.digest}</code></p>
      {#if !sameScore}<p class="notice">This review belongs to another exact score. Its frozen identity is preserved. Return to that score to load source, or start a new review for the displayed score.</p>{/if}
      {#if discardId === review.id}
        <div class="notice" role="group" aria-label="Confirm discard"><p>Discard this local review permanently? Export a completed record first if you need it.</p><button type="button" onclick={() => { workspace.discard(discardId!); discardId = null; }}>Confirm discard</button><button type="button" onclick={() => discardId = null}>Keep review</button></div>
      {/if}
      {#if review.error}<p role="alert" class="notice">{review.error}</p>{/if}
      {#if record}
        <p class="boundary" role="status">Completed local review · frozen {record.completedAt}</p>
        <div class="actions"><button type="button" onclick={() => download(record!, "json")}>Export JSON</button><button type="button" onclick={() => download(record!, "md")}>Export Markdown</button><button type="button" onclick={() => workspace.revise(review!.id)}>Create review revision</button></div>
        <p class="muted">A revision reuses the same frozen criteria and output for retrospective regrading. To change criteria or reviewer, start a new review and freeze a new contract. This completed record stays immutable.</p>
      {/if}
      <section class="step" aria-label="Review contract">
        <h4>1. Declare and freeze the review contract</h4>
        {#if contract}
          <p class="boundary">Criteria frozen {contract.frozenAt}</p><p>Self-declared reviewer: <strong>{contract.reviewer}</strong> · identity is not authenticated</p>
          <h5>Goal</h5><p class="preserve">{contract.goal}</p><p class="muted"><code>{contract.digest}</code></p>
          <ol>{#each contract.criteria as criterion (criterion.id)}<li><strong>{criterion.statement}</strong><p>Evidence required: {criterion.evidence}</p><p>Missing-evidence policy: {criterion.missing}</p></li>{/each}</ol>
        {:else}
          <fieldset disabled={review.loading}><legend>Review declaration</legend>
          <label for={`${uid}-goal`}>Goal (up to 4,000 characters)</label><textarea id={`${uid}-goal`} rows="3" value={review.goal} oninput={(event) => input(event, text => workspace.editContract(review!.id, { goal: text }), () => workspace.active?.goal ?? "")}></textarea>
          <label for={`${uid}-reviewer`}>Self-declared reviewer (up to 256 characters)</label><input id={`${uid}-reviewer`} value={review.reviewer} oninput={(event) => input(event, text => workspace.editContract(review!.id, { reviewer: text }), () => workspace.active?.reviewer ?? "")} />
          <p class="muted">Each criterion field allows 2,000 characters. Declare expected or forbidden behavior, the evidence you require, and how missing evidence will affect judgment.</p>
          {#each review.criteria as criterion, index (criterion.id)}
            <fieldset><legend>Criterion {index + 1}</legend>
              <label for={`${uid}-${criterion.id}-statement`}>Expected or forbidden behavior</label><textarea id={`${uid}-${criterion.id}-statement`} rows="2" value={criterion.statement} oninput={(event) => input(event, text => editCriterion(criterion.id, "statement", text), () => criterionValue(criterion.id, "statement"))}></textarea>
              <label for={`${uid}-${criterion.id}-evidence`}>Evidence requirements</label><textarea id={`${uid}-${criterion.id}-evidence`} rows="2" value={criterion.evidence} oninput={(event) => input(event, text => editCriterion(criterion.id, "evidence", text), () => criterionValue(criterion.id, "evidence"))}></textarea>
              <label for={`${uid}-${criterion.id}-missing`}>Missing-evidence policy</label><textarea id={`${uid}-${criterion.id}-missing`} rows="2" value={criterion.missing} oninput={(event) => input(event, text => editCriterion(criterion.id, "missing", text), () => criterionValue(criterion.id, "missing"))}></textarea>
              {#if review.criteria.length > 1}<button type="button" onclick={() => workspace.editContract(review!.id, { criteria: review!.criteria.filter(item => item.id !== criterion.id) })}>Remove criterion {index + 1}</button>{/if}
            </fieldset>
          {/each}
          <div class="actions"><button type="button" disabled={review.criteria.length >= 8 || review.loading} onclick={addCriterion}>Add criterion</button><button type="button" disabled={review.loading} onclick={() => workspace.freezeContract(review!.id)}>Freeze review contract</button></div>
          </fieldset>
        {/if}
      </section>
      {#if contract && !record}
        <section class="step" aria-label="Retained source">
          <h4>2. Load and freeze exact retained output</h4>
          {#if !source}
            <label for={`${uid}-run`}>Exact Run ID</label><input id={`${uid}-run`} value={review.runId} oninput={(event) => input(event, text => workspace.editRun(review!.id, text), () => workspace.active?.runId ?? "")} />
            {#if linkedRunId}<button type="button" disabled={review.loading || !sameScore} onclick={() => workspace.editRun(review!.id, linkedRunId!)}>Use linked Run</button>{/if}
            <button type="button" disabled={review.loading || !sameScore} onclick={() => workspace.loadSource(review!.id, score)}>Load exact Run output</button>
            <p class="muted">This explicitly reads the Run, verifies its full pinned manifest and inspection binding, then reads its exact Session. It starts no execution.</p>
            {#if review.turns.length}
              <fieldset><legend>Select supplied agent output</legend>
                <p>{review.turns.length === 1 ? "One matching agent turn was supplied. Confirm it explicitly." : "Multiple matching agent turns were supplied. Resolve the ambiguity by selecting the intended output."} No durable turn ID is supplied.</p>
                {#each review.turns as turn, index (`${turn.created_at}:${index}`)}
                  <label class="turn"><input type="radio" name={`${uid}-turn`} disabled={review.loading} checked={review.selectedTurn === index} onchange={() => workspace.selectTurn(review!.id, index)} /> Snapshot position {index + 1} · {turn.role} · {turn.created_at} · {turn.state}<pre>{turn.content}</pre></label>
                {/each}
              </fieldset>
              <button type="button" disabled={review.loading || review.selectedTurn === null} onclick={() => workspace.freezeSource(review!.id)}>Freeze selected output</button>
            {/if}
          {/if}
        </section>
      {/if}
      {#if source}
        <section class="step" aria-label="Frozen output"><h4>Frozen retained output</h4><p>Run <code>{source.runId}</code> · Session <code>{source.sessionId}</code> · role {source.role}</p><p>Supplied timestamp {source.createdAt} · captured {source.capturedAt}</p><p>Run status: <strong>{source.run.status}</strong> (separate from verdict and review completion)</p><p class="muted"><code>{source.digest}</code></p><pre>{source.content}</pre>
          <details><summary>Capture limitations and exact binding</summary><ul>{#each source.limitations as limitation (limitation)}<li>{limitation}</li>{/each}</ul><pre>{JSON.stringify({ pattern: source.pattern, score: source.score, capture: source.capture, snapshotAt: source.snapshotAt }, null, 2)}</pre></details>
        </section>
        <section class="step" aria-label="Criterion judgments"><h4>3. Record criterion judgments</h4>
          <p>Verdicts start UNKNOWN. Give a rationale and an exact supporting quotation or an explicit missing-evidence limitation. Judgment fields allow 8,000 characters.</p>
          {#each contract?.criteria ?? [] as criterion, index (criterion.id)}
            {@const judgment = judgments.find(item => item.criterionId === criterion.id)!}
            <fieldset><legend>Criterion {index + 1}: {criterion.statement}</legend>
              {#if record}<p><strong>{judgment.verdict}</strong></p><h5>Rationale</h5><p class="preserve">{judgment.rationale}</p><h5>Supporting quotation</h5><pre>{judgment.quotation || "None supplied"}</pre><h5>Missing-evidence limitation</h5><p class="preserve">{judgment.limitation || "None declared"}</p>
              {:else}
                <label for={`${uid}-${criterion.id}-verdict`}>Verdict for criterion {index + 1}</label><select id={`${uid}-${criterion.id}-verdict`} value={judgment.verdict} onchange={(event) => workspace.editJudgment(review!.id, criterion.id, { verdict: event.currentTarget.value as Verdict })}>{#each verdicts as verdict (verdict)}<option value={verdict}>{verdict}</option>{/each}</select>
                <label for={`${uid}-${criterion.id}-rationale`}>Rationale for criterion {index + 1}</label><textarea id={`${uid}-${criterion.id}-rationale`} value={judgment.rationale} oninput={(event) => input(event, text => editJudgment(criterion.id, "rationale", text), () => judgmentValue(criterion.id, "rationale"))}></textarea>
                <label for={`${uid}-${criterion.id}-quotation`}>Exact supporting quotation for criterion {index + 1}</label><textarea id={`${uid}-${criterion.id}-quotation`} value={judgment.quotation} oninput={(event) => input(event, text => editJudgment(criterion.id, "quotation", text), () => judgmentValue(criterion.id, "quotation"))}></textarea>
                <label for={`${uid}-${criterion.id}-limitation`}>Missing-evidence limitation for criterion {index + 1}</label><textarea id={`${uid}-${criterion.id}-limitation`} value={judgment.limitation} oninput={(event) => input(event, text => editJudgment(criterion.id, "limitation", text), () => judgmentValue(criterion.id, "limitation"))}></textarea>
              {/if}
            </fieldset>
          {/each}
          {#if !record}<button type="button" onclick={() => workspace.finish(review!.id)}>Finish and freeze review</button>{/if}
        </section>
      {/if}
    </article>
  {:else}<p class="empty">Start a review to declare its goal and criteria. Opening Evaluation performs no source reads.</p>{/if}
</section>

<style>
  .evaluation { max-width:72rem; color:var(--color-parchment); font:var(--text-sm)/1.65 var(--font-body); }
  .evaluation :is(p,code,strong,li,legend) { overflow-wrap:anywhere; }
  .evaluation h3 { font-size:var(--text-xl); color:var(--color-bone); }
  .evaluation h4 { font-size:var(--text-base); color:var(--color-bone); margin:0 0 .75rem; }
  .evaluation h5 { color:var(--color-bone); margin:.8rem 0 .3rem; }
  .evaluation p { margin:.6rem 0; }
  .eyebrow,.muted { color:var(--color-ash); font-size:var(--text-xs); }
  .eyebrow { letter-spacing:.08em; text-transform:uppercase; }
  .boundary { color:var(--color-bone); font-weight:600; }
  .actions,.review-title { display:flex; flex-wrap:wrap; align-items:center; gap:.65rem; margin:1rem 0; }
  .review-title { justify-content:space-between; }
  button,input,textarea,select { font:inherit; color:var(--color-bone); background:var(--color-obsidian); border:1px solid var(--color-control-border); border-radius:4px; }
  button { cursor:pointer; min-height:40px; padding:.5rem .8rem; }
  button:disabled { cursor:default; opacity:.55; }
  button[aria-pressed="true"] { border-color:var(--color-rune); text-decoration:underline; text-underline-offset:.25em; }
  :is(button,input,textarea,select,summary):focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  input:not([type="radio"]),textarea,select { display:block; width:100%; padding:.55rem; margin:.35rem 0 1rem; box-sizing:border-box; }
  textarea { resize:vertical; min-height:5rem; }
  label { display:block; }
  fieldset { min-width:0; border:1px solid var(--color-engraving); padding:1rem; margin:1rem 0; }
  legend { padding:0 .4rem; color:var(--color-bone); max-width:100%; }
  .step { border-top:1px solid var(--color-engraving); margin-top:1.25rem; padding-top:1.25rem; }
  .notice { padding:.7rem 1rem; border-left:2px solid var(--color-heat); background:var(--color-obsidian); }
  .review-list { display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0 1.5rem; }
  pre,.preserve { white-space:pre-wrap; overflow-wrap:anywhere; }
  pre { max-height:28rem; overflow:auto; background:var(--color-obsidian); padding:1rem; border:1px solid var(--color-engraving); font:var(--text-xs)/1.7 var(--font-glyph); }
  .turn { margin:1rem 0; }
  .turn input { margin-right:.5rem; }
  details { margin:1rem 0; }
  summary { cursor:pointer; }
  .empty { padding:1rem 0; }
</style>
