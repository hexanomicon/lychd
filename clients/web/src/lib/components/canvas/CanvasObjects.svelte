<script lang="ts">
  import type { Artwork, CanvasNode, Scene } from "$lib/canvas/types";
  let { scene, selected, disabled, onselect, onrename, onpin, onkind, onconnect, onadd, ondelete, onartwork, onreveal }: {
    scene: Scene; selected: string[]; disabled: boolean; onselect: (ids: string[]) => boolean;
    onrename: (id: string, label: string) => void; onpin: (id: string) => void; onkind: (id: string, kind: CanvasNode["kind"]) => void;
    onconnect: (source: string, target: string, label: string) => void; onadd: () => void; ondelete: () => void;
    onartwork: (id: string, file: File | null) => void; onreveal: (id: string) => void;
  } = $props();
  let node = $derived(selected.length === 1 ? scene.nodes.find((item) => item.id === selected[0]) : undefined);
  let visibleStrokes = $derived(scene.strokes.filter((stroke) => !stroke.archived));
  let archived = $derived(scene.strokes.length - visibleStrokes.length);
  let entries = $derived([
    ...scene.nodes.map((item) => ({ id: item.id, label: item.label, kind: item.kind, detail: item.pinned ? "Pinned" : "Editable node" })),
    ...visibleStrokes.map((item, index) => ({ id: item.id, label: `Stroke ${index + 1}`, kind: "ink", detail: `${item.points.length} points` })),
    ...scene.edges.map((item) => ({ id: item.id, label: item.label || `${scene.nodes.find((candidate) => candidate.id === item.source)?.label ?? "Node"} → ${scene.nodes.find((candidate) => candidate.id === item.target)?.label ?? "Node"}`, kind: "edge", detail: "Connection" }))
  ]);
  function toggle(id: string, input: HTMLInputElement) {
    const accepted = onselect(selected.includes(id) ? selected.filter((value) => value !== id) : [...selected, id]);
    if (!accepted) input.checked = selected.includes(id);
  }
  function rename(event: SubmitEvent) {
    event.preventDefault(); if (!node) return;
    onrename(node.id, String(new FormData(event.currentTarget as HTMLFormElement).get("label") ?? ""));
  }
  function connect(event: SubmitEvent) {
    event.preventDefault(); const form = new FormData(event.currentTarget as HTMLFormElement);
    onconnect(String(form.get("source")), String(form.get("target")), String(form.get("edge-label") ?? ""));
  }
  const kinds: CanvasNode["kind"][] = ["box", "database", "service", "person", "note"];
  function artworkLabel(artwork: Artwork) { return artwork.provenance || "Local PNG attachment"; }
</script>

