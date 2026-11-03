<script lang="ts">
  import type { NexusMapModel, NexusMapNode, NexusMapObject } from "$lib/nexus/map";

  let { model, selectedId, onselect, stale = false }: {
    model: NexusMapModel;
    selectedId: string | null;
    onselect: (id: string, opener: HTMLElement) => void;
    stale?: boolean;
  } = $props();

  const uid = $props.id();
  let viewportWidth = $state(608);
  let viewportHeight = $state(464);
  let camera = $state.raw<{ x: number; y: number; zoom: number } | null>(null);
  let dragging = $state(false);
  let drag: { pointerId: number; x: number; y: number; startX: number; startY: number; zoom: number } | null = null;
  let view = $derived(camera ?? { x: 0, y: 0, zoom: Math.min(1, Math.max(0.65, viewportWidth / model.bounds.width)) });
  let objects = $derived(new Map(model.objects.map((object) => [object.id, object])));
  let positions = $derived(new Map(model.nodes.map((node) => [node.objectId, node])));

  function fit() {
    const zoom = Math.max(0.25, Math.min(1, viewportWidth / model.bounds.width, viewportHeight / model.bounds.height));
    camera = { x: (viewportWidth - model.bounds.width * zoom) / 2, y: (viewportHeight - model.bounds.height * zoom) / 2, zoom };
  }

  function zoomBy(multiplier: number) {
    const zoom = Math.min(2, Math.max(0.25, view.zoom * multiplier));
    camera = { x: viewportWidth / 2 - (viewportWidth / 2 - view.x) * zoom / view.zoom,
      y: viewportHeight / 2 - (viewportHeight / 2 - view.y) * zoom / view.zoom, zoom };
  }

  function pan(x: number, y: number) { camera = { ...view, x: view.x + x, y: view.y + y }; }

  function startPan(event: PointerEvent & { currentTarget: EventTarget & HTMLDivElement }) {
    if (event.button !== 0 || (event.target as Element).closest("button")) return;
    drag = { pointerId: event.pointerId, x: view.x, y: view.y, startX: event.clientX, startY: event.clientY, zoom: view.zoom };
    event.currentTarget.setPointerCapture(event.pointerId);
    dragging = true;
  }

  function movePan(event: PointerEvent) {
    if (!drag || drag.pointerId !== event.pointerId) return;
    camera = { x: drag.x + event.clientX - drag.startX, y: drag.y + event.clientY - drag.startY, zoom: drag.zoom };
  }

  function stopPan() { drag = null; dragging = false; }

  function reveal(node: NexusMapNode) {
    const left = node.x * view.zoom + view.x, top = node.y * view.zoom + view.y;
    const right = left + node.width * view.zoom, bottom = top + node.height * view.zoom;
    const x = left < 8 ? view.x + 8 - left : right > viewportWidth - 8 ? view.x + viewportWidth - 8 - right : view.x;
    const y = top < 8 ? view.y + 8 - top : bottom > viewportHeight - 8 ? view.y + viewportHeight - 8 - bottom : view.y;
    if (x !== view.x || y !== view.y) camera = { ...view, x, y };
  }

  function active(object: NexusMapObject) {
    if (stale) return false;
    return object.kind === "capability" ? object.row.is_active : object.kind === "animator" && object.rows.some((row) => row.is_active);
  }

  function stateLabel(object: NexusMapObject) {
    if (object.kind === "capability") return `${object.row.state} · ${object.row.health || "health unknown"}`;
    if (object.kind === "delegated") return `${object.runtime.runnable ? "available" : object.runtime.delivery} · ${object.runtime.capacity_posture.replaceAll("_", " ")}`;
    const states = [...new Set(object.rows.map((row) => row.state))];
    return states.length === 1 ? states[0] : "mixed capability observations";
  }
</script>

