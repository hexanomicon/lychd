<script lang="ts">
  import { useNodeConnections, useSvelteFlow, type MiniMapNodeProps } from "@xyflow/svelte";
  import { untrack } from "svelte";
  let { id, x = 0, y = 0, width = 0, height = 0, selected, color }: MiniMapNodeProps = $props();
  const camera = useSvelteFlow();
  // XYFlow keys each minimap glyph by its stable node id.
  const outgoing = useNodeConnections({ id: untrack(() => id), handleType: "source" });
  let links = $derived(
    outgoing.current.flatMap((edge) => {
      const target = camera.getNode(edge.target);
      if (!target || target.hidden || target.id === id) return [];
      const bounds = camera.getNodesBounds([target.id]);
      return [{ id: edge.edgeId, x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 }];
    }),
  );
  let radius = $derived(Math.min(width, height) * 0.35);
  let core = $derived(radius * 0.34);
</script>

{#each links as endpoint (endpoint.id)}
  <line
    x1={x + width / 2}
    y1={y + height / 2}
    x2={endpoint.x}
    y2={endpoint.y}
    stroke="var(--color-ash)"
    stroke-opacity=".6"
    stroke-width=".7"
    vector-effect="non-scaling-stroke"
  />
{/each}
<g transform={`translate(${x + width / 2} ${y + height / 2})`} fill={selected ? "var(--color-bone)" : color}>
  <path
    d={`M0 ${-radius} L${core} ${-core} L${radius} 0 L${core} ${core} L0 ${radius} L${-core} ${core} L${-radius} 0 L${-core} ${-core} Z`}
  />
</g>
