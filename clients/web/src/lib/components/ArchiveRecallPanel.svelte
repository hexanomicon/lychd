<script lang="ts">
  import { onDestroy } from "svelte";
  import { ApiError, getArchiveRunRecall } from "$lib/api/client";
  import type { ArchiveRunRecall } from "$lib/api/models";

  let { runId }: { runId: string } = $props();
  const uid = $props.id();
  let result = $state.raw<ArchiveRunRecall | null>(null);
  let readAt = $state("");
  let error = $state("");
  let busy = $state(false);
  let controller: AbortController | undefined;
  let version = 0;
  let alive = true;
  // Orb keys this child by the supplied Run, independently of its snapshot or renderer.
  let visible = $derived(result?.run_id === runId ? result : null);

  onDestroy(() => {
    alive = false;
    version++;
    controller?.abort();
    result = null;
  });

  function failure(cause: unknown): string {
    if (cause instanceof ApiError) {
      if (cause.status === 403) return "Denied: current Archive metadata authority refused this read.";
      if (cause.status === 404) return "Unavailable: Archive is unconfigured or this Run is unavailable.";
      if (cause.status === 409) return "Refused: the current Archive binding or retained selection cannot be inspected.";
    }
    return "Failed: Archive selection could not be read. Retry explicitly.";
  }

  async function read() {
    if (busy || !alive) return;
    const id = runId;
    const attempt = ++version;
    const owned = new AbortController();
    controller?.abort();
    controller = owned;
    result = null;
    readAt = "";
    error = "";
    busy = true;
    const current = () => alive && attempt === version && id === runId && !owned.signal.aborted;
    try {
      const next = await getArchiveRunRecall(id, owned.signal);
      if (!current()) return;
      if (next.run_id !== id || next.capture !== "matching_retained_request" ||
        !["recorded", "not_recorded", "not_applicable"].includes(next.status) ||
        (next.status === "recorded" ? !next.receipt || next.receipt.run_id !== id : next.receipt !== null) ||
        (next.receipt && new Set(next.receipt.selected.map((item) => item.reference.record_id)).size !== next.receipt.selected.length)) {
        error = "Invalid response: Archive returned inconsistent selection identity for this Run.";
        return;
      }
      result = next;
      readAt = new Date().toISOString();
    } catch (cause) {
      if (current()) error = failure(cause);
    } finally {
      if (current()) {
        busy = false;
        controller = undefined;
      }
    }
  }
</script>