<aside aria-label="Board objects and editing">
  <header><h2>Objects</h2><span>{entries.length}</span></header>
  <div class="object-actions"><button type="button" onclick={onadd} {disabled}>+ Add node</button><button type="button" disabled={disabled || !selected.length} onclick={() => onselect([])}>Clear selection</button></div>
  <p class="hint">Checkboxes select whole objects. Select one node to edit its label.</p>
  <ul aria-label="Board objects">
    {#each entries as entry (entry.id)}
      <li class={{ selected: selected.includes(entry.id) }}><label><input type="checkbox" checked={selected.includes(entry.id)} onchange={(event) => toggle(entry.id, event.currentTarget)} {disabled} /><span><strong>{entry.label || "Untitled node"}</strong><small>{entry.kind} · {entry.detail}</small></span></label><button type="button" class="locate" aria-label={`Locate ${entry.label}`} onclick={() => onreveal(entry.id)}>⌖</button></li>
    {:else}<li class="empty">A clean slate. Draw a mark or add your first node.</li>{/each}
  </ul>
  {#if archived}<p class="hint archived">{archived} archived source {archived === 1 ? "stroke" : "strokes"} retained in this document. Undo an accepted transformation to restore its ink.</p>{/if}
  {#if node}
    <section class="editor" aria-label="Selected node editor">
      <h3>Selected node</h3>
      <form onsubmit={rename}><label>Label<input name="label" value={node.label} maxlength="240" {disabled} /></label><button type="submit" {disabled}>Update label</button></form>
      <label>Shape<select value={node.kind} onchange={(event) => onkind(node!.id, event.currentTarget.value as CanvasNode["kind"])} {disabled}>{#each kinds as kind (kind)}<option value={kind}>{kind}</option>{/each}</select></label>
      <button type="button" aria-pressed={node.pinned} onclick={() => onpin(node!.id)} {disabled}>{node.pinned ? "Unpin from arrangement" : "Pin during arrangement"}</button>
      <p class="hint">{node.pinned ? "Arrangement keeps this node fixed. You can still move it yourself." : "Drag on the board or use its arrow keys to move this node."}</p>
      <details><summary>Local artwork</summary><p class="hint">Attach a PNG, up to 512 KiB and 1024 × 1024. Labels remain editable text.</p><label class="file-label">PNG file<input type="file" accept="image/png,.png" {disabled} onchange={(event) => { const file = event.currentTarget.files?.[0]; if (file) onartwork(node!.id, file); event.currentTarget.value = ""; }} /></label>{#if node.artwork}<p class="hint">{artworkLabel(node.artwork)}</p><button type="button" {disabled} onclick={() => onartwork(node!.id, null)}>Remove artwork</button>{/if}</details>
    </section>
  {/if}
  <details class="connection"><summary>Connect nodes with the keyboard</summary><form onsubmit={connect}><label>Source<select name="source" required disabled={disabled || !scene.nodes.length}>{#each scene.nodes as item (item.id)}<option value={item.id}>{item.label || "Untitled node"}</option>{/each}</select></label><label>Target<select name="target" required disabled={disabled || !scene.nodes.length}>{#each scene.nodes as item (item.id)}<option value={item.id}>{item.label || "Untitled node"}</option>{/each}</select></label><label>Connection label<input name="edge-label" maxlength="240" {disabled} placeholder="Optional" /></label><button type="submit" disabled={disabled || !scene.nodes.length}>Add connection</button></form></details>
  {#if selected.length}<button type="button" class="delete" {disabled} onclick={ondelete}>Delete {selected.length} selected {selected.length === 1 ? "object" : "objects"}</button>{/if}
</aside>

<style>
  aside { height:100%; min-width:0; overflow:auto; padding:18px 16px; background:var(--color-obsidian); border-left:1px solid var(--color-engraving); font-size:12px; }
  header { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; } h2 { margin:0; font-size:14px; font-weight:600; } header span { color:var(--color-ash); font:11px var(--font-glyph); }
  h3 { margin:0 0 12px; font-size:12px; font-weight:600; color:var(--color-frost); }.object-actions { display:flex; gap:6px; }.hint { color:var(--color-ash); font-size:11px; line-height:1.6; margin:10px 0; }.archived { padding-top:10px; border-top:1px solid var(--color-engraving); }
  ul { list-style:none; padding:0; margin:12px 0 20px; max-height:270px; overflow:auto; } li { display:flex; gap:4px; align-items:center; border:1px solid transparent; border-radius:3px; margin-bottom:3px; } li.selected { background:color-mix(in srgb,var(--color-rune) 6%,transparent); border-color:var(--color-rune-dim); } li label { display:flex; gap:9px; align-items:center; min-width:0; flex:1; padding:9px 5px; cursor:pointer; } li strong { display:block; font-size:12px; font-weight:500; overflow-wrap:anywhere; } small { display:block; color:var(--color-ash); font-size:10px; margin-top:3px; } input[type="checkbox"] { accent-color:var(--color-rune); flex:none; width:16px; height:16px; }.locate { flex:none; border:0; font-size:17px; min-width:28px; padding:4px; background:transparent; }.empty { padding:16px 0; color:var(--color-ash); line-height:1.6; }
  .editor { border-top:1px solid var(--color-engraving); padding-top:16px; margin-bottom:16px; }.editor > label { margin:12px 0; } form { display:grid; gap:10px; } form label,.editor > label,.file-label { display:grid; gap:5px; color:var(--color-parchment); font-size:11px; } input:not([type="checkbox"]),select { width:100%; min-width:0; padding:8px; border:1px solid var(--color-engraving); border-radius:5px; background:var(--color-void); color:var(--color-bone); font:12px var(--font-body); } input[type="file"] { font-size:10px; }
  button { min-height:33px; padding:6px 9px; border:1px solid var(--color-engraving); border-radius:5px; background:var(--color-obsidian-2); color:var(--color-parchment); font:11px var(--font-body); cursor:pointer; } button:hover:not(:disabled) { color:var(--color-rune); border-color:var(--color-rune-dim); } button:disabled { opacity:.45; cursor:default; } button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; } details { padding:12px 0; border-top:1px solid var(--color-engraving); } summary { cursor:pointer; color:var(--color-parchment); font-size:11px; line-height:1.6; } details form { margin-top:12px; }.delete { margin-top:12px; color:var(--color-ember); width:100%; }
  @container(max-width:850px) { aside { border-left:0; border-top:1px solid var(--color-engraving); max-height:460px; } ul { max-height:190px; } }
</style>
