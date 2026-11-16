<script lang="ts">
  import { afterNavigate, beforeNavigate } from "$app/navigation";
  import { getContext, onMount, onDestroy, tick } from "svelte";
  import { getArchiveProfile, getArchiveBridgeDefault, listArchiveNotes, getArchiveNote, admitArchiveNote, promoteArchiveNote, revokeArchiveNote, discoverArchiveGeneration, registerArchiveGeneration, deriveArchiveNote, inspectArchiveDerivation } from "$lib/api/client";
  import PublicNotePreparation from "./PublicNotePreparation.svelte";
  import PageHeader from "$lib/components/shared/PageHeader.svelte";
  import { PublicNotePreparation as PreparationController, initialPreparationState } from "$lib/pages/bridge/state/archive/preparation";
  import type { NoteRecord } from "$lib/api/models";
  import { PublicNoteManager, initialNotesState, emptyNoteDraft, correctionDraft, validateDraft, prepareNote, notesHref, notesSelection } from "$lib/pages/bridge/state/archive/notes";
  import { altarNavigationContext, type AltarNavigation } from "$lib/navigation/instruments";

  let { selection, onSelect }: { selection: string; onSelect: (selection: string) => void } = $props();
  const navigation = getContext<AltarNavigation | undefined>(altarNavigationContext);
  let noteState = $state.raw(initialNotesState());
  let preparation = $state.raw(initialPreparationState());
  let preparationBusy = $state(false);
  let draft = $state(emptyNoteDraft());
  let filter = $state("");
  let errors = $state.raw<string[]>([]);
  let preparing = $state(false);
  let revokeReview = $state.raw<NoteRecord | null>(null);
  let discardReview = $state(false);
  let errorHeading: HTMLHeadingElement | undefined;
  const errorFocus = (element: HTMLHeadingElement) => { errorHeading = element; return () => { errorHeading = undefined; }; };
  let detailHeading: HTMLHeadingElement | undefined;
  const detailFocus = (element: HTMLHeadingElement) => { detailHeading = element; return () => { detailHeading = undefined; }; };
  let reviewHeading: HTMLHeadingElement | undefined;
  const reviewFocus = (element: HTMLHeadingElement) => { reviewHeading = element; return () => { reviewHeading = undefined; }; };
  let formHeading: HTMLHeadingElement | undefined;
  const formFocus = (element: HTMLHeadingElement) => { formHeading = element; return () => { formHeading = undefined; }; };
  let metadataHeading: HTMLHeadingElement | undefined;
  const metadataFocus = (element: HTMLHeadingElement) => { metadataHeading = element; return () => { metadataHeading = undefined; }; };
  let discardHeading: HTMLHeadingElement | undefined;
  const discardFocus = (element: HTMLHeadingElement) => { discardHeading = element; return () => { discardHeading = undefined; }; };
  let alive = true;
  let draftGeneration = 0;
  let focusGeneration = 0;
  let authorityEpoch = 0;
  const preparationController = new PreparationController({ generation: discoverArchiveGeneration, register: registerArchiveGeneration,
    derive: deriveArchiveNote, inspect: inspectArchiveDerivation }, (next) => { preparation = next; },
    (busy) => { preparationBusy = busy; manager.setPreparationBusy(busy); }, () => manager.capturePreparationRefusal());
  const manager = new PublicNoteManager({ profile: getArchiveProfile, defaults: getArchiveBridgeDefault, list: listArchiveNotes,
    read: getArchiveNote, admit: admitArchiveNote, promote: promoteArchiveNote, revoke: revokeArchiveNote }, (next) => {
    noteState = next;
    preparationController.setContext(next.profile, next.selected, next.record, next.writing);
    if (next.authorityEpoch !== authorityEpoch) {
      authorityEpoch = next.authorityEpoch; ++draftGeneration; draft = emptyNoteDraft(); filter = ""; errors = []; revokeReview = null; preparing = false;
    }
  });
  const hasDraft = $derived(!!(draft.sourceKey || draft.revision || draft.text || draft.producer || draft.observedAt));
  const preparationTransient = $derived(!!preparation.frozen || !!preparation.historical || preparation.unknown || preparation.registrationUnknown || preparation.operation !== "idle");
  const transient = $derived(preparationTransient || hasDraft || !!noteState.frozen || noteState.intakeUnknown || !!noteState.transitionUnknown || noteState.writing);
  const commandBlocked = $derived(preparationBusy || noteState.writing || noteState.detailBusy || !!(noteState.transitionUnknown && noteState.transitionUnknown.recordId === noteState.selected && !noteState.transitionUnknown.checked));
  afterNavigate(() => {
    ++focusGeneration;
    revokeReview = null;
    manager.select(selection);
    void focusSelection(selection);
  });
  onMount(() => {
    manager.select(selection);
    const expected = selection;
    void manager.load().then(() => focusSelection(expected, true));
  });
  async function focusSelection(expected: string, initialFallback = false) {
    await tick();
    if (!alive || selection !== expected) return;
    if (initialFallback && document.activeElement instanceof HTMLElement && document.activeElement.closest("a,button,input,textarea,select,[contenteditable=true],[tabindex]")) return;
    (expected === "new" ? formHeading : expected === "manage" ? metadataHeading : detailHeading)?.focus();
  }
  async function openDiscardReview() {
    discardReview = true; await tick();
    if (alive && discardReview) discardHeading?.focus();
  }
  onDestroy(() => { alive = false; ++draftGeneration; preparationController.dispose(); manager.dispose(); });
  function guardUnload(event: BeforeUnloadEvent) {
    if (transient) { event.preventDefault(); event.returnValue = ""; }
  }
  beforeNavigate((event) => {
    const target = event.to?.url, values = target?.searchParams.getAll("notes") ?? [];
    const stays = !event.willUnload && target?.pathname === "/bridge" && values.length === 1 &&
      notesSelection(values[0] ?? null) !== null && !target.searchParams.has("investigation");
    if ((!stays || (preparationTransient && values[0] !== noteState.selected)) && !event.willUnload && transient && !window.confirm("Leave public notes? Draft and frozen intake/preparation references will be lost. Leaving does not cancel model work or resolve an unknown write. Keep the exact record, source and generation references.")) event.cancel();
  });
  async function prepare(event: SubmitEvent) {
    event.preventDefault();
    if (preparing || preparationBusy || noteState.intakeUnknown || noteState.writing || noteState.frozen || !noteState.profile) return;
    errors = validateDraft($state.snapshot(draft));
    if (errors.length) { await tick(); errorHeading?.focus(); return; }
    const version = ++draftGeneration, namespace = noteState.profile.namespace_id, generation = focusGeneration, expected = selection;
    preparing = true;
    try {
      const body = await prepareNote($state.snapshot(draft), namespace, crypto.randomUUID());
      if (!alive || version !== draftGeneration || namespace !== noteState.profile?.namespace_id || generation !== focusGeneration || expected !== selection) return;
      manager.freeze(body);
    } catch { if (alive && version === draftGeneration) { errors = ["Exact UTF-8 digest could not be prepared. No request was sent."]; await tick(); errorHeading?.focus(); } }
    finally { if (alive && version === draftGeneration) preparing = false; }
  }
  async function submit(replay = false) {
    const expected = selection, generation = focusGeneration;
    if (replay) await manager.replay(); else await manager.submit();
    if (!alive || generation !== focusGeneration || expected !== selection) return;
    if (!noteState.frozen && !noteState.intakeUnknown) { draft = emptyNoteDraft(); if (noteState.selected) onSelect(noteState.selected); }
    await tick();
    if (alive && generation === focusGeneration && expected === selection) detailHeading?.focus();
  }
  async function stageCorrection(record: NoteRecord) {
    if (preparationBusy || noteState.frozen || noteState.writing || hasDraft) { await openDiscardReview(); return; }
    draft = correctionDraft(record); errors = []; onSelect("new");
    await tick(); formHeading?.focus();
  }
  async function reviewRevoke(record: NoteRecord) {
    revokeReview = record; await tick(); reviewHeading?.focus();
  }
  async function confirmRevoke() {
    const expected = revokeReview, focus = selection, generation = focusGeneration; revokeReview = null;
    if (expected) await manager.transition("revoke", expected);
    await tick();
    if (alive && generation === focusGeneration && focus === selection) detailHeading?.focus();
  }
  function discard() {
    manager.discardIntake(); ++draftGeneration; draft = emptyNoteDraft(); errors = []; discardReview = false; preparing = false;
  }
