<script lang="ts">
  import { onDestroy, type Snippet } from "svelte";
  import { MediaQuery } from "svelte/reactivity";
  import GraphMapRail from "$lib/graph/components/GraphMapRail.svelte";
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import { resolvePath } from "$lib/navigation/paths";
  import { studioSession } from "./session";
  import GraphCanvas from "$lib/graph/components/GraphCanvas.svelte";
  import {
    example,
    makeNode,
    project,
    validate,
    kinds,
    relations,
    type Blueprint,
    type DraftNode,
    type Kind,
  } from "./blueprint";

  let draft = $state.raw<Blueprint>(studioSession.draft ?? example());
  let selected = $state(studioSession.selected);
  let dirty = $state(studioSession.dirty);
  onDestroy(() => {
    studioSession.draft = draft;
    studioSession.selected = selected;
    studioSession.dirty = dirty;
  });
  $effect(() => {
    studioSession.dirty = dirty;
  });
  function warnOnReload(event: BeforeUnloadEvent) {
    if (dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  }
  let node = $derived(draft.nodes.find((n) => n.id === selected)!);
  let graph = $derived(project(draft, node.parent));
  let owner = $derived(draft.nodes.find((n) => n.id === node.parent));
  let members = $derived(draft.nodes.filter((n) => n.parent === selected));
  const compact = new MediaQuery("(max-width: 48rem)");
  let mapOpen = $derived(!compact.current);
  let mapWidth = $state(190);
  let inspectorOpen = $state(true);
  let inspectorWidth = $state(290);
  let expanded = $state.raw<string[]>([]);
  const icons: Record<Kind,string> = {agent:"nexus",object:"node",router:"connect",subflow:"loom",ledger:"language"};
  function toggle(id: string) {
    expanded = expanded.includes(id) ? expanded.filter(key => key !== id) : [...expanded, id];
  }
  let focusRevision = $state(0);
  let newKind = $state<Kind>("agent");
  let message = $state("");
  let error = $derived.by(() => {
    try {
      validate(draft);
      return "";
    } catch (e) {
      return e instanceof Error ? e.message : "Invalid blueprint";
    }
  });
  function inspect(id: string) {
    const parents: string[] = [];
    let parent = draft.nodes.find(n => n.id === id)?.parent;
    while (parent) {
      parents.push(parent);
      parent = draft.nodes.find(n => n.id === parent)?.parent;
    }
    expanded = [...new Set([...expanded, ...parents])];
    inspectorOpen = true;
    selected = id;
    focusRevision++;
  }
  function update(patch: Partial<DraftNode>) {
    draft = { ...draft, nodes: draft.nodes.map((n) => (n.id === selected ? { ...n, ...patch } : n)) };
    dirty = true;
    message = "";
  }
  function add(child: boolean) {
    const id = crypto.randomUUID();
    const added = makeNode(id, newKind, "New " + newKind, child ? selected : node.parent);
    draft = {
      ...draft,
      nodes: [...draft.nodes, added],
      edges: child
        ? draft.edges
        : [
            ...draft.edges,
            { id: crypto.randomUUID(), source: selected, target: id, relation: "supplies", label: "Input" },
          ],
    };
    inspect(id);
    dirty = true;
    message = "";
  }
  function changeEdge(id: string, patch: Partial<Blueprint["edges"][number]>) {
    draft = { ...draft, edges: draft.edges.map((e) => (e.id === id ? { ...e, ...patch } : e)) };
    dirty = true;
    message = "";
  }
  function download() {
    const blob = new Blob([JSON.stringify(validate(draft), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sdlc.loom.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dirty = false;
    message = "Exported sdlc.loom.json.";
  }
  async function restore(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    try {
      const next = validate(JSON.parse(await file.text()));
      if (dirty && !window.confirm("Replace the draft and discard its unexported changes?")) {
        input.value = "";
        return;
      }
      dirty = false;
      draft = next;
      inspect(next.nodes.find((n) => !n.parent)!.id);
      message = "Opened " + file.name;
    } catch (e) {
      message = "Could not open blueprint. " + (e instanceof Error ? e.message : "Invalid document");
    }
    input.value = "";
  }
</script>

{#snippet tree(parent: string)}
  <ul class="branches">
    {#each draft.nodes.filter(n => n.parent === parent) as item (item.id)}
      <li>
        <div class="branch">
          {#if draft.nodes.some(n => n.parent === item.id)}
            <button class="fold" aria-label={(expanded.includes(item.id) ? "Collapse " : "Expand ") + item.name} aria-expanded={expanded.includes(item.id)} onclick={() => toggle(item.id)}>{expanded.includes(item.id) ? "▾" : "▸"}</button>
          {/if}
          <button class="target" aria-current={selected === item.id ? "true" : undefined} onclick={() => inspect(item.id)}>
            <AltarIcon name={icons[item.kind]} size={14} />{item.name}
          </button>
        </div>
        {#if expanded.includes(item.id)}{@render tree(item.id)}{/if}
      </li>
    {/each}
  </ul>
{/snippet}
<svelte:window onbeforeunload={warnOnReload} />
<section class="studio" aria-label="Workflow blueprint editor">
  <header>
    <div>
      <small>LOOM · LOCAL BLUEPRINT</small>
      <h2>Software development lifecycle</h2>
    </div>
    <div class="actions">
      <a href={resolvePath("/loom")}>Registered Patterns</a>
      <label class="file"
        >Open JSON<input type="file" accept="application/json,.json" onchange={restore} /></label
      ><button class="primary" disabled={!!error} onclick={download}>Export draft ↓</button>
    </div>
  </header>
  <div class="workspace" style:--inspector-width={inspectorOpen ? inspectorWidth + "px" : "2.3rem"}>
    <div class="diagram">
      <nav aria-label="Flow level">
        <strong>{owner?.name ?? "Workflow overview"}</strong>
        {#if owner}<button onclick={() => inspect(owner!.id)}>↑ Parent flow</button>{/if}
        <span>{graph.nodes.length} nodes</span>
      </nav>
      <GraphCanvas
        projection={graph}
        selectedId={selected}
        focusId={selected}
        {focusRevision}
        onselect={inspect}
        label="Workflow blueprint graph"
        --graph-height="clamp(380px,65vh,900px)"
        --graph-map-width={mapOpen ? mapWidth + "px" : "2.3rem"}
      >
        {#snippet navigator(minimap: Snippet)}
          <GraphMapRail bind:open={mapOpen} bind:width={mapWidth} {minimap} name="Workflow Map">
            {@render tree("")}
          </GraphMapRail>
        {/snippet}
      </GraphCanvas>
      <div class="outline">
        <label
          >Browse nodes<select value={selected} onchange={(e) => inspect(e.currentTarget.value)}>
            {#each draft.nodes as n (n.id)}<option value={n.id}
                >{n.parent ? draft.nodes.find((p) => p.id === n.parent)?.name + " / " : ""}{n.name}</option
              >{/each}
          </select></label
        >
        <div class="note">
          Drafts stay in this tab as you move between instruments. Export a copy before closing the tab.
          Runtime activation is a separate operation.
        </div>
      </div>
    </div>
    <aside aria-label="Blueprint inspector" class:closed={!inspectorOpen}>
      <button class="inspector-toggle" aria-label={inspectorOpen ? "Collapse inspector" : "Expand inspector"} aria-expanded={inspectorOpen} onclick={() => inspectorOpen = !inspectorOpen}>{inspectorOpen ? "›" : "‹"}</button>
      {#if inspectorOpen}
      <PaneGrip bind:width={inspectorWidth} name="Inspector width" min={225} max={510} />
      <div class="fields">
      <small>{node.kind.toUpperCase()}</small>
      <h3>{node.name}</h3>
      {#if members.length}<button class="enter" onclick={() => inspect(members[0]!.id)}
          >Explore {node.kind} <span>{members.length} nodes →</span></button
        >{/if}
      <label>Name<input value={node.name} oninput={(e) => update({ name: e.currentTarget.value })} /></label>
      <label
        >Purpose<textarea
          rows="2"
          value={node.purpose}
          oninput={(e) => update({ purpose: e.currentTarget.value })}></textarea></label
      >
      {#each ["Previous", "Next"] as direction (direction)}
        {@const links = draft.edges.filter((e) =>
          direction === "Previous" ? e.target === selected : e.source === selected,
        )}
        {#if links.length}<div class="links">
            <small>{direction}</small>
            {#each links as edge (edge.id)}
              {@const peer = draft.nodes.find(
                (n) => n.id === (direction === "Previous" ? edge.source : edge.target),
              )!}
              <button onclick={() => inspect(peer.id)}
                ><span>{edge.label}</span>{peer.name} {direction === "Previous" ? "↑" : "→"}</button
              >
            {/each}
          </div>{/if}
      {/each}
      <details open={node.kind === "agent"}>
        <summary>{node.kind === "agent" ? "Agent configuration" : "Data contract"}</summary>
        <label
          >Inputs<textarea
            rows="2"
            value={node.inputs}
            oninput={(e) => update({ inputs: e.currentTarget.value })}></textarea></label
        >
        <label
          >Output schema (JSON)<textarea
            rows="3"
            value={node.schema}
            oninput={(e) => update({ schema: e.currentTarget.value })}></textarea></label
        >
        {#if node.kind === "agent"}
          <label
            >System prompt<textarea
              rows="3"
              value={node.system}
              oninput={(e) => update({ system: e.currentTarget.value })}></textarea></label
          >
          <label
            >User prompt<textarea
              rows="3"
              value={node.user}
              oninput={(e) => update({ user: e.currentTarget.value })}></textarea></label
          >
          <label
            >Model<input
              value={node.model}
              oninput={(e) => update({ model: e.currentTarget.value })}
            /></label
          >
          <label
            >Temperature<input
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={node.temperature}
              oninput={(e) => update({ temperature: e.currentTarget.valueAsNumber })}
            /></label
          >
          <label
            >Fallback<input
              value={node.fallback}
              oninput={(e) => update({ fallback: e.currentTarget.value })}
            /></label
          >
          <label
            >Declared tools<input
              value={node.tools}
              oninput={(e) => update({ tools: e.currentTarget.value })}
            /></label
          >
        {/if}
      </details>
      <details>
        <summary>Edit outgoing connections</summary>
        {#each draft.edges.filter((e) => e.source === selected) as edge (edge.id)}
          <fieldset>
            <legend>{edge.label}</legend><label
              >Relationship<select
                value={edge.relation}
                onchange={(e) =>
                  changeEdge(edge.id, { relation: e.currentTarget.value as typeof edge.relation })}
                >{#each relations as rel (rel)}<option>{rel}</option>{/each}</select
              ></label
            >
            <label
              >Route label or guard<input
                value={edge.label}
                oninput={(e) => changeEdge(edge.id, { label: e.currentTarget.value })}
              /></label
            >
            <label
              >Target<select
                value={edge.target}
                onchange={(e) => changeEdge(edge.id, { target: e.currentTarget.value })}
                >{#each graph.nodes as peer (peer.id)}<option value={peer.id}>{peer.label}</option
                  >{/each}</select
              ></label
            >
          </fieldset>
        {:else}<p>No outgoing connections.</p>{/each}
      </details>
      <div class="add">
        <label
          >Node type<select bind:value={newKind}
            >{#each kinds as kind (kind)}<option>{kind}</option>{/each}</select
          ></label
        ><button onclick={() => add(false)}>＋ Add connected node</button>
        {#if node.kind === "subflow" || node.kind === "router"}<button onclick={() => add(true)}
            >＋ Add inside {node.kind}</button
          >{/if}
      </div>
      </div>
      {/if}
    </aside>
  </div>
  {#if error || message}<p role="status">{error || message}</p>{/if}
</section>

<style>
  .studio {
    color: var(--color-parchment);
    min-width: 0;
  }
  header,
  nav,
  .actions,
  .links button,
  .enter {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }
  header {
    justify-content: space-between;
    flex-wrap: wrap;
    padding: 0.75rem 0 1.1rem;
  }
  small,
  nav span,
  .note {
    font: var(--text-xs)/1.5 var(--font-glyph);
    color: var(--color-ash);
  }
  header small,
  .fields > small {
    color: var(--color-rune);
    letter-spacing: 0.1em;
  }
  h2,
  h3 {
    margin: 0.25rem 0;
    color: var(--color-bone);
  }
  h2 {
    font-size: clamp(1.3rem, 2.4vw, 2.25rem);
  }
  .workspace {
    display: grid;
    grid-template-columns: minmax(0, 1fr) var(--inspector-width);
    border: 1px solid var(--color-engraving);
    border-radius: 6px;
    overflow: hidden;
  }
  .diagram,
  aside {
    min-width: 0;
  }
  aside {
    border-inline-start: 1px solid var(--color-engraving);
    position: relative;
  }
  .fields { max-height:80vh; overflow:auto; padding:1rem; }
  .inspector-toggle { position:absolute; top:.35rem; inset-inline-start:.25rem; z-index:1; }
  .fields > small { display: block; padding-inline-start: 2rem; min-height: 1.5rem; }
  .branches { padding:0; margin:0; list-style:none; }
  .branches .branches { margin-inline-start:.5rem; padding-inline-start:.4rem; border-inline-start:1px solid var(--color-engraving); }
  .branch,.target { display:flex; align-items:center; gap:.25rem; }
  .branch button { font-size:var(--text-xs); border:0; background:transparent; text-align:start; }
  .branch .fold { padding:.25rem; }
  .branch .target { flex:1; padding:.35rem .25rem; }
  .target :global(svg) { flex-shrink:0; color:var(--color-rune); }
  .target[aria-current],.target:hover { background:var(--color-obsidian-2); color:var(--color-rune); }
  .actions a { font-size:var(--text-sm); color:var(--color-parchment); }
  aside.closed { min-height:2.5rem; }
  header h2 { font-size:clamp(1.1rem,1.7vw,1.6rem); }
  @container work-area (max-width:46rem) {
    .fields { max-height:none; }
    aside :global(.grip) { display:none; }
  }
  nav,
  .outline {
    padding: 0.7rem 1rem;
    background: var(--color-obsidian);
  }
  nav span {
    margin-inline-start: auto;
  }
  button,
  .file,
  input,
  textarea,
  select {
    font: inherit;
    font-size: var(--text-sm);
    color: var(--color-bone);
    background: var(--color-obsidian);
    border: 1px solid var(--color-control-border);
    border-radius: 4px;
    padding: 0.4rem 0.55rem;
  }
  button,
  .file,
  summary {
    cursor: pointer;
  }
  button:hover,
  .file:hover {
    border-color: var(--color-rune);
  }
  button:disabled {
    opacity: 0.5;
  }
  .primary,
  .enter {
    color: var(--color-rune);
  }
  .file {
    position: relative;
    overflow: hidden;
    display: block;
    margin: 0;
  }
  .file input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }
  .file:focus-within,
  :is(button, textarea, input, select, summary):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 2px;
  }
  label {
    display: grid;
    gap: 0.25rem;
    margin: 0.6rem 0;
    font-size: var(--text-xs);
  }
  textarea {
    resize: vertical;
  }
  select,
  input,
  textarea {
    width: 100%;
    box-sizing: border-box;
  }
  details,
  .links,
  .add {
    margin-top: 0.75rem;
    padding-top: 0.65rem;
    border-top: 1px solid var(--color-engraving);
  }
  summary {
    font-weight: 600;
  }
  .enter,
  .links button {
    width: 100%;
    justify-content: space-between;
    text-align: start;
    margin: 0.35rem 0;
  }
  .links span,
  .enter span {
    font-size: var(--text-xs);
    color: var(--color-ash);
  }
  .add button {
    margin: 0.25rem 0.25rem 0.25rem 0;
  }
  .note {
    max-width: 68ch;
  }
  @container work-area (max-width:46rem) {
    .workspace {
      grid-template-columns: 1fr;
    }
    aside {
      max-height: none;
      border-inline-start: 0;
      border-top: 1px solid var(--color-engraving);
    }
  }
</style>
