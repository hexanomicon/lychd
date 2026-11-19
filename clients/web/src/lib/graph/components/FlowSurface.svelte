<script lang="ts">
  import { SvelteFlow, Background, ViewportPortal, MiniMap, Panel, MarkerType, useSvelteFlow, type Edge, type NodeTargetEventWithPointer } from "@xyflow/svelte";
  import { onDestroy, tick, untrack } from "svelte";
  import type { GraphCameraCommand } from "./camera-command";
  import type { GraphProjection } from "$lib/graph/model";
  import { reconcileEdges, reconcileNodes, type RenderNode } from "./flow-drafts";
  import { layoutProjection, NODE_WIDTH, NODE_HEIGHT, type Point } from "./layout";
  import { createOrbLayoutMemory, layoutOrbProjection, orbNodeWidth, ORB_NODE_HEIGHT } from "./orb-layout";
  import { layoutLoom } from "./loom-layout";
  import OrbNode from "./OrbNode.svelte";
  import AtlasNode from "./AtlasNode.svelte";
  import FlowNode from "./FlowNode.svelte";
  import FlowEdge from "./FlowEdge.svelte";

  let { projection, selectedId, onselect, label, focusId, focusRevision, onzoom, onviewportinteraction, presentation = "diagram", hideMinimap = false, frameLabel, cameraCommand = null }: {
    projection: GraphProjection; selectedId: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void; label: string;
    focusId: string | null; focusRevision: number;
    onzoom?: (zoom: number) => void; onviewportinteraction?: () => void;
    presentation?: "diagram" | "orb" | "atlas" | "loom"; hideMinimap?: boolean;
    frameLabel?: string;
    cameraCommand?: GraphCameraCommand | null;
  } = $props();
  const nodeTypes = { semantic: FlowNode, loom: FlowNode, orb: OrbNode, atlas: AtlasNode };
  const edgeTypes = { semantic: FlowEdge };
  const viewport = useSvelteFlow<RenderNode>();
  let nodes = $state.raw<RenderNode[]>([]);
  let edges = $state.raw<Edge[]>([]);
  let identity: string | undefined;
  let positions = new Map<string, Point>();
  let orbMemory = createOrbLayoutMemory();
  // Non-reactive gesture caches are intentionally separate from semantic and renderer state.
  const dragging = new Set<string>();
  const suppressPointerUntil = new Map<string, number>();
  let loomLayout = $derived(presentation === "loom" ? layoutLoom(projection) : null);
  let frame = $derived.by(() => {
    if (presentation !== "loom" || !frameLabel || !nodes.length) return null;
    const left = Math.min(...nodes.map(node => node.position.x)) - 25;
    const top = Math.min(...nodes.map(node => node.position.y)) - 39;
    return { left, top, width: Math.max(...nodes.map(node => node.position.x + (node.width ?? 0))) - left + 25,
      height: Math.max(...nodes.map(node => node.position.y + (node.height ?? 0))) - top + 20 };
  });
  let generation = 0;
  let disposed = false;
  let surface: HTMLDivElement;
  let cameraTouched = false;
  let firstLaneMembers = "";
  let fitZoom = 1;
  let lastZoom = 1;
  let cameraZoom = $state(1);

  onDestroy(() => { disposed = true; generation++; });

  function manualCamera() { cameraTouched = true; onviewportinteraction?.(); }

  function select(id: string, opener: HTMLElement, pointer = false) {
    if (pointer && (dragging.has(id) || (suppressPointerUntil.get(id) ?? 0) > performance.now())) return;
    onselect?.(id, opener);
  }
  const rememberDrag: NodeTargetEventWithPointer<MouseEvent | TouchEvent, RenderNode> = ({ nodes: moved }) => {
    if (presentation !== "orb") return;
    for (const node of moved) orbMemory.positions.set(node.id, { ...node.position });
  };
  const startDrag: NodeTargetEventWithPointer<MouseEvent | TouchEvent, RenderNode> = (event) => {
    if (presentation !== "orb") return;
    for (const node of event.nodes) dragging.add(node.id);
    manualCamera();
    rememberDrag(event);
  };
  const stopDrag: NodeTargetEventWithPointer<MouseEvent | TouchEvent, RenderNode> = (event) => {
    rememberDrag(event);
    for (const node of event.nodes) {
      dragging.delete(node.id);
      suppressPointerUntil.set(node.id, performance.now() + 250);
      if (suppressPointerUntil.size > 128) suppressPointerUntil.delete(suppressPointerUntil.keys().next().value!);
    }
  };
  async function fit(current = () => !disposed) {
    if (!current()) return false;
    const runs = presentation === "orb" ? nodes.filter(node => node.data.semantic.kind === "run") : [];
    let applied: boolean;
    if (runs.length && surface?.clientWidth && surface.clientHeight) {
      const left = Math.min(...nodes.map(node => node.position.x));
      const top = Math.min(...nodes.map(node => node.position.y));
      const width = Math.max(...nodes.map(node => node.position.x + (node.width ?? 1))) - left;
      const height = Math.max(...nodes.map(node => node.position.y + (node.height ?? 1))) - top;
      const margin = Math.min(40, surface.clientWidth * .045);
      const head = Math.min(38, surface.clientHeight * .055);
      const scale = Math.max(.08, Math.min(runs.length === 1 ? 1.06 : 1.45,
        (surface.clientWidth - 2 * margin) / width, (surface.clientHeight - head - 22) / height));
      applied = await viewport.setViewport({ x:(surface.clientWidth - width * scale) / 2 - left * scale,
        y:head - top * scale, zoom:scale }, { duration:0 });
    } else applied = await viewport.fitView({ padding:0.18, minZoom:0.1, maxZoom:1, duration:0 });
    if (applied && current()) {
      fitZoom = viewport.getZoom(); lastZoom = fitZoom; cameraZoom = fitZoom;
      if (presentation === "orb" && !runs.length) onzoom?.(cameraZoom);
    }
    return applied;
  }
  async function zoom(direction: "in" | "out", current = () => !disposed, manual = true) {
    if (manual) manualCamera();
    if (!current()) return false;
    // setZoom resolves the current provider; captured zoomIn/out methods can bind
    // the provider placeholder before the child flow mounts.
    const applied = await viewport.setZoom(viewport.getZoom() * (direction === "in" ? 1.2 : 1 / 1.2), { duration:0 });
    if (applied && current()) {
      lastZoom = viewport.getZoom(); cameraZoom = lastZoom;
      onzoom?.(presentation === "orb" ? cameraZoom : lastZoom / fitZoom);
    }
    return applied;
  }

  // Guard after settling and immediately before public renderer access.
  let lastCameraCommand: GraphCameraCommand | null = null;
  $effect(() => {
    const command = cameraCommand;
    if (!command || command === lastCameraCommand) return;
    lastCameraCommand = command;
    let cancelled = false;
    let authorized = true;
    const current = () => {
      authorized = !disposed && !cancelled && cameraCommand === command && command.isCurrent();
      return authorized;
    };
    void tick().then(async () => {
      if (!current()) { command.complete("stale"); return; }
      try {
        const applied = command.action === "fit"
          ? await fit(current)
          : await zoom(command.action === "zoom-in" ? "in" : "out", current, false);
        command.complete(disposed || cancelled || !authorized ? "stale" : applied ? "applied" : "unavailable");
      } catch { command.complete("unavailable"); }
    });
    return () => { cancelled = true; command.complete("stale"); };
  });

  // This effect is the owned external-library synchronization boundary. The raw bound
  // arrays are disposable Svelte Flow drafts, not a second reactive semantic projection.
  $effect(() => {
    const input = projection, chosen = selectedId, mode = presentation, loom = loomLayout;
    untrack(() => {
      const nextIdentity = `${mode}:${input.identity}`;
      const changedIdentity = identity !== nextIdentity;
      if (changedIdentity) {
        cameraTouched = false; firstLaneMembers = "";
        positions = new Map(); orbMemory = createOrbLayoutMemory();
        dragging.clear(); suppressPointerUntil.clear();
      }
      identity = nextIdentity;
      const computed = mode === "orb" ? layoutOrbProjection(input, orbMemory) : loom?.positions ?? layoutProjection(input);
      const retained = new Set(input.nodes.flatMap(node => [node.id, ...(node.members ?? [])]));
      for (const key of positions.keys()) if (!retained.has(key)) positions.delete(key);
      const nextNodes: RenderNode[] = input.nodes.map(semantic => {
        let position = computed.get(semantic.id) ?? { x:0, y:0 };
        const members = (semantic.members ?? []).flatMap(id => positions.has(id) ? [positions.get(id)!] : []);
        if (mode !== "orb" && members.length) position = {
          x:(Math.min(...members.map(p => p.x)) + Math.max(...members.map(p => p.x))) / 2,
          y:(Math.min(...members.map(p => p.y)) + Math.max(...members.map(p => p.y))) / 2
        };
        positions.set(semantic.id, position);
        return { id:semantic.id, type:mode === "diagram" ? "semantic" : mode, position:mode === "atlas" ? {x:position.x * .8, y:position.y * .67} : position,
          width:mode === "orb" ? orbNodeWidth(semantic) : mode === "atlas" ? 172 : mode === "loom" ? 180 : NODE_WIDTH, height:mode === "orb" ? ORB_NODE_HEIGHT : mode === "atlas" ? 60 : mode === "loom" ? 56 : NODE_HEIGHT,
          data:{ semantic:{ ...semantic }, select }, selected:semantic.id === chosen,
          draggable:mode === "orb", dragHandle:mode === "orb" ? ".orb-drag-handle" : undefined, connectable:false, deletable:false, selectable:false, focusable:false };
      });
      const points = new Map(nextNodes.map(node => [node.id, node.position]));
      const nextEdges: Edge[] = input.edges.map(edge => {
        let sourceHandle = "out", targetHandle = "in";
        if (edge.source === edge.target) {
          sourceHandle = "loop-out"; targetHandle = "loop-in";
        } else if (mode === "loom" && loom?.frames.some(frame => frame.id === edge.source || frame.id === edge.target)) {
          sourceHandle = "right-out"; targetHandle = "right-in";
        } else if (mode === "loom") {
          const start = points.get(edge.source), end = points.get(edge.target);
          if (start && end && start.y === end.y) {
            sourceHandle = start.x < end.x ? "right-out" : "left-out";
            targetHandle = start.x < end.x ? "left-in" : "right-in";
          } else if (start && end && start.x === end.x && (end.y - start.y > 160 || end.y < start.y)) {
            // Route a skip or a return around intermediate stations.
            sourceHandle = "right-out"; targetHandle = "right-in";
          }
        }
        return { id:edge.id, source:edge.source, target:edge.target, type:"semantic", sourceHandle, targetHandle,
          label:edge.label, ariaLabel:edge.label, data:{ relation:edge.relation, attention:edge.attention, presentation:mode },
          selectable:false, deletable:false, reconnectable:false,
          markerEnd:mode === "orb" && edge.relation !== "activity" ? undefined : { type:MarkerType.ArrowClosed, color:"var(--color-rune-dim)" } };
      });
      nodes = reconcileNodes(changedIdentity ? [] : nodes, nextNodes);
      edges = reconcileEdges(changedIdentity ? [] : edges, nextEdges);
      const version = ++generation;
      const loadedGroups = new Set(input.nodes.filter(node => node.kind !== "run").map(node => node.group));
      const detailed = mode === "orb" ? input.nodes.filter(node => node.kind === "run" && loadedGroups.has(node.group)).map(node => node.id).join("|") : "";
      if (changedIdentity || (mode === "orb" && detailed !== firstLaneMembers && !cameraTouched)) {
        void tick().then(() => { if (!disposed && version === generation && !cameraTouched) void fit(); });
      }
      firstLaneMembers = detailed;
    });
  });

  $effect(() => {
    const revision = focusRevision, id = focusId;
    if (!revision || !id) return;
    cameraTouched = true;
    void tick().then(() => { if (!disposed && id === focusId && revision === focusRevision) void viewport.fitView({ nodes:[{id}], maxZoom:1, duration:0, padding:0.5 }); });
  });
