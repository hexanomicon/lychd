<script lang="ts">
  import { beforeNavigate } from "$app/navigation";
  import { getContext, onMount, onDestroy, tick } from "svelte";
  import { getArchiveProfile, discoverArchiveGeneration, recallArchiveSemanticNotes, inspectArchiveSemanticRecall, resolveArchiveSemanticRecall } from "$lib/api/client";
  import { PublicSourceRecall, initialRecallState, emptyRecallDraft, validateRecallDraft } from "$lib/archive/semantic";
  import { notesHref } from "$lib/archive/notes";
  import { altarNavigationContext, type AltarNavigation } from "$lib/navigation/instruments";

  const navigation = getContext<AltarNavigation | undefined>(altarNavigationContext);
  let recall = $state.raw(initialRecallState());
  const initialDraft = emptyRecallDraft();
  let draft = $state({ ...initialDraft });
  let errors = $state.raw<string[]>([]);
  let discardReview = $state(false);
  let errorHeading: HTMLHeadingElement | undefined;
  let resultHeading: HTMLHeadingElement | undefined;
  let discardHeading: HTMLHeadingElement | undefined;
  const errorFocus = (element: HTMLHeadingElement) => { errorHeading = element; return () => { errorHeading = undefined; }; };
  const resultFocus = (element: HTMLHeadingElement) => { resultHeading = element; return () => { resultHeading = undefined; }; };
  const discardFocus = (element: HTMLHeadingElement) => { discardHeading = element; return () => { discardHeading = undefined; }; };
  let alive = true;
  let focusVersion = 0;
  let authorityEpoch = 0;
  const controller = new PublicSourceRecall({ profile: getArchiveProfile, generation: discoverArchiveGeneration,
    recall: recallArchiveSemanticNotes, inspect: inspectArchiveSemanticRecall, resolve: resolveArchiveSemanticRecall }, (next) => {
    recall = next;
    if (next.authorityEpoch !== authorityEpoch) {
      authorityEpoch = next.authorityEpoch; ++focusVersion; draft = emptyRecallDraft(); errors = []; discardReview = false;
    }
  });
  const busy = $derived(recall.operation !== "idle");
  const hasDraft = $derived(draft.query !== initialDraft.query || draft.minCosine !== initialDraft.minCosine ||
    draft.maxResults !== initialDraft.maxResults || draft.charBudget !== initialDraft.charBudget);
  const transient = $derived(hasDraft || !!recall.frozen || recall.unknown || busy);
  onMount(() => { void controller.load(); });
  onDestroy(() => { alive = false; ++focusVersion; controller.dispose(); });
  beforeNavigate((event) => {
    const target = event.to?.url;
    const stays = !event.willUnload && target?.pathname === "/bridge" && target.searchParams.getAll("notes").length === 1 &&
      target.searchParams.get("notes") === "recall" && !target.searchParams.has("investigation");
    if (!stays && !event.willUnload && transient && !window.confirm("Leave public-source recall? The transient query, frozen request and source texts will be lost. Leaving does not cancel model work or undo a retained selection.")) event.cancel();
  });
  function guardUnload(event: BeforeUnloadEvent) {
    if (transient) { event.preventDefault(); event.returnValue = ""; }
  }
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy || recall.frozen || recall.configuration !== "configured") return;
    errors = validateRecallDraft($state.snapshot(draft));
    const version = ++focusVersion;
    if (errors.length) { await tick(); if (alive && version === focusVersion) errorHeading?.focus(); return; }
    await controller.submit($state.snapshot(draft));
    await tick(); if (alive && version === focusVersion) resultHeading?.focus();
  }
  async function inspect() {
    const version = ++focusVersion;
    await controller.check(); await tick();
    if (alive && version === focusVersion) resultHeading?.focus();
  }
  async function resolve() {
    const version = ++focusVersion;
    await controller.resolve(); await tick();
    if (alive && version === focusVersion) resultHeading?.focus();
  }
  function refresh() { ++focusVersion; errors = []; discardReview = false; void controller.load(); }
  async function reviewDiscard() {
    discardReview = true; const version = ++focusVersion; await tick();
    if (alive && version === focusVersion && discardReview) discardHeading?.focus();
  }
  function discard() { ++focusVersion; controller.discard(); draft = emptyRecallDraft(); errors = []; discardReview = false; }
</script>

