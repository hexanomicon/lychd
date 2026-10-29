<script lang="ts">
  import { SvelteFlow, MiniMap, Panel, MarkerType, useSvelteFlow, type Node, type Edge, type NodeTargetEventWithPointer } from "@xyflow/svelte";
  import { onDestroy, tick, untrack } from "svelte";
  import type { GraphProjection, GraphNode } from "$lib/graph/model";
  import { layoutProjection, NODE_WIDTH, NODE_HEIGHT, type Point } from "./layout";
  import { createOrbLayoutMemory, layoutOrbProjection, orbTerritories, ORB_NODE_WIDTH, ORB_NODE_HEIGHT } from "./orb-layout";
  import OrbNode from "./OrbNode.svelte";
  import OrbTerritories from "./OrbTerritories.svelte";
  import FlowNode from "./FlowNode.svelte";
  import FlowEdge from "./FlowEdge.svelte";

  let { projection, selectedId, onselect, label, focusId, focusRevision, onzoom, onviewportinteraction, presentation = "diagram", hideMinimap = false }: {
    projection: GraphProjection; selectedId: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void; label: string;
    focusId: string | null; focusRevision: number;
    onzoom?: (zoom: number) => void; onviewportinteraction?: () => void;
    presentation?: "diagram" | "orb"; hideMinimap?: boolean;
  } = $props();
  type RenderNode = Node<{ semantic: GraphNode; select: (id: string, opener: HTMLElement, pointer?: boolean) => void }>;
  const nodeTypes = { semantic: FlowNode, orb: OrbNode };
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
  let territories = $derived(presentation === "orb" ? orbTerritories(projection, new Map(nodes.map(node => [node.id, node.position]))) : []);
  let generation = 0;
  let disposed = false;
  let fitZoom = 1;
  let lastZoom = 1;
  let cameraZoom = $state(1);

  onDestroy(() => { disposed = true; generation++; });

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
    onviewportinteraction?.();
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
  async function fit() {
    await viewport.fitView({ padding:0.18, minZoom:0.1, maxZoom:1, duration:0 });
    if (!disposed) {
      fitZoom = viewport.getZoom(); lastZoom = fitZoom; cameraZoom = fitZoom;
      if (presentation === "orb") onzoom?.(cameraZoom);
    }
  }
  async function zoom(direction: "in" | "out") {
    onviewportinteraction?.();
    // setZoom resolves the current provider; captured zoomIn/out methods can bind
    // the provider placeholder before the child flow mounts.
    await viewport.setZoom(viewport.getZoom() * (direction === "in" ? 1.2 : 1 / 1.2), { duration:0 });
    if (!disposed) {
      lastZoom = viewport.getZoom(); cameraZoom = lastZoom;
      onzoom?.(presentation === "orb" ? cameraZoom : lastZoom / fitZoom);
    }
  }

  // This effect is the owned external-library synchronization boundary. The raw bound
  // arrays are disposable Svelte Flow drafts, not a second reactive semantic projection.
  $effect(() => {
    const input = projection, chosen = selectedId, mode = presentation;
    untrack(() => {
      const nextIdentity = `${mode}:${input.identity}`;
      const changedIdentity = identity !== nextIdentity;
      if (changedIdentity) {
        positions = new Map(); orbMemory = createOrbLayoutMemory();
        dragging.clear(); suppressPointerUntil.clear();
      }
      identity = nextIdentity;
      const computed = mode === "orb" ? layoutOrbProjection(input, orbMemory) : layoutProjection(input);
      const retained = new Set(input.nodes.flatMap(node => [node.id, ...(node.members ?? [])]));
      for (const key of positions.keys()) if (!retained.has(key)) positions.delete(key);
      nodes = input.nodes.map(semantic => {
        let position = computed.get(semantic.id) ?? { x:0, y:0 };
        const members = (semantic.members ?? []).flatMap(id => positions.has(id) ? [positions.get(id)!] : []);
        if (mode !== "orb" && members.length) position = {
          x:(Math.min(...members.map(p => p.x)) + Math.max(...members.map(p => p.x))) / 2,
          y:(Math.min(...members.map(p => p.y)) + Math.max(...members.map(p => p.y))) / 2
        };
        positions.set(semantic.id, position);
        return { id:semantic.id, type:mode === "orb" ? "orb" : "semantic", position,
          width:mode === "orb" ? ORB_NODE_WIDTH : NODE_WIDTH, height:mode === "orb" ? ORB_NODE_HEIGHT : NODE_HEIGHT,
          data:{ semantic:{ ...semantic }, select }, selected:semantic.id === chosen,
          draggable:mode === "orb", dragHandle:mode === "orb" ? ".orb-drag-handle" : undefined, connectable:false, deletable:false, selectable:false, focusable:false };
      });
      edges = input.edges.map(edge => ({ id:edge.id, source:edge.source, target:edge.target,
        type:"semantic", sourceHandle:edge.source === edge.target ? "loop-out" : "out",
        targetHandle:edge.source === edge.target ? "loop-in" : "in", label:edge.label, ariaLabel:edge.label,
        data:{ relation:edge.relation, presentation:mode }, selectable:false, deletable:false, reconnectable:false,
        markerEnd:mode === "orb" ? undefined : { type:MarkerType.ArrowClosed, color:"var(--color-rune-dim)" } }));
      const version = ++generation;
      if (changedIdentity) void tick().then(() => { if (version === generation) void fit(); });
    });
  });

  $effect(() => {
    const revision = focusRevision, id = focusId;
    if (!revision || !id) return;
    void tick().then(() => { if (!disposed && id === focusId && revision === focusRevision) void viewport.fitView({ nodes:[{id}], maxZoom:1, duration:0, padding:0.5 }); });
  });
