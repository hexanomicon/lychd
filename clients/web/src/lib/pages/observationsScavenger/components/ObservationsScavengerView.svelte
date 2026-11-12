<script lang="ts">
  import { afterNavigate, beforeNavigate } from "$app/navigation";
  import { onDestroy, tick } from "svelte";
  import { SvelteMap } from "svelte/reactivity";
  import { cancelBridgeRun, deleteMarketObservation, filterMarketObservation, getMarketObservationConsent, getScavengerState,
    readMarketObservation, submitMarketObservation } from "$lib/api/client";
  import type { ConsentDecision } from "$lib/bridge/workspace.svelte";
  import { emptyObservationDraft, prepareObservation } from "$lib/pages/observationsScavenger/state/draft";
  import { initialObservationState, observationId, ObservationWorkspace } from "$lib/pages/observationsScavenger/state/observation";
  import ConsentCard from "$lib/components/shared/ConsentCard.svelte";
  import PageHeader from "$lib/components/shared/PageHeader.svelte";

  let { admissionId = null }: { admissionId?: string | null } = $props();
  let ui = $state.raw(initialObservationState);
  let draft = $state(emptyObservationDraft());
  let errors = $state<string[]>([]);
  let filter = $state("");
  let showWhole = $state(true);
  let confirmDelete = $state(false);
  let confirmCancel = $state(false);
  let errorHeading: HTMLHeadingElement | undefined;
  let nextPreference = 1;
  let filterSource: string | null = null;
  const decisions = new SvelteMap<string, ConsentDecision>();
  const workspace = new ObservationWorkspace({ current: getScavengerState, read: readMarketObservation,
    submit: submitMarketObservation, consent: getMarketObservationConsent, filter: filterMarketObservation,
    delete: deleteMarketObservation, cancel: async (runId) => {
      const result = await cancelBridgeRun(runId);
      if (result.run_id !== runId) throw new Error("Cancellation identity mismatch");
    } }, (next) => {
    ui = next;
    if (next.document && filterSource !== next.document.admission_id) {
      filterSource = next.document.admission_id;
      filter = next.view?.filter.query ?? next.document.initial_filter?.query ?? "";
      showWhole = true;
    }
    if (next.accessRefused) { draft = emptyObservationDraft(); filter = ""; filterSource = null; decisions.clear(); }
  });
  const busy = $derived(ui.phase !== "idle" || ui.mutationPending);
  const document = $derived(ui.document);
  const observation = $derived(document?.observation);
  const view = $derived(ui.view);
  const rows = $derived(observation?.items.filter((item) => showWhole || view?.visible_ordinals.includes(item.ordinal)) ?? []);
  const hasDraft = $derived(Boolean(draft.need || draft.inventory || draft.criteria || draft.preferences.length ||
    draft.budget || draft.region || draft.deadline || draft.evidence || draft.delivery || draft.filter || draft.subject));
  const unresolvedDecision = $derived([...decisions.values()].some((decision) => !decision.settled));
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  afterNavigate(() => {
    const id = observationId(admissionId);
    confirmDelete = false;
    confirmCancel = false;
    if (admissionId !== null && id === null) { workspace.clearSelection(); errors = ["The observation selection must be one UUID."]; return; }
    errors = [];
    void workspace.open(id);
  });
  beforeNavigate((navigation) => {
    if (!navigation.willUnload && (hasDraft || workspace.needsUnloadWarning || unresolvedDecision) &&
        !window.confirm("Leave Scavenger? Private drafts and identical replay bodies may be lost. Keep any unconfirmed UUID. Leaving does not cancel server work.")) navigation.cancel();
  });
  onDestroy(() => { workspace.dispose(); decisions.clear(); });

  function guardUnload(event: BeforeUnloadEvent) {
    if (!hasDraft && !workspace.needsUnloadWarning && !unresolvedDecision) return;
    event.preventDefault(); event.returnValue = "";
  }
  function captureErrorHeading(node: HTMLHeadingElement) {
    errorHeading = node;
    return () => { if (errorHeading === node) errorHeading = undefined; };
  }
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy || ui.unconfirmedId) return;
    const prepared = prepareObservation($state.snapshot(draft), crypto.randomUUID());
    errors = prepared.errors;
    if (!prepared.request) { await tick(); errorHeading?.focus(); return; }
    await workspace.submit(prepared.request);
    if (ui.document?.admission_id === prepared.request.request_id) draft = emptyObservationDraft();
  }
  async function applyFilter(event: SubmitEvent) {
    event.preventDefault();
    if (new TextEncoder().encode(filter).length > 256) { errors = ["The literal filter permits 256 UTF-8 bytes."]; return; }
    errors = [];
    await workspace.filter(filter);
    showWhole = false;
  }
  async function remove() {
    if (!confirmDelete) return;
    await workspace.delete();
    confirmDelete = false;
    if (ui.deleted) { draft = emptyObservationDraft(); filter = ""; decisions.clear(); }
  }