<section class="archive-recall" aria-labelledby={`${uid}-title`} aria-busy={busy}>
  <h2 id={`${uid}-title`}>Archive selection</h2>
  <p class="run">Exact Run · {runId}</p>
  <p>A separate read under current Archive metadata authority.</p>
  <button type="button" onclick={read} disabled={busy}>
    {busy ? "Reading Archive selection…" : error ? "Retry Archive selection" : visible ? "Refresh Archive selection" : "Read Archive selection"}
  </button>
  {#if error}
    <p role="alert">{error}</p>
  {:else if visible}
    <p class="status" role="status">
      {visible.status === "recorded" ? "Recorded selection" : visible.status === "not_recorded" ? "Not recorded: no matching retained request was found at this read." : "Not applicable: this Run's pinned Pattern does not support this Archive selection."}
    </p>
    <p>Read at <time datetime={readAt}>{readAt}</time>.</p>
    {#if visible.receipt}
      {@const receipt = visible.receipt}
      <p>Capture: matching retained request. A caller can preseed this request before Run execution.
        Workflow consumption and provider transmission are unproved.</p>
      <p>This is bounded selected-note evidence, not complete corpus, Context or token accounting.
        It reconstructs no floor, history or prompt and establishes no current source eligibility.</p>
      <dl>
        <dt>Retained receipt created at</dt><dd><time datetime={receipt.created_at}>{receipt.created_at}</time></dd>
        <dt>Selected notes</dt><dd>{receipt.selected.length}</dd>
        <dt>Result bound (max_results)</dt><dd>{receipt.max_results}</dd>
        <dt>Selected-note character bound (char_budget)</dt><dd>{receipt.char_budget}</dd>
        <dt>Omitted for budget (omitted_for_budget)</dt><dd>{receipt.omitted_for_budget} within this bounded selection</dd>
        <dt>Minimum score</dt><dd>{receipt.min_score}</dd>
      </dl>
      {#if receipt.selected.length === 0}
        <p>Successful empty selection: zero notes selected. This is a recorded receipt, not missing evidence.</p>
      {:else}
        <ol aria-label="Selected source revisions in receipt order">
          {#each receipt.selected as item (item.reference.record_id)}
            <li>
              <h3>{item.source_key}</h3>
              <dl>
                <dt>Source revision</dt><dd>{item.source_revision}</dd>
                <dt>Record</dt><dd>{item.reference.record_id}</dd>
                <dt>Recorded lifecycle version</dt><dd>{item.reference.lifecycle_version}</dd>
                <dt>Score</dt><dd>{item.score}</dd>
                <dt>Projected characters</dt><dd>{item.projected_chars}</dd>
              </dl>
              <details>
                <summary>Source digests</summary>
                <dl>
                  <dt>Source digest</dt><dd>{item.source_digest}</dd>
                  <dt>Revision digest</dt><dd>{item.reference.revision_digest}</dd>
                  <dt>Projection digest</dt><dd>{item.projection_digest}</dd>
                </dl>
              </details>
            </li>
          {/each}
        </ol>
      {/if}
      <details>
        <summary>Receipt identity and policy</summary>
        <dl>
          <dt>Receipt</dt><dd>{receipt.receipt_id}</dd>
          <dt>Request</dt><dd>{receipt.request_id}</dd>
          <dt>Namespace</dt><dd>{receipt.namespace_id}</dd>
          <dt>Subject</dt><dd>{receipt.subject.identity}</dd>
          <dt>Purpose</dt><dd>{receipt.purpose}</dd>
          <dt>Profile</dt><dd>{receipt.profile}</dd>
          <dt>Policy revision</dt><dd>{receipt.policy_revision}</dd>
          <dt>Retrieval policy</dt><dd>{receipt.retrieval_policy}</dd>
          <dt>Receipt digest</dt><dd>{receipt.receipt_digest}</dd>
          <dt>Request digest</dt><dd>{receipt.request_digest}</dd>
          <dt>Query digest</dt><dd>{receipt.query_digest}</dd>
        </dl>
      </details>
    {/if}
  {:else if !busy}
    <p>Not read. Use the explicit read to inspect retained selection metadata.</p>
  {/if}
</section>

<style>
  .archive-recall { min-width: 0; padding: 1.25rem 0; border-top: 1px solid var(--color-engraving); color: var(--color-parchment); overflow-wrap: anywhere; font-size: var(--text-sm); line-height: 1.65; }
  h2 { margin: 0; color: var(--color-bone); font: 600 var(--text-lg)/1.4 var(--font-body); }
  h3 { margin: 0; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-body); }
  p, dl, ol, details { margin-top: 1rem; }
  p, dt { color: var(--color-parchment); }
  .run, dd { overflow-wrap: anywhere; }
  .run { color: var(--color-ash); font: var(--text-sm)/1.6 var(--font-glyph); }
  dl { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0.3rem; }
  dt { font-size: var(--text-sm); color: var(--color-ash); }
  dd + dt { margin-top: 0.65rem; }
  dd { margin: 0; min-width: 0; }
  ol { padding-left: 1.4rem; }
  li { padding-top: 1rem; border-top: 1px solid var(--color-engraving); }
  li + li { margin-top: 1.5rem; }
  button { margin-top: 1rem; min-height: 2.75rem; max-width: 100%; padding: 0.65rem 1rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); background: var(--color-obsidian-2); color: var(--color-bone); white-space: normal; line-height: 1.4; cursor: pointer; }
  button:hover { border-color: var(--color-rune); }
  button:disabled { opacity: 0.5; cursor: default; }
  details { border-top: 1px solid var(--color-engraving); padding-top: 0.5rem; }
  summary { cursor: pointer; padding-block: 0.5rem; color: var(--color-parchment); }
  button:focus-visible, summary:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  [role="alert"] { color: var(--color-ember); }
  .status { color: var(--color-bone); font-weight: 600; }
</style>
