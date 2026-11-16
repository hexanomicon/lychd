<script lang="ts">
  import { ViewportPortal } from "@xyflow/svelte";
  import type { OrbTerritory } from "./orb-layout";
  let { territories }: { territories: readonly OrbTerritory[] } = $props();
</script>

<ViewportPortal target="back" class="orb-territories" aria-hidden="true">
  <svg class="territory-plane" width="1" height="1">
    {#each territories as territory (territory.id)}
      <g data-tone={territory.tone}>
        <path d={territory.path} />
        <text x={territory.labelPosition.x} y={territory.labelPosition.y}>{territory.label}</text>
      </g>
    {/each}
  </svg>
</ViewportPortal>

<style>
  :global(.orb-territories) { pointer-events:none; }
  .territory-plane { overflow:visible; }
  g { --territory-tint:var(--color-primary); }
  g[data-tone="purple"] { --territory-tint:var(--color-tertiary-edge); }
  path { fill:color-mix(in srgb,var(--territory-tint) 7%,transparent); stroke:color-mix(in srgb,var(--territory-tint) 9%,transparent); stroke-width:14px; stroke-linejoin:round; filter:blur(5px); }
  text { fill:var(--color-ash); font:11px var(--font-body); letter-spacing:.065em; }
</style>