</script>

<div class="flow-surface" data-density={cameraZoom < 0.55 ? "far" : cameraZoom < 0.85 ? "middle" : "near"} style:--orb-ui-scale={Math.min(6, Math.max(0.5, 1 / cameraZoom))}>
<SvelteFlow bind:nodes bind:edges {nodeTypes} {edgeTypes} colorMode="dark" fitView
  fitViewOptions={{padding:0.18,minZoom:0.1,maxZoom:1}} minZoom={0.08} maxZoom={2.5}
  nodesDraggable={presentation === "orb"} nodeDragThreshold={5} selectNodesOnDrag={false}
  onnodedragstart={startDrag} onnodedrag={rememberDrag} onnodedragstop={stopDrag} nodesConnectable={false} nodesFocusable={false} edgesFocusable={false}
  elementsSelectable={false} selectionOnDrag={false} deleteKey={[]} clickConnect={false}
  onbeforedelete={async () => false} onbeforeconnect={() => false} onbeforereconnect={() => false}
  onmove={(event,camera) => {
    if (event) onviewportinteraction?.();
    if (event && Math.abs(camera.zoom-lastZoom) > 0.001) onzoom?.(presentation === "orb" ? camera.zoom : camera.zoom / fitZoom);
    cameraZoom = camera.zoom;
    lastZoom = camera.zoom;
  }}
  ariaLabelConfig={{ 'minimap.ariaLabel':`${label} overview` }}>
  {#if presentation === "orb"}<OrbTerritories {territories} />{/if}
  <Panel position="bottom-left">
    <div class={["canvas-controls", { "orb-controls": presentation === "orb" }]} role="group" aria-label="Graph viewport">
      <button type="button" aria-label="Zoom in" onclick={() => zoom("in")}>+</button>
      <button type="button" aria-label="Zoom out" onclick={() => zoom("out")}>−</button>
      <button type="button" onclick={() => { void fit(); }}>Fit graph</button>
    </div>
  </Panel>
  {#if !hideMinimap}<MiniMap nodeColor="var(--color-rune-dim)" maskColor="color-mix(in srgb,var(--color-void) 72%,transparent)" />{/if}
</SvelteFlow>
</div>

<style>
  .flow-surface { width:100%; height:100%; min-width:0; min-height:0; position:relative; }
  .flow-surface[data-density="far"] { --orb-name-visibility:hidden; --orb-caption-visibility:hidden; }
  .flow-surface[data-density="middle"] { --orb-caption-visibility:hidden; }
  .canvas-controls { display:flex; border:1px solid var(--color-engraving); border-radius:var(--radius-rune); overflow:hidden; background:var(--color-obsidian); }
  .orb-controls { background:color-mix(in srgb,var(--color-obsidian) 92%,transparent); }
  button { border:0; border-right:1px solid var(--color-engraving); background:transparent; color:var(--color-bone); padding:9px 12px; min-width:36px; cursor:pointer; font-size:13px; }
  button:last-child { border-right:0; }
  button:hover { background:var(--color-obsidian-2); }
  button:focus-visible { outline:2px solid var(--color-rune); outline-offset:-3px; }
</style>
