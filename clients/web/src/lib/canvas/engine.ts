import { z } from "zod";
import type { Artwork, Bounds, CanvasCrop, CanvasNode, Document, Packet, Point, Proposal, Scene, Stroke } from "./types";

const SCENE_BYTES = 2 * 1024 * 1024;
const DOCUMENT_BYTES = 12 * 1024 * 1024;
const PNG_BYTES = 512 * 1024;
const WORLD = 100000;
const HISTORY = 20;
const NUMBER_BUDGET_TOKEN = "0".repeat(24);
const encoder = new TextEncoder();
const uuid = z.string().regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/, "Use a canonical lowercase UUID.");
const coordinate = z.number().finite().min(-WORLD).max(WORLD);
const boundCoordinate = z.number().finite().min(-102000).max(102000);
const revision = z.number().int().min(1).max(Number.MAX_SAFE_INTEGER);
const text = (max: number, min = 0) => z.string().refine((value) => {
  const characters = [...value];
  return characters.length >= min && characters.length <= max && characters.every((c) => {
    const code = c.codePointAt(0)!;
    return code < 0xd800 || code > 0xdfff;
  });
}, `Use ${min}–${max} valid Unicode characters.`);
const pointSchema = z.object({ x: coordinate, y: coordinate }).strict();
const boundsSchema = z.object({ x: boundCoordinate, y: boundCoordinate, width: z.number().finite().positive().max(400000), height: z.number().finite().positive().max(400000) }).strict();
const sourceIds = z.array(uuid).max(300).refine((ids) => new Set(ids).size === ids.length, "Source ink IDs must be unique.");

function bytes(value: unknown): number {
  try {
    // Shared with Python: every numeric primitive costs 26 ASCII bytes including quotes.
    const encoded = JSON.stringify(value, (_key, item: unknown) => typeof item === "number" ? NUMBER_BUDGET_TOKEN : item);
    if (encoded === undefined) throw new Error();
    return encoder.encode(encoded).byteLength;
  } catch { throw new Error("Canvas input must be finite JSON data."); }
}
function limit(value: unknown, max: number, name: string): void {
  if (bytes(value) > max) throw new Error(`${name} exceeds its byte limit.`);
}

