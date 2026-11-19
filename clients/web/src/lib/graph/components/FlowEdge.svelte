<script lang="ts">
  import { BaseEdge, getBezierPath, getSmoothStepPath, type EdgeProps } from "@xyflow/svelte";
  let { id, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, label, data }: EdgeProps = $props();
  let orb = $derived(data?.presentation === "orb");
  let loop = $derived(source === target);
  let backwards = $derived(!loop && targetX <= sourceX);
  let geometry = $derived.by(() => {
    if (loop && orb) return [`M ${sourceX} ${sourceY} C ${sourceX+32} ${sourceY+19}, ${targetX+32} ${targetY-19}, ${targetX} ${targetY}`, sourceX+24, (sourceY+targetY)/2] as const;
    if (loop) return [`M ${sourceX} ${sourceY} C ${sourceX + 40} ${sourceY - 95}, ${targetX - 40} ${targetY - 95}, ${targetX} ${targetY}`, (sourceX + targetX) / 2, sourceY - 72] as const;
    if (orb || data?.presentation === "loom") return getSmoothStepPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, borderRadius:14, offset:16 });
    if (backwards) {
      const top = Math.min(sourceY, targetY) - 130;
      return [`M ${sourceX} ${sourceY} C ${sourceX + 95} ${top}, ${targetX - 95} ${top}, ${targetX} ${targetY}`, (sourceX + targetX) / 2, top + 25] as const;
    }
    return getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  });
</script>

<g class={{ received: data?.attention === "received" }} data-relation={data?.relation}>
  {#if orb}<title>{label}</title>{/if}
<BaseEdge {id} path={geometry[0]} labelX={geometry[1]} labelY={geometry[2]}
  label={orb || (data?.presentation === "loom" && ["permit", "permits", "permission"].includes(String(label).toLowerCase())) ? undefined : loop ? `${label ?? ""} · return` : label} {markerEnd}
  style={orb
    ? `vector-effect:non-scaling-stroke;stroke:var(--orb-wire);stroke-width:1.35;stroke-linecap:round;${data?.relation === "permission" || data?.relation === "declared" ? "stroke-dasharray:4 4;" : ""}`
    : `stroke:var(--color-rune-dim);stroke-width:1.6;${data?.relation === "order" ? "stroke-dasharray:5 5;" : ""}`}
  labelStyle="fill:var(--color-parchment);font-size:11px" />
</g>

<style>
  g { --orb-wire:color-mix(in srgb,var(--color-accent) 53%,var(--color-engraving)); }
  g[data-relation="contains"] { --orb-wire:color-mix(in srgb,var(--color-accent) 32%,var(--color-engraving)); }
  g[data-relation="activity"] { --orb-wire:color-mix(in srgb,var(--color-primary) 58%,var(--color-engraving)); }
  .received :global(path) { stroke-width:2; animation:activity 1.2s ease-out 1; }
  @keyframes activity { from { stroke-opacity:1; } to { stroke-opacity:.7; } }
  @media(prefers-reduced-motion:reduce) { .received :global(path) { animation:none; } }
</style>
