<script lang="ts">
  import { beforeNavigate, goto } from "$app/navigation";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { untrack } from "svelte";
  import { ApiError, bootstrapCanvasWorkspace, changeAtlasProject, createCanvasProject, getAtlasProject } from "$lib/api/client";
  import type { AtlasMutation, AtlasProject, CanvasProjectCreate } from "$lib/api/models";
  import { blankDocument, replaceDocument, validateDocument } from "$lib/canvas/engine";
  import type { Document as BoardDocument } from "$lib/canvas/types";
  import CanvasView from "./CanvasView.svelte";

  let { projectId, newRequested = false }: { projectId?: string; newRequested?: boolean } = $props();
  type Pending =
    | { kind: "create"; body: CanvasProjectCreate }
    | { kind: "change"; projectId: string; body: AtlasMutation };

  let project = $state.raw<AtlasProject | null>(null);
  let initialDocument = $state.raw<BoardDocument | null>(null);
  let localDocument = $state.raw<BoardDocument | null>(null);
  let savedFingerprint = $state("");
  let boardKey = $state(0);
  let loading = $state(true);
  let saving = $state(false);
  let authoringBusy = $state(false);
  let readError = $state("");
  let saveError = $state("");
  let notice = $state("");
  let pending = $state.raw<Pending | null>(null);
  let uncertain = $state(false);
  let conflict = $state(false);
  let comparison = $state.raw<AtlasProject | null>(null);
  let comparing = $state(false);
  let generation = 0;
  let readController: AbortController | undefined;
  let leaving = false;
  let dirty = $derived(localDocument !== null && JSON.stringify(localDocument) !== savedFingerprint);
  let guarded = $derived(!leaving && (dirty || saving || uncertain || authoringBusy));
  let locked = $derived(loading || saving || uncertain || authoringBusy);

  function message(cause: unknown, fallback: string) { return cause instanceof Error ? cause.message : fallback; }
  function leaveMessage() {
    return uncertain ? "This request may already have reached LychD. Leave and lose the prepared retry?" :
      saving ? "A project request is still in progress. Leave before its outcome is known?" :
      "Leave Canvas and discard local changes that have not been saved to LychD?";
  }
  beforeNavigate((navigation) => {
    if (!navigation.willUnload && navigation.to && navigation.from && navigation.to.url.pathname === navigation.from.url.pathname && navigation.to.url.search === navigation.from.url.search) return;
    if (!guarded) return;
    if (authoringBusy) { navigation.cancel(); notice = "Finish the gesture, capture or proposal review before leaving this board."; return; }
    if (navigation.type === "leave") navigation.cancel();
    else if (!window.confirm(leaveMessage())) navigation.cancel();
  });
  function guardUnload(event: BeforeUnloadEvent) {
    if (guarded) { event.preventDefault(); event.returnValue = ""; }
  }

  // Route identity drives external reads; replacement is deliberate and never follows local edits.
  $effect(() => {
    const id = projectId;
    const create = newRequested;
    return untrack(() => {
      const scope = ++generation;
      readController?.abort();
      project = null; initialDocument = null; localDocument = null; savedFingerprint = "";
      loading = true; saving = false; authoringBusy = false; readError = ""; saveError = "";
      pending = null; uncertain = false; conflict = false; comparison = null; leaving = false;
      if (create && !id) { loading = false; void createNew(false); }
      else void load(scope, id);
      return () => { generation++; readController?.abort(); };
    });
  });

  function install(next: AtlasProject) {
    if (next.workspace_state === "discarded") {
      project = next; initialDocument = null; localDocument = null;
      notice = "This draft was discarded. Open Atlas to choose another project.";
      return;
    }
    const document = next.canvas_document ? validateDocument(next.canvas_document) : blankDocument(Array.from(next.title).slice(0, 120).join(""));
    project = next; initialDocument = document; localDocument = document;
    savedFingerprint = next.canvas_document ? JSON.stringify(document) : "";
    boardKey++; authoringBusy = false;
    notice = next.canvas_document ? "" : "This project has no retained board yet. Save board to attach this blank document.";
  }
  async function load(scope = generation, id = projectId) {
    loading = true; readError = "";
    const controller = new AbortController(); readController?.abort(); readController = controller;
    try {
      const next = id ? await getAtlasProject(id, controller.signal) : await bootstrapCanvasWorkspace();
      if (scope !== generation || controller.signal.aborted) return;
      install(next);
    } catch (cause) {
      if (scope === generation && !controller.signal.aborted) readError = message(cause, "Canvas could not be loaded.");
    } finally { if (scope === generation && !controller.signal.aborted) loading = false; }
  }
  function updated(document: BoardDocument) { localDocument = document; }

  async function createNew(confirm = true) {
    if (saving || uncertain || authoringBusy) return;
    if (confirm && dirty && !window.confirm("Create a new canvas and leave your unsaved local board changes?")) return;
    const document = blankDocument("Untitled canvas");
    pending = { kind: "create", body: { id: crypto.randomUUID(), canvas_document: document } };
    await send();
  }
  async function save() {
    if (!project || !localDocument || locked || conflict) return;
    pending = { kind: "change", projectId: project.id, body: {
      request_id: crypto.randomUUID(), expected_version: project.version,
      change: { kind: "canvas.save", canvas_document: structuredClone(localDocument) }
    } };
    await send();
  }
  async function keep() {
    if (!project || locked || dirty || conflict) return;
    pending = { kind: "change", projectId: project.id, body: {
      request_id: crypto.randomUUID(), expected_version: project.version, change: { kind: "project.keep" }
    } };
    await send();
  }
  async function discard() {
    if (!project || project.workspace_state !== "draft" || locked || conflict) return;
    if (!window.confirm("Discard this draft project and its board? This removes it from Atlas.")) return;
    pending = { kind: "change", projectId: project.id, body: {
      request_id: crypto.randomUUID(), expected_version: project.version, change: { kind: "project.discard" }
    } };
    await send();
  }
  async function send() {
    const request = pending;
    if (!request || saving) return;
    const scope = generation;
    const previouslyUncertain = uncertain;
    saving = true; saveError = ""; notice = "";
    let result: AtlasProject;
    try {
      result = request.kind === "create" ? await createCanvasProject(structuredClone(request.body)) :
        await changeAtlasProject(request.projectId, structuredClone(request.body));
    } catch (cause) {
      if (scope !== generation) return;
      const status = cause instanceof ApiError ? cause.status : undefined;
      const confirmedConflict = status === 409 && cause instanceof ApiError && cause.code === "atlas_write_rejected";
      const definitive = confirmedConflict || (!previouslyUncertain && status !== undefined && status >= 400 && status < 500 && status !== 408);
      uncertain = !definitive; conflict = confirmedConflict && request.kind === "change"; comparison = null;
      if (definitive) pending = null;
      saveError = message(cause, "The project request could not be completed.");
      saving = false; return;
    }
    if (scope !== generation) return;
    pending = null; uncertain = false; conflict = false; comparison = null; saving = false;
    if (result.workspace_state === "discarded") {
      leaving = true; project = result; localDocument = null; initialDocument = null;
      await navigate(resolve("/atlas")); return;
    }
    if (request.kind === "create") {
      install(result); leaving = true;
      await navigate(resolve(`/canvas/${encodeURIComponent(result.id)}`), true);
      return;
    }
    project = result;
    if (request.body.change.kind === "canvas.save") savedFingerprint = result.canvas_document ? JSON.stringify(result.canvas_document) : "";
    notice = request.body.change.kind === "project.keep" ? "Project kept in Atlas." : "Board saved to LychD with its undo and redo history.";
  }
  async function navigate(destination: string, replaceState = false) {
    try { await goto(destination, replaceState ? { replace: true } : undefined); }
    catch (cause) { leaving = false; saveError = message(cause, "The project was saved, but its destination could not be opened."); }
  }
  async function compareSaved() {
    if (!project || comparing) return;
    const scope = generation, id = project.id; comparing = true; saveError = "";
    try {
      const next = await getAtlasProject(id);
      if (scope === generation && project?.id === id) comparison = next;
    } catch (cause) { if (scope === generation) saveError = message(cause, "The saved project could not be loaded for comparison."); }
    finally { if (scope === generation) comparing = false; }
  }
  function reconcile() {
    if (!comparison || comparison.workspace_state === "discarded" || authoringBusy) return;
    try {
      if (localDocument && comparison.canvas_document && localDocument.scene.id !== comparison.canvas_document.scene.id) {
        localDocument = replaceDocument(comparison.canvas_document, localDocument);
        initialDocument = localDocument; boardKey++;
      }
      project = comparison;
      savedFingerprint = comparison.canvas_document ? JSON.stringify(validateDocument(comparison.canvas_document)) : "";
      comparison = null; conflict = false; saveError = "";
      notice = "Saved version selected as the new save basis. Local board content is preserved; review it and Save board explicitly.";
    } catch (cause) { saveError = message(cause, "The local document could not be bound to the saved board."); }
  }
  function downloadSaved() {
    if (!comparison?.canvas_document) return;
    const document = validateDocument(comparison.canvas_document);
    const url = URL.createObjectURL(new Blob([JSON.stringify(document)], { type: "application/json" }));
    const link = window.document.createElement("a"); link.href = url; link.download = `saved-canvas-v${comparison.version}.canvas.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>

<svelte:head><title>{project?.title ?? "Canvas"} · Canvas — LychD</title></svelte:head>
<svelte:window onbeforeunload={guardUnload} />

<section class="canvas-workspace" aria-label="Canvas project workspace">
  <header class="workspace-heading">
    <div class="workspace-identity"><a href={resolve("/atlas")}>Atlas · All projects</a><h1>{project?.title ?? "Canvas workspace"}</h1></div>
    <div class="workspace-actions">
      {#if project && project.workspace_state !== "discarded"}
        <a href={resolve(`/atlas/${encodeURIComponent(project.id)}`)}>Project record</a>
        <button type="button" class="primary" onclick={save} disabled={locked || conflict || !dirty}>Save board</button>
        {#if project.workspace_state === "draft"}<button type="button" onclick={keep} disabled={locked || dirty || conflict}>Keep project</button><button type="button" onclick={discard} disabled={locked || conflict}>Discard draft</button>{/if}
      {/if}
      <button type="button" onclick={() => createNew()} disabled={locked}>New canvas</button>
      <a href={resolve("/canvas/local")}>Portable local board</a>
    </div>
  </header>
  {#if loading}<p role="status">Loading Canvas project…</p>{/if}
  {#if readError}<div class="workspace-error" role="alert"><p>{readError}</p><button type="button" onclick={() => load()}>Retry loading Canvas</button></div>{/if}
  {#if project}<div class="workspace-context">
    <span class="workspace-state">{project.builtin ? "Pinned LychD project" : project.workspace_state === "draft" ? "Draft project" : project.workspace_state === "discarded" ? "Discarded draft" : "Kept project"}</span>
    {#if initialDocument}
      <span class="retention" role="status" aria-live="polite">{saving ? "Saving project request…" : uncertain ? "Request outcome unknown · prepared retry retained" : dirty ? "Local board changes have not been saved to LychD" : `Board retained in LychD · project version ${project.version}`}{#if authoringBusy}<span> · Finish gesture, capture or proposal review before saving or switching.</span>{/if}</span>
      {#if project.builtin}<span class="map-caption">Static architecture map · selected canonical relationships. <a href="https://hexanomicon.dev/state-of-the-work/">State of Work</a></span>{/if}
      {#if project.workspace_state === "draft" && dirty}<span class="workspace-hint">Save board before keeping this draft project.</span>{/if}
    {/if}
  </div>{/if}
  {#if saveError}<div class="workspace-error" role="alert"><strong>{uncertain ? "This request may already have reached LychD." : conflict ? "The project changed while this board was open. Your local board is preserved." : "The project request was refused."}</strong><p>{saveError}</p>
    {#if uncertain}<button type="button" onclick={send} disabled={saving}>Retry same request</button>{/if}
  </div>{/if}
  {#if conflict}<section class="comparison" aria-label="Saved project comparison"><button type="button" onclick={compareSaved} disabled={comparing}>{comparing ? "Loading saved project…" : "Load saved version for comparison"}</button>
    {#if comparison}<p>Saved project version {comparison.version}: {comparison.title}. {comparison.workspace_state === "discarded" ? "This draft has been discarded; your local board remains available to download." : `Saved board revision ${comparison.canvas_document?.scene.revision ?? "unavailable"}. Local board revision ${localDocument?.scene.revision ?? "unavailable"}.`}</p>
      {#if comparison.canvas_document}<p>Saved board: {comparison.canvas_document.scene.title} · {comparison.canvas_document.scene.nodes.length} nodes · {comparison.canvas_document.scene.edges.length} connections · {comparison.canvas_document.scene.strokes.length} ink records.</p><button type="button" onclick={downloadSaved}>Download saved board for comparison</button>{/if}
      {#if comparison.workspace_state !== "discarded"}<p>Using this basis allows your next save to replace the saved board with the local board. Download the saved board first to retain both versions.</p><button type="button" onclick={reconcile} disabled={authoringBusy}>Use saved version as save basis</button>{/if}
    {/if}
  </section>{/if}
  {#if notice}<p class="workspace-notice" role="status">{notice}</p>{/if}
  {#if initialDocument}{#key boardKey}<CanvasView {initialDocument} managed onchange={updated} onbusy={(active) => authoringBusy = active} />{/key}{/if}
</section>

<style>
.canvas-workspace { min-width:0; width:100%; }
  .workspace-heading { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem; padding:1.1rem 1.25rem .75rem; }
  .workspace-identity { min-width:0; flex:1; }
  .workspace-identity h1 { margin:.4rem 0 0; font-size:1.25rem; font-weight:600; letter-spacing:-.035em; line-height:1.35; color:var(--color-bone); overflow-wrap:anywhere; }
  .workspace-identity a,.workspace-actions a,.map-caption a { color:var(--color-ash); font-size:var(--text-xs); text-underline-offset:.2em; }
  .workspace-identity a:hover,.workspace-actions a:hover,.map-caption a:hover { color:var(--color-rune); }
  .workspace-state,.workspace-hint,.retention,.map-caption { color:var(--color-ash); font-size:var(--text-2xs); }
  .workspace-state { color:var(--color-parchment); }
  .workspace-actions { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:.5rem; max-width:33rem; }
  button { min-height:2.25rem; padding:.5rem .75rem; border:1px solid var(--color-control-border); border-radius:var(--radius-rune); background:var(--color-obsidian); color:var(--color-parchment); font:var(--text-xs)/1.4 var(--font-body); cursor:pointer; }
  button:hover:not(:disabled) { color:var(--color-bone); background:var(--color-obsidian-2); }
  button:disabled { opacity:.45; cursor:default; }
  .primary { color:var(--color-void); background:var(--color-bone); border-color:var(--color-bone); font-weight:600; }
  button:focus-visible,a:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  .workspace-context { display:flex; flex-wrap:wrap; align-items:baseline; gap:.35rem .85rem; margin-inline:1.25rem; padding:.25rem 0 .75rem; border-bottom:1px solid var(--color-engraving); line-height:1.6; }
  .workspace-context > span { margin:0; }
  .workspace-notice { margin:.5rem 1.25rem; color:var(--color-parchment); font-size:var(--text-xs); }
  .workspace-error,.comparison { margin:1rem 1.25rem; padding:1rem; border:1px solid var(--color-control-border); border-radius:var(--radius-panel); color:var(--color-parchment); background:var(--color-obsidian); font-size:var(--text-sm); line-height:1.7; }
  .workspace-error { border-left:3px solid var(--color-heat); }
  @container work-area (max-width:48rem) { .workspace-heading { align-items:start; flex-direction:column; padding-inline:1rem; }.workspace-actions { justify-content:flex-start; max-width:none; }.workspace-context { margin-inline:1rem; } }
</style>