const crcTable = Uint32Array.from({ length: 256 }, (_, index) => {
  let crc = index;
  for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  return crc >>> 0;
});
function crc32(data: Uint8Array, start: number, end: number): number {
  let crc = 0xffffffff;
  for (let i = start; i < end; i++) crc = crcTable[(crc ^ data[i]!) & 255]! ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

/** Checks a bounded PNG envelope; this does not run an image decoder or fetch media. */
function pngSize(dataUrl: string): { width: number; height: number } {
  const prefix = "data:image/png;base64,";
  if (!dataUrl.startsWith(prefix) || dataUrl.length > prefix.length + Math.ceil(PNG_BYTES / 3) * 4) throw new Error("Use a local PNG of at most 512 KiB.");
  const encoded = dataUrl.slice(prefix.length);
  if (!encoded || encoded.length % 4 !== 0 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded)) throw new Error("Malformed PNG base64.");
  let binary: string;
  try { binary = atob(encoded); } catch { throw new Error("Malformed PNG base64."); }
  if (btoa(binary) !== encoded) throw new Error("PNG base64 must use canonical encoding.");
  if (binary.length > PNG_BYTES) throw new Error("PNG exceeds 512 KiB.");
  const data = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  const signature = [137, 80, 78, 71, 13, 10, 26, 10];
  if (data.length < 57 || !signature.every((n, i) => data[i] === n)) throw new Error("Invalid PNG signature.");
  const view = new DataView(data.buffer);
  let offset = 8, width = 0, height = 0, depth = 0, color = -1, palette = false, idat = false, idatEnded = false, idatBytes = 0, ended = false;
  while (offset < data.length) {
    if (offset + 12 > data.length) throw new Error("Truncated PNG chunk.");
    const length = view.getUint32(offset);
    const end = offset + 12 + length;
    if (end > data.length) throw new Error("Truncated PNG chunk.");
    const name = String.fromCharCode(...data.subarray(offset + 4, offset + 8));
    if (!/^[A-Za-z]{4}$/.test(name) || crc32(data, offset + 4, end - 4) !== view.getUint32(end - 4)) throw new Error("Invalid PNG chunk or checksum.");
    if (offset === 8 && name !== "IHDR") throw new Error("PNG must begin with IHDR.");
    if (name === "IHDR") {
      if (offset !== 8 || length !== 13) throw new Error("Invalid PNG header.");
      width = view.getUint32(offset + 8); height = view.getUint32(offset + 12);
      if (width < 1 || height < 1 || width > 1024 || height > 1024) throw new Error("PNG dimensions must be 1–1024 pixels.");
      depth = data[offset + 16]!; color = data[offset + 17]!;
      const depths: Record<number, number[]> = { 0: [1, 2, 4, 8, 16], 2: [8, 16], 3: [1, 2, 4, 8], 4: [8, 16], 6: [8, 16] };
      if (!depths[color]?.includes(depth) || data[offset + 18] !== 0 || data[offset + 19] !== 0 || data[offset + 20]! > 1) throw new Error("Invalid PNG header fields.");
    } else if (["acTL", "fcTL", "fdAT"].includes(name)) throw new Error("PNG must contain one static image.");
    else if (name === "PLTE") {
      if (palette || idat || color === 0 || color === 4 || length === 0 || length % 3 !== 0 || length > 768 || (color === 3 && length / 3 > 2 ** depth)) throw new Error("Invalid PNG palette.");
      palette = true;
    } else if (name === "IDAT") {
      if (idatEnded || (color === 3 && !palette)) throw new Error("Invalid PNG image data ordering.");
      idat = true; idatBytes += length;
    } else if (name === "IEND") {
      if (length !== 0 || !idat || !idatBytes || end !== data.length) throw new Error("Invalid PNG ending.");
      ended = true;
    } else if (name.charCodeAt(0) < 97) throw new Error("Unsupported critical PNG chunk.");
    if (idat && name !== "IDAT") idatEnded = true;
    offset = end;
  }
  if (!ended) throw new Error("PNG is missing IEND.");
  return { width, height };
}