<section class="nexus-map" aria-labelledby={`${uid}-title`}>
  <header class="map-header">
    <div><h2 id={`${uid}-title`}>Capability ownership</h2><p>Reported Animator ownership · not physical topology.</p></div>
    <div class="map-controls" role="group" aria-label="Map camera">
      <button type="button" onclick={fit}>Fit</button>
      <button type="button" aria-label="Zoom out" onclick={() => zoomBy(1 / 1.2)}>−</button>
      <output aria-label="Map zoom">{Math.round(view.zoom * 100)}%</output>
      <button type="button" aria-label="Zoom in" onclick={() => zoomBy(1.2)}>+</button>
      <button type="button" aria-label="Pan left" onclick={() => pan(96, 0)}>←</button>
      <button type="button" aria-label="Pan up" onclick={() => pan(0, 96)}>↑</button>
      <button type="button" aria-label="Pan down" onclick={() => pan(0, -96)}>↓</button>
      <button type="button" aria-label="Pan right" onclick={() => pan(-96, 0)}>→</button>
    </div>
  </header>
  <p id={`${uid}-help`} class="map-help">Drag the background to pan, or use the camera buttons. Tab to inspect objects. {stale ? "Retained snapshot · stale." : "Cached snapshot."}</p>
  <div class={["map-viewport", { dragging }]} role="group" aria-label="Nexus observation map" aria-describedby={`${uid}-help`}
    bind:clientWidth={viewportWidth} bind:clientHeight={viewportHeight}
    onpointerdown={startPan} onpointermove={movePan} onpointerup={stopPan} onpointercancel={stopPan} onlostpointercapture={stopPan}>
    {#if !model.objects.length}<p class="map-empty">No managed capabilities, Portals, or delegated runtime pools in this snapshot.</p>{/if}
    <div class="map-plane" style:width={`${model.bounds.width}px`} style:height={`${model.bounds.height}px`}
      style:transform={`translate(${view.x}px, ${view.y}px) scale(${view.zoom})`}>
      <svg class="map-edges" width={model.bounds.width} height={model.bounds.height} aria-hidden="true">
        {#each model.edges as edge (edge.id)}
          {@const from = positions.get(edge.from)}{@const to = positions.get(edge.to)}
          {#if from && to}<path d={`M ${from.x + from.width} ${from.y + from.height / 2} C ${from.x + from.width + 24} ${from.y + from.height / 2}, ${to.x - 24} ${to.y + to.height / 2}, ${to.x} ${to.y + to.height / 2}`} />{/if}
        {/each}
      </svg>
      {#each model.sections as section (section.id)}
        <div class="map-section" style:top={`${section.y}px`}><h3>{section.label}</h3><p>{section.note}</p></div>
      {/each}
      {#each model.nodes as node (node.objectId)}
        {@const object = objects.get(node.objectId)}
        {#if object}
          <button type="button" class="map-object" data-kind={object.kind} data-active={active(object)} data-impact={object.impact}
            aria-label={`Inspect ${object.kind === "capability" ? `${object.scope} capability` : object.kind === "delegated" ? "delegated runtime" : "Animator"} ${object.kind === "delegated" ? object.runtime.runtime_id : object.label}`}
            aria-pressed={selectedId === object.id} title={`Inspect ${object.label}`}
            style:left={`${node.x}px`} style:top={`${node.y}px`} style:width={`${node.width}px`} style:height={`${node.height}px`}
            onpointerdown={(event) => { if (event.button === 0) event.preventDefault(); }}
            onfocus={() => reveal(node)}
            onclick={(event) => onselect(object.id, event.currentTarget)}>
            <span class="object-kind">{object.kind === "capability" ? `${object.scope} capability` : object.kind === "delegated" ? "Delegated runtime" : "Animator"}</span>
            <strong>{object.label}</strong>
            <span class="object-state">{active(object) ? "● " : ""}{stateLabel(object)}</span>
            {#if object.kind === "capability"}<span class="object-detail">{object.row.checked_at ? `Checked ${object.row.checked_at}` : "Freshness unknown"}</span>
            {:else if object.kind === "animator"}<span class="object-detail">{object.groups.length ? `Display groups: ${object.groups.join(" · ")}` : "Display groups not reported"}</span>
            {:else}<span class="object-detail">{object.runtime.runtime_id} · read only</span>{/if}
            {#if object.impact}<span class="object-impact">{object.impact === "both" ? "Planned eviction + launch" : object.impact === "evict" ? "Planned eviction" : "Planned launch"}</span>{/if}
          </button>
        {/if}
      {/each}
    </div>
  </div>
  <p class="map-legend"><span>◇ Identity</span><span>● Observed active</span><span>Selection opens inspection</span><span>Preview labels are non-binding</span></p>
</section>

<style>
  .nexus-map { min-width: 0; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); background: var(--color-void); overflow: hidden; }
  .map-header { display: flex; flex-wrap: wrap; gap: .5rem; justify-content: space-between; padding: .65rem .85rem .4rem; }
  .map-header h2 { color: var(--color-accent); font-family: var(--font-rune); font-size: var(--text-lg); }
  .map-header p, .map-help, .map-legend { color: var(--color-ash); font-size: var(--text-xs); }
  .map-header p { max-width: 35rem; margin-top: .3rem; }
  .map-controls { display: flex; align-items: center; gap: .3rem; flex-wrap: wrap; }
  .map-controls button { min-width: 2rem; min-height: 2rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); background: var(--color-obsidian); color: var(--color-rune); cursor: pointer; }
  .map-controls output { min-width: 3rem; text-align: center; color: var(--color-ash); font: var(--text-xs) var(--font-glyph); }
  .map-help { padding: 0 .85rem .5rem; }
  .map-viewport { position: relative; height: clamp(25rem, 56vh, 34rem); min-height: 25rem; overflow: hidden; border-block: 1px solid var(--color-engraving); cursor: grab; touch-action: none; }
  .map-viewport.dragging { cursor: grabbing; }
  .map-plane { position: absolute; top: 0; left: 0; transform-origin: 0 0; }
  .map-edges { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
  .map-edges path { fill: none; stroke: var(--color-control-border); stroke-width: 1.5; }
  .map-section { position: absolute; left: 24px; right: 24px; pointer-events: none; }
  .map-section h3 { font-size: var(--text-sm); font-family: var(--font-body); color: var(--color-parchment); }
  .map-section p { font-size: var(--text-2xs); color: var(--color-ash); margin-top: .15rem; }
  .map-object { position: absolute; display: flex; flex-direction: column; gap: .2rem; padding: .5rem .65rem; text-align: left; line-height: 1.25; background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-left: 3px solid var(--color-accent); border-radius: var(--radius-panel); color: var(--color-bone); cursor: pointer; overflow: hidden; }
  .map-object > * { flex: 0 0 auto; }
  .map-object[data-kind="animator"] { border-radius: var(--radius-panel) var(--radius-panel) 1rem var(--radius-panel); }
  .map-object[data-kind="delegated"] { border-style: dashed; }
  .map-object:hover, .map-object[aria-pressed="true"] { border-color: var(--color-rune); background: var(--color-obsidian-2); }
  .map-object[aria-pressed="true"] { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .map-object strong { font: var(--text-sm)/1.35 var(--font-glyph); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
  .object-kind { color: var(--color-accent); font-size: var(--text-2xs); text-transform: uppercase; letter-spacing: .07em; }
  .object-state { color: var(--color-ash); font-size: var(--text-xs); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
  .map-object[data-active="true"] .object-state { color: var(--color-lich); }
  .object-detail { color: var(--color-ash); font-size: var(--text-2xs); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
  .object-impact { color: var(--color-heat); font-size: var(--text-2xs); font-weight: 600; }
  .map-object[data-impact="evict"] .object-impact { color: var(--color-ember); }
  .map-object[data-impact] { border-bottom-style: double; border-bottom-width: 3px; }
  .map-legend { display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; padding: .65rem 1rem; }
  .map-legend span:first-child { color: var(--color-accent); }
  .map-legend span:nth-child(2) { color: var(--color-lich); }
  .map-empty { position: relative; z-index: 1; padding: 5rem 1rem; color: var(--color-ash); font-size: var(--text-sm); }
  button:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (forced-colors: active) { .map-object { border-color: CanvasText; } .map-object[aria-pressed="true"] { outline-color: Highlight; } .map-edges path { stroke: CanvasText; } }
</style>
