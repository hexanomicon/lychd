<script lang="ts">
  import { afterNavigate, beforeNavigate } from "$app/navigation";
  import { getContext, onDestroy, tick } from "svelte";
  import { readCreationInvestigation, submitCreationInvestigation } from "$lib/api/client";
  import CreationFeedback from "./CreationFeedback.svelte";
  import PageHeader from "../shared/PageHeader.svelte";
  import { altarNavigationContext, type AltarNavigation } from "$lib/navigation/instruments";
  import {
    emptyDraft, initialIntakeState, InvestigationIntake, investigationHref, investigationSelection, prepareRequest, utf8Bytes
  } from "$lib/creation/intake";

  let { caseId, onSelect }: { caseId: string | null; onSelect: (id: string | null) => void } = $props();
  const navigation = getContext<AltarNavigation | undefined>(altarNavigationContext);
  let draft = $state(emptyDraft());
  let intakeState = $state.raw(initialIntakeState());
  let errors = $state.raw<string[]>([]);
  let submitted = $state(false);
  let errorHeading = $state<HTMLHeadingElement | undefined>();
  let intakeHeading = $state<HTMLHeadingElement | undefined>();
  let discardHeading = $state<HTMLHeadingElement | undefined>();
  let discardReviewOpen = $state(false);
  let discardReviewCaseId: string | null = null;
  let discardReturnFocus: HTMLButtonElement | undefined;
  let nextRow = 1;
  const intake = new InvestigationIntake({ submit: submitCreationInvestigation, read: readCreationInvestigation },
    (next) => { intakeState = next; });
  const busy = $derived(intakeState.phase === "submitting" || intakeState.phase === "checking");
  const report = $derived(caseId === null || intakeState.caseId === caseId ? intakeState.report : null);
  const sourceBytes = $derived(draft.sources.reduce((sum, source) => sum + utf8Bytes(source.text), 0));
  const hasDraft = $derived(!!(draft.repository || draft.baseRevision || draft.digest || draft.question ||
    draft.sources.some((source) => source.name || source.text) || draft.criteria.some((criterion) => criterion.id || criterion.predicate) ||
    draft.nonGoals.length || draft.omissions.length));

  // Route changes invalidate pending reads; selection itself never fetches or submits.
  afterNavigate(() => {
    closeDiscardReview();
    intake.select(caseId);
  });
  onDestroy(() => intake.dispose());
  function guardUnload(event: BeforeUnloadEvent) {
    if (!hasDraft && intakeState.unconfirmedIds.length === 0) return;
    event.preventDefault(); event.returnValue = "";
  }
  beforeNavigate((navigation) => {
    const target = navigation.to?.url;
    const focus = target?.searchParams.getAll("investigation") ?? [];
    const staysInInvestigation = !navigation.willUnload && target?.origin === navigation.from?.url.origin &&
      target?.pathname === "/bridge" && focus.length === 1 && investigationSelection(focus[0] ?? null) !== null;
    if (!staysInInvestigation && !navigation.willUnload && (hasDraft || intakeState.unconfirmedIds.length > 0) &&
      !window.confirm("Leave this investigation focus? Transient source and replay bodies may be lost. Keep any unconfirmed case UUID; leaving does not cancel or resolve it.")) navigation.cancel();
  });
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy || submitted) return;
    const prepared = prepareRequest($state.snapshot(draft), crypto.randomUUID());
    errors = prepared.errors;
    if (!prepared.request) { await tick(); errorHeading?.focus(); return; }
    submitted = true;
    const pending = intake.submit(prepared.request);
    onSelect(prepared.request.request_id);
    await pending;
  }
  function closeDiscardReview() {
    discardReviewOpen = false;
    discardReturnFocus = undefined;
  }
  async function startDifferent(opener: HTMLButtonElement) {
    if (busy) return;
    if (hasDraft || intakeState.unconfirmedIds.length > 0) {
      discardReviewCaseId = intakeState.caseId;
      discardReturnFocus = opener;
      discardReviewOpen = true;
      await tick();
      if (discardReviewOpen && discardReviewCaseId === intakeState.caseId && discardHeading?.isConnected) discardHeading.focus();
      return;
    }
    await resetForDifferent();
  }
  async function keepCurrent() {
    const target = discardReturnFocus;
    closeDiscardReview();
    await tick();
    if (target?.isConnected && !target.disabled) target.focus();
    else if (intakeHeading?.isConnected) intakeHeading.focus();
  }
  async function confirmDifferent() {
    if (!discardReviewOpen || busy || discardReviewCaseId !== intakeState.caseId) return;
    await resetForDifferent();
  }
  async function resetForDifferent() {
    closeDiscardReview();
    intake.startDifferent(); draft = emptyDraft(); submitted = false; errors = []; onSelect(null);
    await tick();
    if (intakeHeading?.isConnected) intakeHeading.focus();
  }
  function addSource() { draft.sources.push({ key: `source-${nextRow++}`, name: "", text: "" }); }
  function addCriterion() { draft.criteria.push({ key: `criterion-${nextRow++}`, id: "", predicate: "" }); }
  function nativeReason(value: string | null): string {
    if (value === "output_bytes") return "Canonical output exceeded its byte bound.";
    if (value === "output_length") return "The provider response ended at its output limit.";
    if (value === "expired") return "The case deadline elapsed.";
    if (value === "cancelled") return "Adoption was cancelled.";
    return value ? "A native noncompletion reason is retained." : "No native noncompletion reason supplied.";
  }
