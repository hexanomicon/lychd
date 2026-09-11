<script lang="ts">
  import { beforeNavigate, goto } from "$app/navigation";
  import { tick, untrack } from "svelte";
  import { atlasHref, parseAtlasLink, type AtlasLinkIntent } from "$lib/atlas/navigation";

  import {
    ApiError,
    changeAtlasProject,
    createAtlasProject,
    getAtlasProject,
    getAtlasProjects
  } from "$lib/api/client";
  import type {
    AtlasAssessment,
    AtlasCatalogue,
    AtlasConcern,
    AtlasCreate,
    AtlasDecision,
    AtlasMutation,
    AtlasProject,
    AtlasReference
  } from "$lib/api/models";

  let { projectId, linkKind, linkId }: { projectId?: string; linkKind?: string | null; linkId?: string | null } = $props();
  type Mode = "create" | "project" | "concern" | "assessment" | "decision" | "reference";
  type Lifecycle = "active" | "paused" | "closed";
  type Judgment = "sufficient" | "insufficient" | "disputed";
  type ConcernFilter = "all" | "unassessed" | "review" | Judgment;
  const concernFilters: Array<{ value: ConcernFilter; label: string }> = [
    { value: "all", label: "All concerns" }, { value: "unassessed", label: "Unassessed" },
    { value: "review", label: "Needs review" }, { value: "insufficient", label: "Insufficient" },
    { value: "disputed", label: "Disputed" }, { value: "sufficient", label: "Sufficient" }
  ];
  type Editor = {
    mode: Mode;
    baseVersion: number;
    title: string;
    brief: string;
    next_action: string;
    lifecycle: Lifecycle;
    concern_id: string;
    statement: string;
    criteria: string;
    judgment: Judgment | "";
    rationale: string;
    reference_ids: string[];
    reference_kind: "session" | "run";
    target_id: string;
    note: string;
    supersedes_id: string;
  };
  type Pending =
    | { kind: "create"; body: AtlasCreate; routeId: undefined }
    | { kind: "change"; body: AtlasMutation; routeId: string };

  const uid = $props.id();
  const lifecycleNames = { active: "Active", paused: "Paused", closed: "Closed" } as const;
  const lifecycles: Lifecycle[] = ["active", "paused", "closed"];
  const judgmentNames = {
    sufficient: "Sufficient",
    insufficient: "Insufficient",
    disputed: "Disputed"
  } as const;
  const editorNames: Record<Mode, string> = {
    create: "New project",
    project: "Edit project",
    concern: "Save concern",
    assessment: "Record assessment",
    decision: "Record decision",
    reference: "Link existing activity"
  };

  let catalogue = $state.raw<AtlasCatalogue | null>(null);
  let project = $state.raw<AtlasProject | null>(null);
  let editor = $state<Editor | null>(null);
  let baseline = $state("");
  let pending = $state.raw<Pending | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let readError = $state("");
  let saveError = $state("");
  let notice = $state("");
  let uncertain = $state(false);
  let conflict = $state(false);
  let latestLoaded = $state(false);
  let lifecycleFilter = $state<Lifecycle | "all">("all");
  let reviewOnly = $state(false);
  let unassessedOnly = $state(false);
  let insufficientOnly = $state(false);
  let disputedOnly = $state(false);
  let concernFilter = $state<ConcernFilter>("all");
  let concernQuery = $state("");
  let offeredLink = "";
  let requestedOffset = 0;
  let generation = 0;
  let readSequence = 0;
  let controller: AbortController | undefined;
  let focusOrigin: HTMLElement | null = null;

  let view = $derived(project?.id === projectId ? project : null);
  let linkIntent = $derived(parseAtlasLink(linkKind, linkId));
  let linkedIntent = $derived(Boolean(linkIntent && view?.references.some(
    (reference) => reference.kind === linkIntent?.kind && reference.target_id === linkIntent?.targetId
  )));
  let visibleConcerns = $derived((view?.concerns ?? []).filter((concern) =>
    ((editor?.mode === "concern" || editor?.mode === "assessment") && editor.concern_id === concern.id) || matchesConcern(concern)
  ));
  let pinnedConcern = $derived(view?.concerns.find((concern) =>
    (editor?.mode === "concern" || editor?.mode === "assessment") && editor.concern_id === concern.id && !matchesConcern(concern)
  ));
  let currentDecisions = $derived((view?.decisions ?? []).filter(
    (decision) => !view?.decisions.some((other) => other.supersedes_id === decision.id)
  ).toReversed());
  let earlierDecisions = $derived((view?.decisions ?? []).filter(
    (decision) => view?.decisions.some((other) => other.supersedes_id === decision.id)
  ).toReversed());
  let comparison = $derived.by(() => {
    if (!editor || !view || !conflict || !latestLoaded) return [];
    type Key = "title" | "brief" | "next_action" | "lifecycle" | "statement" | "criteria";
    const fields: Array<{ key: Key; label: string; saved: string }> = [];
    if (editor.mode === "project") {
      fields.push({ key: "title", label: "Name", saved: view.title },
        { key: "brief", label: "Brief", saved: view.brief },
        { key: "next_action", label: "Proposed next step", saved: view.next_action },
        { key: "lifecycle", label: "Lifecycle", saved: view.lifecycle });
    } else if (editor.mode === "concern" || editor.mode === "assessment") {
      const concern = view.concerns.find((item) => item.id === editor?.concern_id);
      if (concern) fields.push({ key: "statement", label: "Concern", saved: concern.statement },
        { key: "criteria", label: "Satisfaction conditions", saved: concern.criteria });
      if (editor.mode === "assessment") fields.push({ key: "brief", label: "Brief", saved: view.brief });
    }
    return fields.filter((field) => editor?.[field.key] !== field.saved);
  });
  let dirty = $derived(editor !== null && JSON.stringify(editor) !== baseline);
  let guarded = $derived(dirty || saving || uncertain);
  let editorLocked = $derived(saving || uncertain);
  let eligibleReferences = $derived(
    (view?.references ?? []).filter(
      (reference) => reference.concern_id === null || reference.concern_id === editor?.concern_id
    )
  );
  let continuationTargets = $derived(
    [...new Set((view?.references ?? []).filter((reference) => reference.kind === "session").map((reference) => reference.target_id))]
      .map((targetId) => ({
        targetId,
        note: view?.references.find((reference) => reference.kind === "session" && reference.target_id === targetId && reference.note.trim())?.note ?? ""
      }))
  );
  let filteredProjects = $derived(
    (catalogue?.projects ?? []).filter(
      (item) =>
        (lifecycleFilter === "all" || item.lifecycle === lifecycleFilter) &&
        (!reviewOnly || item.review_needed_count > 0) &&
        (!unassessedOnly || item.unassessed_count > 0) &&
        (!insufficientOnly || item.insufficient_count > 0) &&
        (!disputedOnly || item.disputed_count > 0)
    )
  );

  beforeNavigate((navigation) => {
    // Moving within the same document preserves the draft and its editor.
    if (!navigation.willUnload && navigation.to && navigation.from && navigation.to.url.origin === navigation.from.url.origin &&
        navigation.to.url.pathname === navigation.from.url.pathname && navigation.to.url.search === navigation.from.url.search) return;
    if (!guarded) return;
    if (navigation.type === "leave") {
      navigation.cancel();
    } else if (!window.confirm(leaveMessage())) {
      navigation.cancel();
    }
  });

  // One external read per route identity; state read by load must not become dependencies.
  $effect(() => {
    const id = projectId;
    const linkKey = `${linkKind ?? ""}:${linkId ?? ""}`;
    return untrack(() => {
      void linkKey;
      generation++;
      controller?.abort();
      project = null;
      catalogue = null;
      editor = null;
      pending = null;
      baseline = "";
      readError = "";
      saveError = "";
      notice = "";
      saving = false;
      uncertain = false;
      conflict = false;
      latestLoaded = false;
      requestedOffset = 0;
      concernFilter = "all";
      concernQuery = "";
      offeredLink = "";
      void load(id, 0);
      return () => {
        generation++;
        readSequence++;
        controller?.abort();
      };
    });
  });

  function leaveMessage() {
    return uncertain
      ? "This save may already have reached Atlas. Leave and lose the prepared retry?"
      : saving
        ? "A save is still in progress. Leave before its outcome is known?"
        : "Leave Atlas and discard your unsaved draft?";
  }

  function current(scope: number, id: string | undefined) {
    return generation === scope && projectId === id;
  }

  function message(cause: unknown, fallback: string) {
    return cause instanceof Error ? cause.message : fallback;
  }

  async function load(id: string | undefined, offset = 0, forComparison = false) {
    const scope = generation;
    const sequence = ++readSequence;
    controller?.abort();
    const requestController = new AbortController();
    controller = requestController;
    requestedOffset = offset;
    loading = true;
    readError = "";
    try {
      if (id) {
        const next = await getAtlasProject(id, requestController.signal);
        if (!current(scope, id) || sequence !== readSequence) return;
        project = next;
        if (forComparison) latestLoaded = true;
      } else {
        const next = await getAtlasProjects({ limit: 50, offset, signal: requestController.signal });
        if (!current(scope, id) || sequence !== readSequence) return;
        catalogue = next;
      }
    } catch (cause) {
      if (!current(scope, id) || sequence !== readSequence || requestController.signal.aborted) return;
      readError = message(cause, "Atlas could not be loaded.");
    } finally {
      if (current(scope, id) && sequence === readSequence) {
        loading = false;
        if (id && view && linkIntent && !editor && !linkedIntent && !readError && !offeredLink) {
          offeredLink = `${linkIntent.kind}:${linkIntent.targetId}`;
          openEditor("reference", undefined, "", linkIntent);
        }
      }
    }
  }

  function refresh(offset = catalogue?.offset ?? 0) {
    if (saving || uncertain) return;
    if (dirty && !window.confirm("Refresh Atlas and discard your unsaved draft?")) return;
    clearEditor();
    void load(projectId, offset);
  }

  function clearEditor() {
    editor = null;
    baseline = "";
    pending = null;
    saveError = "";
    conflict = false;
    uncertain = false;
    latestLoaded = false;
  }

  function cancelEditor() {
    if (saving || uncertain) return;
    if (dirty && !window.confirm("Discard this unsaved draft?")) return;
    clearEditor();
    restoreFocus();
  }

  function restoreFocus() {
    const scope = generation;
    const id = projectId;
    const target = focusOrigin;
    void tick().then(() => {
      if (!current(scope, id)) return;
      if (target?.isConnected) target.focus();
      else if (target?.closest(".concern")) document.getElementById(`${uid}-concern-filter`)?.focus();
      else document.getElementById(`${uid}-page-title`)?.focus();
    });
  }

  function openEditor(mode: Mode, concern?: AtlasConcern, supersedesId = "", preset?: AtlasLinkIntent) {
    if (saving || uncertain || loading) return;
    if (dirty && !window.confirm("Discard the current draft and open another editor?")) return;
    if (mode !== "create" && !view) return;
    focusOrigin = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    clearEditor();
    notice = "";
    editor = {
      mode,
      baseVersion: view?.version ?? 0,
      title: view?.title ?? "",
      brief: view?.brief ?? "",
      next_action: view?.next_action ?? "",
      lifecycle: view?.lifecycle ?? "active",
      concern_id: concern?.id ?? "",
      statement: concern?.statement ?? "",
      criteria: concern?.criteria ?? "",
      judgment: "",
      rationale: "",
      reference_ids: [],
      reference_kind: preset?.kind ?? "session",
      target_id: preset?.targetId ?? "",
      note: "",
      supersedes_id: supersedesId
    };
    baseline = JSON.stringify(editor);
    const scope = generation;
    const id = projectId;
    void tick().then(() => {
      if (!current(scope, id)) return;
      document.getElementById(`${uid}-editor-title`)?.focus();
    });
  }

  function latestAssessment(concernId: string): AtlasAssessment | undefined {
    return (view?.assessments ?? []).filter((item) => item.concern_id === concernId).at(-1);
  }

  function needsReview(concern: AtlasConcern, assessment?: AtlasAssessment) {
    return Boolean(
      assessment &&
        (assessment.concern_revision !== concern.revision ||
          assessment.brief_revision !== view?.brief_revision)
    );
  }

  function assessmentLabel(concern: AtlasConcern) {
    const latest = latestAssessment(concern.id);
    if (!latest) return "Unassessed";
    if (needsReview(concern, latest)) return "Review needed";
    return `Recorded ${latest.judgment}`;
  }

  function concernState(concern: AtlasConcern): Exclude<ConcernFilter, "all"> {
    const latest = latestAssessment(concern.id);
    return !latest ? "unassessed" : needsReview(concern, latest) ? "review" : latest.judgment;
  }

  function matchesConcern(concern: AtlasConcern) {
    return (concernFilter === "all" || concernState(concern) === concernFilter) &&
      `${concern.statement} ${concern.criteria}`.toLocaleLowerCase().includes(concernQuery.trim().toLocaleLowerCase());
  }

  function activityName(reference: AtlasReference) {
    const note = reference.note.length > 100 ? `${reference.note.slice(0, 100)}…` : reference.note;
    return `${reference.kind === "session" ? "Conversation" : "Run"} · ${note ? `${note} · ` : ""}${reference.target_id}`;
  }

  function referenceHref(reference: Pick<AtlasReference, "kind" | "target_id">) {
    return `/${reference.kind === "session" ? "bridge" : "orb"}/${encodeURIComponent(reference.target_id)}`;
  }

  function date(value: string) {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime())
      ? value
      : parsed.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
  }

  function buildChange(draft: Editor): AtlasMutation["change"] {
    switch (draft.mode) {
      case "project":
        return {
          kind: "project.update",
          title: draft.title.trim(),
          brief: draft.brief,
          lifecycle: draft.lifecycle,
          next_action: draft.next_action
        };
      case "concern":
        return {
          kind: "concern.save",
          concern_id: draft.concern_id || null,
          statement: draft.statement.trim(),
          criteria: draft.criteria
        };
      case "assessment":
        if (!draft.judgment) throw new Error("Choose an assessment judgment.");
        return {
          kind: "concern.assess",
          concern_id: draft.concern_id,
          judgment: draft.judgment,
          rationale: draft.rationale.trim(),
          reference_ids: [...draft.reference_ids]
        };
      case "decision":
        return {
          kind: "decision.record",
          statement: draft.statement.trim(),
          rationale: draft.rationale.trim(),
          supersedes_id: draft.supersedes_id || null
        };
      case "reference":
        return {
          kind: "reference.add",
          reference_kind: draft.reference_kind,
          target_id: draft.target_id.trim(),
          concern_id: draft.concern_id || null,
          note: draft.note
        };
      default:
        throw new Error("Choose an project change before saving.");
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!editor || editorLocked || conflict) return;
    const draft = $state.snapshot(editor);
    if (
      ((draft.mode === "create" || draft.mode === "project") && !draft.title.trim()) ||
      ((draft.mode === "concern" || draft.mode === "decision") && !draft.statement.trim()) ||
      ((draft.mode === "assessment" || draft.mode === "decision") && !draft.rationale.trim()) ||
      (draft.mode === "assessment" && !draft.judgment) ||
      (draft.mode === "reference" && !draft.target_id.trim())
    ) {
      saveError = "Complete the required fields with more than spaces.";
      return;
    }
    if (draft.mode === "create") {
      pending = {
        kind: "create",
        routeId: undefined,
        body: {
          id: crypto.randomUUID(),
          title: draft.title.trim(),
          brief: draft.brief,
          next_action: draft.next_action
        }
      };
    } else if (view && projectId) {
      pending = {
        kind: "change",
        routeId: projectId,
        body: {
          request_id: crypto.randomUUID(),
          expected_version: draft.baseVersion,
          change: buildChange(draft)
        }
      };
    }
    await sendPending();
  }

  async function sendPending() {
    const request = pending;
    if (!request || saving || request.routeId !== projectId) return;
    const previouslyUncertain = uncertain;
    const scope = generation;
    readSequence++;
    controller?.abort();
    loading = false;
    saving = true;
    saveError = "";
    notice = "";
    let result: AtlasProject;
    try {
      result = request.kind === "create"
        ? await createAtlasProject(structuredClone(request.body))
        : await changeAtlasProject(request.routeId, structuredClone(request.body));
    } catch (cause) {
      if (!current(scope, request.routeId)) return;
      const status = cause instanceof ApiError ? cause.status : undefined;
      // A later middleware rejection cannot resolve an earlier unknown commit.
      // A tagged Atlas conflict follows its locked replay check and proves refusal.
      const atlasConflict = status === 409 && cause instanceof ApiError && cause.code === "atlas_write_rejected";
      const definitive = atlasConflict || (!previouslyUncertain && status !== undefined && status >= 400 && status < 500 && status !== 408);
      uncertain = !definitive;
      conflict = definitive && status === 409 && request.kind === "change";
      latestLoaded = false;
      saveError = message(cause, "The save could not be confirmed.");
      if (definitive) pending = null;
      return;
    } finally {
      if (current(scope, request.routeId)) saving = false;
    }
    if (!current(scope, request.routeId)) return;
    clearEditor();
    readError = "";
    if (request.kind === "create") {
      notice = `Created ${result.title}.`;
      const id = result.id;
      // Navigation failure must not turn a confirmed creation into a retryable mutation.
      try {
        await goto(atlasHref(id, linkIntent));
      } catch {
        if (!current(scope, request.routeId)) return;
        notice = `Created ${result.title}. Open it from the project list.`;
        void load(undefined, 0);
      }
    } else {
      project = result;
      notice = "Saved to Atlas.";
      restoreFocus();
    }
  }

  function compareLatest() {
    if (!projectId || saving || uncertain) return;
    latestLoaded = false;
    void load(projectId, 0, true);
  }

  function useSavedValue(key: "title" | "brief" | "next_action" | "lifecycle" | "statement" | "criteria", saved: string) {
    if (!editor) return;
    const draft = editor;
    if (key === "lifecycle") draft.lifecycle = saved as Lifecycle;
    else draft[key] = saved;
    const scope = generation;
    const id = projectId;
    void tick().then(() => {
      if (!current(scope, id) || editor !== draft) return;
      document.getElementById(`${uid}-${key === "next_action" ? "next" : key}`)?.focus();
    });
  }

  function keepDraft() {
    if (!editor || !view || !latestLoaded || loading) return;
    editor.baseVersion = view.version;
    if (editor.mode === "assessment") {
      const concern = view.concerns.find((item) => item.id === editor?.concern_id);
      if (!concern) return;
      editor.statement = concern.statement;
      editor.criteria = concern.criteria;
      editor.brief = view.brief;
    }
    conflict = false;
    latestLoaded = false;
    saveError = "";
    notice = "Draft retained. Review its values, then save when ready.";
  }
