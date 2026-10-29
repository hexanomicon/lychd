<script lang="ts">
  import { SvelteFlow, MiniMap, Panel, MarkerType, useSvelteFlow, type Node, type Edge } from "@xyflow/svelte";
  import { onDestroy, tick, untrack } from "svelte";
  import type { GraphProjection, GraphNode } from "$lib/graph/model";
  import { layoutProjection, NODE_WIDTH, NODE_HEIGHT, type Point } from "./layout";
  import FlowNode from "./FlowNode.svelte";
  import FlowEdge from "./FlowEdge.svelte";

  let { projection, selectedId, onselect, label, focusId, focusRevision, onzoom, onviewportinteraction }: {
    projection: GraphProjection; selectedId: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void; label: string;
    focusId: string | null; focusRevision: number;
    onzoom?: (zoom: number) => void; onviewportinteraction?: () => void;
  } = $props();
  type RenderNode = Node<{ semantic: GraphNode; select: (id: string, opener: HTMLElement) => void }>;
  const nodeTypes = { semantic: FlowNode };
  const edgeTypes = { semantic: FlowEdge };
  const viewport = useSvelteFlow<RenderNode>();
  let nodes = $state.raw<RenderNode[]>([]);
  let edges = $state.raw<Edge[]>([]);
  let identity: string | undefined;
  let positions = new Map<string, Point>();
  let generation = 0;
  let disposed = false;
  let fitZoom = 1;
  let lastZoom = 1;

  onDestroy(() => { disposed = true; generation++; });

  function select(id: string, opener: HTMLElement) { onselect?.(id, opener); }
  async function fit() {
    await viewport.fitView({ padding:0.18, minZoom:0.1, maxZoom:1, duration:0 });
    if (!disposed) { fitZoom = viewport.getZoom(); lastZoom = fitZoom; }
  }
  async function zoom(direction: "in" | "out") {
    onviewportinteraction?.();
    // setZoom resolves the current provider; captured zoomIn/out methods can bind
    // the provider placeholder before the child flow mounts.
    await viewport.setZoom(viewport.getZoom() * (direction === "in" ? 1.2 : 1 / 1.2), { duration:0 });
    if (!disposed) { lastZoom = viewport.getZoom(); onzoom?.(lastZoom / fitZoom); }
  }

  // Synchronize disposable third-party drafts from the immutable semantic input.
  $effect(() => {
    const input = projection, chosen = selectedId;
    untrack(() => {
      const changedIdentity = identity !== input.identity;
      if (changedIdentity) positions = new Map();
      identity = input.identity;
      const computed = layoutProjection(input);
      const retained = new Set(input.nodes.flatMap(node => [node.id, ...(node.members ?? [])]));
      for (const key of positions.keys()) if (!retained.has(key)) positions.delete(key);
      nodes = input.nodes.map(semantic => {
        let position = computed.get(semantic.id) ?? { x:0, y:0 };
        const members = (semantic.members ?? []).flatMap(id => positions.has(id) ? [positions.get(id)!] : []);
        if (members.length) position = {
          x:(Math.min(...members.map(p => p.x)) + Math.max(...members.map(p => p.x))) / 2,
          y:(Math.min(...members.map(p => p.y)) + Math.max(...members.map(p => p.y))) / 2
        };
        positions.set(semantic.id, position);
        return { id:semantic.id, type:"semantic", position, width:NODE_WIDTH, height:NODE_HEIGHT,
          data:{ semantic:{ ...semantic }, select }, selected:semantic.id === chosen,
          draggable:false, connectable:false, deletable:false, selectable:false, focusable:false };
      });
      edges = input.edges.map(edge => ({ id:edge.id, source:edge.source, target:edge.target,
        type:"semantic", sourceHandle:edge.source === edge.target ? "loop-out" : "out",
        targetHandle:edge.source === edge.target ? "loop-in" : "in", label:edge.label,
        data:{ relation:edge.relation }, selectable:false, deletable:false, reconnectable:false,
        markerEnd:{ type:MarkerType.ArrowClosed, color:"var(--color-rune-dim)" } }));
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

<SvelteFlow bind:nodes bind:edges {nodeTypes} {edgeTypes} colorMode="dark" fitView
  fitViewOptions={{padding:0.18,minZoom:0.1,maxZoom:1}} minZoom={0.08} maxZoom={2.5}
  nodesDraggable={false} nodesConnectable={false} nodesFocusable={false} edgesFocusable={false}
  elementsSelectable={false} selectionOnDrag={false} deleteKey={[]} clickConnect={false}
  onbeforedelete={async () => false} onbeforeconnect={() => false} onbeforereconnect={() => false}
  onmove={(event,camera) => {
    if (event) onviewportinteraction?.();
    if (event && Math.abs(camera.zoom-lastZoom) > 0.001) onzoom?.(camera.zoom / fitZoom);
    lastZoom = camera.zoom;
  }}
  ariaLabelConfig={{ 'minimap.ariaLabel':`${label} overview` }}>
  <Panel position="bottom-left">
    <div class="canvas-controls" role="group" aria-label="Graph viewport">
      <button type="button" aria-label="Zoom in" onclick={() => zoom("in")}>+</button>
      <button type="button" aria-label="Zoom out" onclick={() => zoom("out")}>−</button>
      <button type="button" onclick={() => { void fit(); }}>Fit graph</button>
    </div>
  </Panel>
  <MiniMap nodeColor="var(--color-rune-dim)" maskColor="color-mix(in srgb,var(--color-void) 72%,transparent)" />
</SvelteFlow>

<style>
  .canvas-controls { display:flex; border:1px solid var(--color-engraving); border-radius:var(--radius-rune); overflow:hidden; background:var(--color-obsidian); }
  button { border:0; border-right:1px solid var(--color-engraving); background:transparent; color:var(--color-bone); padding:9px 12px; min-width:36px; cursor:pointer; font-size:13px; }
  button:last-child { border-right:0; }
  button:hover { background:var(--color-obsidian-2); }
  button:focus-visible { outline:2px solid var(--color-rune); outline-offset:-3px; }
</style>
