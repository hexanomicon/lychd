<script lang="ts">
  import { getContext, onMount, tick, untrack } from "svelte";
  import { beforeNavigate } from "$app/navigation";
  import { applyProposal, arrangeScene, blankDocument, boundsOfSelection, commit, deleteSelection, exampleDocument, makePacket, moveSelection, pngArtwork, redo, renameNode, replaceDocument, tidyProposal, undo, validateDocument, validateProposal } from "$lib/pages/canvas/state/engine";
  import type { CanvasNode, Document as BoardDocument, Packet, Proposal, Scene, Tool } from "$lib/pages/canvas/state/types";
  import { CANVAS_COMMAND_HELP, isCanvasCommandCurrent, planCanvasCommand, type CanvasCommandPlan } from "$lib/pages/canvas/state/commands";
  import { workCommandKey, type CommandResult, type CommandTarget, type WorkCommandRegistry } from "$lib/shell/state/work-commands";
  import CanvasSurface from "./CanvasSurface.svelte";
  import CanvasObjects from "./CanvasObjects.svelte";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import PageHeader from "$lib/components/shared/PageHeader.svelte";

  let { initialDocument, managed = false, onchange, onbusy }: {
    initialDocument?: BoardDocument;
    managed?: boolean;
    onchange?: (document: BoardDocument) => void;
    onbusy?: (busy: boolean) => void;
  } = $props();
  type Review = { scene: Scene; sceneId: string; revision: number; title: string; summary: string; author: string; proposal: Proposal | null; packet: Packet | null; commandPlan?: CanvasCommandPlan; commandTarget?: CommandTarget };
  const workCommands = getContext<WorkCommandRegistry | undefined>(workCommandKey);
  let unregisterCommands: (() => void) | undefined;
  let commandsMounted = false;
  let registeredIdentity = "";
  const commandExamples = ["add node Vessel then add database Postgres then connect Vessel to Postgres", "rename selected to New label", "connect selected to Postgres", "move selected by 40, -20", "arrange selected"];
  let board = $state.raw<BoardDocument>(untrack(() => initialDocument ? validateDocument(initialDocument) : exampleDocument()));
  let selected = $state.raw<string[]>([]);
  let tool = $state<Tool>("select");
  let objectsOpen = $state(false);
  let helpOpen = $state(false);
  let unexported = $state(false);
  let fileState = $state(untrack(() => managed ? "Loaded project document" : "Temporary example · download to keep"));
  let notice = $state(untrack(() => managed ? "Project board loaded. Save to retain edits in LychD, or download a portable copy." : "Illustrative example. Draw, select a region, then try Tidy or capture a selection packet."));
  let error = $state("");
  let instruction = $state("");
  let capturing = $state(false);
  let gestureBusy = $state(false);
  let pending = $state.raw<Review | null>(null);
  let commandTargetCurrent = $state(true);
  let original = $state(false);
  let packet = $state.raw<Packet | null>(null);
    let surface: CanvasSurface;
  let root: HTMLElement | undefined;
  function attachRoot(element: HTMLElement) { root = element; return () => { root = undefined; }; }
  function chooseFile(kind: "board" | "proposal") { root?.querySelector<HTMLInputElement>(`[data-file="${kind}"]`)?.click(); }
  let scene = $derived(board.scene);
  let stale = $derived(pending !== null && (pending.sceneId !== scene.id || pending.revision !== scene.revision || (pending.commandPlan !== undefined && (!commandTargetCurrent || !isCanvasCommandCurrent(pending.commandPlan, scene, selected)))));
  let packetStale = $derived(packet !== null && (packet.scene.id !== scene.id || packet.scene.revision !== scene.revision));
  let displayScene = $derived(pending && !original && !stale ? pending.scene : scene);
  let editingLocked = $derived(capturing || pending !== null || gestureBusy);
  let count = $derived(scene.nodes.length + scene.edges.length + scene.strokes.filter((stroke) => !stroke.archived).length);
  const tools: { key: Tool; label: string; shortcut: string }[] = [
    { key: "draw", label: "Draw", shortcut: "D" }, { key: "lasso", label: "Lasso", shortcut: "L" }, { key: "select", label: "Select", shortcut: "V" },
    { key: "box", label: "Node", shortcut: "B" }, { key: "connect", label: "Connect", shortcut: "C" }, { key: "pan", label: "Pan", shortcut: "H" }
  ];

  function previewNodeDescription(node: CanvasNode) {
    return `${node.label || "Untitled node"} · ${node.kind} · position (${node.x}, ${node.y}) · size ${node.width} × ${node.height} · ${node.pinned ? "pinned" : "not pinned"}`;
  }
  function previewEndpoint(proposed: Scene, id: string) {
    return proposed.nodes.find((node) => node.id === id)?.label || "Untitled node";
  }
  function selectionKey() { return JSON.stringify([...selected].sort()); }
  function commandRevision() { return String(scene.revision); }
  function syncCommands(replace = false) {
    if (!workCommands || !commandsMounted) return;
    const identity = JSON.stringify([scene.id, scene.title]);
    if (replace || identity !== registeredIdentity) {
      unregisterCommands?.();
      registeredIdentity = identity;
      unregisterCommands = workCommands.register({
        instrument: "canvas", id: scene.id, label: scene.title,
        snapshot: () => ({ revisionKey: commandRevision(), selectionKey: selectionKey(), commands: commandExamples }),
        execute: previewCommand
      });
    } else workCommands.refresh();
  }
  onMount(() => {
    commandsMounted = true;
    syncCommands(true);
    const unsubscribe = workCommands?.subscribe(() => {
      commandTargetCurrent = !pending?.commandTarget || !!workCommands?.isCurrent(pending.commandTarget);
    });
    return () => { commandsMounted = false; unsubscribe?.(); unregisterCommands?.(); unregisterCommands = undefined; };
  });
  function previewCommand(text: string, captured: CommandTarget): CommandResult {
    if (!commandsMounted || !workCommands?.isCurrent(captured) || captured.id !== scene.id ||
        captured.revisionKey !== commandRevision() || captured.selectionKey !== selectionKey()) {
      return { status: "stale", summary: "The Canvas scene or selection changed. Capture the current target again." };
    }
    if (editingLocked) return { status: "unavailable", summary: "Finish the current Canvas gesture, capture or preview first." };
    try {
      const commandPlan = planCanvasCommand(scene, selected, text, { origin: surface?.center() ?? { x: 300, y: 220 } });
      commandTargetCurrent = true;
      const review: Review = { scene: commandPlan.scene, sceneId: scene.id, revision: scene.revision,
        title: "Canvas command preview", summary: commandPlan.summary, author: "Local command helper · no model",
        proposal: null, packet: null, commandPlan, commandTarget: captured };
      pending = review;
      original = false; error = "";
      busy();
      if (!scene.nodes.length && !scene.strokes.some((stroke) => !stroke.archived)) {
        void tick().then(() => {
          if (commandsMounted && pending === review && !original && workCommands?.isCurrent(captured)) surface?.fit();
        });
      }
      notice = "Preview only. Apply to keep this command as one undoable change.";
      return { status: "preview", summary: commandPlan.summary };
    } catch (cause) {
      fail(cause);
      return { status: "unsupported", summary: error };
    }
  }

  beforeNavigate((navigation) => {
    if (managed) return;
    if (!unexported || navigation.willUnload) return;
    if (!window.confirm("This board has changes that have not been downloaded. Leave and discard this draft?")) navigation.cancel();
  });
  function guardUnload(event: BeforeUnloadEvent) { if (!managed && (unexported || capturing)) { event.preventDefault(); event.returnValue = ""; } }
  function changed() { syncCommands(); onchange?.(structuredClone(board)); }
  function busy() { onbusy?.(capturing || gestureBusy || pending !== null); }
  function fail(cause: unknown) { error = cause instanceof Error ? cause.message : "The change could not be completed."; }
  function select(ids: string[]): boolean {
    if (capturing || pending) return false;
    const unique = [...new Set(ids)];
    if (unique.length > 128) { error = "Select up to 128 objects at a time. Use a smaller region."; return false; }
    selected = unique; syncCommands(); error = ""; return true;
  }
  function change(next: Scene, message: string) {
    if (capturing || pending) return;
    try { board = commit(board, next); unexported = true; fileState = managed ? "Edited project document" : "Unsaved changes · download to keep"; notice = message; error = ""; selected = selected.filter((id) => boundsOfSelection(board.scene, [id]) !== null); changed(); }
    catch (cause) { fail(cause); }
  }
  function history(direction: "undo" | "redo") {
    if (capturing || gestureBusy) return;
    try {
      surface?.settleAnimation();
      board = direction === "undo" ? undo(board) : redo(board); selected = []; changed(); unexported = true; fileState = managed ? "Edited project document" : "Unsaved changes · download to keep";
      notice = direction === "undo" ? "Change undone. A fresh revision prevents old proposals from being reused." : "Change redone."; error = "";
    } catch (cause) { fail(cause); }
  }
  function patchNode(id: string, update: Partial<CanvasNode>, message: string) { change({ ...scene, nodes: scene.nodes.map((node) => node.id === id ? { ...node, ...update } : node) }, message); }
  function addNode() {
    if (editingLocked) return;
    const point = surface?.center() ?? { x: 300, y: 220 };
    const node: CanvasNode = { id: crypto.randomUUID(), x: Math.round(point.x - 100), y: Math.round(point.y - 52), width: 200, height: 104, label: `Node ${scene.nodes.length + 1}`, kind: "box", pinned: false, source_stroke_ids: [], artwork: null };
    change({ ...scene, nodes: [...scene.nodes, node] }, "Node added. Open Objects to edit its label."); selected = [node.id]; syncCommands(); objectsOpen = true;
  }
  function connect(source: string, target: string, label: string) { change({ ...scene, edges: [...scene.edges, { id: crypto.randomUUID(), source, target, label, source_stroke_ids: [] }] }, "Connection added."); }
  function deleteObjects() { if (!selected.length || editingLocked) return; try { change(deleteSelection(scene, selected), "Selected objects deleted. Undo restores them."); selected = []; syncCommands(); } catch (cause) { fail(cause); } }
  function rename(id: string, label: string) { try { change(renameNode(scene, id, label), "Node label updated."); } catch (cause) { fail(cause); } }
  function edit(id: string) { select([id]); objectsOpen = true; void tick().then(() => root?.querySelector<HTMLInputElement>('[name="label"]')?.focus()); }
  function newBoard(example: boolean) {
    if (capturing || gestureBusy) return;
    if (unexported && !window.confirm("Download your current board first if you want to keep it. Replace this draft?")) return;
    board = example ? exampleDocument() : blankDocument(); selected = []; pending = null; packet = null; unexported = false; instruction = "";
    syncCommands(true); changed(); busy();
    fileState = example ? "Temporary example · download to keep" : "Temporary blank board · download to keep";
    notice = example ? "Illustrative example loaded. These objects do not describe running LychD architecture." : "Blank board ready. Draw freely or add an editable node."; error = "";
    void tick().then(() => surface.fit());
  }
  function download(value: unknown, name: string) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function saveBoard() {
    if (capturing || gestureBusy) return;
    try { const valid = validateDocument(board); download(valid, `${scene.title.replace(/[^a-z0-9]+/gi, "-").slice(0, 60) || "canvas"}.canvas.json`); unexported = false; fileState = `Downloaded revision ${scene.revision}`; notice = "Board document downloaded with its bounded undo and redo history. Keep the file to return later."; error = ""; }
    catch (cause) { fail(cause); }
  }
  async function openBoard(event: Event) {
    const input = event.currentTarget as HTMLInputElement, file = input.files?.[0]; input.value = ""; if (!file || capturing || gestureBusy) return;
    try {
      if (file.size > 12 * 1024 * 1024) throw new Error("Board document exceeds the 12 MiB limit.");
      let next = validateDocument(JSON.parse(await file.text()));
      if (capturing || gestureBusy) throw new Error("A board gesture or capture began while reading the file. Open the document again when it finishes.");
      if (unexported && !window.confirm("Replace the current draft? Changes that have not been downloaded will be lost.")) return;
      if (managed) next = replaceDocument(board, next);
      board = next; selected = []; pending = null; packet = null; unexported = false; fileState = managed ? "Imported local document · save to retain" : "Opened local document · no new edits"; notice = managed ? `Imported ${file.name} into this project board. Save board to retain it. No file was sent to a server.` : `Opened ${file.name}. No file was sent to a server.`; error = "";
      syncCommands(true); changed(); busy();
      await tick(); surface.fit();
    } catch (cause) { fail(cause); }
  }
  function selectedPacket(text: string): Packet {
    const bounds = boundsOfSelection(scene, selected); if (!bounds || !selected.length) throw new Error("Select at least one whole object first.");
    return makePacket(scene, selected, bounds, text, null);
  }
  function tidy() {
    if (editingLocked) return;
    try {
      const captured = selectedPacket("Regularize selected geometry with the local Tidy helper.");
      const proposal = tidyProposal(captured), next = applyProposal(scene, proposal, captured);
      pending = { scene: next, sceneId: scene.id, revision: scene.revision, title: "Tidy preview", summary: proposal.summary, author: "Local geometry helper · no model", proposal, packet: captured }; original = false; error = "";
      busy();
      notice = "Preview only. Tidy regularizes geometry; it does not interpret the instruction field.";
    } catch (cause) { fail(cause); }
  }
  function arrange() {
    if (editingLocked) return;
    try {
      if (!scene.nodes.length) throw new Error("Add an editable node before arranging the board.");
      const next = arrangeScene(scene, selected.length ? selected : undefined);
      surface.animateArrangement(scene, next);
      pending = { scene: next, sceneId: scene.id, revision: scene.revision, title: "Arrangement preview", summary: "Settle movable nodes around their connections and pinned obstacles. Unselected nodes and raw ink stay fixed.", author: "Local CPU layout", proposal: null, packet: null }; original = false; error = "";
      busy();
      notice = "Preview only. Apply to keep this arrangement as one undoable change.";
    } catch (cause) { fail(cause); }
  }
  function accept() {
    if (!pending || capturing || gestureBusy) return;
    if (stale || (pending.commandPlan && (!isCanvasCommandCurrent(pending.commandPlan, scene, selected) || !workCommands?.isCurrent(pending.commandTarget ?? null)))) { error = "This preview is stale. Reject it and capture the current revision again."; return; }
    try {
      surface.settleAnimation();
      const next = pending.proposal && pending.packet ? applyProposal(scene, pending.proposal, pending.packet) : pending.scene;
      board = commit(board, next); pending = null; original = false; selected = []; unexported = true; fileState = managed ? "Edited project document" : "Unsaved changes · download to keep"; notice = "Proposal applied as one change. Undo restores the previous board and source ink."; error = ""; surface.focusBoard();
      changed(); busy();
    } catch (cause) { fail(cause); }
  }
  function reject() { surface.settleAnimation(); pending = null; busy(); original = false; error = ""; notice = "Preview rejected. The board is unchanged."; surface.focusBoard(); }
  async function capture() {
    if (editingLocked) return;
    try {
      if (!instruction.trim()) throw new Error("Write an instruction to include in the selection packet.");
      const captured = selectedPacket(instruction.trim()); capturing = true; error = ""; notice = "Capturing this scene revision locally…";
      busy();
      await tick();
      let crop: Packet["crop"] = null;
      try { crop = await surface.captureCrop(captured.selection.bounds); }
      catch (cause) { error = `${cause instanceof Error ? cause.message : "PNG capture failed."} The packet contains records only; try capturing again.`; }
      if (scene.id !== captured.scene.id || scene.revision !== captured.scene.revision) throw new Error("The board changed during capture. Capture the selection again.");
      packet = makePacket(captured.scene, captured.selection.object_ids, captured.selection.bounds, captured.instruction, crop);
      notice = crop ? `Captured revision ${scene.revision}: ${selected.length} objects and a ${crop.width} × ${crop.height} PNG. Download the packet for manual model transport.` : "Selection records captured without a PNG. No model transmission occurred.";
    } catch (cause) { fail(cause); }
    finally { capturing = false; busy(); }
  }
  async function importProposal(event: Event) {
    const input = event.currentTarget as HTMLInputElement, file = input.files?.[0]; input.value = ""; if (!file || capturing || gestureBusy || pending) return;
    try {
      if (!packet) throw new Error("Capture a selection packet before importing its proposal.");
      if (packetStale) throw new Error("The captured packet is stale. Capture this revision again before importing a proposal.");
      if (file.size > 2 * 1024 * 1024) throw new Error("Proposal exceeds the 2 MiB import limit.");
      const boundPacket = packet, revision = scene.revision, id = scene.id;
      const text = await file.text();
      if (gestureBusy || capturing || pending) throw new Error("A board gesture, capture or preview began while reading the proposal. Import it again when that action finishes.");
      if (scene.id !== id || scene.revision !== revision) throw new Error("The board changed while reading the proposal. Capture it again.");
      const proposal = validateProposal(JSON.parse(text), boundPacket);
      const next = applyProposal(scene, proposal, boundPacket);
      selected = [...boundPacket.selection.object_ids]; syncCommands();
      pending = { scene: next, sceneId: scene.id, revision: scene.revision, title: "Imported proposal", summary: proposal.summary, author: proposal.author, proposal, packet: boundPacket }; original = false; error = "";
      busy();
      notice = "Manual proposal import. Inspect the proposed objects before applying.";
    } catch (cause) { fail(cause); }
  }
  async function artwork(id: string, file: File | null) {
    if (editingLocked) return;
    if (!file) { patchNode(id, { artwork: null }, "Local artwork removed."); return; }
    try {
      if (file.size > 512 * 1024) throw new Error("PNG artwork exceeds 512 KiB.");
      const revision = scene.revision, sceneId = scene.id;
      const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error("The local PNG could not be read.")); reader.readAsDataURL(file); });
      if (scene.revision !== revision || scene.id !== sceneId || editingLocked) throw new Error("The board changed while reading the PNG. Attach it again.");
      const result = pngArtwork(data, scene.nodes.find((node) => node.id === id)?.label || "Local symbolic artwork");
      const node = scene.nodes.find((item) => item.id === id);
      patchNode(id, { artwork: result, width: Math.max(160, node?.width ?? 160), height: Math.max(150, node?.height ?? 150) }, "Local PNG attached. Its label remains editable.");
    } catch (cause) { fail(cause); }
  }
  function keys(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (!root?.contains(target) || target.closest("input,textarea,select,[contenteditable='true']")) return;
    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && key === "s") { event.preventDefault(); saveBoard(); return; }
    if ((event.ctrlKey || event.metaKey) && key === "z") { event.preventDefault(); history(event.shiftKey ? "redo" : "undo"); return; }
    if ((event.ctrlKey || event.metaKey) && key === "y") { event.preventDefault(); history("redo"); return; }
    if (event.key === "Escape") { if (pending) reject(); else { selected = []; syncCommands(); } return; }
    if (editingLocked || event.ctrlKey || event.metaKey || event.altKey) return;
    const chosen = tools.find((item) => item.shortcut.toLowerCase() === key);
    if (chosen) { event.preventDefault(); tool = chosen.key; return; }
    if (event.key === "Delete" || event.key === "Backspace") { event.preventDefault(); deleteObjects(); }
    if (event.key === "Enter" && selected.length === 1 && scene.nodes.some((node) => node.id === selected[0])) { event.preventDefault(); edit(selected[0]!); }
    if (target.closest(".board-host") && selected.length && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault(); const step = event.shiftKey ? 10 : 1;
      try { change(moveSelection(scene, selected, event.key === "ArrowLeft" ? -step : event.key === "ArrowRight" ? step : 0, event.key === "ArrowUp" ? -step : event.key === "ArrowDown" ? step : 0), "Selection nudged."); } catch (cause) { fail(cause); }
    }
  }