</script>

<div class="flow-surface" bind:this={surface}>
<SvelteFlow bind:nodes bind:edges {nodeTypes} {edgeTypes} colorMode="dark" fitView={presentation !== "orb"}
  oninit={() => { if (presentation === "orb" && !cameraTouched) void fit(); }}
  fitViewOptions={{padding:0.18,minZoom:0.1,maxZoom:1}} minZoom={0.08} maxZoom={2.5}
  nodesDraggable={presentation === "orb"} nodeDragThreshold={5} selectNodesOnDrag={false}
  onnodedragstart={startDrag} onnodedrag={rememberDrag} onnodedragstop={stopDrag} nodesConnectable={false} nodesFocusable={false} edgesFocusable={false}
  elementsSelectable={false} selectionOnDrag={false} deleteKey={[]} clickConnect={false}
  onbeforedelete={async () => false} onbeforeconnect={() => false} onbeforereconnect={() => false}
  onmove={(event,camera) => {
    if (event) manualCamera();
    if (event && Math.abs(camera.zoom-lastZoom) > 0.001) onzoom?.(presentation === "orb" ? camera.zoom : camera.zoom / fitZoom);
    cameraZoom = camera.zoom;
    lastZoom = camera.zoom;
  }}
  ariaLabelConfig={{ 'minimap.ariaLabel':`${label} overview` }}>
  {#if presentation === "orb"}<Background gap={24} size={1} patternColor="var(--color-engraving)" bgColor="var(--color-obsidian)" />{/if}
  {#if loomLayout?.frames.length}
    <ViewportPortal target="back">
      {#each loomLayout.frames as region (region.id)}
        <div class="scope-frame" aria-hidden="true" style:left={region.x+"px"} style:top={region.y+"px"} style:width={region.width+"px"} style:height={region.height+"px"}>
          <span>{region.title}</span>
        </div>
      {/each}
    </ViewportPortal>
  {/if}
  {#if frame}
    <ViewportPortal target="back">
      <div class="scope-frame" aria-hidden="true" style:left={frame.left+"px"} style:top={frame.top+"px"} style:width={frame.width+"px"} style:height={frame.height+"px"}>
        <span>{frameLabel}</span>
      </div>
    </ViewportPortal>
  {/if}
  <Panel position={presentation === "orb" ? "bottom-right" : "bottom-left"}>
    <div class={["canvas-controls", { "orb-controls": presentation === "orb" }]} role="group" aria-label="Graph viewport">
      {#if presentation !== "orb"}<button type="button" aria-label="Zoom in" onclick={() => zoom("in")}>+</button>{/if}
      <button type="button" aria-label="Zoom out" onclick={() => zoom("out")}>−</button>
      {#if presentation === "orb"}
        <output aria-label="Current zoom">{Math.round(cameraZoom * 100)}%</output>
        <button type="button" aria-label="Zoom in" onclick={() => zoom("in")}>+</button>
      {/if}
      <button type="button" aria-label="Fit graph" title="Fit graph" onclick={() => { manualCamera(); void fit(); }}>
        {#if presentation === "orb"}<svg aria-hidden="true" width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 8V2h6m4 0h6v6m0 4v6h-6m-4 0H2v-6"/></svg>{:else}Fit graph{/if}
      </button>
    </div>
  </Panel>
  {#if !hideMinimap}<MiniMap nodeColor="var(--color-rune-dim)" maskColor="color-mix(in srgb,var(--color-void) 72%,transparent)" />{/if}
</SvelteFlow>
</div>

<style>
.scope-frame { position:absolute; pointer-events:none; border:1px solid color-mix(in srgb,var(--color-accent) 32%,var(--color-void)); border-radius:12px;
    background:color-mix(in srgb,var(--color-accent) 3%,transparent); color:var(--color-parchment); font:500 12px var(--font-body); }
  .scope-frame span { position:absolute; top:9px; left:14px; }
  .flow-surface { width:100%; height:100%; min-width:0; min-height:0; position:relative; }
  .canvas-controls { display:flex; border:1px solid var(--color-control-border); border-radius:6px; overflow:hidden; background:var(--color-obsidian); box-shadow:0 6px 24px #0005; }
  .orb-controls { align-items:center; border-color:var(--color-engraving); }
  .orb-controls button { display:grid; place-items:center; min-width:32px; min-height:31px; padding:4px; border:0; }
  .orb-controls button:last-child { border-inline-start:1px solid var(--color-engraving); }
  .orb-controls output { color:var(--color-parchment); font:11px var(--font-glyph); }
  button { border:0; border-inline-end:1px solid var(--color-engraving); background:transparent; color:var(--color-bone); padding:.55rem .8rem; min-width:38px; min-height:38px; cursor:pointer; font:500 13px/1.4 var(--font-body); }
  button:last-child { border-inline-end:0; }
  button:hover { background:var(--color-obsidian-2); color:var(--color-rune); }
  button:focus-visible { outline:2px solid var(--color-rune); outline-offset:-3px; }
</style>
