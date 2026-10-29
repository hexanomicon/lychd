<script lang="ts">
  import { tick } from "svelte";
  import { beforeNavigate } from "$app/navigation";
  import { applyProposal, arrangeScene, blankDocument, boundsOfSelection, commit, deleteSelection, exampleDocument, makePacket, moveSelection, pngArtwork, redo, renameNode, tidyProposal, undo, validateDocument, validateProposal } from "$lib/canvas/engine";
  import type { CanvasNode, Document as BoardDocument, Packet, Proposal, Scene, Tool } from "$lib/canvas/types";
  import CanvasSurface from "./canvas/CanvasSurface.svelte";
  import CanvasObjects from "./canvas/CanvasObjects.svelte";
  import AltarIcon from "./AltarIcon.svelte";

  type Review = { scene: Scene; sceneId: string; revision: number; title: string; summary: string; author: string; proposal: Proposal | null; packet: Packet | null };
  let board = $state.raw<BoardDocument>(exampleDocument());
  let selected = $state.raw<string[]>([]);
  let tool = $state<Tool>("select");
  let objectsOpen = $state(false);
  let helpOpen = $state(false);
  let unexported = $state(false);
  let fileState = $state("Temporary example · download to keep");
  let notice = $state("Illustrative example. Draw, select a region, then try Tidy or capture a selection packet.");
  let error = $state("");
  let instruction = $state("");
  let capturing = $state(false);
  let gestureBusy = $state(false);
  let pending = $state.raw<Review | null>(null);
  let original = $state(false);
  let packet = $state.raw<Packet | null>(null);
    let surface: CanvasSurface;
  let root: HTMLElement | undefined;
  function attachRoot(element: HTMLElement) { root = element; return () => { root = undefined; }; }
  function chooseFile(kind: "board" | "proposal") { root?.querySelector<HTMLInputElement>(`[data-file="${kind}"]`)?.click(); }
  let scene = $derived(board.scene);
  let stale = $derived(pending !== null && (pending.sceneId !== scene.id || pending.revision !== scene.revision));
  let packetStale = $derived(packet !== null && (packet.scene.id !== scene.id || packet.scene.revision !== scene.revision));
  let displayScene = $derived(pending && !original && !stale ? pending.scene : scene);
  let editingLocked = $derived(capturing || pending !== null || gestureBusy);
  let count = $derived(scene.nodes.length + scene.edges.length + scene.strokes.filter((stroke) => !stroke.archived).length);
  const tools: { key: Tool; label: string; shortcut: string }[] = [
    { key: "draw", label: "Draw", shortcut: "D" }, { key: "lasso", label: "Lasso", shortcut: "L" }, { key: "select", label: "Select", shortcut: "V" },
    { key: "box", label: "Node", shortcut: "B" }, { key: "connect", label: "Connect", shortcut: "C" }, { key: "pan", label: "Pan", shortcut: "H" }
  ];

  beforeNavigate((navigation) => {
    if (!unexported || navigation.willUnload) return;
    if (!window.confirm("This board has changes that have not been downloaded. Leave and discard this draft?")) navigation.cancel();
  });
  function guardUnload(event: BeforeUnloadEvent) { if (unexported || capturing) { event.preventDefault(); event.returnValue = ""; } }
  function fail(cause: unknown) { error = cause instanceof Error ? cause.message : "The change could not be completed."; }
  function select(ids: string[]): boolean {
    if (capturing || pending) return false;
    const unique = [...new Set(ids)];
    if (unique.length > 128) { error = "Select up to 128 objects at a time. Use a smaller region."; return false; }
    selected = unique; error = ""; return true;
  }
  function change(next: Scene, message: string) {
    if (capturing || pending) return;
    try { board = commit(board, next); unexported = true; fileState = "Unsaved changes · download to keep"; notice = message; error = ""; selected = selected.filter((id) => boundsOfSelection(board.scene, [id]) !== null); }
    catch (cause) { fail(cause); }
  }
  function history(direction: "undo" | "redo") {
    if (capturing || gestureBusy) return;
    try {
      surface?.settleAnimation();
      board = direction === "undo" ? undo(board) : redo(board); selected = []; unexported = true; fileState = "Unsaved changes · download to keep";
      notice = direction === "undo" ? "Change undone. A fresh revision prevents old proposals from being reused." : "Change redone."; error = "";
    } catch (cause) { fail(cause); }
  }
  function patchNode(id: string, update: Partial<CanvasNode>, message: string) { change({ ...scene, nodes: scene.nodes.map((node) => node.id === id ? { ...node, ...update } : node) }, message); }
  function addNode() {
    if (editingLocked) return;
    const point = surface?.center() ?? { x: 300, y: 220 };
    const node: CanvasNode = { id: crypto.randomUUID(), x: Math.round(point.x - 100), y: Math.round(point.y - 52), width: 200, height: 104, label: `Node ${scene.nodes.length + 1}`, kind: "box", pinned: false, source_stroke_ids: [], artwork: null };
    change({ ...scene, nodes: [...scene.nodes, node] }, "Node added. Open Objects to edit its label."); selected = [node.id]; objectsOpen = true;
  }
  function connect(source: string, target: string, label: string) { change({ ...scene, edges: [...scene.edges, { id: crypto.randomUUID(), source, target, label, source_stroke_ids: [] }] }, "Connection added."); }
  function deleteObjects() { if (!selected.length || editingLocked) return; try { change(deleteSelection(scene, selected), "Selected objects deleted. Undo restores them."); selected = []; } catch (cause) { fail(cause); } }
  function rename(id: string, label: string) { try { change(renameNode(scene, id, label), "Node label updated."); } catch (cause) { fail(cause); } }
  function edit(id: string) { select([id]); objectsOpen = true; void tick().then(() => root?.querySelector<HTMLInputElement>('[name="label"]')?.focus()); }
  function newBoard(example: boolean) {
    if (capturing || gestureBusy) return;
    if (unexported && !window.confirm("Download your current board first if you want to keep it. Replace this draft?")) return;
    board = example ? exampleDocument() : blankDocument(); selected = []; pending = null; packet = null; unexported = false; instruction = "";
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
      const next = validateDocument(JSON.parse(await file.text()));
      if (capturing || gestureBusy) throw new Error("A board gesture or capture began while reading the file. Open the document again when it finishes.");
      if (unexported && !window.confirm("Replace the current draft? Changes that have not been downloaded will be lost.")) return;
      board = next; selected = []; pending = null; packet = null; unexported = false; fileState = "Opened local document · no new edits"; notice = `Opened ${file.name}. No file was sent to a server.`; error = "";
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
      notice = "Preview only. Apply to keep this arrangement as one undoable change.";
    } catch (cause) { fail(cause); }
  }
  function accept() {
    if (!pending || capturing || gestureBusy) return;
    if (stale) { error = "This preview is stale. Reject it and capture the current revision again."; return; }
    try {
      surface.settleAnimation();
      const next = pending.proposal && pending.packet ? applyProposal(scene, pending.proposal, pending.packet) : pending.scene;
      board = commit(board, next); pending = null; original = false; selected = []; unexported = true; fileState = "Unsaved changes · download to keep"; notice = "Proposal applied as one change. Undo restores the previous board and source ink."; error = ""; surface.focusBoard();
    } catch (cause) { fail(cause); }
  }
  function reject() { surface.settleAnimation(); pending = null; original = false; error = ""; notice = "Preview rejected. The board is unchanged."; surface.focusBoard(); }
  async function capture() {
    if (editingLocked) return;
    try {
      if (!instruction.trim()) throw new Error("Write an instruction to include in the selection packet.");
      const captured = selectedPacket(instruction.trim()); capturing = true; error = ""; notice = "Capturing this scene revision locally…";
      await tick();
      let crop: Packet["crop"] = null;
      try { crop = await surface.captureCrop(captured.selection.bounds); }
      catch (cause) { error = `${cause instanceof Error ? cause.message : "PNG capture failed."} The packet contains records only; try capturing again.`; }
      if (scene.id !== captured.scene.id || scene.revision !== captured.scene.revision) throw new Error("The board changed during capture. Capture the selection again.");
      packet = makePacket(captured.scene, captured.selection.object_ids, captured.selection.bounds, captured.instruction, crop);
      notice = crop ? `Captured revision ${scene.revision}: ${selected.length} objects and a ${crop.width} × ${crop.height} PNG. Download the packet for manual model transport.` : "Selection records captured without a PNG. No model transmission occurred.";
    } catch (cause) { fail(cause); }
    finally { capturing = false; }
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
      selected = [...boundPacket.selection.object_ids];
      pending = { scene: next, sceneId: scene.id, revision: scene.revision, title: "Imported proposal", summary: proposal.summary, author: proposal.author, proposal, packet: boundPacket }; original = false; error = "";
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
    if (event.key === "Escape") { if (pending) reject(); else selected = []; return; }
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

<section class="canvas-view" aria-label="Canvas board authoring" {@attach attachRoot}>
  <header class="canvas-header"><div class="identity"><span class="eyebrow">Portable board</span><h1>Canvas</h1></div><div class="document-actions"><button type="button" onclick={() => newBoard(false)} disabled={capturing || gestureBusy}>Blank board</button><button type="button" onclick={() => newBoard(true)} disabled={capturing || gestureBusy}>Example</button><button type="button" onclick={() => chooseFile("board")} disabled={capturing || gestureBusy}>Open JSON</button><button type="button" class="primary" onclick={saveBoard} disabled={capturing || gestureBusy}>Download board <span aria-hidden="true">↓</span></button></div></header>
  <input class="file-input" data-file="board" type="file" accept="application/json,.json" aria-label="Open board document" onchange={openBoard} />
  <input class="file-input" data-file="proposal" type="file" accept="application/json,.json" aria-label="Import proposal document" onchange={importProposal} />
  <div class="board-meta"><label class="board-title"><span class="visually-hidden">Board title</span><input aria-label="Board title" maxlength="120" value={scene.title} disabled={editingLocked} onblur={(event) => { const title = event.currentTarget.value.trim(); if (title && title !== scene.title) change({ ...scene, title }, "Board renamed."); else event.currentTarget.value = scene.title; }} onkeydown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} /></label><span class="file-state" data-unsaved={unexported}>{unexported ? "● " : ""}{fileState}</span><span class="revision">r{scene.revision} · {count} objects</span></div>
  <div class={["workbench", { "with-objects": objectsOpen }]}>
    <div class="board-host"><div class="floating-tools" role="toolbar" aria-label="Canvas tools">{#each tools as item (item.key)}<button type="button" class="tool" aria-label={`${item.label} tool (${item.shortcut})`} aria-pressed={tool === item.key} title={`${item.label} (${item.shortcut})`} disabled={capturing || gestureBusy} onclick={() => { tool = item.key; surface.focusBoard(); }}><span aria-hidden="true"><AltarIcon name={item.key === "box" ? "node" : item.key} size={18} /></span><span>{item.label}</span><kbd>{item.shortcut}</kbd></button>{/each}<span class="tool-divider"></span><button type="button" class="history" aria-label="Undo" title="Undo (Ctrl/⌘ Z)" disabled={!board.past.length || capturing || gestureBusy} onclick={() => history("undo")}><AltarIcon name="undo" size={18} /></button><button type="button" class="history" aria-label="Redo" title="Redo (Ctrl/⌘ Shift Z)" disabled={!board.future.length || capturing || gestureBusy} onclick={() => history("redo")}><AltarIcon name="redo" size={18} /></button></div>
      <button type="button" class="object-toggle" aria-pressed={objectsOpen} onclick={() => objectsOpen = !objectsOpen}>Objects <span aria-hidden="true">{objectsOpen ? "×" : "☷"}</span></button>
      <CanvasSurface bind:this={surface} scene={displayScene} {tool} {selected} locked={capturing || pending !== null} onselect={select} onchange={change} onbusy={(busy) => gestureBusy = busy} onerror={(message) => error = message} onedit={edit} />
      {#if !count}<div class="empty-board"><span aria-hidden="true">✧</span><h2>Give your idea some room.</h2><p>Draw a first mark, add a node, or start with the example.</p><button type="button" onclick={addNode}>Add your first node</button></div>{/if}
    </div>
    {#if objectsOpen}<CanvasObjects {scene} {selected} disabled={editingLocked} onselect={select} onrename={rename} onpin={(id) => { const node = scene.nodes.find((item) => item.id === id); if (node) patchNode(id, { pinned: !node.pinned }, node.pinned ? "Node unpinned." : "Node pinned during arrangement."); }} onkind={(id, kind) => patchNode(id, { kind }, "Node shape updated.")} onconnect={connect} onadd={addNode} ondelete={deleteObjects} onartwork={artwork} onreveal={(id) => { surface.reveal(id); surface.focusBoard(); }} />{/if}
  </div>
  {#if pending}
    <section class="review-tray" aria-label="Proposal review"><div class="review-copy"><span class="eyebrow">{stale ? "Stale preview" : "Preview · board unchanged"}</span><h2>{pending.title}</h2><p>{pending.summary}</p><small>Attributed author: {pending.author} · based on revision {pending.revision}</small>{#if pending.proposal}<small>{pending.proposal.nodes.length} node upserts · {pending.proposal.edges.length} connection upserts · {pending.proposal.archive_stroke_ids.length} source strokes archived on Apply</small>{/if}{#if stale}<p class="stale">The board changed. Reject this preview and create a fresh one.</p>{/if}</div><div class="review-actions"><button type="button" aria-pressed={original} onclick={() => { surface.settleAnimation(); original = !original; }} disabled={stale}>{original ? "Show proposal" : "Show original"}</button><button type="button" onclick={reject}>Reject</button><button type="button" class="primary" onclick={accept} disabled={stale || capturing}>Apply change</button></div></section>
  {:else}
    <section class="composer" aria-label="Selection and transformation"><div class="selection-summary"><strong>{selected.length ? `${selected.length} selected` : "Select a region"}</strong><span>Whole objects · original ink retained</span></div><div class="instruction-field"><label for="canvas-instruction">Instruction for a model packet</label><textarea id="canvas-instruction" maxlength="4000" rows="2" bind:value={instruction} disabled={capturing} placeholder="e.g. Clean this up. Move Database under Vessel."></textarea></div><div class="selection-actions"><div><button type="button" disabled={!selected.length || editingLocked} onclick={tidy} title="Local geometry regularizer. Does not interpret your instruction.">Tidy <span>local</span></button><button type="button" disabled={!scene.nodes.length || editingLocked} onclick={arrange}>Arrange <span>preview</span></button></div><button type="button" class="primary" disabled={!selected.length || !instruction.trim() || editingLocked} onclick={capture}>{capturing ? "Capturing PNG…" : "Capture selection packet"} <span aria-hidden="true">↗</span></button></div></section>
  {/if}
  {#if packet}<div class="packet-strip"><div><strong>{packetStale ? "Captured packet is stale" : `Packet · revision ${packet.scene.revision}`}</strong><span>{packet.selection.object_ids.length} objects · {packet.crop ? `${packet.crop.width} × ${packet.crop.height} PNG` : "records only · PNG unavailable"} · full scene context included</span></div><button type="button" onclick={() => download(packet, `canvas-selection-r${packet!.scene.revision}.json`)}>Download packet</button><button type="button" onclick={() => chooseFile("proposal")} disabled={packetStale || capturing || gestureBusy || pending !== null}>Import proposal</button></div>{/if}
  <div class="feedback"><p role="status" aria-live="polite">{notice}</p>{#if error}<p class="error" role="alert">{error}</p>{/if}</div>
  <footer class="canvas-footer"><span>Offline authoring · local CPU helpers</span><span>Voice, live model interpretation & image generation unavailable</span><button type="button" aria-expanded={helpOpen} onclick={() => helpOpen = !helpOpen}>How this works {helpOpen ? "−" : "+"}</button></footer>
  {#if helpOpen}<div class="help" id="canvas-gestures"><p><strong>Draw → circle or select → preview → apply.</strong> Tidy is a local geometry helper. It does not read the instruction. Capture downloads nothing automatically and sends nothing to a model. Download the packet, take it to your model yourself, then import its strict proposal JSON for review.</p><p><strong>Keep your board.</strong> Download board JSON to retain the current scene and bounded history. This browser draft has no automatic storage or server retention.</p><p><strong>Keyboard.</strong> D Draw, L Lasso, V rectangle Select, B Node, C Connect, H Pan. On the board: Space temporarily pans, arrows move selected objects, Shift + arrows move further, Enter edits a node, Delete removes selection, +/− zoom, 0 fits. Use Objects for checkboxes, label editing and a keyboard connection form. Touch: one finger uses the active tool; two fingers pan and zoom.</p></div>{:else}<p id="canvas-gestures" class="visually-hidden">Use Objects for keyboard selection, node labels and connections. Board shortcuts: D draw, L lasso, V rectangle select, B node, C connect, H pan. Space pans; arrows move selected objects; Enter edits; Delete removes; plus and minus zoom; zero fits.</p>{/if}
</section>

<style>
  .canvas-view { width:100%; max-width:1800px; margin:0 auto; container-type:inline-size; padding:18px 20px 14px; color:var(--color-bone); }
  .canvas-header { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:18px; }.eyebrow { color:var(--color-rune); font-size:10px; letter-spacing:.15em; text-transform:uppercase; } h1 { margin:5px 0 0; font-size:27px; font-weight:550; letter-spacing:-.04em; line-height:1.3; }.document-actions { display:flex; gap:8px; flex-wrap:wrap; }
  button { min-height:36px; padding:8px 12px; border:1px solid var(--color-engraving); border-radius:var(--radius-rune); background:var(--color-obsidian); color:var(--color-parchment); font:12px var(--font-body); cursor:pointer; white-space:nowrap; } button:hover:not(:disabled) { border-color:var(--color-rune-dim); color:var(--color-rune); background:var(--color-obsidian-2); } button:disabled { opacity:.4; cursor:default; }.primary { background:var(--color-rune); border-color:var(--color-rune); color:#071115; }.primary span { margin-left:8px; } button:focus-visible,input:focus-visible,textarea:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }.file-input { display:none; }
  .board-meta { display:flex; align-items:center; gap:14px; margin-bottom:10px; min-width:0; }.board-title { min-width:100px; flex:1; }.board-title input { width:min(100%,460px); background:transparent; border:1px solid transparent; border-radius:4px; padding:5px 0; color:var(--color-parchment); font:13px var(--font-body); }.board-title input:hover:not(:disabled) { border-bottom-color:var(--color-engraving); }.file-state,.revision { font:10px var(--font-glyph); color:var(--color-ash); white-space:nowrap; }.file-state[data-unsaved="true"] { color:var(--color-heat); }
  .workbench { display:grid; grid-template-columns:minmax(0,1fr); border:1px solid var(--color-engraving); border-radius:4px 4px 0 0; overflow:hidden; }.with-objects { grid-template-columns:minmax(0,1fr) 280px; }.board-host { position:relative; height:clamp(430px,65vh,880px); min-width:0; }.floating-tools { position:absolute; left:18px; top:16px; z-index:2; display:flex; align-items:center; gap:3px; padding:5px; border:1px solid var(--color-engraving); border-radius:4px; background:var(--color-obsidian); box-shadow:none; }.tool { display:flex; align-items:center; gap:6px; min-height:38px; padding:8px 9px; border:1px solid transparent; background:transparent; }.tool > span:first-child { font-size:18px; line-height:1; }.tool[aria-pressed="true"] { color:var(--color-rune); background:color-mix(in srgb,var(--color-rune) 9%,transparent); border-color:var(--color-rune-dim); } kbd { font:9px var(--font-glyph); color:var(--color-ash); }.tool-divider { width:1px; height:24px; background:var(--color-engraving); margin:0 5px; }.history { font-size:23px; padding:2px 7px; border:0; background:transparent; }.object-toggle { position:absolute; top:22px; right:18px; z-index:2; min-height:36px; }.object-toggle span { margin-left:10px; }.object-toggle[aria-pressed="true"] { color:var(--color-rune); border-color:var(--color-rune-dim); }
  .empty-board { position:absolute; left:50%; top:48%; transform:translate(-50%,-50%); width:min(420px,80%); text-align:center; pointer-events:none; }.empty-board > span { font-size:48px; color:var(--color-rune-dim); }.empty-board h2 { font-size:22px; font-weight:450; margin:12px 0; }.empty-board p { color:var(--color-ash); font-size:13px; line-height:1.7; margin-bottom:20px; }.empty-board button { pointer-events:auto; }
  .composer { display:grid; grid-template-columns:135px minmax(100px,1fr) auto; align-items:center; gap:22px; padding:18px 20px; border:1px solid var(--color-engraving); border-top:0; border-radius:0 0 4px 4px; background:var(--color-obsidian); }.selection-summary { display:grid; gap:8px; }.selection-summary strong { font-size:13px; font-weight:550; }.selection-summary > span { color:var(--color-ash); font-size:10px; line-height:1.6; max-width:140px; }.instruction-field label { display:block; margin-bottom:7px; color:var(--color-ash); font-size:10px; }.instruction-field textarea { width:100%; resize:vertical; min-height:52px; max-height:160px; padding:9px 11px; border:1px solid var(--color-engraving); border-radius:6px; color:var(--color-bone); background:var(--color-void); font:12px/1.55 var(--font-body); }.instruction-field textarea::placeholder { color:var(--color-ash); }.selection-actions { display:grid; gap:8px; }.selection-actions > div { display:flex; gap:7px; }.selection-actions > div > button { flex:1; }.selection-actions button span { color:var(--color-ash); font-size:9px; margin-left:6px; }
  .review-tray { display:flex; justify-content:space-between; gap:22px; align-items:center; padding:22px; border:1px solid var(--color-rune-dim); border-radius:0 0 4px 4px; background:color-mix(in srgb,var(--color-rune) 4%,var(--color-obsidian)); }.review-copy { max-width:850px; }.review-copy h2 { margin:8px 0; font-size:18px; font-weight:550; }.review-copy p { font-size:12px; color:var(--color-parchment); line-height:1.7; overflow-wrap:anywhere; }.review-copy small { display:block; margin-top:7px; color:var(--color-ash); font-size:10px; }.review-actions { display:flex; gap:7px; flex-wrap:wrap; }.review-copy .stale { color:var(--color-heat); }
  .packet-strip { display:flex; align-items:center; gap:8px; padding:12px 16px; margin-top:10px; border:1px solid var(--color-engraving); border-radius:4px; background:var(--color-obsidian); }.packet-strip > div { flex:1; display:grid; gap:5px; }.packet-strip strong { font-size:11px; font-weight:550; }.packet-strip span { font-size:10px; color:var(--color-ash); }.packet-strip button { font-size:11px; }
  .feedback { padding:11px 2px 0; font-size:11px; line-height:1.7; color:var(--color-ash); }.feedback p { margin:0; }.feedback .error { margin-top:6px; color:var(--color-ember); padding:7px 10px; border-left:2px solid var(--color-ember); background:color-mix(in srgb,var(--color-ember) 5%,transparent); }.canvas-footer { display:flex; align-items:center; gap:16px; margin-top:12px; padding-top:10px; color:var(--color-ash); font-size:10px; border-top:1px solid var(--color-engraving); }.canvas-footer > span:first-child { color:var(--color-parchment); }.canvas-footer button { margin-left:auto; min-height:28px; padding:4px 0; border:0; background:transparent; font-size:10px; }.help { max-width:1000px; padding:12px 0; color:var(--color-ash); font-size:12px; line-height:1.8; }.help p { margin:0 0 12px; }.help strong { color:var(--color-parchment); font-weight:550; }
  @container(max-width:1100px) { .tool kbd { display:none; }.tool { padding:8px; }.composer { grid-template-columns:130px minmax(100px,1fr) auto; gap:14px; }.with-objects .tool > span:nth-child(2) { display:none; } }
  @container(max-width:850px) { .canvas-view { padding:16px 14px; }.canvas-header { align-items:flex-start; flex-direction:column; gap:12px; margin-bottom:12px; }.document-actions { gap:6px; }.document-actions button { font-size:11px; padding:7px 9px; }.with-objects { grid-template-columns:minmax(0,1fr); }.composer { grid-template-columns:minmax(0,1fr) auto; padding:14px; gap:12px; }.selection-summary { grid-column:1/-1; display:flex; align-items:center; gap:14px; }.selection-summary > span { max-width:none; }.file-state { font-size:9px; }.revision { display:none; }.review-tray { flex-direction:column; align-items:stretch; }.canvas-footer { align-items:flex-start; flex-wrap:wrap; gap:8px 14px; }.canvas-footer button { margin-left:0; }.board-host { height:55vh; min-height:430px; }.tool kbd { display:none; } }
  @container(max-width:560px) { h1 { font-size:25px; }.floating-tools { left:9px; right:9px; top:10px; justify-content:space-between; }.tool { padding:7px; }.tool > span:nth-child(2) { display:none; }.history { padding:2px 6px; }.tool-divider { margin:0; }.object-toggle { top:73px; right:12px; font-size:10px; }.composer { grid-template-columns:minmax(0,1fr); }.selection-actions { grid-template-columns:1fr; }.selection-actions > div { justify-content:stretch; }.file-state { max-width:43%; white-space:normal; line-height:1.6; }.board-title input { font-size:12px; }.packet-strip { flex-wrap:wrap; }.packet-strip > div { flex-basis:100%; margin-bottom:4px; }.review-actions { display:grid; grid-template-columns:1fr 1fr; }.review-actions .primary { grid-column:1/-1; } }
  @media(prefers-reduced-motion:reduce) { * { scroll-behavior:auto; transition:none; } }
  @media(forced-colors:active) { .workbench,.composer,.review-tray,button { border-color:ButtonText; }.tool[aria-pressed="true"] { outline:2px solid Highlight; } }
</style>