</script>

<svelte:head><title>Public notes — Bridge — LychD</title></svelte:head>
<svelte:window onbeforeunload={guardUnload} />
<section class="public-notes" aria-labelledby="notes-title">
  <PageHeader
    title="Public notes"
    kicker="Bridge · public notes"
    description="Explicit public intake and exact revision management. Conversation text is never saved here automatically."
    titleId="notes-title"
  >
    <nav aria-label="Public notes focus"><a href={navigation?.bridgePath ?? "/bridge"}>Return to conversation</a><a href={notesHref("manage")}>Manage notes</a><a href={notesHref("new")}>New public note</a></nav>
  </PageHeader>
  {#if noteState.profilePhase === "loading"}<p role="status">Loading authorized public-note configuration…</p>
  {:else if noteState.profile}
    <section aria-labelledby="profile-title"><h2 id="profile-title">Configured profile</h2>
      <dl><dt>Profile</dt><dd>{noteState.profile.profile}</dd><dt>Namespace</dt><dd><code>{noteState.profile.namespace_id}</code></dd>
        <dt>Owner</dt><dd>{noteState.profile.owner_subject.identity}</dd><dt>Policy revision</dt><dd>{noteState.profile.policy_revision}</dd></dl>
      <p>Configuration establishes neither storage readiness nor successful recall.</p>
      <h3>Current Bridge default</h3>
      {#if noteState.defaultError}<p role="alert">Current-default read failed. {noteState.defaultError}</p>
      {:else if noteState.defaults?.current_default}<p>{noteState.defaults.current_default.pattern_id}@{noteState.defaults.current_default.pattern_revision}</p>
        <p>{noteState.defaults.requests_profile ? "Current default requests this profile." : "Current default does not request this profile."}</p>
      {:else if noteState.defaults}<p>Current default unavailable.</p>{:else}<p role="status">Loading current default…</p>{/if}
      <p>This is current configuration, separate from the catalogue and historical Runs; it does not predict a routed Run.</p>
    </section>
  {:else}<p role="alert">Public-note configuration is unavailable. {noteState.message}</p><button class="rune-btn" onclick={() => manager.load()}>Reload authorized configuration</button>{/if}

  {#if noteState.message && noteState.profile}<p class="notice" role="status">{noteState.message}</p>{/if}
  {#if noteState.intakeUnknown}<aside class="notice" aria-label="Unknown intake outcome"><h2>Intake outcome unknown</h2>
    <p>Metadata can recover a retained source identity, but contains no intake request UUID and cannot identify which intake attempt committed. A missing record, unchanged version or later refusal does not prove rollback.</p>
    {#if noteState.frozen}<p>Request <code>{noteState.frozen.request_id}</code> · source <code>{noteState.frozen.source_key}</code> · revision <code>{noteState.frozen.source_revision}</code></p>
      <button class="rune-btn" disabled={noteState.listBusy || noteState.writing} onclick={() => { filter = noteState.frozen!.source_key; void manager.list(false, filter); }}>Look up exact intake source key</button>
    {:else}<p>The original body is unavailable. Reload recovers authorized metadata only; identical replay is unavailable.</p>{/if}
  </aside>{/if}
  {#if noteState.transitionUnknown}<aside class="notice" aria-label="Lifecycle attempt"><p>Unconfirmed {noteState.transitionUnknown.target} of <a href={notesHref(noteState.transitionUnknown.recordId)}>{noteState.transitionUnknown.recordId}</a>, namespace <code>{noteState.transitionUnknown.namespace}</code>, expected version {noteState.transitionUnknown.version}. Check exact metadata before a new decision. A newer version does not attribute this occurrence.</p></aside>{/if}

  {#if noteState.profile}
    {#if selection === "new"}
      <form onsubmit={prepare} novalidate aria-label="Public note intake">
        <h2 {@attach formFocus} tabindex="-1">{draft.replacesRevision ? "Stage correction" : "New public note"}</h2>
        <p>Source text is never read back. Supply complete replacement text. The digest binds the exact UTF-8 text submitted by this form; no application trimming or normalization is applied. Drafts and replay bodies stay in this document only.</p>
        {#if draft.replacesRevision}<p>Replacing revision <code>{draft.replacesRevision}</code>. Choose a different revision; revision labels do not imply ordering. The predecessor stays promoted until this candidate is explicitly promoted.</p>{/if}
        {#if errors.length}<div role="alert"><h3 {@attach errorFocus} tabindex="-1">Check public intake</h3><ul>{#each errors as error (error)}<li>{error}</li>{/each}</ul></div>{/if}
        <fieldset disabled={preparing || preparationBusy || noteState.intakeUnknown || noteState.writing || !!noteState.frozen}>
          <legend>Public source revision</legend>
          <label>Source key <input bind:value={draft.sourceKey} readonly={draft.replacesRevision !== null} autocomplete="off" /></label>
          <label>Source revision <input bind:value={draft.revision} autocomplete="off" /></label>
          <label>Producer <input bind:value={draft.producer} autocomplete="off" /></label>
          <label>Observation time with timezone <input bind:value={draft.observedAt} placeholder="2026-10-19T12:00:00Z" autocomplete="off" /></label>
          <label>Complete replacement text <textarea rows="9" bind:value={draft.text} spellcheck="false"></textarea><span>{[...draft.text].length} / 16,000 code points</span></label>
          <label class="declaration"><input type="checkbox" bind:checked={draft.publicMaterial} />I confirm this is public material.</label>
        </fieldset>
        <button class="rune-btn" type="submit" disabled={preparing || preparationBusy || noteState.intakeUnknown || noteState.writing || !!noteState.frozen}>{preparing ? "Computing exact UTF-8 digest…" : "Prepare public intake"}</button>
      </form>
    {/if}
    {#if noteState.frozen}<section class="notice" aria-labelledby="frozen-title"><h2 id="frozen-title">Frozen public intake</h2>
      <dl><dt>Classification</dt><dd>public</dd><dt>Namespace</dt><dd>{noteState.frozen.namespace_id}</dd><dt>Request UUID</dt><dd>{noteState.frozen.request_id}</dd>
        <dt>Source key</dt><dd>{noteState.frozen.source_key}</dd><dt>Source revision</dt><dd>{noteState.frozen.source_revision}</dd><dt>Exact UTF-8 SHA-256</dt><dd>{noteState.frozen.source_digest}</dd></dl>
      <p>UUID, observation timestamp, digest and complete body are frozen before sending. Intake alone does not make this revision recall-eligible.</p>
      {#if noteState.replayAvailable}<button class="rune-btn" disabled={noteState.writing || preparationBusy} onclick={() => submit(true)}>Replay identical intake</button>
      {:else if !noteState.intakeUnknown}<button class="rune-btn" disabled={noteState.writing || preparationBusy} onclick={() => submit()}>Submit candidate once</button>{/if}
      <button class="rune-btn" disabled={noteState.writing} onclick={openDiscardReview}>Discard draft and replay body</button>
    </section>{/if}
    {#if discardReview}<section class="notice" aria-label="Discard review"><h2 {@attach discardFocus} tabindex="-1">Discard transient material?</h2><p>Discarding loses identical replay ability and does not cancel or resolve an unknown write. Keep the displayed source identity and any exact record UUID.</p>
      <button class="rune-btn" onclick={() => { discardReview = false; }}>Keep current draft</button><button class="rune-btn" disabled={noteState.writing} onclick={discard}>Confirm discard</button></section>{/if}

    {#if selection !== "new" || noteState.intakeUnknown}
      <section aria-labelledby="metadata-title"><h2 id="metadata-title" {@attach metadataFocus} tabindex="-1">Retained metadata</h2>
        <form class="filter" onsubmit={(event) => { event.preventDefault(); void manager.list(false, filter); }}><label>Exact source-key filter (optional) <input bind:value={filter} autocomplete="off" /></label><button class="rune-btn" type="submit" disabled={noteState.listBusy}>Apply exact filter</button></form>
        <button class="rune-btn" disabled={noteState.listBusy} onclick={() => manager.list(false)}>Refresh loaded metadata</button>
        {#if noteState.listError}<p role="alert">{noteState.listError}</p>{/if}
        <p>Applied exact source filter: <code>{noteState.filter || "None (all source keys)"}</code></p>
        <p>{noteState.records.length} loaded; this is not a total count. At most 50 records per request. All lifecycles are inspectable.</p>
        {#if noteState.listBusy}<p role="status">Loading metadata…</p>{:else if !noteState.records.length && !noteState.listError}<p>No retained metadata in this selection.</p>{/if}
        <ul>{#each noteState.records as record (record.reference.record_id)}<li><a href={notesHref(record.reference.record_id)}>{record.source_key} · {record.source_revision}</a> — {record.lifecycle} · version {record.reference.lifecycle_version}</li>{/each}</ul>
        {#if noteState.cursor}<button class="rune-btn" disabled={noteState.listBusy} onclick={() => manager.list(true)}>Load more metadata</button>{/if}
      </section>
    {/if}
    {#if noteState.selected}<article aria-labelledby="detail-title"><h2 id="detail-title" {@attach detailFocus} tabindex="-1">Exact note metadata</h2>
      <p>Record <code>{noteState.selected}</code></p><button class="rune-btn" disabled={noteState.detailBusy || noteState.writing} onclick={() => manager.check()}>{noteState.detailBusy ? "Checking…" : "Check exact record"}</button>
      {#if noteState.detailError}<p role="alert">{noteState.detailError}</p>{/if}
      {#if noteState.record}<dl><dt>Source key</dt><dd>{noteState.record.source_key}</dd><dt>Source revision</dt><dd>{noteState.record.source_revision}</dd><dt>Lifecycle</dt><dd>{noteState.record.lifecycle}</dd>
        <dt>Lifecycle version</dt><dd>{noteState.record.reference.lifecycle_version}</dd><dt>Revision digest</dt><dd>{noteState.record.reference.revision_digest}</dd><dt>Source digest</dt><dd>{noteState.record.source_digest}</dd>
        <dt>Producer</dt><dd>{noteState.record.producer}</dd><dt>Observed</dt><dd>{noteState.record.observed_at}</dd><dt>Created</dt><dd>{noteState.record.created_at}</dd></dl>
        <p>{noteState.record.lifecycle === "candidate" ? "Candidate: excluded from ordinary recall." : noteState.record.lifecycle === "promoted" ? "Promoted: lifecycle-eligible; current authorization and a matching answer are not promised." : noteState.record.lifecycle === "revoked" ? "Revoked tombstone: this source revision cannot be re-ingested." : "Archived: excluded from ordinary recall."}</p>
        {#if noteState.record.lifecycle === "candidate"}<button class="rune-btn" disabled={commandBlocked} onclick={() => manager.transition("promote", noteState.record!)}>Promote this candidate</button>{/if}
        <button class="rune-btn" disabled={noteState.writing || preparationBusy} onclick={() => stageCorrection(noteState.record!)}>Stage correction</button>
        {#if noteState.record.lifecycle !== "revoked"}<button class="rune-btn" disabled={commandBlocked} onclick={() => reviewRevoke(noteState.record!)}>Review revoke</button>{/if}
      {/if}
      {#if revokeReview}<section class="notice" aria-labelledby="revoke-title"><h3 id="revoke-title" {@attach reviewFocus} tabindex="-1">Revoke this exact revision?</h3>
        <p>Namespace <code>{revokeReview.namespace_id}</code>, record <code>{revokeReview.reference.record_id}</code>, source <code>{revokeReview.source_key}</code>, revision <code>{revokeReview.source_revision}</code>, revision digest <code>{revokeReview.reference.revision_digest}</code>, expected version {revokeReview.reference.lifecycle_version}.</p>
        <p>Controlled source text is cleared and an anti-reingestion tombstone remains. Earlier answers and backups are outside this promise. Revocation cannot return this revision to recall.</p>
        <button class="rune-btn" onclick={() => { revokeReview = null; detailHeading?.focus(); }}>Keep revision</button><button class="rune-btn" disabled={commandBlocked} onclick={confirmRevoke}>Confirm exact revoke</button>
      </section>{/if}
      <PublicNotePreparation state={preparation} controller={preparationController} blocked={noteState.writing} recordAvailable={!!noteState.record} />
      <a href={notesHref("manage")}>Return to metadata list</a>
    </article>{/if}
  {/if}
</section>

<style>
  .public-notes { width: min(100%, 64rem); margin: 0 auto; padding: clamp(1rem, 3vw, 2.5rem); display: grid; align-content: start; gap: 2rem; min-width: 0; }
  section, article, form, fieldset { display: grid; align-content: start; gap: 1rem; min-width: 0; }
  h2, h3, p { margin: 0; }
  h2, h3, legend { color: var(--color-bone); font-family: var(--font-body); font-variant: normal; letter-spacing: normal; }
  h2 { font-size: var(--text-xl); font-weight: 600; line-height: 1.35; }
  h3 { font-size: var(--text-base); font-weight: 600; line-height: 1.5; }
  .public-notes > form, .public-notes > article { border-top: 1px solid var(--color-engraving); padding-top: 1.5rem; }
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
  @media (max-width: 36rem) { .public-notes { padding: 1rem; gap: 1.5rem; } dl { grid-template-columns: minmax(0, 1fr); gap: 0.25rem; } dd + dt { margin-top: 0.65rem; } .notice { padding: 1rem; } }

  nav { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1.25rem; padding-top: 0.5rem; font-size: var(--text-sm); }
  nav a { padding-block: 0.35rem; }

  .declaration { display: flex; align-items: start; gap: 0.75rem; padding-top: 0.25rem; }
  .declaration input { margin-top: 0.35rem; accent-color: var(--color-rune); }

  ul { margin: 0; padding-left: 1.25rem; }
  li { padding-block: 0.35rem; }

  textarea { font-family: var(--font-glyph); }
  .filter { display: flex; flex-wrap: wrap; align-items: end; gap: 0.75rem; }
  .filter label { flex: 1 1 20rem; }
  .filter button { align-self: end; }
</style>
