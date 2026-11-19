<script lang="ts">
  import type { Snippet } from "svelte";
  import { MiniMap, SvelteFlowProvider } from "@xyflow/svelte";
  import type { GraphCameraCommand } from "./camera-command";
  import type { GraphProjection } from "$lib/graph/model";
  import FlowSurface from "./FlowSurface.svelte";
  import MinimapStar from "./MinimapStar.svelte";
  import "@xyflow/svelte/dist/style.css";
  let { projection, selectedId = null, onselect, label, focusId = null, focusRevision = 0, onzoom, onviewportinteraction, presentation = "diagram", hideMinimap = false, frameLabel, cameraCommand = null, navigator, navigatorRight = false }: {
    projection: GraphProjection;
    selectedId?: string | null;
    onselect?: (id: string, opener?: HTMLElement) => void;
    label: string;
    focusId?: string | null;
    focusRevision?: number;
    onzoom?: (zoom: number) => void;
    onviewportinteraction?: () => void;
    presentation?: "diagram" | "orb" | "atlas" | "loom";
    frameLabel?: string;
    navigator?: Snippet<[Snippet]>;
    navigatorRight?: boolean;
    hideMinimap?: boolean;
    cameraCommand?: GraphCameraCommand | null;
  } = $props();
</script>

{#snippet navigatorMap()}
  <div class="navigator-map">
    <MiniMap ariaLabel={`${label} navigator with current camera viewport`} width={196} height={114}
      nodeComponent={MinimapStar}
      pannable zoomable maskColor="color-mix(in srgb,var(--color-void) 72%,transparent)"
      nodeColor="var(--color-accent)" maskStrokeColor="var(--color-rune)" maskStrokeWidth={1.6} />
  </div>
{/snippet}

<div class={["graph-canvas", { "orb-canvas": presentation === "orb", "atlas-canvas": presentation === "atlas", "with-navigator": !!navigator, "map-right": navigatorRight && !!navigator }]} role="region" aria-label={label}>
  <svelte:boundary>
    <SvelteFlowProvider>
      {#if navigator}{@render navigator(navigatorMap)}{/if}
      <FlowSurface {projection} {selectedId} {onselect} {label} {focusId} {focusRevision} {onzoom} {onviewportinteraction} {presentation} {frameLabel} hideMinimap={hideMinimap || !!navigator} {cameraCommand} />
    </SvelteFlowProvider>
    {#snippet failed()}
      <div class="graph-failure" role="alert">The graph could not be displayed. The semantic outline and recorded details remain available below.</div>
    {/snippet}
  </svelte:boundary>
</div>

<style>
.graph-canvas { width:100%; min-width:0; height:var(--graph-height,clamp(460px,68vh,900px)); position:relative; overflow:hidden; border:0; border-radius:0; background:#000; --xy-background-color:#000; --xy-node-color:var(--color-bone); --xy-minimap-background-color:var(--color-obsidian); --xy-minimap-mask-background-color:color-mix(in srgb,var(--color-void) 72%,transparent); --xy-edge-label-background-color:var(--color-void); --xy-edge-label-color:var(--color-parchment); }
  .graph-canvas.with-navigator { display:grid; grid-template-columns:minmax(0,var(--graph-map-width,210px)) minmax(0,1fr); }
  .graph-canvas.map-right { grid-template-columns:minmax(0,1fr) minmax(0,var(--graph-map-width,210px)); }
  .map-right > :global(.svelte-flow) { grid-column:1; grid-row:1; }
  .map-right > :global(aside) { grid-column:2; grid-row:1; }
  .graph-canvas.atlas-canvas { height:var(--atlas-height,70vh); min-height:440px; }
  .navigator-map :global(.svelte-flow__minimap) { position:relative; inset:auto; margin:0; border:1px solid var(--color-engraving); border-radius:4px; overflow:hidden; background:var(--color-void); }
  .navigator-map :global(svg) { display:block; width:100%; height:auto; cursor:grab; }
  .graph-canvas.orb-canvas { height:100%; min-height:0; border:0; border-radius:0; background:var(--color-obsidian); --xy-background-color:var(--color-obsidian); }
  .orb-canvas :global(.svelte-flow__handle) { opacity:0; }
  .graph-failure { padding:2rem; color:var(--color-ember); font:14px/1.6 var(--font-body); }
  .graph-canvas :global(.svelte-flow__edge-textbg) { fill:var(--color-void); }
  /* The media reset's max-width:100% collapses these SVGs against XYFlow's
     zero-sized edge layer. Their paths deliberately overflow their viewport. */
  .graph-canvas :global(.svelte-flow__edges svg) { max-width:none; }
  .graph-canvas :global(.svelte-flow__attribution) { background:var(--color-obsidian); }
  .graph-canvas :global(.svelte-flow__attribution a) { color:var(--color-parchment); }
  .graph-canvas :global(.svelte-flow__handle) { width:7px; height:7px; background:var(--color-rune-dim); border:1px solid var(--color-void); pointer-events:none; }
  @media(max-width:600px) { .graph-canvas:not(.orb-canvas) { height:480px; } }
</style>
