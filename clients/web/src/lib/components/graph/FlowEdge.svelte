<script lang="ts">
  import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/svelte";
  let { id, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, label, data }: EdgeProps = $props();
  let orb = $derived(data?.presentation === "orb");
  let loop = $derived(source === target);
  let backwards = $derived(!loop && targetX <= sourceX);
  let geometry = $derived.by(() => {
    if (loop) return [`M ${sourceX} ${sourceY} C ${sourceX + 40} ${sourceY - 95}, ${targetX - 40} ${targetY - 95}, ${targetX} ${targetY}`, (sourceX + targetX) / 2, sourceY - 72] as const;
    if (orb && !loop) {
      const dx = targetX - sourceX, dy = targetY - sourceY;
      const bend = Math.min(52, Math.hypot(dx, dy) * 0.15);
      const distance = Math.max(1, Math.hypot(dx, dy));
      const cx = (sourceX + targetX) / 2 - dy / distance * bend;
      const cy = (sourceY + targetY) / 2 + dx / distance * bend;
      return [`M ${sourceX} ${sourceY} Q ${cx} ${cy}, ${targetX} ${targetY}`, cx, cy] as const;
    }
    if (backwards) {
      const top = Math.min(sourceY, targetY) - 130;
      return [`M ${sourceX} ${sourceY} C ${sourceX + 95} ${top}, ${targetX - 95} ${top}, ${targetX} ${targetY}`, (sourceX + targetX) / 2, top + 25] as const;
    }
    return getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  });
</script>

<g>
  {#if orb}<title>{label}</title>{/if}
<BaseEdge {id} path={geometry[0]} labelX={geometry[1]} labelY={geometry[2]}
  label={orb ? undefined : loop ? `${label ?? ""} · return` : label} {markerEnd}
  style={orb
    ? `vector-effect:non-scaling-stroke;stroke:color-mix(in srgb,var(--color-${data?.relation === "selection" ? "tertiary-edge" : "rune-dim"}) ${data?.relation === "contains" ? "40" : "65"}%,transparent);stroke-width:${data?.relation === "contains" ? "0.8" : "1.1"};${data?.relation === "permission" || data?.relation === "selection" ? "stroke-dasharray:3 6;" : ""}`
    : `stroke:var(--color-rune-dim);stroke-width:1.6;${data?.relation === "order" ? "stroke-dasharray:5 5;" : ""}`}
  labelStyle="fill:var(--color-parchment);font-size:11px" />
</g>
