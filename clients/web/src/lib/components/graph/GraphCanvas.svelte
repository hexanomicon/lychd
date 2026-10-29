<script lang="ts">
  import { SvelteFlowProvider } from "@xyflow/svelte";
  import type { GraphProjection } from "$lib/graph/model";
  import FlowSurface from "./FlowSurface.svelte";
  import "@xyflow/svelte/dist/style.css";
  let { projection, selectedId = null, onselect, label, focusId = null, focusRevision = 0, onzoom, onviewportinteraction }: {
    projection: GraphProjection;
    selectedId?: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void;
    label: string;
    focusId?: string | null;
    focusRevision?: number;
    onzoom?: (zoom: number) => void;
    onviewportinteraction?: () => void;
  } = $props();
</script>

<div class="graph-canvas" role="region" aria-label={label}>
  <svelte:boundary>
    <SvelteFlowProvider>
      <FlowSurface {projection} {selectedId} {onselect} {label} {focusId} {focusRevision} {onzoom} {onviewportinteraction} />
    </SvelteFlowProvider>
    {#snippet failed()}
      <div class="graph-failure" role="alert">The graph could not be displayed. The semantic outline and recorded details remain available below.</div>
    {/snippet}
  </svelte:boundary>
</div>

<style>
  .graph-canvas { width:100%; min-width:0; height:var(--graph-height,clamp(460px,68vh,900px)); position:relative; overflow:hidden; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-void); --xy-background-color:var(--color-void); --xy-node-color:var(--color-bone); --xy-minimap-background-color:var(--color-obsidian); --xy-minimap-mask-background-color:color-mix(in srgb,var(--color-void) 72%,transparent); --xy-edge-label-background-color:var(--color-void); --xy-edge-label-color:var(--color-parchment); }
  .graph-failure { padding:2rem; color:var(--color-ember); }
  .graph-canvas :global(.svelte-flow__edge-textbg) { fill:var(--color-void); }
  .graph-canvas :global(.svelte-flow__attribution) { background:var(--color-obsidian); }
  .graph-canvas :global(.svelte-flow__attribution a) { color:var(--color-parchment); }
  .graph-canvas :global(.svelte-flow__handle) { width:7px; height:7px; background:var(--color-rune-dim); border:1px solid var(--color-void); pointer-events:none; }
  @media(max-width:600px) { .graph-canvas { height:480px; } }
</style>