</script>

<svelte:head><title>Scavenger market — LychD</title></svelte:head>
<svelte:window onbeforeunload={guardUnload} />
<section class="scavenger" aria-labelledby="market-title" aria-busy={busy}>
  <PageHeader
    title="Scavenger market"
    kicker="Altar · application"
    description="One bounded Bazoš PC feed observation. Keep the whole field, then inspect it with a literal title/link filter."
    titleId="market-title"
  >
    <p class="limits">Title and link only · no seller judgment, price assessment, ranking, learning or automatic continuation.</p>
    {#snippet actions()}
      <button type="button" class="rune-btn" disabled={busy} onclick={() => { confirmDelete = false; void workspace.refresh(); }}>Refresh retained state</button>
      {#if ui.selectedId}<a class="heading-link" href={`/scavenger?observation=${encodeURIComponent(ui.selectedId)}`}>Link to this UUID</a>{/if}
    {/snippet}
  </PageHeader>
  {#if ui.phase === "reading"}<p role="status">Reading current protected state. No source acquisition was requested.</p>{/if}
  {#if ui.phase === "submitting"}<p role="status">Submitting once. No automatic retry will be sent.</p>{/if}
  {#if ui.configured === false}<p role="status">Scavenger is not configured. This page cannot admit an observation.</p>
  {:else if ui.configured === null && !busy}<p role="status">Configuration or current access is unknown. Refresh to check.</p>{/if}
  {#if ui.message}<p class="notice" role="status">{ui.message}</p>{/if}
  {#if ui.unconfirmedCancel}
    <aside class="notice" aria-label="Unconfirmed cancellation">
      <p>Cancellation of Run <code>{ui.unconfirmedCancel.runId}</code> remains unconfirmed. Leaving does not resolve it.</p>
      <button type="button" class="rune-btn" disabled={busy} onclick={() => workspace.open(ui.unconfirmedCancel!.admissionId)}>Check cancellation outcome</button>
    </aside>
  {/if}
  {#if ui.unconfirmedDeletion}
    <aside class="notice" aria-label="Unconfirmed deletion">
      <p>Deletion of <code>{ui.unconfirmedDeletion.admissionId}</code> remains unconfirmed. Leaving does not resolve it.</p>
      <button type="button" class="rune-btn" disabled={busy} onclick={() => workspace.open(ui.unconfirmedDeletion!.admissionId)}>Check deletion outcome</button>
    </aside>
  {/if}
  {#if ui.unconfirmedId}
    <aside class="notice" aria-label="Unconfirmed submission">
      <h2>Admission unconfirmed</h2>
      <p>Keep <code>{ui.unconfirmedId}</code>. A failed Check, including 404, does not prove refusal.</p>
      <button type="button" class="rune-btn" disabled={busy} onclick={() => workspace.open(ui.unconfirmedId)}>Check this request</button>
      {#if ui.canReplay}<button type="button" class="rune-btn" disabled={busy} onclick={() => workspace.replay()}>Replay identical request</button>
      {:else}<p>The original body is unavailable. Reload cannot reconstruct it from the UUID.</p>{/if}
    </aside>
  {/if}
  {#if errors.length}
    <section class="notice" role="alert" aria-labelledby="market-errors">
      <h2 id="market-errors" tabindex="-1" {@attach captureErrorHeading}>Check the supplied facts</h2>
      <ul>{#each errors as error (error)}<li>{error}</li>{/each}</ul>
    </section>
  {/if}
  {#if document}
    <section class="retained-observation" aria-labelledby="field-state-title">
      <h2 id="field-state-title">Retained observation · {document.status}</h2>
      <p class="run-state">Run: {document.run_status ?? "not bound"} · acquisition: {document.acquisition_status ?? "no attempt recorded"} · disposition: {document.terminal_disposition}.
        {#if document.run_id}<a href={`/orb/${encodeURIComponent(document.run_id)}`}>Inspect Run evidence</a>{/if}</p>
      {#if document.status === "awaiting_consent"}<p>The Run is waiting for your native acquisition review. Refresh to load its current outcome.</p>
      {:else if document.status === "unknown"}<p class="notice">Acquisition outcome is unknown. Deletion and a replacement fetch cannot settle this reservation. No automatic refetch is allowed.</p>
      {:else if document.status === "unavailable"}<p>No complete consumer field is available. Run completion or a Scout receipt alone does not prove a saved observation.</p>
      {:else if document.status === "deleted"}<p>Deleted, not an empty market. This UUID cannot recreate its application payload.</p>
      {:else if document.status === "pending" || document.status === "reserved"}<p>Work is pending. Refresh explicitly. Deletion does not cancel this Run.</p>{/if}
      {#if document.seed}
        <details><summary>Complete retained campaign facts</summary><p>Admission <code>{document.admission_id}</code></p><pre>{document.seed_document ?? "Exact campaign document unavailable; refresh current state."}</pre></details>
      {/if}
    </section>
  {/if}
  {#if ui.consent && document?.run_id}
    <ConsentCard consent={ui.consent} sessionId={`scavenger:${document.admission_id}`} {decisions}
      onauthority={() => workspace.invalidate()}
      ondecided={(_consent, _pending, version) => { if (workspace.isCurrent(version)) void workspace.refresh(); }}
      onrefresh={() => workspace.refresh()} />
  {/if}
  {#if observation && document && view}
    <section class="whole-field" aria-labelledby="whole-field-title">
      <h2 id="whole-field-title">Whole field</h2>
      <dl class="identity">
        <dt>Source</dt><dd><code>{observation.contacted_url}</code></dd>
        <dt>Acquired</dt><dd><time datetime={observation.acquired_at}>{observation.acquired_at}</time></dd>
        <dt>Coverage</dt><dd>This bounded feed response only; this response is not the entire market. {observation.omitted_elements} omitted elements.</dd>
      </dl>
      <details><summary>Filter this field locally</summary>
        <form onsubmit={applyFilter} aria-label="Local field filter" class="filter">
          <label>Literal title/link substring<input bind:value={filter} maxlength="256" disabled={busy} /></label>
          <button class="rune-btn" disabled={busy}>Apply local filter</button>
          <button type="button" class="rune-btn" disabled={busy} onclick={() => { showWhole = true; }}>Show entire field</button>
        </form>
      </details>
      <p>Filter <code>{view.filter.query || "(empty)"}</code> · {view.visible_count} matching / {view.total_count} total · {view.unmatched_count} unmatched · {view.duplicate_count} duplicates · {view.missing_title_count} missing titles.</p>
      <p>{showWhole ? "Showing the entire field in source order." : "Showing the server's local filtered view."} Filtering changes no retained item and performs no acquisition.</p>
      {#if observation.items.length === 0}<p role="status">The complete bounded response contains no items. This is an empty field.</p>
      {:else if rows.length === 0}<p role="status">No local matches. The complete field still contains {view.total_count} items.</p>{/if}
      <!-- Scrollable inert text needs native keyboard focus. -->
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div class="field-table" role="region" aria-label="Observation items" tabindex="0"><table>
        <caption>Original title/link occurrences; locators are inert text and are never previewed or fetched by this page.</caption>
        <thead><tr><th scope="col">Occurrence</th><th scope="col">Original title</th><th scope="col">Original link</th><th scope="col">Duplicate</th></tr></thead>
        <tbody>{#each rows as item (`${observation.observation_id}:${item.ordinal}`)}
          <tr><th scope="row">{item.ordinal + 1}</th><td>{item.title ?? "Title missing"}</td><td><code>{item.link}</code></td><td>{item.duplicate_of === null ? "First occurrence" : `Same link as occurrence ${item.duplicate_of + 1}`}</td></tr>
        {/each}</tbody>
      </table></div>
      <p class="limits">Price, condition, seller, eligibility and source freshness: not assessed.</p>
      <details><summary>Acquisition attribution</summary><dl class="identity">
        <dt>Requested source</dt><dd><code>{observation.requested_url}</code></dd>
        <dt>Coverage profile</dt><dd>{observation.coverage}</dd>
        <dt>Field digest</dt><dd><code>{view.field_digest}</code></dd>
        <dt>Literal filter</dt><dd>{view.filter.revision}, Unicode {view.casefold_unicode_version}</dd>
        <dt>Profile / extractor</dt><dd>{observation.profile} / {observation.extractor}</dd>
        <dt>Scout receipt</dt><dd><code>{observation.scout_receipt_id}</code></dd>
        <dt>Source digest</dt><dd><code>{observation.source_digest}</code></dd>
        <dt>Record digest</dt><dd><code>{observation.record_digest}</code></dd>
        <dt>Observation digest</dt><dd><code>{document.observation_digest}</code></dd>
      </dl></details>
    </section>
  {/if}
  {#if document?.run_id && document.run_status && !["done", "failed", "cancelled"].includes(document.run_status)}
    <section class="cancel-work" aria-labelledby="cancel-title">
      <h2 id="cancel-title">Cancel pending work</h2>
      <p>The Run owner stops work and withdraws pending consent. Cancellation does not delete retained data or settle an unknown source outcome.</p>
      <label class="confirm"><input type="checkbox" bind:checked={confirmCancel} disabled={busy} /> I intend to cancel this Run.</label>
      <button type="button" class="rune-btn rune-btn--ash" disabled={busy || !confirmCancel || Boolean(ui.unconfirmedId || ui.unconfirmedDeletion)}
        onclick={async () => { await workspace.cancel(); confirmCancel = false; }}>Cancel this Run</button>
    </section>
  {/if}
  {#if document && document.status !== "deleted"}
    <section class="deletion" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete retained application payload</h2>
      <p>Deletion removes the campaign seed and complete item field. Immutable execution/contact receipts and backups are outside this acknowledgement. It does not refund allowance or cancel work.</p>
      {#if document.terminal_disposition !== "terminal"}<p>Unavailable while disposition is {document.terminal_disposition}. Pending cancellation belongs to the Run owner; unknown custody requires reconciliation.</p>
      {:else}
        <label class="confirm"><input type="checkbox" bind:checked={confirmDelete} disabled={busy} /> I intend to delete this exact retained payload.</label>
        <button type="button" class="rune-btn rune-btn--ash" disabled={busy || !confirmDelete || Boolean(ui.unconfirmedId || ui.unconfirmedCancel) ||
          Boolean(ui.unconfirmedDeletion && ui.unconfirmedDeletion.admissionId !== document.admission_id)} onclick={remove}>Delete this payload</button>
      {/if}
    </section>
  {/if}
  {#if ui.deleted || document?.status === "deleted"}
    <button type="button" class="rune-btn" disabled={busy || Boolean(ui.unconfirmedId || ui.unconfirmedDeletion || ui.unconfirmedCancel)} onclick={() => workspace.open(null)}>Prepare a new observation</button>
  {/if}
  {#if ui.slotAvailable && ui.configured === true && !document && !ui.deleted && !ui.unconfirmedId && !ui.unconfirmedDeletion && !ui.unconfirmedCancel && !busy}
    <form class="observation-form" onsubmit={submit} aria-label="New feed observation" novalidate>
      <h2>Prepare a new observation</h2>
      <p>Private drafts stay in this document. The server retains admitted facts until explicit deletion. Every field below is supplied by you; empty lists and unknown budget/region remain explicit.</p>
      <fieldset class="campaign-facts"><legend>Campaign facts</legend>
        <label>Subject profile<select bind:value={draft.subject} required><option value="">Choose…</option><option value="Technology@1">Technology</option><option value="Bazaar@1">Bazaar</option></select></label>
        <label>Need<textarea bind:value={draft.need} required rows="3"></textarea></label>
        <label>Inventory<textarea bind:value={draft.inventory} rows="2" aria-describedby="market-lines"></textarea></label>
        <label>Hard criteria<textarea bind:value={draft.criteria} rows="2" aria-describedby="market-lines"></textarea></label>
        <p id="market-lines">One nonempty entry per line, at most 16. Empty fields mean empty arrays; blank lines are ignored.</p>
        <fieldset class="soft-preferences"><legend>Soft preferences · not ranked by this profile</legend>
          {#each draft.preferences as preference (preference.key)}
            <div class="preference"><label>Criterion<input bind:value={preference.criterion} /></label><label>Weight<input inputmode="numeric" bind:value={preference.weight} /></label>
              <button type="button" class="rune-btn" aria-label={`Remove preference ${preference.key}`} onclick={() => { draft.preferences = draft.preferences.filter((p) => p.key !== preference.key); }}>Remove</button></div>
          {/each}
          <button type="button" class="rune-btn" disabled={draft.preferences.length >= 16} onclick={() => { draft.preferences.push({ key: String(nextPreference++), criterion: "", weight: "" }); }}>Add preference</button>
          {#if !draft.preferences.length}<p>Preferences: empty array.</p>{/if}
        </fieldset>
        <div class="form-grid"><label>Budget in EUR · empty = not assessed<input inputmode="decimal" bind:value={draft.budget} /></label>
          <label>Region · empty = not assessed<input bind:value={draft.region} /></label>
          <label>Deadline · {timezone}<input type="datetime-local" bind:value={draft.deadline} required /></label></div>
        <label>Evidence standard<textarea bind:value={draft.evidence} required rows="2"></textarea></label>
        <label>Travel / delivery facts<textarea bind:value={draft.delivery} required rows="2"></textarea></label>
        <label>Initial literal title/link filter · optional<input bind:value={draft.filter} maxlength="256" /></label>
      </fieldset>
      <dl class="identity"><dt>Source</dt><dd><code>https://www.bazos.sk/rss.php?rub=pc</code> · fixed bounded public RSS profile</dd>
        <dt>Policy</dt><dd>Watch · admitted public feed only · no disclosure · no learning · no model</dd>
        <dt>Limits</dt><dd>16 KiB complete seed · at most 100 extracted items · acquisition still requires the native consent review</dd></dl>
      <button class="rune-btn rune-btn--frost">Submit new observation for review</button>
    </form>
  {/if}
</section>

<style>
  .scavenger { width: min(100%, 88rem); margin-inline: auto; padding: clamp(1.25rem, 3vw, 2.5rem); display: grid; align-content: start; gap: 1.75rem; min-width: 0; }
  .limits { margin-top: .4rem; font-size: var(--text-xs); }
  .limits, caption { color: var(--color-ash); }
  h2 { font-size: 1.25rem; font-weight: 550; margin-block: .25rem .75rem; }
  p { max-width: 80ch; line-height: 1.65; margin-block: .5rem; }
  .filter, .preference { display: flex; flex-wrap: wrap; align-items: end; gap: .75rem; }
  .heading-link { padding-block: .35rem; font-size: var(--text-sm); }
  .notice { padding: 1.25rem; border: 1px solid var(--color-control-border); border-inline-start: 3px solid var(--color-heat); background: var(--color-obsidian); }
  .retained-observation { padding: 1.25rem 1.5rem; border-inline-start: 2px solid var(--color-engraving); background: var(--color-obsidian); }
  .retained-observation h2 { font-size: 1rem; }
  .whole-field { padding-block: .5rem; }
  .whole-field > .identity { padding: 1rem 0; border-bottom: 1px solid var(--color-engraving); }
  .cancel-work, .deletion { border-top: 1px solid var(--color-engraving); padding-top: 1.5rem; margin-top: .5rem; }
  .cancel-work h2, .deletion h2 { font-size: 1rem; }
  .cancel-work p, .deletion p { color: var(--color-parchment); font-size: var(--text-sm); }
  label { display: grid; gap: .5rem; margin-block: .5rem; min-width: 0; font-size: var(--text-sm); }
  .confirm { display: flex; align-items: center; gap: .75rem; }
  input:not([type="checkbox"]), textarea, select { width: 100%; min-width: 0; min-height: 2.75rem; padding: .75rem; color: var(--color-bone); background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); font: inherit; font-size: 1rem; }
  input[type="checkbox"] { width: 1.125rem; height: 1.125rem; flex-shrink: 0; accent-color: var(--color-rune); }
  button { align-self: start; justify-self: start; min-height: 2.75rem; max-width: 100%; white-space: normal; }
  .rune-btn { color: var(--color-parchment); background: var(--color-obsidian-2); border-color: var(--color-control-border); font-size: var(--text-sm); }
  .rune-btn--frost { background: var(--color-bone); color: var(--color-void); border-color: var(--color-bone); font-weight: 600; }
  .rune-btn--ash { color: var(--color-parchment); background: transparent; }
  button:disabled { opacity: .5; }
  textarea { resize: vertical; line-height: 1.65; }
  .observation-form { display: grid; gap: 1.25rem; max-width: 72rem; padding-top: 1rem; }
  .observation-form > p { margin-top: -.5rem; color: var(--color-parchment); }
  fieldset { min-width: 0; border: 0; border-top: 1px solid var(--color-engraving); padding: 1.25rem 0 0; margin: .5rem 0 0; }
  legend { padding: 0 .75rem 0 0; color: var(--color-bone); font-size: var(--text-sm); font-weight: 550; }
  .campaign-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem 1.5rem; }
  .campaign-facts > p, .campaign-facts > fieldset, .campaign-facts > .form-grid, .campaign-facts > label:nth-of-type(2), .campaign-facts > label:last-child { grid-column: 1 / -1; }
  .campaign-facts > p { margin: 0; color: var(--color-ash); font-size: var(--text-sm); }
  .soft-preferences { padding: 1.25rem; background: var(--color-tertiary); border: 0; margin-block: .75rem; }
  .soft-preferences legend { padding-inline: .5rem; }
  .soft-preferences > p { color: var(--color-ash); font-size: var(--text-sm); }
  .campaign-facts > label:first-of-type { grid-column: 1 / -1; max-width: 24rem; }
  .preference label:first-child { flex: 1 1 16rem; }
  .preference label:nth-child(2) { flex: 0 1 8rem; }
  .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: 1rem; }
  .identity { display: grid; grid-template-columns: minmax(8rem, 1fr) minmax(0, 4fr); gap: .65rem 1rem; font-size: var(--text-sm); line-height: 1.6; }
  dt { color: var(--color-ash); }
  dd { margin: 0; min-width: 0; }
  code, td, dd, pre { overflow-wrap: anywhere; }
  pre { white-space: pre-wrap; padding: 1rem; background: var(--color-obsidian); }
  details { margin-block: .75rem; }
  summary { cursor: pointer; min-height: 2.75rem; padding-block: .6rem; color: var(--color-parchment); font-size: var(--text-sm); }
  .filter { padding: 1rem 0; }
  .filter label { flex: 1 1 20rem; }
  .field-table { overflow-x: auto; margin-top: 1.25rem; border-block: 1px solid var(--color-engraving); }
  table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: var(--text-sm); }
  caption { text-align: start; padding-block: 1rem; line-height: 1.6; }
  td, th { padding: 1rem; text-align: start; vertical-align: top; border-block-end: 1px solid var(--color-engraving); }
  thead { background: var(--color-obsidian); }
  thead th { color: var(--color-ash); font-weight: 500; }
  tbody th { color: var(--color-ash); font: var(--text-sm)/1.6 var(--font-glyph); }
  tbody td { line-height: 1.65; }
  th:first-child { width: 7rem; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @container work-area (max-width: 48rem) {
    .campaign-facts { grid-template-columns: minmax(0, 1fr); }
    .identity { grid-template-columns: minmax(0, 1fr); }
    .identity dd { margin-block-end: .5rem; }
    table { min-width: 42rem; }
  }
  @media (max-width: 40rem) {
    .campaign-facts, .identity { grid-template-columns: minmax(0, 1fr); }
    .identity dd { margin-block-end: .5rem; }
    table { min-width: 42rem; }
  }
  @container work-area (max-width: 35rem) { .scavenger { padding: 1rem; } .retained-observation, .soft-preferences { padding: 1rem; } }
  @media (forced-colors: active) { .field-table, fieldset, .notice, .retained-observation { border-color: CanvasText; } }
</style>