</script>

<svelte:head><title>Canvas · LychD</title><meta name="description" content="A portable visual board for drawing, selecting and judging editable proposals." /></svelte:head>
<svelte:window onbeforeunload={guardUnload} onkeydown={keys} />

<section class={["canvas-view", { "canvas-managed": managed }]} aria-label="Canvas board authoring" {@attach attachRoot}>
  {#snippet boardTitle()}<label class="board-title"><span class="visually-hidden">Board title</span><input aria-label="Board title" maxlength="120" value={scene.title} disabled={editingLocked} onblur={(event) => { const title = event.currentTarget.value.trim(); if (title && title !== scene.title) change({ ...scene, title }, "Board renamed."); else event.currentTarget.value = scene.title; }} onkeydown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} /></label>{/snippet}
  {#snippet fileActions()}<button type="button" onclick={() => chooseFile("board")} disabled={capturing || gestureBusy}>Open JSON</button><button type="button" class="primary" onclick={saveBoard} disabled={capturing || gestureBusy}>Download board <span aria-hidden="true">↓</span></button>{/snippet}
  {#if managed}
    <div class="managed-document-row">{@render boardTitle()}<span class="revision">r{scene.revision} · {count} objects</span><div class="document-actions">{@render fileActions()}</div></div>
  {:else}
    <PageHeader title="Canvas" kicker="Portable board">
      {#snippet actions()}<div class="document-actions"><button type="button" onclick={() => newBoard(false)} disabled={capturing || gestureBusy}>Blank board</button><button type="button" onclick={() => newBoard(true)} disabled={capturing || gestureBusy}>Example</button>{@render fileActions()}</div>{/snippet}
    </PageHeader>
    <div class="board-meta">{@render boardTitle()}<span class="file-state" data-unsaved={unexported}>{unexported ? "● " : ""}{fileState}</span><span class="revision">r{scene.revision} · {count} objects</span></div>
  {/if}
  <input class="file-input" data-file="board" type="file" accept="application/json,.json" aria-label="Open board document" onchange={openBoard} />
  <input class="file-input" data-file="proposal" type="file" accept="application/json,.json" aria-label="Import proposal document" onchange={importProposal} />
  <div class={["workbench", { "with-objects": objectsOpen }]}>
    <div class="board-host"><div class="floating-tools" role="toolbar" aria-label="Canvas tools">{#each tools as item (item.key)}<button type="button" class="tool" aria-label={`${item.label} tool (${item.shortcut})`} aria-pressed={tool === item.key} title={`${item.label} (${item.shortcut})`} disabled={capturing || gestureBusy} onclick={() => { tool = item.key; surface.focusBoard(); }}><span aria-hidden="true"><AltarIcon name={item.key === "box" ? "node" : item.key} size={18} /></span><span>{item.label}</span><kbd>{item.shortcut}</kbd></button>{/each}<span class="tool-divider"></span><button type="button" class="history" aria-label="Undo" title="Undo (Ctrl/⌘ Z)" disabled={!board.past.length || capturing || gestureBusy} onclick={() => history("undo")}><AltarIcon name="undo" size={18} /></button><button type="button" class="history" aria-label="Redo" title="Redo (Ctrl/⌘ Shift Z)" disabled={!board.future.length || capturing || gestureBusy} onclick={() => history("redo")}><AltarIcon name="redo" size={18} /></button></div>
      <button type="button" class="object-toggle" aria-pressed={objectsOpen} onclick={() => objectsOpen = !objectsOpen}>Objects <span aria-hidden="true">{objectsOpen ? "×" : "☷"}</span></button>
      <CanvasSurface bind:this={surface} scene={displayScene} {tool} {selected} locked={capturing || pending !== null} onselect={select} onchange={change} onbusy={(active) => { gestureBusy = active; busy(); }} onerror={(message) => error = message} onedit={edit} />
      {#if !count && !pending}<div class="empty-board"><span aria-hidden="true">✧</span><h2>Give your idea some room.</h2><p>{managed ? "Draw a first mark or add an editable node." : "Draw a first mark, add a node, or start with the example."}</p><button type="button" onclick={addNode}>Add your first node</button></div>{/if}
    </div>
    {#if objectsOpen}<CanvasObjects {scene} {selected} disabled={editingLocked} onselect={select} onrename={rename} onpin={(id) => { const node = scene.nodes.find((item) => item.id === id); if (node) patchNode(id, { pinned: !node.pinned }, node.pinned ? "Node unpinned." : "Node pinned during arrangement."); }} onkind={(id, kind) => patchNode(id, { kind }, "Node shape updated.")} onconnect={connect} onadd={addNode} ondelete={deleteObjects} onartwork={artwork} onreveal={(id) => { surface.reveal(id); surface.focusBoard(); }} />{/if}
  </div>
  {#if pending}
    <section class="review-tray" aria-label="Proposal review"><div class="review-copy"><span class="eyebrow">{stale ? "Stale preview" : "Preview · board unchanged"}</span><h2>{pending.title}</h2><p>{pending.summary}</p><small>Attributed author: {pending.author} · based on revision {pending.revision}</small>{#if pending.proposal}<small>{pending.proposal.nodes.length} node upserts · {pending.proposal.edges.length} connection upserts · {pending.proposal.archive_stroke_ids.length} source strokes archived on Apply</small>{/if}{#if stale}<p class="stale">The board or command target changed. Reject this preview and create a fresh one.</p>{/if}
      <details class="semantic-preview" open>
        <summary>Proposed nodes and connections · read-only</summary>
        <p>Proposed values below have not been applied. The Objects editor still shows the current board.</p>
        <ul aria-label="Proposed nodes">
          {#each pending.scene.nodes as node (node.id)}
            {@const previous = scene.nodes.find((item) => item.id === node.id)}
            <li><span>{previewNodeDescription(node)}</span>{#if !previous}<small>New node</small>{:else if previewNodeDescription(previous) !== previewNodeDescription(node)}<small>Before: {previewNodeDescription(previous)}</small>{/if}</li>
          {:else}<li>No proposed nodes.</li>{/each}
        </ul>
        <ul aria-label="Proposed connections">
          {#each pending.scene.edges as edge (edge.id)}
            {@const previous = scene.edges.find((item) => item.id === edge.id)}
            <li><span>From {previewEndpoint(pending.scene, edge.source)} to {previewEndpoint(pending.scene, edge.target)} · {edge.label || "Unlabeled connection"}</span>{#if !previous}<small>New connection</small>{:else if previous.label !== edge.label || previewEndpoint(scene, previous.source) !== previewEndpoint(pending.scene, edge.source) || previewEndpoint(scene, previous.target) !== previewEndpoint(pending.scene, edge.target)}<small>Before: from {previewEndpoint(scene, previous.source)} to {previewEndpoint(scene, previous.target)} · {previous.label || "Unlabeled connection"}</small>{/if}</li>
          {:else}<li>No proposed connections.</li>{/each}
        </ul>
      </details>
      </div><div class="review-actions"><button type="button" aria-pressed={original} onclick={() => { surface.settleAnimation(); original = !original; }} disabled={stale}>{original ? "Show proposal" : "Show original"}</button><button type="button" onclick={reject}>Reject</button><button type="button" class="primary" onclick={accept} disabled={stale || capturing}>Apply change</button></div></section>
  {:else}
    <details class="selection-tools" open={selected.length > 0 || !!instruction.trim()}>
      <summary>Selection tools <span>{selected.length ? `${selected.length} selected` : "Select ink or nodes to refine"}</span></summary>
      <section class="composer" aria-label="Selection and transformation"><div class="selection-summary"><strong>{selected.length ? `${selected.length} selected` : "Select a region"}</strong><span>Whole objects · original ink retained</span></div><div class="instruction-field"><label for="canvas-instruction">Instruction for a model packet</label><textarea id="canvas-instruction" maxlength="4000" rows="2" bind:value={instruction} disabled={capturing} placeholder="e.g. Clean this up. Move Database under Vessel."></textarea></div><div class="selection-actions"><div><button type="button" disabled={!selected.length || editingLocked} onclick={tidy} title="Local geometry regularizer. Does not interpret your instruction.">Tidy <span>local</span></button><button type="button" disabled={!scene.nodes.length || editingLocked} onclick={arrange}>Arrange <span>preview</span></button></div><button type="button" class="primary" disabled={!selected.length || !instruction.trim() || editingLocked} onclick={capture}>{capturing ? "Capturing PNG…" : "Capture selection packet"} <span aria-hidden="true">↗</span></button></div></section>
    </details>
  {/if}
  {#if packet}<div class="packet-strip"><div><strong>{packetStale ? "Captured packet is stale" : `Packet · revision ${packet.scene.revision}`}</strong><span>{packet.selection.object_ids.length} objects · {packet.crop ? `${packet.crop.width} × ${packet.crop.height} PNG` : "records only · PNG unavailable"} · full scene context included</span></div><button type="button" onclick={() => download(packet, `canvas-selection-r${packet!.scene.revision}.json`)}>Download packet</button><button type="button" onclick={() => chooseFile("proposal")} disabled={packetStale || capturing || gestureBusy || pending !== null}>Import proposal</button></div>{/if}
  <div class="feedback"><p role="status" aria-live="polite">{notice}</p>{#if error}<p class="error" role="alert">{error}</p>{/if}</div>
  <footer class="canvas-footer"><span>{managed ? "Project authoring · local CPU helpers" : "Offline authoring · local CPU helpers"}</span><span>{workCommands ? "Canvas commands in Bridge · live model interpretation & image generation unavailable" : "Voice, live model interpretation & image generation unavailable"}</span><button type="button" aria-expanded={helpOpen} onclick={() => helpOpen = !helpOpen}>How this works {helpOpen ? "−" : "+"}</button></footer>
  {#if helpOpen}<div class="help" id="canvas-gestures"><p><strong>Draw → circle or select → preview → apply.</strong> Tidy is a local geometry helper. It does not read the instruction. Capture downloads nothing automatically and sends nothing to a model. Download the packet, take it to your model yourself, then import its strict proposal JSON for review.</p><p><strong>Canvas commands in Bridge.</strong> Use Bridge’s work command mode to preview editable nodes and connections on this board, then Apply here. Commands never save automatically.</p><p class="command-help">{CANVAS_COMMAND_HELP}</p><p><strong>Keep your board.</strong> {managed ? "Save board retains the complete document and bounded history in this project. Download board makes a separate portable JSON copy. Local edits remain unsaved until the server confirms a save." : "Download board JSON to retain the current scene and bounded history. This browser draft has no automatic storage or server retention."}</p><p><strong>Keyboard.</strong> D Draw, L Lasso, V rectangle Select, B Node, C Connect, H Pan. On the board: Space temporarily pans, arrows move selected objects, Shift + arrows move further, Enter edits a node, Delete removes selection, +/− zoom, 0 fits. Use Objects for checkboxes, label editing and a keyboard connection form. Touch: one finger uses the active tool; two fingers pan and zoom.</p></div>{:else}<p id="canvas-gestures" class="visually-hidden">Use Objects for keyboard selection, node labels and connections. Board shortcuts: D draw, L lasso, V rectangle select, B node, C connect, H pan. Space pans; arrows move selected objects; Enter edits; Delete removes; plus and minus zoom; zero fits.</p>{/if}
</section>

<style>
.canvas-view { width:100%; min-width:0; margin:0 auto; padding:.5rem 1rem 1rem; container-type:inline-size; color:var(--color-bone); }
  .document-actions { display:flex; align-items:center; flex-wrap:wrap; gap:.4rem; }
  button { min-height:2.25rem; padding:.5rem .75rem; border:1px solid var(--color-control-border); border-radius:var(--radius-rune); background:var(--color-obsidian); color:var(--color-parchment); font:var(--text-xs)/1.4 var(--font-body); cursor:pointer; white-space:nowrap; }
  button:hover:not(:disabled) { color:var(--color-bone); background:var(--color-obsidian-2); border-color:var(--color-ash); }
  button:disabled { opacity:.45; cursor:default; }
  .primary { background:var(--color-bone); border-color:var(--color-bone); color:var(--color-void); font-weight:600; }
  .primary:hover:not(:disabled) { background:white; color:var(--color-void); }
  .primary span { margin-left:.4rem; }
  button:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  .file-input { display:none; }
  .eyebrow { color:var(--color-ash); font-size:var(--text-xs); letter-spacing:.06em; }
  .canvas-view > :global(.page-header) { margin-block:.5rem .25rem; padding-bottom:.75rem; }
  .board-meta,.managed-document-row { display:flex; align-items:center; flex-wrap:wrap; gap:.6rem 1rem; min-width:0; padding:.5rem 0 .75rem; }
  .board-title { min-width:7rem; flex:1; }
  .board-title input { width:min(100%,28rem); min-height:2.25rem; padding:.4rem .6rem; border:1px solid transparent; border-radius:var(--radius-rune); background:transparent; color:var(--color-parchment); font:var(--text-sm)/1.4 var(--font-body); }
  .board-title input:hover:not(:disabled) { border-color:var(--color-control-border); }
  .file-state,.revision { color:var(--color-ash); font:var(--text-2xs)/1.5 var(--font-glyph); }
  .file-state[data-unsaved="true"] { color:var(--color-heat); }
  .managed-document-row .board-title { min-width:0; }
  .managed-document-row .document-actions { flex-shrink:0; }
  .workbench { display:grid; grid-template-columns:minmax(0,1fr); overflow:hidden; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-void); }
  .with-objects { grid-template-columns:minmax(0,1fr) 18rem; }
  .board-host { position:relative; min-width:0; height:calc(100dvh - 17rem); min-height:25rem; max-height:60rem; }
  .floating-tools { position:absolute; z-index:2; left:50%; top:1rem; transform:translateX(-50%); display:flex; align-items:center; gap:.125rem; padding:.3rem; max-width:calc(100% - 2rem); overflow-x:auto; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-obsidian); box-shadow:0 .5rem 1.5rem #0006; }
  .tool { display:flex; align-items:center; gap:.4rem; min-height:2.5rem; padding:.5rem .65rem; border:1px solid transparent; background:transparent; }
  .tool > span:first-child { display:grid; place-items:center; }
  .tool[aria-pressed="true"] { color:var(--color-rune); background:color-mix(in srgb,var(--color-rune) 9%,var(--color-obsidian)); border-color:var(--color-rune-dim); }
  kbd { font:var(--text-2xs)/1 var(--font-glyph); color:var(--color-ash); }
  .tool-divider { width:1px; min-width:1px; height:1.5rem; margin-inline:.35rem; background:var(--color-engraving); }
  .history { padding:.45rem; min-height:2.5rem; border:0; background:transparent; }
  .object-toggle { position:absolute; z-index:2; top:1rem; right:1rem; border-color:var(--color-engraving); }
  .object-toggle span { margin-left:.5rem; }
  .object-toggle[aria-pressed="true"] { color:var(--color-rune); border-color:var(--color-rune-dim); }
  .empty-board { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:min(26rem,80%); text-align:center; pointer-events:none; }
  .empty-board > span { font-size:2.5rem; color:var(--color-accent); }
  .empty-board h2 { margin:.75rem 0; font-size:1.4rem; font-weight:500; letter-spacing:-.035em; }
  .empty-board p { margin-bottom:1.2rem; color:var(--color-ash); font-size:var(--text-sm); line-height:1.7; }
  .empty-board button { pointer-events:auto; }
  .selection-tools { margin-top:.65rem; border-radius:var(--radius-panel); background:var(--color-obsidian); }
  .selection-tools > summary { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.5rem; padding:.85rem 1rem; color:var(--color-parchment); font-size:var(--text-xs); cursor:pointer; }
  .selection-tools > summary span { color:var(--color-ash); }
  .selection-tools[open] > summary { border-bottom:1px solid var(--color-engraving); }
  .composer { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:1rem; padding:1rem; }
  .selection-summary { grid-column:1/-1; display:flex; align-items:baseline; flex-wrap:wrap; gap:.5rem 1rem; }
  .selection-summary strong { font-size:var(--text-sm); font-weight:550; }
  .selection-summary > span { color:var(--color-ash); font-size:var(--text-xs); }
  .instruction-field { min-width:0; }
  .instruction-field label { display:block; margin-bottom:.4rem; color:var(--color-ash); font-size:var(--text-xs); }
  .instruction-field textarea { width:100%; min-height:4rem; max-height:10rem; resize:vertical; padding:.7rem .85rem; border:1px solid var(--color-control-border); border-radius:var(--radius-rune); background:var(--color-void); color:var(--color-bone); font:var(--text-sm)/1.6 var(--font-body); }
  .instruction-field textarea::placeholder { color:var(--color-ash); }
  .selection-actions { display:grid; gap:.5rem; }
  .selection-actions > div { display:flex; gap:.4rem; }
  .selection-actions > div > button { flex:1; }
  .selection-actions button span { margin-left:.3rem; font-size:var(--text-2xs); }
  .review-tray { display:grid; grid-template-columns:minmax(0,1fr); gap:1rem; margin-top:.75rem; padding:1.25rem; border:1px solid var(--color-control-border); border-radius:var(--radius-panel); background:var(--color-obsidian); }
  .review-copy { min-width:0; }
  .review-copy h2 { margin:.5rem 0; font-size:1.15rem; font-weight:600; letter-spacing:-.025em; }
  .review-copy p { color:var(--color-parchment); font-size:var(--text-sm); line-height:1.7; overflow-wrap:anywhere; }
  .review-copy small { display:block; margin-top:.45rem; color:var(--color-ash); font-size:var(--text-xs); }
  .review-copy .stale { color:var(--color-heat); }
  .review-actions { display:flex; justify-content:flex-end; flex-wrap:wrap; gap:.5rem; padding-top:.75rem; border-top:1px solid var(--color-engraving); }
  .semantic-preview { margin-top:1rem; padding:.75rem; max-height:22rem; overflow:auto; border:1px solid var(--color-engraving); border-radius:var(--radius-rune); font-size:var(--text-xs); line-height:1.7; overflow-wrap:anywhere; }
  .semantic-preview summary { cursor:pointer; }
  .semantic-preview ul { padding-left:1rem; }
  .semantic-preview li { margin-block:.5rem; }
  .packet-strip { display:flex; align-items:center; flex-wrap:wrap; gap:.5rem; margin-top:.75rem; padding:1rem; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-obsidian); }
  .packet-strip > div { flex:1; min-width:12rem; display:grid; gap:.3rem; }
  .packet-strip strong { font-size:var(--text-xs); font-weight:600; }
  .packet-strip span { color:var(--color-ash); font-size:var(--text-xs); }
  .feedback { padding:.65rem .25rem 0; color:var(--color-ash); font-size:var(--text-xs); line-height:1.65; }
  .feedback p { margin:0; }
  .feedback .error { margin-top:.4rem; padding:.5rem .75rem; border-left:2px solid var(--color-ember); color:var(--color-ember); background:var(--color-obsidian); }
  .canvas-footer { display:flex; align-items:center; flex-wrap:wrap; gap:.5rem 1rem; margin-top:.65rem; color:var(--color-ash); font-size:var(--text-2xs); line-height:1.5; }
  .canvas-footer > span:first-child { color:var(--color-parchment); }
  .canvas-footer button { margin-left:auto; min-height:2rem; padding:.25rem .5rem; border:0; background:transparent; font-size:var(--text-2xs); }
  .help { max-width:60rem; padding:1rem 0; color:var(--color-ash); font-size:var(--text-xs); line-height:1.8; }
  .help p { margin-bottom:.75rem; }
  .help strong { color:var(--color-parchment); font-weight:600; }
  .command-help { white-space:pre-line; overflow-wrap:anywhere; }
  @container (max-width:75rem) { kbd { display:none; }.tool { padding:.5rem; }.floating-tools { left:1rem; transform:none; }.object-toggle { top:1.3rem; } }
  @container (max-width:56rem) { .tool > span:nth-child(2) { display:none; }.with-objects { grid-template-columns:minmax(0,1fr); }.revision { display:none; } }
  @container (max-width:40rem) { .canvas-view { padding-inline:.5rem; }.floating-tools { left:.75rem; right:.75rem; top:.75rem; max-width:calc(100% - 1.5rem); justify-content:flex-start; }.tool,.history { flex-shrink:0; min-width:2.25rem; }.tool { padding:.45rem; }.object-toggle { top:4.5rem; right:.75rem; }.board-host { min-height:26rem; }.composer { grid-template-columns:minmax(0,1fr); }.document-actions { gap:.3rem; }.document-actions button { padding:.45rem .55rem; }.board-title { flex-basis:100%; }.selection-tools > summary { align-items:start; flex-direction:column; }.canvas-footer button { margin-left:0; } }
  @media (prefers-reduced-motion:reduce) { * { scroll-behavior:auto; transition:none; } }
  @media (forced-colors:active) { .workbench,.selection-tools,.review-tray,button { border:1px solid ButtonText; }.tool[aria-pressed="true"] { outline:2px solid Highlight; } }
</style>