const artworkSchema = z.object({ png_data_url: z.string(), alt: text(240), provenance: text(240) }).strict().superRefine((value, context) => {
  try { pngSize(value.png_data_url); } catch (error) { context.addIssue({ code: "custom", message: (error as Error).message }); }
});
const strokeSchema = z.object({ id: uuid, points: z.array(pointSchema).min(1).max(2048), color: z.string().regex(/^#[0-9a-f]{6}$/), width: z.number().finite().min(1).max(16), archived: z.boolean() }).strict();
const nodeSchema = z.object({ id: uuid, x: coordinate, y: coordinate, width: z.number().finite().min(32).max(1600), height: z.number().finite().min(32).max(1600), label: text(240), kind: z.enum(["box", "database", "service", "person", "note"]), pinned: z.boolean(), source_stroke_ids: sourceIds, artwork: artworkSchema.nullable() }).strict();
const edgeSchema = z.object({ id: uuid, source: uuid, target: uuid, label: text(240), source_stroke_ids: sourceIds }).strict();
const sceneSchema = z.object({ format: z.literal("lychd.canvas/1"), id: uuid, revision, title: text(120, 1), strokes: z.array(strokeSchema).max(300), nodes: z.array(nodeSchema).max(128), edges: z.array(edgeSchema).max(256) }).strict().superRefine((scene, context) => {
  const allIds = [...scene.strokes, ...scene.nodes, ...scene.edges].map((object) => object.id);
  const strokes = new Set(scene.strokes.map((s) => s.id)), nodes = new Set(scene.nodes.map((n) => n.id));
  if (new Set(allIds).size !== allIds.length) context.addIssue({ code: "custom", message: "Object IDs must be globally unique." });
  if (scene.strokes.reduce((total, stroke) => total + stroke.points.length, 0) > 30000) context.addIssue({ code: "custom", message: "Scene exceeds 30,000 ink points." });
  for (const object of [...scene.nodes, ...scene.edges]) if (object.source_stroke_ids.some((id) => !strokes.has(id))) context.addIssue({ code: "custom", message: "Source ink does not exist." });
  for (const edge of scene.edges) if (!nodes.has(edge.source) || !nodes.has(edge.target)) context.addIssue({ code: "custom", message: "Edge endpoints must exist." });
});
const documentSchema = z.object({ format: z.literal("lychd.canvas.document/1"), scene: sceneSchema, past: z.array(sceneSchema).max(HISTORY), future: z.array(sceneSchema).max(HISTORY) }).strict();
const selectionSchema = z.object({ scene_id: uuid, revision, object_ids: z.array(uuid).min(1).max(128), bounds: boundsSchema }).strict();
const cropSchema = z.object({ png_data_url: z.string(), width: z.number().int().min(1).max(1024), height: z.number().int().min(1).max(1024), bounds: boundsSchema }).strict().superRefine((crop, context) => {
  try { const size = pngSize(crop.png_data_url); if (size.width !== crop.width || size.height !== crop.height) throw new Error("Crop dimensions do not match its PNG."); }
  catch (error) { context.addIssue({ code: "custom", message: (error as Error).message }); }
});
const packetSchema = z.object({ format: z.literal("lychd.canvas.selection/1"), scene: sceneSchema, selection: selectionSchema, instruction: text(4000, 1), crop: cropSchema.nullable() }).strict();
const proposalSchema = z.object({ format: z.literal("lychd.canvas.proposal/1"), id: uuid, scene_id: uuid, base_revision: revision, selection_ids: z.array(uuid).min(1).max(128), author: text(120, 1), summary: text(1000, 1), nodes: z.array(nodeSchema).max(128), edges: z.array(edgeSchema).max(256), archive_stroke_ids: z.array(uuid).max(128) }).strict();

export function validateScene(value: unknown): Scene {
  limit(value, SCENE_BYTES, "Scene");
  return sceneSchema.parse(value);
}
export function validateDocument(value: unknown): Document {
  limit(value, DOCUMENT_BYTES, "Document");
  const document = documentSchema.parse(value);
  for (const scene of [document.scene, ...document.past, ...document.future]) {
    if (scene.id !== document.scene.id) throw new Error("History belongs to a different scene.");
    limit(scene, SCENE_BYTES, "Scene");
  }
  return document;
}
function visibleIds(scene: Scene): Set<string> {
  return new Set([...scene.strokes.filter((s) => !s.archived), ...scene.nodes, ...scene.edges].map((object) => object.id));
}
function sameSet(left: string[], right: string[]): boolean {
  return new Set(left).size === left.length && new Set(right).size === right.length && left.length === right.length && left.every((id) => right.includes(id));
}
function sameBounds(left: Bounds, right: Bounds): boolean {
  return left.x === right.x && left.y === right.y && left.width === right.width && left.height === right.height;
}
export function validatePacket(value: unknown): Packet {
  limit(value, SCENE_BYTES + 1024 * 1024, "Packet");
  const packet = packetSchema.parse(value);
  limit(packet.scene, SCENE_BYTES, "Scene");
  const selection = packet.selection, ids = visibleIds(packet.scene);
  if (selection.scene_id !== packet.scene.id || selection.revision !== packet.scene.revision) throw new Error("Selection does not match the captured scene revision.");
  if (new Set(selection.object_ids).size !== selection.object_ids.length || selection.object_ids.some((id) => !ids.has(id))) throw new Error("Select unique, visible objects from this scene.");
  if (packet.crop && !sameBounds(packet.crop.bounds, selection.bounds)) throw new Error("Crop bounds do not match the selection.");
  return packet;
}

function mergeProposal(scene: Scene, proposal: Proposal): Scene {
  const nodes = new Map(scene.nodes.map((node) => [node.id, node]));
  const edges = new Map(scene.edges.map((edge) => [edge.id, edge]));
  const archived = new Set(proposal.archive_stroke_ids);
  proposal.nodes.forEach((node) => nodes.set(node.id, node));
  proposal.edges.forEach((edge) => edges.set(edge.id, edge));
  return { ...scene, revision: scene.revision + 1, nodes: [...nodes.values()], edges: [...edges.values()], strokes: scene.strokes.map((stroke) => archived.has(stroke.id) ? { ...stroke, archived: true } : stroke) };
}
export function validateProposal(value: unknown, input: Packet): Proposal {
  limit(value, SCENE_BYTES, "Proposal");
  const packet = validatePacket(input), proposal = proposalSchema.parse(value);
  if (proposal.scene_id !== packet.scene.id || proposal.base_revision !== packet.scene.revision) throw new Error("Proposal is stale or belongs to another scene.");
  if (!sameSet(proposal.selection_ids, packet.selection.object_ids)) throw new Error("Proposal selection does not match the captured selection.");
  const selected = new Set(packet.selection.object_ids), strokes = new Set(packet.scene.strokes.map((s) => s.id));
  const visibleStrokes = new Set(packet.scene.strokes.filter((s) => !s.archived).map((s) => s.id));
  const nodes = new Set(packet.scene.nodes.map((n) => n.id)), edges = new Set(packet.scene.edges.map((e) => e.id));
  const originalSources = new Map([...packet.scene.nodes, ...packet.scene.edges].map((object) => [object.id, new Set(object.source_stroke_ids)]));
  const proposedIds = [...proposal.nodes, ...proposal.edges].map((object) => object.id);
  if (new Set(proposedIds).size !== proposedIds.length || new Set(proposal.archive_stroke_ids).size !== proposal.archive_stroke_ids.length) throw new Error("Proposal object IDs must be unique.");
  for (const node of proposal.nodes) {
    if (strokes.has(node.id) || edges.has(node.id)) throw new Error("Object identity cannot change category.");
    if (nodes.has(node.id) && !selected.has(node.id)) throw new Error("Proposal updates a node outside the selection.");
  }
  for (const edge of proposal.edges) {
    if (strokes.has(edge.id) || nodes.has(edge.id)) throw new Error("Object identity cannot change category.");
    if (edges.has(edge.id) && !selected.has(edge.id)) throw new Error("Proposal updates an edge outside the selection.");
  }
  for (const object of [...proposal.nodes, ...proposal.edges]) {
    const retained = originalSources.get(object.id);
    if (object.source_stroke_ids.some((id) => !retained?.has(id) && (!selected.has(id) || !visibleStrokes.has(id)))) throw new Error("New source references must name selected visible ink.");
  }
  for (const id of proposal.archive_stroke_ids) if (!visibleStrokes.has(id) || !selected.has(id)) throw new Error("Proposal archives ink outside the selection.");
  validateScene(mergeProposal(packet.scene, proposal));
  return proposal;
}
export function makePacket(scene: Scene, ids: string[], bounds: Bounds, instruction: string, crop: CanvasCrop | null = null): Packet {
  return validatePacket({ format: "lychd.canvas.selection/1", scene, selection: { scene_id: scene.id, revision: scene.revision, object_ids: ids, bounds }, instruction, crop });
}
export function applyProposal(scene: Scene, input: Proposal, captured: Packet): Scene {
  const live = validateScene(scene), packet = validatePacket(captured);
  if (live.id !== packet.scene.id || live.revision !== packet.scene.revision || JSON.stringify(live) !== JSON.stringify(packet.scene)) throw new Error("The scene changed after capture. Capture a fresh packet.");
  const proposal = validateProposal(input, packet);
  return validateScene(mergeProposal(live, proposal));
}

function nextRevision(document: Document): number {
  const current = Math.max(document.scene.revision, ...document.past.map((s) => s.revision), ...document.future.map((s) => s.revision));
  if (current >= Number.MAX_SAFE_INTEGER) throw new Error("Scene revision limit reached.");
  return current + 1;
}
/** Replace portable content within a retained board, invalidating packets from either document. */
export function replaceDocument(input: Document, replacement: Document): Document {
  const current = validateDocument(input), next = validateDocument(replacement);
  const freshRevision = Math.max(nextRevision(current), nextRevision(next));
  const id = current.scene.id;
  return validateDocument({ ...next, scene: { ...next.scene, id, revision: freshRevision },
    past: next.past.map((entry) => ({ ...entry, id })),
    future: next.future.map((entry) => ({ ...entry, id })) });
}
function retainHistory(document: Document): Document {
  const bounded = { ...document, past: document.past.slice(-HISTORY), future: document.future.slice(-HISTORY) };
  while (bytes(bounded) > DOCUMENT_BYTES && (bounded.past.length || bounded.future.length)) {
    if (bounded.past.length) bounded.past = bounded.past.slice(1);
    else bounded.future = bounded.future.slice(1);
  }
  return validateDocument(bounded);
}
export function commit(input: Document, scene: Scene): Document {
  const document = validateDocument(input), candidate = validateScene(scene);
  if (candidate.id !== document.scene.id) throw new Error("A commit cannot replace the scene identity.");
  return retainHistory({ format: "lychd.canvas.document/1", scene: { ...candidate, revision: nextRevision(document) }, past: [...document.past, document.scene], future: [] });
}
export function undo(input: Document): Document {
  const document = validateDocument(input), target = document.past.at(-1);
  if (!target) return document;
  return retainHistory({ ...document, scene: { ...target, revision: nextRevision(document) }, past: document.past.slice(0, -1), future: [...document.future, document.scene] });
}
export function redo(input: Document): Document {
  const document = validateDocument(input), target = document.future.at(-1);
  if (!target) return document;
  return retainHistory({ ...document, scene: { ...target, revision: nextRevision(document) }, past: [...document.past, document.scene], future: document.future.slice(0, -1) });
}

export function blankDocument(title = "Untitled board"): Document {
  return validateDocument({ format: "lychd.canvas.document/1", scene: { format: "lychd.canvas/1", id: crypto.randomUUID(), revision: 1, title, strokes: [], nodes: [], edges: [] }, past: [], future: [] });
}
export function exampleDocument(): Document {
  const document = blankDocument("Illustrative sketch — local sample");
  const sampleId = (suffix: string) => `38bd86d5-20e0-4c92-a2c6-${suffix.padStart(12, "0")}`;
  document.scene.id = sampleId("1");
  const stroke = (suffix: string, points: Point[]): Stroke => ({ id: sampleId(suffix), points, color: "#b9cbd8", width: 3, archived: false });
  document.scene.strokes = [
    stroke("11", [{ x: 90, y: 110 }, { x: 249, y: 105 }, { x: 255, y: 225 }, { x: 86, y: 230 }, { x: 90, y: 110 }]),
    stroke("12", [{ x: 425, y: 113 }, { x: 585, y: 108 }, { x: 592, y: 228 }, { x: 422, y: 231 }, { x: 425, y: 113 }]),
    stroke("13", [{ x: 267, y: 165 }, { x: 395, y: 169 }, { x: 379, y: 154 }, { x: 395, y: 169 }, { x: 377, y: 182 }])
  ];
  document.scene.nodes = [{ id: sampleId("21"), x: 300, y: 330, width: 220, height: 96, label: "Illustrative context", kind: "note", pinned: false, source_stroke_ids: [], artwork: null }];
  return validateDocument(document);
}

function pointBounds(points: Point[], padding = 0): Bounds {
  const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  return { x: minX - padding, y: minY - padding, width: Math.max(1, Math.max(...xs) - minX + padding * 2), height: Math.max(1, Math.max(...ys) - minY + padding * 2) };
}
export function objectBounds(scene: Scene, id: string): Bounds | null {
  const node = scene.nodes.find((n) => n.id === id);
  if (node) return { x: node.x, y: node.y, width: node.width, height: node.height };
  const stroke = scene.strokes.find((s) => s.id === id && !s.archived);
  if (stroke) return pointBounds(stroke.points, stroke.width / 2);
  const edge = scene.edges.find((e) => e.id === id);
  if (!edge) return null;
  const source = scene.nodes.find((n) => n.id === edge.source), target = scene.nodes.find((n) => n.id === edge.target);
  if (source && edge.source === edge.target) return { x: source.x - 35, y: source.y - 80, width: source.width + 70, height: source.height + 80 };
  return source && target ? pointBounds([{ x: source.x, y: source.y }, { x: source.x + source.width, y: source.y + source.height }, { x: target.x, y: target.y }, { x: target.x + target.width, y: target.y + target.height }]) : null;
}
export function boundsOfSelection(scene: Scene, ids: string[]): Bounds | null {
  const bounds = ids.map((id) => objectBounds(scene, id)).filter((b): b is Bounds => b !== null);
  if (!bounds.length) return null;
  return pointBounds(bounds.flatMap((b) => [{ x: b.x, y: b.y }, { x: b.x + b.width, y: b.y + b.height }]));
}
function intersects(left: Bounds, right: Bounds): boolean {
  return left.x <= right.x + right.width && left.x + left.width >= right.x && left.y <= right.y + right.height && left.y + left.height >= right.y;
}
export function selectInBounds(scene: Scene, input: Bounds): string[] {
  const bounds = boundsSchema.parse(input);
  return [...scene.strokes.filter((s) => !s.archived), ...scene.nodes, ...scene.edges].filter((object) => {
    const objectBox = objectBounds(scene, object.id);
    return objectBox !== null && intersects(bounds, objectBox);
  }).map((object) => object.id);
}
export function moveSelection(scene: Scene, ids: string[], dx: number, dy: number): Scene {
  if (!Number.isFinite(dx) || !Number.isFinite(dy)) throw new Error("Movement must be finite.");
  const selected = new Set(ids);
  return validateScene({ ...scene, nodes: scene.nodes.map((node) => selected.has(node.id) ? { ...node, x: node.x + dx, y: node.y + dy } : node), strokes: scene.strokes.map((stroke) => selected.has(stroke.id) && !stroke.archived ? { ...stroke, points: stroke.points.map((point) => ({ x: point.x + dx, y: point.y + dy })) } : stroke) });
}
export function deleteSelection(scene: Scene, ids: string[]): Scene {
  const selected = new Set(ids);
  return validateScene({ ...scene, strokes: scene.strokes.filter((s) => !selected.has(s.id)), nodes: scene.nodes.filter((n) => !selected.has(n.id)).map((n) => ({ ...n, source_stroke_ids: n.source_stroke_ids.filter((id) => !selected.has(id)) })), edges: scene.edges.filter((e) => !selected.has(e.id) && !selected.has(e.source) && !selected.has(e.target)).map((e) => ({ ...e, source_stroke_ids: e.source_stroke_ids.filter((id) => !selected.has(id)) })) });
}
export function renameNode(scene: Scene, id: string, label: string): Scene {
  if (!scene.nodes.some((n) => n.id === id)) throw new Error("Node does not exist.");
  return validateScene({ ...scene, nodes: scene.nodes.map((n) => n.id === id ? { ...n, label } : n) });
}
export function pngArtwork(dataUrl: string, alt: string): Artwork {
  return artworkSchema.parse({ png_data_url: dataUrl, alt, provenance: "Local PNG import; generation provenance unverified." });
}

const distance = (left: Point, right: Point): number => Math.hypot(left.x - right.x, left.y - right.y);
function rectangle(strokes: Stroke[], closed: boolean): Bounds | null {
  const points = strokes.flatMap((stroke) => stroke.points);
  if (points.length < 5) return null;
  const bounds = pointBounds(points), small = Math.min(bounds.width, bounds.height);
  if (small < 32 || Math.max(bounds.width, bounds.height) > 1600) return null;
  if (closed && distance(points[0]!, points.at(-1)!) > Math.max(12, small * 0.16)) return null;
  const cornerTolerance = Math.max(8, small * 0.18), boundaryTolerance = Math.max(6, small * 0.1);
  const corners = [{ x: bounds.x, y: bounds.y }, { x: bounds.x + bounds.width, y: bounds.y }, { x: bounds.x, y: bounds.y + bounds.height }, { x: bounds.x + bounds.width, y: bounds.y + bounds.height }];
  if (!corners.every((corner) => points.some((point) => distance(corner, point) <= cornerTolerance))) return null;
  const onBoundary = (point: Point) => Math.min(Math.abs(point.x - bounds.x), Math.abs(point.x - bounds.x - bounds.width), Math.abs(point.y - bounds.y), Math.abs(point.y - bounds.y - bounds.height)) <= boundaryTolerance;
  if (points.filter(onBoundary).length / points.length < 0.9) return null;
  // Sparse corner samples alone also describe a crossed bow tie; inspect each drawn segment.
  const midpoints = strokes.flatMap((stroke) => stroke.points.slice(1).map((point, index) => ({ x: (point.x + stroke.points[index]!.x) / 2, y: (point.y + stroke.points[index]!.y) / 2 })));
  return midpoints.every(onBoundary) ? bounds : null;
}
function strokeGroups(strokes: Stroke[]): Stroke[][] {
  const groups: Stroke[][] = [], pending = new Set(strokes);
  while (pending.size) {
    const first = pending.values().next().value as Stroke;
    pending.delete(first);
    const group = [first];
    for (let index = 0; index < group.length; index++) {
      const current = group[index]!;
      for (const candidate of pending) {
        if ([current.points[0]!, current.points.at(-1)!].some((a) => [candidate.points[0]!, candidate.points.at(-1)!].some((b) => distance(a, b) <= 16))) {
          pending.delete(candidate); group.push(candidate);
        }
      }
    }
    groups.push(group.sort((a, b) => strokes.indexOf(a) - strokes.indexOf(b)));
  }
  return groups;
}
export function tidyProposal(input: Packet): Proposal {
  const packet = validatePacket(input), selected = new Set(packet.selection.object_ids);
  const strokes = packet.scene.strokes.filter((s) => selected.has(s.id) && !s.archived);
  const converted = new Set<string>(), shapes: { strokes: Stroke[]; bounds: Bounds }[] = [];
  for (const stroke of strokes) {
    const bounds = rectangle([stroke], true);
    if (bounds) { shapes.push({ strokes: [stroke], bounds }); converted.add(stroke.id); }
  }
  for (const group of strokeGroups(strokes.filter((s) => !converted.has(s.id)))) {
    if (group.length < 2 || group.length > 8) continue;
    const endpoints = group.flatMap((s) => [{ owner: s.id, point: s.points[0]! }, { owner: s.id, point: s.points.at(-1)! }]);
    if (!endpoints.every((a) => endpoints.filter((b) => a.owner !== b.owner && distance(a.point, b.point) <= 16).length === 1)) continue;
    const bounds = rectangle(group, false);
    if (bounds) { shapes.push({ strokes: group, bounds }); group.forEach((s) => converted.add(s.id)); }
  }
  const snap = (n: number) => Math.max(-WORLD, Math.min(WORLD, Math.round(n / 16) * 16));
  const nodes: CanvasNode[] = packet.scene.nodes.filter((n) => selected.has(n.id)).map((n) => ({ ...n, x: n.pinned ? n.x : snap(n.x), y: n.pinned ? n.y : snap(n.y) }));
  for (const [index, shape] of shapes.entries()) nodes.push({ id: crypto.randomUUID(), x: snap(shape.bounds.x), y: snap(shape.bounds.y), width: Math.min(1600, Math.max(64, Math.round(shape.bounds.width / 16) * 16)), height: Math.min(1600, Math.max(48, Math.round(shape.bounds.height / 16) * 16)), label: `Box ${index + 1}`, kind: "box", pinned: false, source_stroke_ids: shape.strokes.map((s) => s.id), artwork: null });
  return validateProposal({ format: "lychd.canvas.proposal/1", id: crypto.randomUUID(), scene_id: packet.scene.id, base_revision: packet.scene.revision, selection_ids: packet.selection.object_ids, author: "Local geometry Tidy (no model)", summary: `Geometry only: ${shapes.length} closed box group(s) converted; selected native positions aligned to a 16-unit grid. Ambiguous ink is retained; no connections inferred.`, nodes, edges: [], archive_stroke_ids: [...converted] }, packet);
}

/** Bounded CPU relaxation. Only requested, unpinned nodes move; other rectangles anchor it. */
export function arrangeScene(input: Scene, ids?: string[]): Scene {
  const scene = validateScene(input), selected = ids ? new Set(ids) : null;
  const nodes = scene.nodes.map((node) => ({ ...node }));
  const initial = new Map(nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
  const movable = new Set(nodes.filter((n) => !n.pinned && (!selected || selected.has(n.id))).map((n) => n.id));
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const clamp = (n: number) => Math.max(-WORLD, Math.min(WORLD, n));
  for (let step = 0; step < 96; step++) {
    const force = new Map(nodes.map((n) => [n.id, { x: (initial.get(n.id)!.x - n.x) * 0.025, y: (initial.get(n.id)!.y - n.y) * 0.025 }]));
    const push = (node: CanvasNode, x: number, y: number) => { if (movable.has(node.id)) { force.get(node.id)!.x += x; force.get(node.id)!.y += y; } };
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i]!, b = nodes[j]!;
      if (!movable.has(a.id) && !movable.has(b.id)) continue;
      const dx = b.x + b.width / 2 - a.x - a.width / 2, dy = b.y + b.height / 2 - a.y - a.height / 2;
      const overlapX = (a.width + b.width) / 2 + 28 - Math.abs(dx), overlapY = (a.height + b.height) / 2 + 28 - Math.abs(dy);
      if (overlapX > 0 && overlapY > 0) {
        if (overlapX < overlapY) { const amount = overlapX * 0.6 * (dx < 0 ? -1 : 1); push(a, -amount, 0); push(b, amount, 0); }
        else { const amount = overlapY * 0.6 * (dy < 0 ? -1 : 1); push(a, 0, -amount); push(b, 0, amount); }
      } else {
        const length = Math.max(1, Math.hypot(dx, dy)), amount = Math.min(2, 1600 / (length * length));
        push(a, -dx / length * amount, -dy / length * amount); push(b, dx / length * amount, dy / length * amount);
      }
    }
    for (const edge of scene.edges) {
      const a = byId.get(edge.source)!, b = byId.get(edge.target)!;
      if (a.id === b.id) continue;
      const dx = b.x + b.width / 2 - a.x - a.width / 2, dy = b.y + b.height / 2 - a.y - a.height / 2;
      const length = Math.hypot(dx, dy), ux = length < 0.001 ? 1 : dx / length, uy = length < 0.001 ? 0 : dy / length;
      const radius = (n: CanvasNode) => Math.min(Math.abs(ux) < 0.001 ? Infinity : n.width / 2 / Math.abs(ux), Math.abs(uy) < 0.001 ? Infinity : n.height / 2 / Math.abs(uy));
      const amount = (length - radius(a) - radius(b) - 88) * 0.018;
      push(a, ux * amount, uy * amount); push(b, -ux * amount, -uy * amount);
    }
    let largest = 0;
    for (const node of nodes) if (movable.has(node.id)) {
      const f = force.get(node.id)!, scale = Math.min(1, 18 / Math.max(1, Math.hypot(f.x, f.y)));
      const dx = f.x * scale * 0.65, dy = f.y * scale * 0.65;
      node.x = clamp(node.x + dx); node.y = clamp(node.y + dy); largest = Math.max(largest, Math.abs(dx), Math.abs(dy));
    }
    if (largest < 0.05) break;
  }
  // Resolve residual collisions without spring drift, including against fixed obstacles.
  for (let step = 0; step < 24; step++) {
    let changed = false;
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i]!, b = nodes[j]!, am = movable.has(a.id), bm = movable.has(b.id);
      if (!am && !bm) continue;
      const dx = b.x + b.width / 2 - a.x - a.width / 2, dy = b.y + b.height / 2 - a.y - a.height / 2;
      const ox = (a.width + b.width) / 2 + 24 - Math.abs(dx), oy = (a.height + b.height) / 2 + 24 - Math.abs(dy);
      if (ox <= 0 || oy <= 0) continue;
      const share = am && bm ? 0.5 : 1;
      if (ox < oy) { const shift = (ox + 0.01) * share * (dx < 0 ? -1 : 1); if (am) a.x = clamp(a.x - shift); if (bm) b.x = clamp(b.x + shift); }
      else { const shift = (oy + 0.01) * share * (dy < 0 ? -1 : 1); if (am) a.y = clamp(a.y - shift); if (bm) b.y = clamp(b.y + shift); }
      changed = true;
    }
    if (!changed) break;
  }
  return validateScene({ ...scene, nodes });
}
