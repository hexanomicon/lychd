<script lang="ts">
  let {
    width = $bindable(320),
    name,
    side = "right",
    min = 220,
    max = 620,
  }: { width?: number; name: string; side?: "left" | "right"; min?: number; max?: number } = $props();
  let drag: { id: number; x: number; width: number } | null = null;
  const bound = (value: number) => Math.min(max, Math.max(min, Math.round(value)));
  function start(event: PointerEvent) {
    if (event.button !== 0) return;
    drag = { id: event.pointerId, x: event.clientX, width };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    event.preventDefault();
  }
  function move(event: PointerEvent) {
    if (drag?.id === event.pointerId)
      width = bound(drag.width + (event.clientX - drag.x) * (side === "left" ? 1 : -1));
  }
  function key(event: KeyboardEvent) {
    if (event.key === "Home") width = min;
    else if (event.key === "End") width = max;
    else if (event.key === "ArrowLeft" || event.key === "ArrowRight")
      width = bound(width + (event.key === "ArrowRight" ? 16 : -16) * (side === "left" ? 1 : -1));
    else return;
    event.preventDefault();
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions (adjustable splitter follows the ARIA separator pattern) -->
<div
  class="grip"
  class:left={side === "left"}
  role="separator"
  tabindex="0"
  aria-label={name}
  aria-orientation="vertical"
  aria-valuenow={width}
  aria-valuemin={min}
  aria-valuemax={max}
  onkeydown={key}
  onpointerdown={start}
  onpointermove={move}
  onlostpointercapture={() => (drag = null)}
></div>

<style>
  .grip {
    position: absolute;
    inset-block: 0;
    left: -4px;
    width: 8px;
    z-index: 5;
    touch-action: none;
    cursor: col-resize;
  }
  .grip.left {
    left: auto;
    right: -4px;
  }
  .grip:hover,
  .grip:focus-visible {
    background: color-mix(in srgb, var(--color-accent) 30%, transparent);
  }
</style>