</script>

<svelte:head><title>Creation investigation — Bridge — LychD</title></svelte:head>
<svelte:window onbeforeunload={guardUnload} />
<section class="investigation" aria-labelledby="investigation-title">
  <PageHeader
    title="Creation investigation"
    kicker="Bridge · public source"
    description="A bounded question about literal public source. The fixed investigation is tools-free: it does not acquire a repository, edit source or promote a change."
    back={{ href: navigation?.bridgePath ?? "/bridge", label: "Return to conversation" }}
    titleId="investigation-title"
    titleFocusable
    bind:heading={intakeHeading}
  />
  {#if intakeState.unconfirmedIds.length > 0}
    <aside class="notice" aria-label="Unconfirmed admissions">
      <h2>Admission unconfirmed</h2>
      <p>Keep these exact case UUIDs. A failed Check, including 404, does not prove that submission was refused.</p>
      <ul>{#each intakeState.unconfirmedIds as id (id)}<li><a href={investigationHref(id)}>{id}</a></li>{/each}</ul>
    </aside>
  {/if}
  <div class="actions">
    {#if intakeState.caseId}
      <p>Selected case <code>{intakeState.caseId}</code></p>
      <button class="rune-btn" type="button" disabled={busy} onclick={() => intake.check()}>
        {intakeState.phase === "checking" ? "Checking…" : report ? "Refresh retained case" : "Check this case"}
      </button>
      {#if intakeState.canReplay}<button class="rune-btn" type="button" onclick={() => intake.replay()}>Replay identical request</button>{/if}
      <button class="rune-btn" type="button" disabled={busy || discardReviewOpen}
        aria-expanded={discardReviewOpen} aria-controls="investigation-discard-review"
        onclick={(event) => startDifferent(event.currentTarget)}>Start different request</button>
      {#if !intakeState.canReplay && !busy && !report}<p>The original request body is unavailable for this selected case. Reload cannot recover identical replay.</p>{/if}
    {/if}
  </div>
  {#if discardReviewOpen}
    <section id="investigation-discard-review" class="notice" aria-labelledby="investigation-discard-title">
      <h2 id="investigation-discard-title" bind:this={discardHeading} tabindex="-1">Start a different request?</h2>
      <p>This discards the transient draft and original replay body. Earlier unconfirmed case UUIDs remain listed; this does not cancel or resolve them. Keep the current request to Check or replay it first.</p>
      <div class="actions">
        <button class="rune-btn" type="button" onclick={keepCurrent}>Keep current request</button>
        <button class="rune-btn" type="button" disabled={busy} onclick={confirmDifferent}>Discard draft and replay body</button>
      </div>
    </section>
  {/if}
  {#if intakeState.message}<p class="notice" role="status">{intakeState.message}</p>{/if}
  {#if intakeState.phase === "submitting"}<p role="status">Submitting once. No automatic retry will be sent.</p>{/if}
  {#if !intakeState.caseId}
    <form onsubmit={submit} novalidate aria-label="Public-source investigation">
      <p>Sources and request bodies stay in memory here; only the case UUID enters navigation. Leaving or reloading can discard them. The server retains admitted public material.</p>
      {#if errors.length}
        <div role="alert"><h2 bind:this={errorHeading} tabindex="-1">Check the request</h2><ul>{#each errors as error (error)}<li>{error}</li>{/each}</ul></div>
      {/if}
      <fieldset disabled={busy || submitted}>
        <legend>Declared target</legend>
        <label>Repository <input bind:value={draft.repository} autocomplete="off" spellcheck="false" /></label>
        <label>Base revision <input bind:value={draft.baseRevision} autocomplete="off" spellcheck="false" /></label>
        <label>Tree or patch digest <input bind:value={draft.digest} autocomplete="off" spellcheck="false" /></label>
        <p>These are your declared identities, not an observed live Git tree. Use a lowercase hexadecimal digest of 40–64 characters.</p>
        <label>Question <textarea rows="3" bind:value={draft.question}></textarea><span>{utf8Bytes(draft.question)} / 512 UTF-8 bytes</span></label>
      </fieldset>
      <fieldset disabled={busy || submitted}>
        <legend>Literal public sources</legend>
        <p>{sourceBytes} / 4096 UTF-8 bytes total · 1–8 sources. Relative names are unique; no parent path, colon or backslash.</p>
        {#each draft.sources as source (source.key)}
          <div class="entry">
            <label>Source name <input bind:value={source.name} autocomplete="off" spellcheck="false" /></label>
            <label>Source text <textarea class="source" rows="6" bind:value={source.text} spellcheck="false"></textarea></label>
            <button class="rune-btn" type="button" disabled={draft.sources.length === 1} onclick={() => { draft.sources = draft.sources.filter((row) => row.key !== source.key); }}>Remove source</button>
          </div>
        {/each}
        <button class="rune-btn" type="button" disabled={draft.sources.length >= 8} onclick={addSource}>Add source</button>
      </fieldset>
      <fieldset disabled={busy || submitted}>
        <legend>Explicit criteria</legend>
        <p>1–4 criteria; each predicate at most 192 UTF-8 bytes. IDs are unique, lowercase and at most 32 characters.</p>
        {#each draft.criteria as criterion (criterion.key)}
          <div class="entry">
            <label>Criterion ID <input bind:value={criterion.id} autocomplete="off" spellcheck="false" /></label>
            <label>Criterion predicate <textarea rows="2" bind:value={criterion.predicate}></textarea><span>{utf8Bytes(criterion.predicate)} / 192 UTF-8 bytes</span></label>
            <button class="rune-btn" type="button" disabled={draft.criteria.length === 1} onclick={() => { draft.criteria = draft.criteria.filter((row) => row.key !== criterion.key); }}>Remove criterion</button>
          </div>
        {/each}
        <button class="rune-btn" type="button" disabled={draft.criteria.length >= 4} onclick={addCriterion}>Add criterion</button>
      </fieldset>
      <fieldset disabled={busy || submitted}>
        <legend>Boundary (optional)</legend>
        <p>At most four non-goals and four omissions, each 192 UTF-8 bytes. Empty added entries must be removed.</p>
        {#each draft.nonGoals as row (row.key)}
          <div class="entry"><label>Non-goal <textarea rows="2" bind:value={row.text}></textarea><span>{utf8Bytes(row.text)} / 192 UTF-8 bytes</span></label>
            <button class="rune-btn" type="button" onclick={() => { draft.nonGoals = draft.nonGoals.filter((entry) => entry.key !== row.key); }}>Remove non-goal</button></div>
        {/each}
        <button class="rune-btn" type="button" disabled={draft.nonGoals.length >= 4} onclick={() => draft.nonGoals.push({ key: `non-goal-${nextRow++}`, text: "" })}>Add non-goal</button>
        {#each draft.omissions as row (row.key)}
          <div class="entry"><label>Omission <textarea rows="2" bind:value={row.text}></textarea><span>{utf8Bytes(row.text)} / 192 UTF-8 bytes</span></label>
            <button class="rune-btn" type="button" onclick={() => { draft.omissions = draft.omissions.filter((entry) => entry.key !== row.key); }}>Remove omission</button></div>
        {/each}
        <button class="rune-btn" type="button" disabled={draft.omissions.length >= 4} onclick={() => draft.omissions.push({ key: `omission-${nextRow++}`, text: "" })}>Add omission</button>
        <label class="declaration"><input type="checkbox" bind:checked={draft.publicMaterial} />I confirm every supplied item is public material.</label>
      </fieldset>
      <button class="rune-btn rune-btn--frost" type="submit" disabled={busy || submitted}>Submit investigation once</button>
    </form>
  {/if}
  {#if report}
    <article aria-labelledby="retained-report">
      <h2 id="retained-report">Retained investigation</h2>
      <dl><dt>Case status</dt><dd>{report.status}</dd><dt>Deadline</dt><dd>{report.deadline}</dd>
        <dt>Execution slot</dt><dd>{report.slot_encumbered ? "Encumbered" : "Released"}</dd><dt>Native noncompletion</dt><dd>{nativeReason(report.reason)}</dd></dl>
      <p>Case status and verifier judgment are separate from Run completion. A complete response does not establish semantic correctness.</p>
      <h3>Admitted Runs</h3>
      <ul>{#each report.admissions as admission (admission.admission_id)}<li>
        Admission <code>{admission.admission_id}</code>:
        {#if admission.run_id}<a href={`/orb/${encodeURIComponent(admission.run_id)}`}>Look into the Orb · {admission.run_id}</a>{:else}No Run link retained.{/if}
      </li>{/each}</ul>
      <p>A native accepted verdict is not final owner acceptance.</p>
      {#key report.case_id}<CreationFeedback caseId={report.case_id} />{/key}
      <details><summary>Retained question and declared target</summary><h3>{report.request.question}</h3>
        <dl><dt>Repository</dt><dd>{report.request.repository}</dd><dt>Base revision</dt><dd>{report.request.base_revision}</dd><dt>Declared tree/patch digest</dt><dd>{report.request.tree_or_patch_digest}</dd></dl>
        <h4>Criteria</h4><ul>{#each report.request.criteria as criterion (criterion.id)}<li>{criterion.id}: {criterion.predicate}</li>{/each}</ul>
        <h4>Non-goals</h4><pre>{report.request.non_goals.join("\n") || "None supplied."}</pre>
        <h4>Omissions</h4><pre>{report.request.omissions.join("\n") || "None supplied."}</pre>
      </details>
      <section aria-labelledby="candidate-report"><h3 id="candidate-report">Native candidate report</h3>
        {#if report.candidate}<p>{report.candidate.summary}</p>
          {#each report.candidate.findings as finding (finding.criterion)}<section class="entry"><h4>{finding.criterion}</h4><p>{finding.claim}</p>
            <p>Sources: {finding.citations.map((citation) => `${citation.source}:${citation.first_line}–${citation.last_line}`).join("; ") || "No citations retained."}</p>
            <p>Unknown: {finding.unknown || "None supplied."}</p></section>{/each}
        {:else}<p>No canonical candidate report is retained. This does not establish whether a provider response was retained.</p>{/if}
      </section>
      <section aria-labelledby="verifier-verdict"><h3 id="verifier-verdict">Native verifier verdict</h3>
        {#if report.verdict}<p>Disposition: <strong>{report.verdict.disposition}</strong></p>
          {#each report.verdict.findings as finding (finding.criterion)}<section class="entry"><h4>{finding.criterion}</h4><p>{finding.claim}</p>
            <p>Sources: {finding.citations.map((citation) => `${citation.source}:${citation.first_line}–${citation.last_line}`).join("; ") || "No citations retained."}</p>
            <p>Unknown: {finding.unknown || "None supplied."}</p></section>{/each}
          <p>Contradictions: {report.verdict.contradictions.join("; ") || "None supplied."}</p>
        {:else}<p>No canonical verifier verdict is retained.</p>{/if}
      </section>
      <details><summary>Retained literal sources</summary>{#each report.request.sources as source (source.name)}<section><h3>{source.name}</h3><pre>{source.text}</pre></section>{/each}</details>
    </article>
  {/if}
  <p class="read-boundary">Check and Refresh read the protected case and may expire an overdue investigation. They do not continue execution or append feedback. Later report or review changes need an explicit Refresh.</p>
</section>

<style>
  .investigation { width: min(100%, 64rem); margin: 0 auto; padding: clamp(1rem, 3vw, 2.5rem); display: grid; align-content: start; gap: 2rem; min-width: 0; }
  section, article, form, fieldset { display: grid; align-content: start; gap: 1rem; min-width: 0; }
  h2, h3, p { margin: 0; }
  h2, h3, legend { color: var(--color-bone); font-family: var(--font-body); font-variant: normal; letter-spacing: normal; }
  h2 { font-size: var(--text-xl); font-weight: 600; line-height: 1.35; }
  h3 { font-size: var(--text-base); font-weight: 600; line-height: 1.5; }
  .investigation > form, .investigation > article { border-top: 1px solid var(--color-engraving); padding-top: 1.5rem; }
  fieldset { margin: 0; padding: 1.25rem 0 0; border: 0; border-top: 1px solid var(--color-engraving); gap: 1.25rem; }
  legend { padding: 0 0.75rem 0 0; font-size: var(--text-sm); font-weight: 600; }
  .notice { display: grid; align-content: start; gap: 1rem; min-width: 0; padding: 1.25rem; border: 0; border-left: 2px solid var(--color-control-border); border-radius: 0 var(--radius-panel) var(--radius-panel) 0; background: var(--color-obsidian); }
  label { display: grid; gap: 0.5rem; color: var(--color-bone); }
  input:not([type="checkbox"]), textarea { width: 100%; min-width: 0; min-height: 2.75rem; padding: 0.75rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); background: var(--color-void); color: var(--color-bone); }
  label span { color: var(--color-ash); font-size: var(--text-sm); }
  textarea { resize: vertical; line-height: 1.6; }
  dd, code, a, li { overflow-wrap: anywhere; }
  dl { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 3fr); gap: 0.65rem 1.5rem; margin: 0; padding-block: 0.25rem; }
  dt { color: var(--color-ash); font-size: var(--text-sm); }
  dd { margin: 0; min-width: 0; }
  button { align-self: start; justify-self: start; min-height: 2.75rem; max-width: 100%; white-space: normal; line-height: 1.4; }
  [role="alert"] { color: var(--color-ember); }
  :is(a, button, input, textarea):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 36rem) { .investigation { padding: 1rem; gap: 1.5rem; } dl { grid-template-columns: minmax(0, 1fr); gap: 0.25rem; } dd + dt { margin-top: 0.65rem; } .notice { padding: 1rem; } }

  .declaration { display: flex; align-items: start; gap: 0.75rem; padding-top: 0.25rem; }
  .declaration input { margin-top: 0.35rem; accent-color: var(--color-rune); }

  ul { margin: 0; padding-left: 1.25rem; }
  li { padding-block: 0.35rem; }

  details { padding-block: 0.5rem; border-top: 1px solid var(--color-engraving); }
  summary { padding-block: 0.4rem; color: var(--color-parchment); cursor: pointer; }
  details[open] > summary { margin-bottom: 0.75rem; }
  summary:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; font: var(--text-sm)/1.7 var(--font-glyph); margin: 0; }

  h4 { margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-body); }
  .entry { display: grid; align-content: start; gap: 1rem; min-width: 0; padding: 0.25rem 0 0.25rem 1rem; border-left: 2px solid var(--color-engraving); }
  article > section { padding-top: 1.5rem; border-top: 1px solid var(--color-engraving); }
  .source, code { font-family: var(--font-glyph); }
  details > :is(h3, h4, section, pre, ul, dl) { margin-bottom: 1rem; }
  .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
  .actions:empty { display: none; }
  .actions p { flex-basis: 100%; }
  .read-boundary { padding-top: 1.25rem; border-top: 1px solid var(--color-engraving); font-size: var(--text-sm); color: var(--color-ash); }
</style>
