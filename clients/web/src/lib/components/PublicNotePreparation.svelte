<script lang="ts">
  import { onDestroy, tick } from "svelte";
  import { preparationStatusReason, type PreparationState, type PublicNotePreparation } from "$lib/archive/preparation";
  import { notesHref } from "$lib/archive/notes";
  let { state, controller, blocked, recordAvailable }: { state: PreparationState; controller: PublicNotePreparation; blocked: boolean; recordAvailable: boolean } = $props();
  const uid = $props.id();
  const busy = $derived(state.operation !== "idle");
  let reviewHeading: HTMLHeadingElement | undefined;
  let resultHeading: HTMLHeadingElement | undefined;
  const reviewFocus = (element: HTMLHeadingElement) => { reviewHeading = element; return () => { reviewHeading = undefined; }; };
  const resultFocus = (element: HTMLHeadingElement) => { resultHeading = element; return () => { resultHeading = undefined; }; };
  let alive = true;
  onDestroy(() => { alive = false; });
  async function review() {
    controller.review(); const version = controller.contextVersion;
    await tick(); if (alive && controller.contextVersion === version && state.review) reviewHeading?.focus();
  }
  function intent(action: () => Promise<void>, version: number) {
    return () => { if (version === controller.contextVersion) return act(action); };
  }
  async function act(action: () => Promise<void>) {
    const result = action(), version = controller.contextVersion;
    await result; await tick(); if (alive && version === controller.contextVersion) resultHeading?.focus();
  }
</script>