<svelte:head><title>Recall public sources — Bridge — LychD</title></svelte:head>
<svelte:window onbeforeunload={guardUnload} />
<section class="public-recall" aria-labelledby="recall-title">
  <header>
    <span class="instrument-kicker">Bridge · public notes</span>
    <h1 id="recall-title">Recall public sources</h1>
    <p>One explicit semantic query and exact current-source load. This view generates no answer and starts no conversation Run.</p>
    <nav aria-label="Public-source recall focus"><a href={navigation?.bridgePath ?? "/bridge"}>Return to conversation</a><a href={notesHref("manage")}>Manage public notes</a><a href={notesHref("new")}>New public note</a></nav>
  </header>
  <aside class="notice" aria-label="Recall prerequisites">
    <p>Already promoted public sources with complete derivations and the exact warm embedding profile are prerequisites. Prepare them separately. This view does not register generations, derive sources or activate runtime capabilities.</p>
    <p>Configuration metadata establishes neither semantic opt-in, active generation registration, eligible sources nor runtime warmth. Similarity locates context; it is not answer confidence or evidence of truth.</p>
  </aside>
  <section aria-labelledby="recall-configuration"><h2 id="recall-configuration">Configured metadata</h2>
    {#if recall.configuration === "loading"}<p role="status">Loading authorized profile and generation metadata…</p>
    {:else if recall.configuration === "configured" && recall.profile && recall.generation}
      <details><summary>Configured profile and generation</summary><dl><dt>Namespace</dt><dd><code>{recall.profile.namespace_id}</code></dd><dt>Owner</dt><dd>{recall.profile.owner_subject.identity}</dd>
        <dt>Policy revision</dt><dd>{recall.profile.policy_revision}</dd><dt>Configured generation</dt><dd><code>{recall.generation.generation_id}</code></dd>
        <dt>Manifest digest</dt><dd><code>{recall.generation.manifest_digest}</code></dd></dl></details>
    {:else}<p role="alert">Configured semantic metadata is unavailable.</p>{/if}
    <button class="rune-btn" disabled={recall.configuration === "loading"} onclick={refresh}>Refresh metadata only</button>
  </section>
  <form onsubmit={submit} novalidate aria-label="Semantic source query">
    <h2>Explicit source query</h2>
    <p>Raw query bytes and numeric bounds freeze with a fresh UUID when submitted. This may perform one local embedding operation. Query and source text stay in this document, outside navigation and storage.</p>
    {#if errors.length}<div role="alert"><h3 {@attach errorFocus} tabindex="-1">Check source query</h3><ul>{#each errors as error (error)}<li>{error}</li>{/each}</ul></div>{/if}
    <fieldset disabled={busy || !!recall.frozen || recall.configuration !== "configured"}>
      <legend>Query and visible limits</legend>
      <label>Exact public query <textarea rows="5" bind:value={draft.query} spellcheck="false"></textarea><span>{[...draft.query].length} / 2,000 code points</span></label>
      <label>Minimum cosine similarity (required, −1 to 1) <input type="text" inputmode="decimal" bind:value={draft.minCosine} autocomplete="off" /></label>
      <label>Maximum results (1–20) <input type="text" inputmode="numeric" bind:value={draft.maxResults} autocomplete="off" /></label>
      <label>Source character budget (1–32,000) <input type="text" inputmode="numeric" bind:value={draft.charBudget} autocomplete="off" /></label>
    </fieldset>
    <button class="rune-btn" type="submit" disabled={busy || !!recall.frozen || recall.configuration !== "configured"}>Query and load exact sources once</button>
  </form>
  <section class="notice" aria-labelledby="recall-result"><h2 id="recall-result" {@attach resultFocus} tabindex="-1">Selection and current sources</h2>
    {#if recall.message}<p role="status">{recall.message}</p>{/if}
    {#if busy}<p role="status">Waiting for {recall.operation}. This is HTTP presentation state. Leaving or aborting a read does not establish server cancellation.</p>{/if}
    {#if recall.unknown}<p>Earlier query outcome remains unknown. A missing receipt or later refusal cannot prove that an in-flight query failed. No automatic retry is available.</p>{/if}
    {#if recall.frozen}
      <dl><dt>Frozen request UUID</dt><dd><code>{recall.frozen.request_id}</code></dd><dt>Namespace</dt><dd>{recall.frozen.namespace_id}</dd>
        <dt>Generation</dt><dd>{recall.frozen.generation.generation_id}</dd><dt>Minimum similarity</dt><dd>{recall.frozen.min_cosine}</dd>
        <dt>Result limit</dt><dd>{recall.frozen.max_results}</dd><dt>Character budget</dt><dd>{recall.frozen.char_budget}</dd></dl>
      <details><summary>Exact frozen query</summary><pre>{recall.frozen.query}</pre></details>
      <button class="rune-btn" disabled={busy || recall.configuration !== "configured"} onclick={inspect}>Check exact request metadata only</button>
    {/if}
    {#if recall.receipt}
      <details><summary>Exact selection receipt</summary><dl><dt>Receipt</dt><dd><code>{recall.receipt.receipt_id}</code></dd><dt>Receipt digest</dt><dd><code>{recall.receipt.receipt_digest}</code></dd>
        </dl></details>
      <p>Selection time (server): {recall.receipt.created_at}. Resolution response received (this browser): {recall.resolvedAt ?? "Not loaded"}.</p>
      <p>Coverage at selection: {recall.receipt.coverage.eligible_notes} eligible / {recall.receipt.coverage.promoted_notes} promoted notes. {recall.receipt.selected.length} selected; {recall.receipt.omitted_for_budget} omitted for whole-source character budget. Coverage is historical, including after Check or replay.</p>
      {#if recall.receipt.coverage.eligible_notes < recall.receipt.coverage.promoted_notes}<p>Partial derivation coverage: some promoted sources were ineligible for this exact generation.</p>{/if}
      {#if !recall.receipt.selected.length}<p>No source met this selection within its threshold and budgets. This does not establish an answer or a complete corpus.</p>{/if}
      {#if recall.execution}<p>This query response reported {recall.execution.tokens} embedding tokens for this caller. Retained selection usage is not an all-attempt cost ledger.</p>{/if}
      <button class="rune-btn" disabled={busy || recall.configuration !== "configured"} onclick={resolve}>Load exact current sources</button>
    {/if}
    {#if recall.projection}
      <ol aria-label="Currently resolved sources">
        {#each recall.projection.items as item (item.selection.reference.record_id)}
          <li><article aria-label={`Source ${item.selection.source_key}`}><h3>{item.selection.source_key} · {item.selection.source_revision}</h3>
            <p>Record <code>{item.selection.reference.record_id}</code> · lifecycle version {item.selection.reference.lifecycle_version} · similarity {item.selection.score}</p>
            <details><summary>Exact source digests</summary><p>Revision digest <code>{item.selection.reference.revision_digest}</code> · source digest <code>{item.selection.source_digest}</code></p></details>
            <pre>{item.text}</pre>
          </article></li>
        {/each}
      </ol>
    {/if}
    {#if recall.frozen || hasDraft}<button class="rune-btn" disabled={busy} onclick={reviewDiscard}>Review clearing query and sources</button>{/if}
    {#if discardReview}<section aria-label="Clear recall review"><h3 {@attach discardFocus} tabindex="-1">Clear transient query and sources?</h3>
      <p>Clearing loses the frozen body used for exact Check. It does not cancel model work or undo a retained selection. A later submission is a new explicit query with a new UUID.</p>
      <button class="rune-btn" onclick={() => { discardReview = false; resultHeading?.focus(); }}>Keep query</button><button class="rune-btn" disabled={busy} onclick={discard}>Confirm clear</button>
    </section>{/if}
  </section>
</section>

<style>
  .public-recall { width: min(100%, 58rem); margin: 0 auto; padding: 1.25rem; display: grid; align-content: start; gap: 1.25rem; min-width: 0; }
  header, section, form, fieldset, article { display: grid; align-content: start; gap: 0.8rem; min-width: 0; }
  h1, h2, h3, p { margin: 0; }
  nav { display: flex; flex-wrap: wrap; gap: 1rem; }
  fieldset, article, .notice { border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); padding: 1rem; }
  aside.notice { background: var(--color-grimoire); border-color: var(--color-tertiary-edge); }
  label span { color: var(--color-ash); font-size: var(--text-sm); }
  legend { padding: 0 0.35rem; }
  label { display: grid; gap: 0.4rem; }
  input, textarea { width: 100%; min-width: 0; min-height: 2.75rem; padding: 0.65rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); background: var(--color-void); }
  textarea { resize: vertical; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; font-family: var(--font-glyph); margin: 0; }
  dl { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 3fr); gap: 0.4rem 1rem; }
  dd { margin: 0; }
  dd, code, a, li { overflow-wrap: anywhere; }
  ol { display: grid; gap: 1rem; padding-left: 1.5rem; margin: 0; }
  button { align-self: start; justify-self: start; min-height: 2.75rem; max-width: 100%; white-space: normal; }
  :is(a, button, input, textarea, summary):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 36rem) { .public-recall { padding: 0.75rem; } dl { grid-template-columns: minmax(0, 1fr); } }
</style>
