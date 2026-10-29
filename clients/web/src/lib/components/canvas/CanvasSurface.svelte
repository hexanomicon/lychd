<script lang="ts">
  import { onMount } from "svelte";
  import { boundsOfSelection, moveSelection, selectInBounds } from "$lib/canvas/engine";
  import { LASSO_POINT_LIMIT, selectInLasso } from "$lib/canvas/selection";
  import type { Bounds, CanvasNode, Packet, Point, Scene, Tool } from "$lib/canvas/types";
  import CanvasScene from "./CanvasScene.svelte";
  let { scene, tool, selected, locked = false, onselect, onchange, onbusy, onerror, onedit }: {
    scene: Scene; tool: Tool; selected: string[]; locked?: boolean;
    onselect: (ids: string[]) => boolean; onchange: (next: Scene, message: string) => void;
    onbusy: (busy: boolean) => void; onerror: (message: string) => void; onedit: (id: string) => void;
  } = $props();
  type Gesture = { pointer: number; mode: Tool | "move"; start: Point; client: Point; camera: { x: number; y: number; zoom: number }; ids: string[]; base: Scene; additive: boolean };
  let svg: SVGSVGElement;
  let width = $state(1000), height = $state(570);
  let camera = $state.raw({ x: 70, y: 80, zoom: 1 });
  let gesture = $state.raw<Gesture | null>(null);
  let draft = $state.raw<Scene | null>(null);
  let animation = $state.raw<Scene | null>(null);
  let animationFrame: number | undefined;
  let ink = $state.raw<Point[]>([]);
  let lasso = $state.raw<Point[]>([]);
  let marquee = $state.raw<Bounds | null>(null);
  let connectSource = $state<string | null>(null);
  let space = $state(false);
  const pointers: Record<number, Point> = Object.create(null);
  let pinch: { distance: number; zoom: number; world: Point } | null = null;
  let rendered = $derived(draft ?? animation ?? scene);
  let activeMode = $derived(space ? "pan" : tool);
  let selectionBounds = $derived(boundsOfSelection(rendered, selected));

  function local(event: PointerEvent | WheelEvent): Point { const rect = svg.getBoundingClientRect(); return { x: event.clientX - rect.left, y: event.clientY - rect.top }; }
  function world(point: Point): Point { return { x: (point.x - camera.x) / camera.zoom, y: (point.y - camera.y) / camera.zoom }; }
  function rectangle(a: Point, b: Point): Bounds { return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), width: Math.max(1, Math.abs(b.x - a.x)), height: Math.max(1, Math.abs(b.y - a.y)) }; }
  function hit(event: PointerEvent): string | null { return (event.target as Element).closest("[data-object-id]")?.getAttribute("data-object-id") ?? null; }
  function bounded(point: Point): Point { return { x: Math.max(-99000, Math.min(99000, point.x)), y: Math.max(-99000, Math.min(99000, point.y)) }; }

  export function center(): Point { return world({ x: width / 2, y: height / 2 }); }
  export function focusBoard() { svg?.focus(); }
  export function settleAnimation() { if (animationFrame !== undefined) cancelAnimationFrame(animationFrame); animationFrame = undefined; animation = null; }
  export function animateArrangement(from: Scene, to: Scene) {
    settleAnimation();
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const previous = new Map(from.nodes.map((node) => [node.id, node]));
    const started = performance.now(); animation = from;
    function step(now: number) {
      const progress = Math.min(1, (now - started) / 240), eased = 1 - (1 - progress) ** 3;
      animation = { ...to, nodes: to.nodes.map((node) => { const before = previous.get(node.id); return before ? { ...node, x: before.x + (node.x - before.x) * eased, y: before.y + (node.y - before.y) * eased } : node; }) };
      if (progress < 1) animationFrame = requestAnimationFrame(step);
      else { animationFrame = undefined; animation = null; }
    }
    animationFrame = requestAnimationFrame(step);
  }
  export function fit() {
    const ids = [...scene.nodes.map((node) => node.id), ...scene.strokes.filter((stroke) => !stroke.archived).map((stroke) => stroke.id)];
    const bounds = boundsOfSelection(scene, ids);
    if (!bounds) { camera = { x: width / 2 - 160, y: height / 2 - 100, zoom: 1 }; return; }
    const zoom = Math.max(.15, Math.min(1.2, (width - 140) / bounds.width, (height - 170) / bounds.height));
    camera = { x: (width - bounds.width * zoom) / 2 - bounds.x * zoom, y: (height - bounds.height * zoom) / 2 - bounds.y * zoom + 12, zoom };
  }
  export function reveal(id: string) {
    const bounds = boundsOfSelection(scene, [id]);
    if (bounds) camera = { ...camera, x: width / 2 - (bounds.x + bounds.width / 2) * camera.zoom, y: height / 2 - (bounds.y + bounds.height / 2) * camera.zoom };
  }
  function zoomBy(factor: number, anchor: Point = { x: width / 2, y: height / 2 }) {
    const point = world(anchor), zoom = Math.max(.15, Math.min(3, camera.zoom * factor));
    camera = { x: anchor.x - point.x * zoom, y: anchor.y - point.y * zoom, zoom };
  }
  function cancelGesture() { gesture = null; draft = null; ink = []; lasso = []; marquee = null; onbusy(false); }
  function start(event: PointerEvent) {
    if (event.button !== 0 && event.button !== 1) return;
    settleAnimation();
    event.preventDefault(); svg.focus();
    const client = local(event); pointers[event.pointerId] = client; svg.setPointerCapture?.(event.pointerId);
    if (Object.keys(pointers).length === 2) {
      cancelGesture();
      const [a, b] = Object.values(pointers);
      if (!a || !b) return;
      pinch = { distance: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), zoom: camera.zoom, world: world({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }) };
      return;
    }
    if (Object.keys(pointers).length > 1) return;
    const mode = event.button === 1 ? "pan" : activeMode;
    if (locked && mode !== "pan") return;
    const object = hit(event), point = bounded(world(client));
    if (mode === "connect") {
      const node = scene.nodes.find((item) => item.id === object);
      if (!node) { connectSource = null; return; }
      if (!connectSource) { connectSource = node.id; onselect([node.id]); return; }
      const next = { ...scene, edges: [...scene.edges, { id: crypto.randomUUID(), source: connectSource, target: node.id, label: "", source_stroke_ids: [] }] };
      onchange(next, "Connection added."); connectSource = null; return;
    }
    const ids = object ? (event.shiftKey ? selected.includes(object) ? selected.filter((id) => id !== object) : [...selected, object] : selected.includes(object) ? selected : [object]) : selected;
    if (mode === "select" && object && !onselect(ids)) return;
    if (mode === "select" && !object && !event.shiftKey && !onselect([])) return;
    gesture = { pointer: event.pointerId, mode: mode === "select" && object ? "move" : mode, start: point, client, camera, ids, base: scene, additive: event.shiftKey };
    onbusy(true);
    if (mode === "draw") ink = [point];
    if (mode === "lasso") lasso = [point];
    if (mode === "box" || mode === "select" && !object) marquee = rectangle(point, point);
  }
  function move(event: PointerEvent) {
    const client = local(event);
    if (Object.hasOwn(pointers, event.pointerId)) pointers[event.pointerId] = client;
    if (pinch && Object.keys(pointers).length >= 2) {
      const [a, b] = Object.values(pointers);
      if (!a || !b) return;
      const middle = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      const zoom = Math.max(.15, Math.min(3, pinch.zoom * Math.hypot(a.x - b.x, a.y - b.y) / pinch.distance));
      camera = { x: middle.x - pinch.world.x * zoom, y: middle.y - pinch.world.y * zoom, zoom }; return;
    }
    if (!gesture || event.pointerId !== gesture.pointer) return;
    const point = bounded(world(client));
    if (gesture.mode === "pan") camera = { ...camera, x: gesture.camera.x + client.x - gesture.client.x, y: gesture.camera.y + client.y - gesture.client.y };
    else if (gesture.mode === "draw") {
      const last = ink.at(-1)!;
      if (ink.length >= 2048) { finish(event); onerror("Stroke saved at the 2,048-point limit. Release the pointer to start another stroke."); return; }
      if (Math.hypot(point.x - last.x, point.y - last.y) > 1.5 / camera.zoom) ink = [...ink, point];
    } else if (gesture.mode === "lasso") {
      const last = lasso.at(-1)!;
      if (Math.hypot(point.x - last.x, point.y - last.y) > 3 / camera.zoom) {
        // Keep the transient contour bounded while allowing one continuous circling gesture.
        if (lasso.length >= LASSO_POINT_LIMIT) lasso = lasso.filter((_point, index) => index % 2 === 0);
        lasso = [...lasso, point];
      }
    } else if (gesture.mode === "move") {
      try { draft = moveSelection(gesture.base, gesture.ids, point.x - gesture.start.x, point.y - gesture.start.y); }
      catch (error) { onerror(error instanceof Error ? error.message : "Objects could not be moved."); cancelGesture(); }
    } else marquee = rectangle(gesture.start, point);
  }
  function finish(event: PointerEvent) {
    delete pointers[event.pointerId];
    if (pinch) { if (Object.keys(pointers).length < 2) pinch = null; cancelGesture(); return; }
    if (!gesture || gesture.pointer !== event.pointerId) return;
    const current = gesture;
    if (current.mode === "draw" && ink.length) {
      const points = ink.length === 1 ? [...ink, { x: ink[0]!.x + .1, y: ink[0]!.y + .1 }] : ink;
      onchange({ ...current.base, strokes: [...current.base.strokes, { id: crypto.randomUUID(), points, color: "#eef1f4", width: 2.5, archived: false }] }, "Stroke drawn.");
    } else if (current.mode === "move" && draft && Math.hypot(event.clientX - svg.getBoundingClientRect().left - current.client.x, event.clientY - svg.getBoundingClientRect().top - current.client.y) > 2) onchange(draft, "Selection moved.");
    else if (current.mode === "box" && marquee) {
      const node: CanvasNode = { id: crypto.randomUUID(), x: marquee.x, y: marquee.y, width: Math.max(160, Math.min(1600, marquee.width)), height: Math.max(90, Math.min(1600, marquee.height)), label: `Node ${scene.nodes.length + 1}`, kind: "box", pinned: false, source_stroke_ids: [], artwork: null };
      onchange({ ...current.base, nodes: [...current.base.nodes, node] }, "Editable node added."); onselect([node.id]);
    } else if (current.mode === "lasso") {
      const ids = selectInLasso(current.base, lasso);
      onselect(current.additive ? [...new Set([...selected, ...ids])] : ids);
    } else if (current.mode === "select" && marquee) {
      const ids = selectInBounds(scene, marquee); onselect(current.additive ? [...new Set([...selected, ...ids])] : ids);
    }
    cancelGesture();
  }
  function keydown(event: KeyboardEvent) {
    if (event.code === "Space") { event.preventDefault(); space = true; }
    if (event.key === "Escape") { cancelGesture(); connectSource = null; Object.keys(pointers).forEach((id) => delete pointers[Number(id)]); }
    if (event.key === "+" || event.key === "=") { event.preventDefault(); zoomBy(1.2); }
    if (event.key === "-") { event.preventDefault(); zoomBy(1 / 1.2); }
    if (event.key === "0") { event.preventDefault(); fit(); }
  }
  function wheel(event: WheelEvent) {
    event.preventDefault();
    if (gesture) return;
    if (event.ctrlKey || event.metaKey) zoomBy(Math.exp(-event.deltaY * .005), local(event));
    else camera = { ...camera, x: camera.x - event.deltaX, y: camera.y - event.deltaY };
  }
  function attachWheel(element: SVGSVGElement) {
    svg = element;
    element.addEventListener("wheel", wheel, { passive: false });
    return () => element.removeEventListener("wheel", wheel);
  }
  export async function captureCrop(bounds: Bounds): Promise<NonNullable<Packet["crop"]>> {
    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.querySelectorAll("[data-overlay], [data-grid]").forEach((element) => element.remove());
    clone.querySelector("[data-scene]")?.removeAttribute("transform");
    const ratio = Math.min(1.5, 1024 / Math.max(bounds.width, bounds.height));
    const cropWidth = Math.max(1, Math.min(1024, Math.ceil(bounds.width * ratio))), cropHeight = Math.max(1, Math.min(1024, Math.ceil(bounds.height * ratio)));
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg"); clone.setAttribute("viewBox", `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`);
    clone.setAttribute("width", String(cropWidth)); clone.setAttribute("height", String(cropHeight));
    clone.removeAttribute("class"); clone.removeAttribute("style");
    const palette = getComputedStyle(svg);
    for (const element of [clone, ...clone.querySelectorAll("*")]) for (const name of ["fill", "stroke"]) {
      const value = element.getAttribute(name);
      if (value?.startsWith("var(")) element.setAttribute(name, value.replace(/var\((--[\w-]+),\s*([^\)]+)\)/g, (_all, token: string, fallback: string) => palette.getPropertyValue(token).trim() || fallback));
    }
    const source = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" }));
    try {
      const image = new Image();
      await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error("The scene crop could not be rendered.")); image.src = source; });
      const canvas = document.createElement("canvas"); canvas.width = cropWidth; canvas.height = cropHeight;
      const context = canvas.getContext("2d"); if (!context) throw new Error("PNG capture is unavailable in this browser.");
      context.fillStyle = "#000000"; context.fillRect(0, 0, cropWidth, cropHeight); context.drawImage(image, 0, 0, cropWidth, cropHeight);
      const png = canvas.toDataURL("image/png");
      if ((png.length - png.indexOf(",") - 1) * .75 > 512 * 1024) throw new Error("PNG crop exceeds 512 KiB. Select a smaller area.");
      return { png_data_url: png, width: cropWidth, height: cropHeight, bounds };
    } finally { URL.revokeObjectURL(source); }
  }
  onMount(() => { const frame = requestAnimationFrame(fit); return () => { cancelAnimationFrame(frame); settleAnimation(); onbusy(false); }; });
