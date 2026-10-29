<script lang="ts">
  import { SvelteFlowProvider } from "@xyflow/svelte";
  import type { GraphProjection } from "$lib/graph/model";
  import FlowSurface from "./FlowSurface.svelte";
  import "@xyflow/svelte/dist/style.css";
  let { projection, selectedId = null, onselect, label, focusId = null, focusRevision = 0, onzoom, onviewportinteraction, presentation = "diagram", hideMinimap = false }: {
    projection: GraphProjection;
    selectedId?: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void;
    label: string;
    focusId?: string | null;
    focusRevision?: number;
    onzoom?: (zoom: number) => void;
    onviewportinteraction?: () => void;
    presentation?: "diagram" | "orb";
    hideMinimap?: boolean;
  } = $props();
</script>

<div class={["graph-canvas", { "orb-canvas": presentation === "orb" }]} role="region" aria-label={label}>
  <svelte:boundary>
    <SvelteFlowProvider>
      <FlowSurface {projection} {selectedId} {onselect} {label} {focusId} {focusRevision} {onzoom} {onviewportinteraction} {presentation} {hideMinimap} />
    </SvelteFlowProvider>
    {#snippet failed()}
      <div class="graph-failure" role="alert">The graph could not be displayed. The semantic outline and recorded details remain available below.</div>
    {/snippet}
  </svelte:boundary>
</div>

<style>
  .graph-canvas { width:100%; min-width:0; height:var(--graph-height,clamp(460px,68vh,900px)); position:relative; overflow:hidden; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-void); --xy-background-color:var(--color-void); --xy-node-color:var(--color-bone); --xy-minimap-background-color:var(--color-obsidian); --xy-minimap-mask-background-color:color-mix(in srgb,var(--color-void) 72%,transparent); --xy-edge-label-background-color:var(--color-void); --xy-edge-label-color:var(--color-parchment); }
  .graph-canvas.orb-canvas { height:100%; min-height:0; border:0; border-radius:0; background:var(--color-void); --xy-background-color:var(--color-void); }
  .orb-canvas :global(.svelte-flow__handle) { opacity:0; }
  .graph-failure { padding:2rem; color:var(--color-ember); }
  .graph-canvas :global(.svelte-flow__edge-textbg) { fill:var(--color-void); }
  /* The media reset's max-width:100% collapses these SVGs against XYFlow's
     zero-sized edge layer. Their paths deliberately overflow their viewport. */
  .graph-canvas :global(.svelte-flow__edges svg) { max-width:none; }
  .graph-canvas :global(.svelte-flow__attribution) { background:var(--color-obsidian); }
  .graph-canvas :global(.svelte-flow__attribution a) { color:var(--color-parchment); }
  .graph-canvas :global(.svelte-flow__handle) { width:7px; height:7px; background:var(--color-rune-dim); border:1px solid var(--color-void); pointer-events:none; }
  @media(max-width:600px) { .graph-canvas:not(.orb-canvas) { height:480px; } }
</style>