<section class="preparation" aria-labelledby={`${uid}-title`}>
  <h3 id={`${uid}-title`}>Semantic preparation</h3>
  <p>Prepare only this exact promoted public revision. Source text stays server-side. Runtime warmth is prepared separately; this section activates no model and starts no recall or conversation Run.</p>
  {#if state.configuration === "loading"}<p role="status">Loading configured generation metadata…</p>
  {:else if state.generation}
    <details><summary>Configured generation</summary><dl><dt>Generation</dt><dd><code>{state.generation.generation_id}</code></dd><dt>Manifest digest</dt><dd><code>{state.generation.manifest_digest}</code></dd></dl></details>
    <p>Discovery is configuration only: it establishes neither registration, readiness nor complete source coverage.</p>
    <button class="rune-btn" disabled={blocked || busy} onclick={intent(() => controller.register(), state.contextVersion)}>Register configured generation</button>
    <p>This explicit POST uses the exact shared generation above. Exact registration repeats return retained state without embedding and cannot reactivate a retired generation.</p>
  {:else}<p>Configured derivation metadata is unavailable.</p>{/if}
  <button class="rune-btn" disabled={blocked || busy || state.configuration === "loading"} onclick={intent(() => controller.loadGeneration(), state.contextVersion)}>Refresh configured generation metadata</button>
  {#if state.registration}<p>Generation observed: {state.registration.state} · version {state.registration.version} · created {state.registration.created_at}{state.registration.retired_at ? ` · retired ${state.registration.retired_at}` : ""}.</p>{/if}
  {#if state.registrationUnknown}<p>Registration response is unconfirmed. Only an explicit exact registration repeat can recover retained state; no automatic repeat is sent.</p>{/if}
  <button class="rune-btn" disabled={blocked || busy || !recordAvailable || !state.generation} onclick={intent(() => controller.check(), state.contextVersion)}>Check preparation</button>
  <p>Check is a protected metadata-only POST for the current exact source reference. After reload, no historical lifecycle version is guessed.</p>
  <button class="rune-btn" disabled={blocked || busy || !state.eligible} onclick={review}>{state.frozen || state.unknown ? "Review another preparation attempt" : "Review preparation"}</button>
  {#if !state.eligible}<p>A current promoted revision and configured generation are required for a new preparation decision. Configuration does not promise eligibility or available embedding capacity.</p>{/if}
  {#if state.review}
    <section class="notice" aria-labelledby={`${uid}-review`}>
      <h4 id={`${uid}-review`} {@attach reviewFocus} tabindex="-1">Review exact preparation</h4>
      <dl><dt>Profile</dt><dd>{state.review.profile.profile}</dd><dt>Namespace</dt><dd><code>{state.review.profile.namespace_id}</code></dd>
        <dt>Owner</dt><dd>{state.review.profile.owner_subject.identity}</dd><dt>Policy revision</dt><dd>{state.review.profile.policy_revision}</dd>
        <dt>Source</dt><dd>{state.review.sourceKey} · {state.review.sourceRevision}</dd><dt>Record</dt><dd><code>{state.review.request.source.record_id}</code></dd>
        <dt>Revision digest</dt><dd><code>{state.review.request.source.revision_digest}</code></dd><dt>Lifecycle version</dt><dd>{state.review.request.source.lifecycle_version}</dd>
        <dt>Source digest</dt><dd><code>{state.review.sourceDigest}</code></dd><dt>Generation</dt><dd><code>{state.review.request.generation.generation_id}</code></dd>
        <dt>Manifest digest</dt><dd><code>{state.review.request.generation.manifest_digest}</code></dd></dl>
      <p>This may consume one local embedding operation. Another attempt may repeat compute even with an identical body, including after prepared, failed or DB-observed expired status. Only the server can establish a current eligible complete replay with zero embedding. Expiry does not prove earlier work stopped.</p>
      <p>The request has no occurrence UUID or caller attempt-version precondition. Latest status cannot identify which HTTP invocation committed or report all-attempt cost. Earlier lost responses remain unknown.</p>
      <button class="rune-btn" disabled={blocked || busy} onclick={() => { controller.cancelReview(); resultHeading?.focus(); }}>Cancel preparation review</button>
      <button class="rune-btn" disabled={blocked || busy || !state.eligible} onclick={intent(() => controller.prepare(), state.contextVersion)}>Prepare this promoted revision</button>
    </section>
  {/if}
  <section aria-labelledby={`${uid}-result`}>
    <h4 id={`${uid}-result`} {@attach resultFocus} tabindex="-1">Latest preparation metadata</h4>
    {#if busy}<p role="status">Waiting for {state.operation} response. This is HTTP presentation state.</p>{/if}
    {#if state.message}<p role="status">{state.message}</p>{/if}
    {#if state.unknown}<p>Earlier preparation outcome remains unknown. Check cannot attribute that invocation, prove rollback or establish total compute usage. No automatic retry or polling occurs.</p>{/if}
    {#if !state.status}<p>No latest row is currently displayed. Use explicit Check; an absent or failed read does not prove pending work failed.</p>{/if}
    {#if state.frozen}
      <details><summary>Frozen last preparation reference</summary><p>Source {state.frozen.sourceKey} · {state.frozen.sourceRevision}; record <code>{state.frozen.request.source.record_id}</code>; revision digest <code>{state.frozen.request.source.revision_digest}</code>; lifecycle version {state.frozen.request.source.lifecycle_version}; generation <code>{state.frozen.request.generation.generation_id}</code>; manifest <code>{state.frozen.request.generation.manifest_digest}</code>.</p></details>
      <button class="rune-btn" disabled={blocked || busy || !state.generation} onclick={intent(() => controller.check("frozen"), state.contextVersion)}>Check frozen preparation reference</button>
    {/if}
    {#if state.historical}
      <details><summary>Previous historical preparation reference</summary><p>Record <code>{state.historical.request.source.record_id}</code>; revision digest <code>{state.historical.request.source.revision_digest}</code>; lifecycle version {state.historical.request.source.lifecycle_version}; generation <code>{state.historical.request.generation.generation_id}</code>; manifest <code>{state.historical.request.generation.manifest_digest}</code>.</p></details>
      <button class="rune-btn" disabled={blocked || busy || !state.generation} onclick={intent(() => controller.check("historical"), state.contextVersion)}>Check previous historical reference</button>
    {/if}
    {#if state.status}
      <p>{state.statusHistorical ? "Historical source status: metadata only, with no current preparation or source-access permission." : "Status for the current metadata reference; eligibility remains a server decision."}</p>
      <p>Latest retained state: <strong>{state.status.state}</strong>. Server observed {state.status.observed_at}. This observation applies only to the displayed exact status reference.</p>
      <dl><dt>Derivation row</dt><dd><code>{state.status.derivation_id}</code></dd><dt>Row version</dt><dd>{state.status.row_version}</dd><dt>Attempt version</dt><dd>{state.status.attempt_version}</dd>
        <dt>Generation</dt><dd><code>{state.status.generation.generation_id}</code></dd><dt>Manifest digest</dt><dd><code>{state.status.generation.manifest_digest}</code></dd>
        <dt>Exact source record</dt><dd><code>{state.status.source.record_id}</code></dd><dt>Revision digest</dt><dd><code>{state.status.source.revision_digest}</code></dd><dt>Lifecycle version</dt><dd>{state.status.source.lifecycle_version}</dd>
        <dt>Server deadline</dt><dd>{state.status.expires_at ?? "None"}</dd><dt>Completed</dt><dd>{state.status.completed_at ?? "Not reported"}</dd></dl>
      {#if preparationStatusReason(state.status)}<p>{preparationStatusReason(state.status)}</p>{/if}
      <p>Complete describes this exact retained derivation only. It promises neither corpus completeness, future eligibility, warm runtime nor selection by recall. Historical status grants no source access.</p>
    {/if}
  </section>
  <a href={notesHref("recall")}>Open separate public-source recall</a>
</section>

<style>
  section { display: grid; align-content: start; gap: 0.8rem; min-width: 0; }
  .preparation { border-top: 1px solid var(--color-engraving); padding-top: 1rem; }
  .notice { background: var(--color-grimoire); border: 1px solid var(--color-tertiary-edge); border-radius: var(--radius-panel); padding: 1rem; }
  h3, h4, p { margin: 0; }
  dl { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 3fr); gap: 0.4rem 1rem; }
  dd { margin: 0; }
  dd, code, a { overflow-wrap: anywhere; }
  button { align-self: start; justify-self: start; min-height: 2.75rem; max-width: 100%; white-space: normal; }
  :is(a, button, summary):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 36rem) { dl { grid-template-columns: minmax(0, 1fr); } }
</style>