</script>

<svelte:window onkeyup={(event) => { if (event.code === "Space") space = false; }} onblur={() => { space = false; cancelGesture(); Object.keys(pointers).forEach((id) => delete pointers[Number(id)]); pinch = null; }} />
<div class="surface" bind:clientWidth={width} bind:clientHeight={height}>
  <!-- A two-dimensional drawing application needs focus and keyboard gestures. The semantic object list supplies ordinary controls for every authored object. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
  <svg class={["board", `mode-${activeMode}`]} viewBox={`0 0 ${width || 1000} ${height || 570}`} aria-label="Canvas drawing surface" role="application" tabindex="0" aria-describedby="canvas-gestures" onpointerdown={start} onpointermove={move} onpointerup={finish} onpointercancel={(event) => { delete pointers[event.pointerId]; pinch = null; cancelGesture(); }} onlostpointercapture={() => { if (gesture) cancelGesture(); }} onkeydown={keydown} ondblclick={(event) => { const id = (event.target as Element).closest("[data-object-id]")?.getAttribute("data-object-id"); if (id && !locked) onedit(id); }} {@attach attachWheel}>
    <g data-scene transform={`translate(${camera.x} ${camera.y}) scale(${camera.zoom})`}><CanvasScene scene={rendered} selected={selected} /></g>
    <g data-overlay transform={`translate(${camera.x} ${camera.y}) scale(${camera.zoom})`} pointer-events="none">
      {#if selectionBounds}<rect x={selectionBounds.x - 6} y={selectionBounds.y - 6} width={selectionBounds.width + 12} height={selectionBounds.height + 12} fill="none" stroke="var(--color-rune)" stroke-width={1 / camera.zoom} stroke-dasharray="5 4" />{/if}
      {#if ink.length}<polyline points={ink.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="var(--color-frost)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />{/if}
      {#if lasso.length}<polygon points={lasso.map((point) => `${point.x},${point.y}`).join(" ")} fill="var(--color-rune)" fill-opacity=".04" stroke="var(--color-rune)" stroke-width={1.5 / camera.zoom} stroke-linejoin="round" />{/if}
      {#if marquee}<rect x={marquee.x} y={marquee.y} width={marquee.width} height={marquee.height} rx={tool === "box" ? 12 : 0} fill="var(--color-rune)" fill-opacity=".07" stroke="var(--color-rune)" stroke-width={1 / camera.zoom} stroke-dasharray={tool === "box" ? undefined : "5 4"} />{/if}
    </g>
  </svg>
  <div class="surface-note" aria-hidden="true">{connectSource ? "Choose the target node · Esc to cancel" : locked ? "Preview · pan and zoom to inspect" : activeMode === "draw" ? "Draw freely · your ink stays where you leave it" : activeMode === "lasso" ? "Circle drawings to select whole objects · Shift adds to selection" : activeMode === "box" ? "Drag to add an editable node" : activeMode === "connect" ? "Choose a source node, then a target" : activeMode === "pan" ? "Drag to move the view" : "Drag empty space to select whole objects"}</div>
  <div class="zoom" aria-label="Board view controls"><button type="button" aria-label="Zoom out" onclick={() => zoomBy(1 / 1.2)}>−</button><output aria-label="Zoom level">{Math.round(camera.zoom * 100)}%</output><button type="button" aria-label="Zoom in" onclick={() => zoomBy(1.2)}>+</button><button type="button" onclick={fit} title="Fit board (0)">Fit</button></div>
</div>

<style>
  .surface { position:relative; width:100%; height:100%; min-height:420px; overflow:hidden; background:#000; }
  .board { display:block; width:100%; height:100%; min-height:420px; touch-action:none; outline:none; }
  .board:focus-visible { box-shadow:inset 0 0 0 2px var(--color-rune); }
  .mode-draw,.mode-lasso,.mode-box,.mode-connect { cursor:crosshair; }.mode-pan { cursor:grab; }.mode-pan:active { cursor:grabbing; }
  .surface-note { position:absolute; left:20px; bottom:18px; max-width:calc(100% - 230px); pointer-events:none; font-size:11px; color:var(--color-ash); }
  .zoom { position:absolute; bottom:12px; right:14px; display:flex; align-items:center; gap:3px; padding:4px; background:var(--color-obsidian); border:1px solid var(--color-engraving); border-radius:var(--radius-rune); }
  button { border:0; min-width:32px; min-height:32px; padding:4px 8px; background:transparent; color:var(--color-parchment); border-radius:4px; cursor:pointer; font:12px var(--font-body); } button:hover { background:var(--color-obsidian-2); color:var(--color-rune); } button:focus-visible { outline:2px solid var(--color-rune); outline-offset:2px; }
  output { min-width:42px; text-align:center; color:var(--color-ash); font:11px var(--font-glyph); }
  @media(max-width:650px) { .surface-note { bottom:58px; max-width:calc(100% - 40px); }.surface,.board { min-height:400px; } }
  @media(forced-colors:active) { .board { border:1px solid CanvasText; }.zoom { border-color:ButtonText; } }
</style>