</script>

<svelte:window onfocus={() => { if (!editor && !saving && !uncertain) void load(projectId, requestedOffset); }} />

<svelte:head><title>{view ? `${view.title} · Atlas` : "Atlas"} — LychD</title></svelte:head>

<div class="atlas">
  <header class="atlas-heading">
    <div>
      {#if projectId}<a class="back-link" href={atlasHref(undefined, linkIntent)}>← All projects</a>{/if}
      <span class="instrument-kicker">Atlas · Projects</span>
      <h1 class="rune-head" id={`${uid}-page-title`} tabindex="-1">{view?.title ?? "Atlas"}</h1>
      {#if !projectId && catalogue?.total !== 0}<p>Work and ongoing care, across conversations.</p>{/if}
    </div>
    <div class="actions">
      <button type="button" disabled={loading || saving || uncertain} onclick={() => refresh()}>
        {loading && (catalogue || view) ? "Refreshing…" : "Refresh"}
      </button>
      {#if !projectId && catalogue?.total !== 0}
        <button class="primary" type="button" disabled={loading || editorLocked} onclick={() => openEditor("create")}>New project</button>
      {:else if view}
        <span class="badge">{lifecycleNames[view.lifecycle]}</span>
      {/if}
    </div>
  </header>

  {#if notice}<p class="notice" role="status">{notice}</p>{/if}
  {#if linkIntent}
    <section class="link-intent panel" aria-label="Activity to link">
      <h2>{linkedIntent ? "Activity linked to this project" : projectId ? "Review this activity link" : "Choose a project for this activity"}</h2>
      <a href={referenceHref({ kind: linkIntent.kind, target_id: linkIntent.targetId })} target="_blank" rel="noopener noreferrer">{linkIntent.kind === "session" ? "Conversation in Bridge" : "Run in Orb"} · {linkIntent.targetId} ↗</a>
      {#if !projectId}<p class="field-help">Select a project below, or create one. You will review the link before saving.</p>{/if}
      <a href={atlasHref(projectId)}>{linkedIntent ? "Finish linking" : "Cancel linking"}</a>
    </section>
  {/if}
  {#if readError}
    <div class="fault" role="alert">
      <strong>{view || catalogue ? "Refresh failed. Showing the last loaded information." : "Atlas could not be loaded."}</strong>
      <p>{readError}</p>
      <button type="button" disabled={loading || editorLocked} onclick={() => void load(projectId, requestedOffset, conflict)}>Retry loading</button>
    </div>
  {/if}

  {#snippet editorPanel()}
  {#if editor}
    <section class="panel editor" aria-labelledby={`${uid}-editor-title`}>
      <header class="section-heading">
        <div>
          <span class="instrument-kicker">{uncertain ? "Save outcome unknown" : "Draft"}</span>
          <h2 id={`${uid}-editor-title`} tabindex="-1">{editorNames[editor.mode]}</h2>
        </div>
        <button type="button" disabled={editorLocked} onclick={cancelEditor}>Cancel</button>
      </header>

      {#if saveError}
        <div class="fault" role={conflict && latestLoaded ? undefined : "alert"}>
          <strong>{uncertain ? "The save may already have reached Atlas." : conflict ? "This change conflicts with saved information." : "The change was not saved."}</strong>
          <p>{saveError}</p>
          {#if uncertain}
            <p>Your submitted values are held unchanged. Retry to confirm this same save.</p>
            <button class="primary" type="button" disabled={saving} onclick={() => void sendPending()}>{saving ? "Retrying…" : "Retry same save"}</button>
          {:else if conflict}
            <p>Your draft is preserved. Compare it with the latest saved values before saving again.</p>
            <div class="actions">
              <button type="button" disabled={loading} onclick={compareLatest}>{loading ? "Loading latest…" : "Load latest for comparison"}</button>
            </div>
            {#if latestLoaded}
              <section class="comparison" aria-label="Compare with saved values">
                <h3>{editor.mode === "assessment" ? "Changed requirements" : "Review differing fields"}</h3>
                {#each comparison as field (field.key)}
                  <section class="comparison-field" aria-label={field.label}>
                    <h4>{field.label}</h4>
                    <div class="comparison-values">
                      <div><span>Your draft</span><p class="prose">{editor[field.key] || "Empty"}</p></div>
                      <div><span>Latest saved</span><p class="prose">{field.saved || "Empty"}</p></div>
                    </div>
                    {#if editor.mode !== "assessment"}
                      <button type="button" onclick={() => useSavedValue(field.key, field.saved)}>Use saved {field.label.toLocaleLowerCase()}</button>
                    {/if}
                  </section>
                {:else}<p>No differing text fields. Review the latest records before retrying this change.</p>{/each}
                <p>{editor.mode === "assessment" ? "The next assessment will judge the latest requirements. Review whether your judgment and reason still apply." : "The next save uses all values currently shown in this form."}</p>
                <button type="button" onclick={keepDraft}>Use reviewed values</button>
              </section>
            {/if}
          {/if}
        </div>
      {/if}

      <form onsubmit={submit} aria-label={editorNames[editor.mode]}>
        <fieldset disabled={editorLocked}>
          <legend class="visually-hidden">{editorNames[editor.mode]}</legend>
          {#if editor.mode === "create" || editor.mode === "project"}
            <label for={`${uid}-title`}>Name <span class="required">required</span></label>
            <input id={`${uid}-title`} bind:value={editor.title} required maxlength="200" autocomplete="off" />
            <label for={`${uid}-brief`}>Brief</label>
            <p class="field-help" id={`${uid}-brief-help`}>Describe the desired outcome or the responsibility you want to keep caring for.</p>
            <textarea id={`${uid}-brief`} bind:value={editor.brief} rows="5" maxlength="20000" aria-describedby={`${uid}-brief-help`}></textarea>
            <label for={`${uid}-next`}>Proposed next step</label>
            <p class="field-help" id={`${uid}-next-help`}>A reminder of what to consider next. Saving it does not start or schedule work.</p>
            <textarea id={`${uid}-next`} bind:value={editor.next_action} rows="2" maxlength="4000" aria-describedby={`${uid}-next-help`}></textarea>
            {#if editor.mode === "project"}
              <label for={`${uid}-lifecycle`}>Lifecycle</label>
              <select id={`${uid}-lifecycle`} bind:value={editor.lifecycle} aria-describedby={`${uid}-lifecycle-help`}>
                {#each lifecycles as lifecycle (lifecycle)}<option value={lifecycle}>{lifecycleNames[lifecycle]}</option>{/each}
              </select>
              <p class="field-help" id={`${uid}-lifecycle-help`}>Pausing or closing this project does not pause or cancel an admitted Run. Reopening does not resume execution.</p>
              {#if editor.brief !== view?.brief && (view?.assessments.length ?? 0) > 0}
                <p class="review-note">Changing the brief will mark earlier concern assessments for review.</p>
              {/if}
            {/if}
          {:else if editor.mode === "concern"}
            <label for={`${uid}-statement`}>Concern <span class="required">required</span></label>
            <textarea id={`${uid}-statement`} bind:value={editor.statement} required rows="3" maxlength="4000"></textarea>
            <label for={`${uid}-criteria`}>Satisfaction conditions</label>
            <p class="field-help" id={`${uid}-criteria-help`}>What would give you enough reason to consider this concern addressed?</p>
            <textarea id={`${uid}-criteria`} bind:value={editor.criteria} rows="3" maxlength="8000" aria-describedby={`${uid}-criteria-help`}></textarea>
            {#if editor.concern_id && latestAssessment(editor.concern_id)}
              <p class="field-help">Changing the concern or its conditions will mark its earlier assessment for review.</p>
            {/if}
          {:else if editor.mode === "assessment"}
            <blockquote class="assessment-subject">{editor.statement}</blockquote>
            <details open class="judged-text">
              <summary>Requirements for this assessment</summary>
              <dl><dt>Satisfaction conditions</dt><dd class="prose">{editor.criteria || "None recorded"}</dd><dt>Brief</dt><dd class="prose">{editor.brief || "None recorded"}</dd></dl>
            </details>
            <p class="field-help">Record your judgment against the current concern, conditions, and brief. A successful Run alone does not establish sufficiency.</p>
            <label for={`${uid}-judgment`}>Judgment</label>
            <select id={`${uid}-judgment`} bind:value={editor.judgment} required>
              <option value="" disabled>Choose a judgment</option>
              <option value="insufficient">Insufficient — more is needed</option>
              <option value="sufficient">Sufficient — the conditions are met</option>
              <option value="disputed">Disputed — the conclusion is contested</option>
            </select>
            <label for={`${uid}-rationale`}>Reason <span class="required">required</span></label>
            <textarea id={`${uid}-rationale`} bind:value={editor.rationale} required rows="4" maxlength="8000"></textarea>
            <fieldset class="reference-choice">
              <legend>Cited activity</legend>
              {#each eligibleReferences as reference (reference.id)}
                <div class="citation-choice">
                  <label class="checkbox-label">
                    <input type="checkbox" bind:group={editor.reference_ids} value={reference.id} />
                    <span>{activityName(reference)}</span>
                  </label>
                  <a href={referenceHref(reference)} target="_blank" rel="noopener noreferrer" aria-label={`Open ${activityName(reference)} in new tab`}>Open in new tab ↗</a>
                </div>
              {:else}
                <p class="field-help">No activity is linked to this concern or the project. You can record a reason without a reference.</p>
              {/each}
            </fieldset>
          {:else if editor.mode === "decision"}
            <label for={`${uid}-replaces`}>Replaces decision</label>
            <select id={`${uid}-replaces`} bind:value={editor.supersedes_id}>
              <option value="">Record independently</option>
              {#if editor.supersedes_id && view?.decisions.some((item) => item.supersedes_id === editor?.supersedes_id)}
                <option value={editor.supersedes_id} disabled>Already superseded — choose how to retain this draft</option>
              {/if}
              {#each (view?.decisions ?? []).filter((item) => !view?.decisions.some((other) => other.supersedes_id === item.id)) as decision (decision.id)}
                <option value={decision.id}>{decision.statement}</option>
              {/each}
            </select>
            {#if editor.supersedes_id}
              <p class="review-note">This decision will supersede the earlier decision shown below. Both records remain visible.</p>
              <blockquote>{view?.decisions.find((decision) => decision.id === editor?.supersedes_id)?.statement}</blockquote>
            {/if}
            <label for={`${uid}-statement`}>Decision <span class="required">required</span></label>
            <textarea id={`${uid}-statement`} bind:value={editor.statement} required rows="3" maxlength="4000"></textarea>
            <label for={`${uid}-rationale`}>Reason <span class="required">required</span></label>
            <textarea id={`${uid}-rationale`} bind:value={editor.rationale} required rows="3" maxlength="8000"></textarea>
          {:else if editor.mode === "reference"}
            <p class="field-help">Link an existing Bridge conversation or a specific Orb Run. Linking a conversation does not link all of its Runs.</p>
            <div class="form-pair">
              <div>
                <label for={`${uid}-kind`}>Activity</label>
                <select id={`${uid}-kind`} bind:value={editor.reference_kind}>
                  <option value="session">Bridge conversation</option>
                  <option value="run">Orb Run</option>
                </select>
              </div>
              <div>
                <label for={`${uid}-target`}>Existing ID <span class="required">required</span></label>
                <input id={`${uid}-target`} bind:value={editor.target_id} required maxlength="128" spellcheck="false" autocomplete="off" aria-describedby={`${uid}-target-help`} />
              </div>
            </div>
            <p class="field-help" id={`${uid}-target-help`}>Use “Link to project” in Bridge or Orb to fill this in, or copy the ID after /bridge/ or /orb/ in the activity's address.</p>
            {#if editor.target_id.trim()}<a href={referenceHref({ kind: editor.reference_kind, target_id: editor.target_id.trim() })} target="_blank" rel="noopener noreferrer">Inspect this activity in a new tab ↗</a>{/if}
            <label for={`${uid}-scope`}>Related to</label>
            <select id={`${uid}-scope`} bind:value={editor.concern_id}>
              <option value="">The project as a whole</option>
              {#each view?.concerns ?? [] as concern (concern.id)}<option value={concern.id}>{concern.statement}</option>{/each}
            </select>
            <label for={`${uid}-note`}>Context note</label>
            <textarea id={`${uid}-note`} bind:value={editor.note} rows="2" maxlength="2000"></textarea>
            <p class="field-help">The link records context. It does not establish that a concern is satisfied.</p>
          {/if}
          <div class="form-footer">
            <button class="primary" type="submit" disabled={conflict}>{saving ? "Saving…" : editor.mode === "create" ? "Create project" : "Save"}</button>
            <span class="field-help">{uncertain ? "Values held for the same retry." : dirty ? "Unsaved draft" : "Changes are saved only when you submit."}</span>
          </div>
        </fieldset>
      </form>
    </section>
  {/if}

  {/snippet}

  {#if editor && !((editor.mode === "concern" || editor.mode === "assessment") && editor.concern_id)}
    {@render editorPanel()}
  {/if}

  {#if loading && !view && !catalogue}
    <p class="loading" role="status">Loading Atlas…</p>
  {:else if !projectId && catalogue && (catalogue.total > 0 || (!editor && !readError))}
    <section aria-label={catalogue.total === 0 ? "Start a project" : undefined} aria-labelledby={catalogue.total > 0 ? `${uid}-list-title` : undefined}>
      {#if catalogue.total > 0}
      <div class="section-heading">
        <h2 id={`${uid}-list-title`}>Your projects</h2>
        <span class="metadata">{catalogue.total} recorded</span>
      </div>
      {/if}
      {#if catalogue.total === 0}
        <div class="atlas-introduction panel">
          <div class="introduction-copy">
            <h2>A place for work that lasts</h2>
            <p>Start with a brief, a question, or a responsibility. Keep its concerns, decisions, and next step together as the work takes shape.</p>
            <button class="primary" type="button" disabled={loading || editorLocked} onclick={() => openEditor("create")}>New project</button>
            <p class="field-help">Begin here, then link conversations and evidence when they matter.</p>
          </div>
          <svg class="atlas-chart" viewBox="0 0 240 200" fill="none" aria-hidden="true">
            <circle cx="120" cy="100" r="74" />
            <circle cx="120" cy="100" r="52" stroke-dasharray="2 8" />
            <path d="M120 12v22m0 132v22M32 100h22m132 0h22M58 38l15 15m94 94 15 15M58 162l15-15m94-94 15-15" />
            <path class="atlas-chart__route" d="m70 122 38-47 52 48 22-55" />
            <circle class="atlas-chart__point" cx="70" cy="122" r="4" />
            <circle class="atlas-chart__point" cx="108" cy="75" r="4" />
            <circle class="atlas-chart__point" cx="160" cy="123" r="4" />
            <path class="atlas-chart__point" d="m182 61 6 7-6 7-6-7Z" />
          </svg>
        </div>
      {:else}
        <div class="list-filters">
          <label for={`${uid}-filter`}>Lifecycle on this page</label>
          <select id={`${uid}-filter`} bind:value={lifecycleFilter}>
            <option value="all">All</option>
            {#each lifecycles as lifecycle (lifecycle)}<option value={lifecycle}>{lifecycleNames[lifecycle]}</option>{/each}
          </select>
          <label class="checkbox-label"><input type="checkbox" bind:checked={reviewOnly} /> Assessment review needed</label>
          <label class="checkbox-label"><input type="checkbox" bind:checked={unassessedOnly} /> Unassessed concerns</label>
          <label class="checkbox-label"><input type="checkbox" bind:checked={insufficientOnly} /> Current insufficient judgments</label>
          <label class="checkbox-label"><input type="checkbox" bind:checked={disputedOnly} /> Current disputed judgments</label>
        </div>
        {#each lifecycles as lifecycle (lifecycle)}
          {@const items = filteredProjects.filter((item) => item.lifecycle === lifecycle)}
          {#if items.length > 0}
            <section class="lifecycle-group" aria-labelledby={`${uid}-${lifecycle}`}>
              <h3 id={`${uid}-${lifecycle}`}>{lifecycleNames[lifecycle]} <span class="metadata">{items.length}</span></h3>
              <ul class="project-grid">
                {#each items as item (item.id)}
                  <li>
                    <a class="project-card panel" href={atlasHref(item.id, linkIntent)}>
                      <h4>{item.title}</h4>
                      {#if item.review_needed_count > 0}<span class="review-count">{item.review_needed_count} {item.review_needed_count === 1 ? "assessment needs" : "assessments need"} review</span>{/if}
                      {#if item.insufficient_count > 0}<span class="review-count">{item.insufficient_count} current insufficient {item.insufficient_count === 1 ? "judgment" : "judgments"}</span>{/if}
                      {#if item.disputed_count > 0}<span class="review-count">{item.disputed_count} current disputed {item.disputed_count === 1 ? "judgment" : "judgments"}</span>{/if}
                      <p class="card-brief">{item.brief || "No brief recorded yet."}</p>
                      <div class="next-preview"><span>Proposed next step</span><p>{item.next_action || "No next step recorded."}</p></div>
                      <div class="card-foot">
                        <span>{item.concern_count} {item.concern_count === 1 ? "concern" : "concerns"} · {item.unassessed_count} unassessed</span>
                      </div>
                      <time datetime={item.updated_at}>Updated {date(item.updated_at)}</time>
                    </a>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}
        {/each}
        {#if filteredProjects.length === 0}<p class="empty">No projects on this page match these filters.</p>{/if}
        {#if catalogue.total > catalogue.limit || catalogue.offset > 0}
        <nav class="pagination" aria-label="Project pages">
          <button type="button" disabled={loading || editorLocked || catalogue.offset === 0} onclick={() => refresh(Math.max(0, (catalogue?.offset ?? 0) - (catalogue?.limit ?? 50)))}>Previous</button>
          <span>{catalogue.offset + (catalogue.projects.length ? 1 : 0)}–{catalogue.offset + catalogue.projects.length} of {catalogue.total}</span>
          <button type="button" disabled={loading || editorLocked || catalogue.offset + catalogue.projects.length >= catalogue.total} onclick={() => refresh((catalogue?.offset ?? 0) + (catalogue?.limit ?? 50))}>Next</button>
        </nav>
        {/if}
      {/if}
    </section>
  {:else if view}
    <div class="project-detail">
      <nav class="section-nav" aria-label="Project sections">
        <a href={`#${uid}-brief-title`}>Brief &amp; next step</a>
        <a href={`#${uid}-concerns-title`}>Concerns · {view.concerns.length}</a>
        <a href={`#${uid}-decisions-title`}>Decisions · {currentDecisions.length}</a>
        <a href={`#${uid}-references-title`}>Linked activity · {view.references.length}</a>
      </nav>
      {#if conflict && latestLoaded}<p class="review-note">Latest saved information is shown below. Your draft above has not been applied.</p>{/if}
      <section class="panel overview" aria-labelledby={`${uid}-brief-title`}>
        <header class="section-heading">
          <h2 id={`${uid}-brief-title`} tabindex="-1">Brief</h2>
          <button type="button" disabled={editorLocked || loading} onclick={() => openEditor("project")}>Edit project</button>
        </header>
        <div class="overview-body">
          <div class="overview-brief">
            <p class="prose">{view.brief || "No brief recorded yet."}</p>
            <p class="metadata">Updated <time datetime={view.updated_at}>{date(view.updated_at)}</time></p>
          </div>
          <div class="next-step">
            <h3>Proposed next step</h3>
            <p class="prose">{view.next_action || "No next step recorded."}</p>
            <nav class="next-links" aria-label="Continue in Bridge">
              <a href={`/bridge?choose=conversation&project=${encodeURIComponent(view.id)}`}>Choose or start a conversation →</a>
              {#each continuationTargets as { targetId, note } (targetId)}
                <a href={`${referenceHref({ kind: "session", target_id: targetId })}?project=${encodeURIComponent(view.id)}`}>{note || "Conversation"} · {targetId} →</a>
              {/each}
            </nav>
            <p class="field-help">Choose a conversation or start one in Bridge. Project context is not sent automatically.</p>
          </div>
        </div>
      </section>

      <section aria-labelledby={`${uid}-concerns-title`}>
        <header class="section-heading">
          <div><h2 id={`${uid}-concerns-title`} tabindex="-1">Concerns <span class="metadata">{view.concerns.length}</span></h2></div>
          <button class="primary" type="button" disabled={editorLocked || loading} onclick={() => openEditor("concern")}>Add concern</button>
        </header>
        {#if view.concerns.length > 1}
          <div class="concern-filters">
            <div><label for={`${uid}-concern-query`}>Find a concern</label><input id={`${uid}-concern-query`} type="search" bind:value={concernQuery} disabled={Boolean(editor)} placeholder="Search questions and conditions" /></div>
            <div><label for={`${uid}-concern-filter`}>Assessment</label>
              <select id={`${uid}-concern-filter`} bind:value={concernFilter} disabled={Boolean(editor)}>
                {#each concernFilters as filter (filter.value)}
                  <option value={filter.value}>{filter.label} ({view.concerns.filter((concern) => filter.value === "all" || concernState(concern) === filter.value).length})</option>
                {/each}
              </select>
            </div>
          </div>
          <p class="metadata" role="status">Showing {visibleConcerns.length} of {view.concerns.length} concerns</p>
          {#if pinnedConcern}<p class="field-help">The concern being edited stays visible while you compare changes.</p>{/if}
        {/if}
        <ul class="record-list">
          {#each visibleConcerns as concern (concern.id)}
            {@const latest = latestAssessment(concern.id)}
            {@const related = view.references.filter((reference) => reference.concern_id === concern.id && !latest?.reference_ids.includes(reference.id))}
            <li class="panel concern">
              <header class="section-heading">
                <h3 id={`${uid}-concern-${concern.id}`}>{concern.statement}</h3>
                <span class={['badge', needsReview(concern, latest) && 'review-badge']}>{assessmentLabel(concern)}</span>
              </header>
              <div class="criteria"><h4>Satisfaction conditions</h4><p class="prose">{concern.criteria || "No conditions recorded yet."}</p></div>
              {#if latest}
                <div class="latest-assessment">
                  {#if needsReview(concern, latest)}<p class="review-note">The concern or brief has changed since this judgment. Review is needed.</p>{/if}
                  <h4>{needsReview(concern, latest) ? "Earlier" : "Latest"} judgment: {judgmentNames[latest.judgment]}</h4>
                  <p class="prose">{latest.rationale}</p>
                  <p class="metadata">Recorded by {latest.author} · <time datetime={latest.created_at}>{date(latest.created_at)}</time></p>
                  {#if latest.reference_ids.length}
                    <p class="field-help">Cited in this judgment</p>
                    <ul class="assessment-references">
                      {#each latest.reference_ids as referenceId (referenceId)}
                        {@const reference = view.references.find((item) => item.id === referenceId)}
                        <li>{#if reference}<a href={referenceHref(reference)} target="_blank" rel="noopener noreferrer">{activityName(reference)} · Open in new tab ↗</a>{:else}Reference unavailable{/if}</li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              {:else}<p class="field-help">No assessment has been recorded.</p>{/if}
              {#if related.length}
                <p class="field-help">Related to this concern</p>
                <ul class="assessment-references">
                  {#each related as reference (reference.id)}<li><a href={referenceHref(reference)} target="_blank" rel="noopener noreferrer">{activityName(reference)} · Open in new tab ↗</a></li>{/each}
                </ul>
              {/if}
              <div class="actions concern-actions">
                <button type="button" aria-describedby={`${uid}-concern-${concern.id}`} disabled={editorLocked || loading} onclick={() => openEditor("concern", concern)}>Edit concern</button>
                <button class:primary={needsReview(concern, latest)} type="button" aria-describedby={`${uid}-concern-${concern.id}`} disabled={editorLocked || loading} onclick={() => openEditor("assessment", concern)}>{needsReview(concern, latest) ? "Review assessment" : "Record assessment"}</button>
              </div>
              {#if editor?.concern_id === concern.id && (editor.mode === "concern" || editor.mode === "assessment")}{@render editorPanel()}{/if}
              {#if latest}
                <details class="history">
                  <summary>Assessment history ({view.assessments.filter((item) => item.concern_id === concern.id).length})</summary>
                  <ol class="history-list">
                    {#each view.assessments.filter((item) => item.concern_id === concern.id).slice().reverse() as assessment (assessment.id)}
                      <li>
                        <h4>{judgmentNames[assessment.judgment]} <span class="metadata">{date(assessment.created_at)}</span></h4>
                        <p class="prose">{assessment.rationale}</p>
                        <p class="metadata">Recorded by {assessment.author}</p>
                        <details class="judged-text">
                          <summary>Text judged at the time</summary>
                          <dl><dt>Concern</dt><dd class="prose">{assessment.statement}</dd><dt>Conditions</dt><dd class="prose">{assessment.criteria || "None recorded"}</dd><dt>Brief</dt><dd class="prose">{assessment.brief || "None recorded"}</dd></dl>
                        </details>
                        {#if assessment.reference_ids.length > 0}
                          <p class="field-help">Activity cited in this judgment</p>
                          <ul class="assessment-references">
                            {#each assessment.reference_ids as referenceId (referenceId)}
                              {@const reference = view.references.find((item) => item.id === referenceId)}
                              <li>{#if reference}<a href={referenceHref(reference)}>{reference.kind === "session" ? "Conversation" : "Run"}: {reference.target_id}</a>{:else}<span>Reference unavailable</span>{/if}</li>
                            {/each}
                          </ul>
                        {/if}
                      </li>
                    {/each}
                  </ol>
                </details>
              {/if}
            </li>
          {:else}
            {#if view.concerns.length}
              <li class="panel empty"><p>No concerns match these filters.</p><button type="button" onclick={() => { concernFilter = "all"; concernQuery = ""; }}>Show all concerns</button></li>
            {:else}
              <li class="panel empty"><h3>What deserves attention?</h3><p>Add a question, requirement, or concern. It can exist before there is any result to assess.</p></li>
            {/if}
          {/each}
        </ul>
      </section>

      <div class="supporting-grid">
        <section class="panel supporting" aria-labelledby={`${uid}-decisions-title`}>
          <header class="section-heading"><h2 id={`${uid}-decisions-title`} tabindex="-1">Decisions</h2><button type="button" disabled={editorLocked || loading} onclick={() => openEditor("decision")}>Record decision</button></header>
          {#snippet decisionRecord(decision: AtlasDecision)}
              {@const replacement = view.decisions.find((item) => item.supersedes_id === decision.id)}
              <li class="decision">
                <h3>{decision.statement}</h3>
                {#if replacement}<span class="badge">Superseded</span>{:else if decision.supersedes_id}<span class="badge">Replaces an earlier decision</span>{/if}
                <p class="prose">{decision.rationale}</p>
                <p class="metadata">{decision.author} · <time datetime={decision.created_at}>{date(decision.created_at)}</time></p>
                {#if replacement}<p class="field-help">Replaced by: {replacement.statement}</p>{:else}<button type="button" disabled={editorLocked || loading} onclick={() => openEditor("decision", undefined, decision.id)}>Supersede</button>{/if}
              </li>
          {/snippet}
          <ul class="record-list">
            {#each currentDecisions as decision (decision.id)}
              {@render decisionRecord(decision)}
            {:else}<li class="field-help">No decisions recorded. Keep important choices and their reasons here.</li>{/each}
          </ul>
          {#if earlierDecisions.length}
            <details class="history">
              <summary>Earlier decisions ({earlierDecisions.length})</summary>
              <ul class="record-list">
                {#each earlierDecisions as decision (decision.id)}{@render decisionRecord(decision)}{/each}
              </ul>
            </details>
          {/if}
        </section>

        <section class="panel supporting" aria-labelledby={`${uid}-references-title`}>
          <header class="section-heading"><h2 id={`${uid}-references-title`} tabindex="-1">Linked activity</h2><button type="button" disabled={editorLocked || loading} onclick={() => openEditor("reference")}>Link activity</button></header>
          <p class="field-help">Context from Bridge and Orb. Links alone do not establish sufficiency.</p>
          <ul class="record-list">
            {#each view.references as reference (reference.id)}
              <li class="reference">
                <a href={referenceHref(reference)}>{reference.kind === "session" ? "Conversation in Bridge" : "Run in Orb"} →</a>
                <code>{reference.target_id}</code>
                <p class="field-help">{reference.concern_id ? view.concerns.find((item) => item.id === reference.concern_id)?.statement ?? "Concern unavailable" : "Project as a whole"}</p>
                {#if reference.note}<p class="prose">{reference.note}</p>{/if}
                <p class="metadata">Linked by {reference.author} · {date(reference.created_at)}</p>
              </li>
            {:else}<li class="field-help">No linked activity. This project can stand on its own.</li>{/each}
          </ul>
        </section>
      </div>
    </div>
  {/if}
</div>

<style>
  .atlas {
    width: min(100%, 86rem);
    min-width: 0;
    margin-inline: auto;
    padding: clamp(1rem, 2vw, 1.5rem);
    color: var(--color-bone);
  }
  .atlas-heading, .section-heading, .actions, .form-footer, .pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  .atlas-heading { align-items: flex-start; margin-bottom: 1rem; }
  .atlas-heading h1 { margin-block: 0.35rem 0.6rem; font-size: clamp(1.8rem, 2.5vw, 2.2rem); letter-spacing: 0.07em; overflow-wrap: anywhere; }
  .atlas-heading p { color: var(--color-parchment); max-width: 48rem; }
  .back-link { display: inline-block; margin-bottom: 0.6rem; }
  h2 { font-size: var(--text-xl); font-weight: 500; }
  h3 { font-size: var(--text-lg); font-weight: 500; overflow-wrap: anywhere; }
  h4 { font-size: var(--text-base); font-weight: 600; }
  p { margin-block: 0.45rem; }
  a { color: var(--color-rune); text-underline-offset: 0.2em; }
  button, input, textarea, select { font: inherit; }
  button {
    min-height: 2.75rem;
    padding: 0.55rem 0.85rem;
    border: 1px solid var(--color-engraving);
    border-radius: var(--radius-rune);
    background: var(--color-obsidian-2);
    color: var(--color-bone);
    cursor: pointer;
  }
  button:hover:not(:disabled) { border-color: var(--color-rune); }
  button.primary { color: var(--color-rune); border-color: var(--color-rune-dim); background: color-mix(in srgb, var(--color-rune) 8%, var(--color-obsidian)); }
  button:disabled { opacity: 0.55; cursor: not-allowed; }
  :is(button, a, input, select, textarea, summary):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .actions { justify-content: flex-start; }
  .panel { border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-obsidian); }
  .section-heading { margin-bottom: 1rem; align-items: flex-start; }
  .section-heading > div { min-width: 0; }
  .badge { display: inline-flex; padding: 0.2rem 0.6rem; border: 1px solid var(--color-engraving); border-radius: 999px; color: var(--color-parchment); font-size: var(--text-xs); white-space: nowrap; }
  .review-badge { color: var(--color-heat); border-color: var(--color-heat-deep); }
  .metadata, .field-help { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.6; }
  .metadata { font-weight: 400; }
  .notice, .fault, .review-note { padding: 0.85rem 1rem; margin-block: 0.8rem; border-radius: var(--radius-rune); }
  .notice { color: var(--color-frost); border: 1px solid var(--color-rune-dim); background: var(--color-obsidian); }
  .fault { color: var(--color-ember); border: 1px solid var(--color-ember); background: var(--color-obsidian); }
  .fault p { color: var(--color-parchment); overflow-wrap: anywhere; }
  .review-note { color: var(--color-parchment); border-left: 3px solid var(--color-heat); background: color-mix(in srgb, var(--color-heat) 6%, var(--color-obsidian)); }
  .loading { padding-block: 2rem; color: var(--color-parchment); }
  .editor { padding: clamp(1rem, 2vw, 1.5rem); margin-bottom: 1.5rem; border-color: var(--color-rune-dim); }
  .editor form { max-width: 58rem; }
  .concern .editor { margin-block: 1rem; background: var(--color-void); }
  .section-nav, .next-links { display: flex; flex-wrap: wrap; gap: 0.65rem 1.2rem; }
  .section-nav { padding-block: 0.35rem; border-bottom: 1px solid var(--color-engraving); }
  .section-nav a, .next-links a { display: inline-flex; align-items: center; min-height: 2.75rem; }
  .next-links { margin-top: 0.75rem; overflow-wrap: anywhere; }
  h2[id], h3[id] { scroll-margin-top: 8rem; }
  .link-intent { display: grid; gap: 0.65rem; padding: 1.1rem; margin-bottom: 1rem; overflow-wrap: anywhere; }
  .link-intent h2 { font-size: var(--text-lg); }
  .comparison { margin-top: 1.2rem; }
  .comparison-field { border-top: 1px solid var(--color-engraving); padding-block: 1rem; }
  .comparison-values { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-block: 0.5rem; }
  .comparison-values > div { min-width: 0; padding: 0.7rem; background: var(--color-void); }
  .comparison-values span { font-size: var(--text-sm); color: var(--color-frost); }
  .citation-choice { display: grid; gap: 0.15rem; margin-block: 0.65rem; }
  .citation-choice .checkbox-label { margin: 0; }
  .citation-choice > a { justify-self: start; margin-left: 1.85rem; min-height: 2.5rem; display: inline-flex; align-items: center; }
  .concern-filters { display: grid; grid-template-columns: minmax(0, 1fr) minmax(12rem, 0.5fr); gap: 1rem; margin-bottom: 0.6rem; }
  .concern-filters label { margin-top: 0; }
  fieldset { min-width: 0; padding: 0; margin: 0; border: 0; }
  label, legend { display: block; margin-top: 1rem; margin-bottom: 0.4rem; font-weight: 500; }
  input:not([type="checkbox"]), textarea, select {
    display: block;
    width: 100%;
    min-width: 0;
    min-height: 2.75rem;
    padding: 0.6rem 0.7rem;
    border: 1px solid var(--color-engraving);
    border-radius: var(--radius-rune);
    background: var(--color-void);
    color: var(--color-bone);
  }
  textarea { resize: vertical; line-height: 1.6; }
  :is(input, textarea, select):disabled { opacity: 0.7; }
  .required { margin-left: 0.3rem; color: var(--color-parchment); font-size: var(--text-xs); font-weight: 400; }
  .form-pair { display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; }
  .form-footer { justify-content: flex-start; margin-top: 1.25rem; }
  .checkbox-label { display: flex; align-items: flex-start; gap: 0.65rem; font-weight: 400; overflow-wrap: anywhere; }
  input[type="checkbox"] { flex: 0 0 auto; width: 1.2rem; height: 1.2rem; margin-top: 0.15rem; accent-color: var(--color-rune); }
  .reference-choice { margin-top: 1rem; }
  blockquote { padding: 0.6rem 1rem; margin-block: 0.75rem; border-left: 2px solid var(--color-rune-dim); overflow-wrap: anywhere; }
  .list-filters { display: flex; align-items: center; flex-wrap: wrap; gap: 0.8rem; padding-block: 0.35rem 1rem; }
  .list-filters label { margin: 0; }
  .list-filters select { width: auto; min-width: 8rem; }
  .lifecycle-group { margin-block: 0.5rem 1.75rem; }
  .lifecycle-group > h3 { margin-bottom: 0.7rem; }
  .project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr)); gap: 1rem; list-style: none; margin: 0; padding: 0; }
  .project-grid li, .record-list, .history-list, .assessment-references { list-style: none; margin: 0; padding: 0; }
  .project-card { display: flex; flex-direction: column; height: 100%; padding: 1.15rem; color: var(--color-bone); text-decoration: none; }
  .project-card:hover { border-color: var(--color-rune-dim); }
  .project-card h4 { color: var(--color-frost); font-size: var(--text-lg); overflow-wrap: anywhere; }
  .card-brief { color: var(--color-parchment); display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3; overflow: hidden; }
  .next-preview { margin-block: auto 0; padding-top: 1rem; }
  .next-preview > span { color: var(--color-parchment); font-size: var(--text-xs); }
  .next-preview p { font-size: var(--text-sm); overflow-wrap: anywhere; }
  .card-foot { display: flex; flex-wrap: wrap; gap: 0.4rem 0.8rem; margin-top: 0.8rem; padding-top: 0.7rem; border-top: 1px solid var(--color-engraving); font-size: var(--text-xs); color: var(--color-parchment); }
  .review-count { color: var(--color-heat); }
  .project-card time { margin-top: 0.6rem; font-size: var(--text-xs); color: var(--color-parchment); }
  .pagination { justify-content: center; padding-block: 0.5rem; color: var(--color-parchment); }
  .empty { padding: 1.8rem; color: var(--color-parchment); }
  .empty h3 { color: var(--color-bone); }
  .empty p { max-width: 42rem; margin-block: 0.6rem 1rem; }
  .atlas-introduction { display: flex; align-items: center; justify-content: space-between; gap: 2rem; padding: clamp(1.5rem, 4vw, 3rem); background: linear-gradient(115deg, var(--color-obsidian), color-mix(in srgb, var(--color-tertiary) 15%, var(--color-obsidian))); }
  .introduction-copy { max-width: 38rem; }
  .introduction-copy h2 { font-family: var(--font-rune); font-size: clamp(1.6rem, 3vw, 2.2rem); line-height: 1.2; text-wrap: balance; }
  .introduction-copy > p { color: var(--color-parchment); margin-block: 1rem 1.4rem; line-height: 1.7; }
  .introduction-copy > .field-help { margin-block: 0.85rem 0; }
  .atlas-chart { width: clamp(10rem, 22vw, 16rem); flex-shrink: 0; stroke: var(--color-rune-dim); stroke-width: 1; }
  .atlas-chart__route { stroke: var(--color-rune); stroke-width: 1.5; }
  .atlas-chart__point { fill: var(--color-obsidian); stroke: var(--color-rune); stroke-width: 1.5; }
  .project-detail { display: grid; gap: 1.2rem; }
  .overview-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1.5rem; align-items: start; }
  .overview-brief { max-width: 44rem; }
  .overview-brief .metadata { margin-top: 1rem; }
  .overview, .concern, .supporting { padding: clamp(1rem, 2vw, 1.5rem); }
  .prose { white-space: pre-wrap; overflow-wrap: anywhere; color: var(--color-parchment); line-height: 1.65; }
  .next-step { padding: 0 0 0 1.1rem; border-left: 2px solid var(--color-rune-dim); }
  .record-list { display: grid; gap: 1rem; }
  .concern .section-heading h3 { flex: 1 1 18rem; }
  .criteria h4 { color: var(--color-parchment); font-weight: 500; }
  .latest-assessment { margin-top: 1rem; }
  .concern-actions { margin-top: 1rem; }
  .history { margin-top: 1rem; border-top: 1px solid var(--color-engraving); padding-top: 0.7rem; }
  summary { min-height: 2.75rem; padding-block: 0.6rem; color: var(--color-rune); cursor: pointer; }
  .history-list > li { padding-block: 1rem; border-top: 1px solid var(--color-engraving); }
  .history-list h4 .metadata { display: inline-block; margin-left: 0.4rem; }
  .judged-text { margin-top: 0.5rem; }
  dl { margin: 0.6rem 0 1rem; padding: 0.75rem 1rem; background: var(--color-void); }
  dt { font-size: var(--text-sm); color: var(--color-frost); }
  dd { margin: 0.25rem 0 0.75rem; }
  .assessment-references { display: grid; gap: 0.5rem; overflow-wrap: anywhere; }
  .supporting-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: start; }
  .supporting { min-width: 0; }
  .decision, .reference { border-top: 1px solid var(--color-engraving); padding-top: 1rem; }
  .decision .badge { margin-block: 0.5rem; }
  .reference code { display: block; margin-top: 0.35rem; overflow-wrap: anywhere; font-size: var(--text-xs); }
  @media (max-width: 48rem) {
    .atlas-introduction { gap: 0; }
    .atlas-chart { display: none; }
    .supporting-grid, .form-pair, .comparison-values, .concern-filters, .overview-body { grid-template-columns: 1fr; }
    .atlas-heading { gap: 1rem; }
    .section-heading { gap: 0.8rem; }
    .atlas { padding: 1rem; }
    .editor input, .editor textarea, .editor select { font-size: 1rem; }
  }
</style>
