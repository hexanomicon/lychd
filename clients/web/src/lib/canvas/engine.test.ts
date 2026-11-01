import { deflateSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { applyProposal, arrangeScene, blankDocument, boundsOfSelection, commit, deleteSelection, exampleDocument, makePacket, moveSelection, objectBounds, pngArtwork, redo, renameNode, replaceDocument, selectInBounds, tidyProposal, undo, validateDocument, validatePacket, validateProposal, validateScene } from "./engine";
import type { Bounds, CanvasNode, Packet, Proposal, Scene, Stroke } from "./types";
import parity from "./parity.json";

const id = (n: number) => `00000000-0000-0000-0000-${n.toString().padStart(12, "0")}`;
const node = (n: number, x = 20, y = 20): CanvasNode => ({ id: id(n), x, y, width: 160, height: 80, label: `Node ${n}`, kind: "box", pinned: false, source_stroke_ids: [], artwork: null });
const stroke = (n: number, archived = false): Stroke => ({ id: id(n), color: "#abcdef", width: 3, archived, points: [{ x: 10, y: 10 }, { x: 150, y: 10 }, { x: 150, y: 90 }, { x: 10, y: 90 }, { x: 10, y: 10 }] });
function scene(): Scene {
  return { format: "lychd.canvas/1", id: id(100), revision: 1, title: "Test board", strokes: [stroke(1), stroke(2, true)], nodes: [node(3), node(4, 400)], edges: [{ id: id(5), source: id(3), target: id(4), label: "Known connection", source_stroke_ids: [] }] };
}
const region: Bounds = { x: 0, y: 0, width: 200, height: 120 };
function packet(source = scene(), ids = [id(1), id(3)]): Packet { return makePacket(source, ids, region, "Regularize the selected geometry."); }
function proposal(input = packet()): Proposal {
  return { format: "lychd.canvas.proposal/1", id: id(200), scene_id: input.scene.id, base_revision: input.scene.revision, selection_ids: input.selection.object_ids, author: "Explicit imported fixture", summary: "Update the selected node and preserve original ink.", nodes: [{ ...input.scene.nodes[0]!, label: "Reviewed label", source_stroke_ids: [id(1)] }], edges: [], archive_stroke_ids: [id(1)] };
}
function freeze<T>(value: T): T {
  if (value && typeof value === "object") { Object.freeze(value); for (const item of Object.values(value)) freeze(item); }
  return value;
}
// Independent fixture encoder: valid RGBA PNG, optionally with a bounded ancillary chunk.
type PngChunk = { name: string; body: Buffer };
function png(width = 1, height = 1, padding = 0, edit?: (chunks: PngChunk[]) => PngChunk[]): string {
  function chunk(name: string, body: Uint8Array): Buffer {
    const data = Buffer.concat([Buffer.from(name, "ascii"), body]);
    let crc = 0xffffffff;
    for (const byte of data) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
    const size = Buffer.alloc(4), checksum = Buffer.alloc(4);
    size.writeUInt32BE(body.length); checksum.writeUInt32BE((crc ^ 0xffffffff) >>> 0);
    return Buffer.concat([size, data, checksum]);
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width); header.writeUInt32BE(height, 4); header[8] = 8; header[9] = 6;
  const image = deflateSync(Buffer.alloc((width * 4 + 1) * height));
  const chunks: PngChunk[] = [{ name: "IHDR", body: header }];
  if (padding) chunks.push({ name: "tEXt", body: Buffer.alloc(padding, 65) });
  chunks.push({ name: "IDAT", body: image }, { name: "IEND", body: Buffer.alloc(0) });
  const parts = [Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), ...(edit ? edit(chunks) : chunks).map((part) => chunk(part.name, part.body))];
  return `data:image/png;base64,${Buffer.concat(parts).toString("base64")}`;
}

describe("portable scene and packet validation", () => {
  it("replaces retained board content with a fresh revision while preserving object identity, ink and history", () => {
    const current = validateDocument({ format: "lychd.canvas.document/1", scene: { ...scene(), revision: 4 },
      past: [{ ...scene(), revision: 6 }], future: [{ ...scene(), revision: 8 }] });
    const incomingScene = { ...scene(), id: id(101), revision: 10, title: "Imported board" };
    const incoming = validateDocument({ format: "lychd.canvas.document/1", scene: incomingScene,
      past: [{ ...incomingScene, revision: 16 }], future: [{ ...incomingScene, revision: 12 }] });
    const captured = packet(current.scene), candidate = proposal(captured);
    const rebound = replaceDocument(freeze(current), freeze(incoming));
    expect(rebound).toEqual({ ...incoming, scene: { ...incoming.scene, id: current.scene.id, revision: 17 },
      past: incoming.past.map((entry) => ({ ...entry, id: current.scene.id })),
      future: incoming.future.map((entry) => ({ ...entry, id: current.scene.id })) });
    expect(() => applyProposal(rebound.scene, candidate, captured)).toThrow(/changed after capture/);
    expect(current.scene.revision).toBe(4); expect(incoming.scene.id).toBe(id(101));
  });
  it("refuses document replacement atomically when either revision history cannot advance", () => {
    const normal = blankDocument();
    const exhausted = { ...normal, future: [{ ...normal.scene, revision: Number.MAX_SAFE_INTEGER }] };
    expect(() => replaceDocument(freeze(exhausted), freeze(normal))).toThrow(/revision limit/);
    expect(() => replaceDocument(freeze(normal), freeze(exhausted))).toThrow(/revision limit/);
    expect(normal.scene.revision).toBe(1); expect(exhausted.future[0]!.revision).toBe(Number.MAX_SAFE_INTEGER);
  });
  it("creates an explicit example and exports independent validated documents", () => {
    const document = blankDocument();
    expect(document.past).toEqual([]); expect(document.scene.revision).toBe(1);
    expect(validateDocument(exampleDocument()).scene.title).toContain("Illustrative");
    const clone = validateDocument(document); clone.scene.title = "Changed clone";
    expect(document.scene.title).toBe("Untitled board");
  });
  it("matches the portable shared fixture and one successor revision", () => {
    const document = validateDocument(parity.document), captured = validatePacket(parity.packet);
    const candidate = validateProposal(parity.proposal, captured);
    expect(applyProposal(document.scene, candidate, captured)).toEqual(parity.expected_scene);
    for (const sample of parity.expected_bounds) expect(objectBounds(document.scene, sample.id)).toEqual(sample.bounds);
    expect(exampleDocument()).toEqual(document);
  });
  it("rejects unknown fields at every imported level and malformed finite geometry", () => {
    const document = { format: "lychd.canvas.document/1", scene: scene(), past: [], future: [] };
    for (const invalid of [
      { ...document, hidden: true },
      { ...document, scene: { ...scene(), hidden: true } },
      { ...document, scene: { ...scene(), nodes: [{ ...node(3), x: Infinity }] } },
      { ...document, scene: { ...scene(), nodes: [{ ...node(3), width: 31 }] } },
      { ...document, scene: { ...scene(), strokes: [{ ...stroke(1), points: [{ x: NaN, y: 1 }] }] } },
      { ...document, scene: { ...scene(), strokes: [{ ...stroke(1), points: [{ x: 0, y: 0, pressure: 1 }] }] } },
      { ...document, scene: { ...scene(), strokes: [{ ...stroke(1), color: "#ABCDEF" }] } },
      { ...document, scene: { ...scene(), revision: 1.5 } },
      { ...document, scene: { ...scene(), id: "NOT-A-UUID" } }
    ]) expect(() => validateDocument(invalid)).toThrow();
    expect(() => validateScene({ ...scene(), nodes: [{ ...node(3), label: "x".repeat(241) }] })).toThrow();
    expect(() => validateScene({ ...scene(), nodes: [{ ...node(3), label: "\ud800" }] })).toThrow();
  });
  it("rejects duplicate object identities, missing endpoints and source references", () => {
    expect(() => validateScene({ ...scene(), nodes: [node(1)] })).toThrow(/unique/);
    expect(() => validateScene({ ...scene(), nodes: [node(3)] })).toThrow(/endpoints/);
    expect(() => validateScene({ ...scene(), nodes: [{ ...node(3), source_stroke_ids: [id(99)] }, node(4)] })).toThrow(/Source/);
    expect(() => validateScene({ ...scene(), edges: [{ ...scene().edges[0]!, source_stroke_ids: [id(99)] }] })).toThrow(/Source/);
    expect(() => validateScene({ ...scene(), nodes: [{ ...node(3), source_stroke_ids: [id(1), id(1)] }, node(4)] })).toThrow(/unique/);
    expect(validateScene({ ...scene(), edges: [{ ...scene().edges[0]!, target: id(3) }] }).edges).toHaveLength(1);
  });
  it("bounds point counts, snapshot counts, history identities and encoded scene bytes", () => {
    const many = Array.from({ length: 15 }, (_, i) => ({ ...stroke(1000 + i), points: Array.from({ length: 2048 }, () => ({ x: 1, y: 1 })) }));
    expect(() => validateScene({ ...scene(), strokes: many })).toThrow(/30,000/);
    const document = blankDocument();
    expect(() => validateDocument({ ...document, past: Array.from({ length: 21 }, () => document.scene) })).toThrow();
    expect(() => validateDocument({ ...document, past: [scene()] })).toThrow(/different scene/);
    const artwork = pngArtwork(png(1, 1, 410000), "A valid local PNG");
    expect(() => validateScene({ ...scene(), nodes: Array.from({ length: 4 }, (_, i) => ({ ...node(20 + i), artwork })), edges: [] })).toThrow(/byte limit/);
  });
  it("uses the shared conservative numeric budget without changing exported numeric data", () => {
    for (const recipe of parity.size_recipes) {
      const artwork = recipe.png_padding ? pngArtwork(png(1, 1, recipe.png_padding), "Budget fixture") : null;
      const strokes: Stroke[] = [];
      for (let offset = 0; offset < recipe.point_count; offset += 2048) strokes.push({ ...stroke(1000 + strokes.length), points: Array.from({ length: Math.min(2048, recipe.point_count - offset) }, () => ({ x: 1, y: 1 })) });
      const candidate = { ...scene(), title: "Conservative size parity", strokes, nodes: Array.from({ length: recipe.node_count }, (_, index) => ({ ...node(2000 + index), artwork })), edges: [] };
      // This rejection would pass the previous literal-JSON byte counter.
      if (!recipe.expected_valid) {
        expect(new TextEncoder().encode(JSON.stringify(candidate)).byteLength).toBeLessThan(2 * 1024 * 1024);
        expect(() => validateScene(candidate), recipe.name).toThrow(/byte limit/);
      } else {
        const validated = validateScene(candidate);
        expect(validated.strokes.reduce((count, item) => count + item.points.length, 0)).toBe(recipe.point_count);
        expect(JSON.parse(JSON.stringify(validated)).strokes[0].points[0]).toEqual({ x: 1, y: 1 });
        expect(validated.strokes[0]!.points[0]!.x).toBeTypeOf("number");
      }
    }
  });
  it("captures exact visible whole-object identities without cutting crossing ink", () => {
    const source = scene(), narrow = { x: 70, y: 0, width: 1, height: 20 };
    const selected = selectInBounds(source, narrow);
    expect(selected).toContain(id(1)); expect(selected).not.toContain(id(2));
    expect(source.strokes[0]!.points).toHaveLength(5);
    expect(objectBounds(source, id(2))).toBeNull(); expect(objectBounds(source, id(99))).toBeNull();
    expect(objectBounds(source, id(5))).toEqual({ x: 20, y: 20, width: 540, height: 80 });
    expect(boundsOfSelection(source, [id(1), id(3)])).toEqual({ x: 8.5, y: 8.5, width: 171.5, height: 91.5 });
    expect(boundsOfSelection(source, [])).toBeNull();
    expect(packet().scene.strokes[0]!.points).toEqual(source.strokes[0]!.points);
    for (const ids of [[], [id(1), id(1)], [id(2)], [id(99)]]) expect(() => packet(source, ids)).toThrow();
    expect(() => validatePacket({ ...packet(), selection: { ...packet().selection, revision: 2 } })).toThrow(/revision/);
  });
  it("includes the full pen width when selecting horizontal, vertical and single-point ink", () => {
    const source = { ...scene(), nodes: [], edges: [], strokes: [
      { ...stroke(1), width: 16, points: [{ x: -20, y: 0 }, { x: 20, y: 0 }] },
      { ...stroke(2), width: 16, points: [{ x: 100, y: -20 }, { x: 100, y: 20 }] },
      { ...stroke(3), width: 16, points: [{ x: 200, y: 11 }] }
    ] };
    expect(objectBounds(source, id(1))).toEqual({ x: -28, y: -8, width: 56, height: 16 });
    expect(objectBounds(source, id(2))).toEqual({ x: 92, y: -28, width: 16, height: 56 });
    expect(objectBounds(source, id(3))).toEqual({ x: 192, y: 3, width: 16, height: 16 });
    expect(selectInBounds(source, { x: -1, y: -6, width: 2, height: 1 })).toEqual([id(1)]);
    expect(selectInBounds(source, { x: 94, y: -1, width: 1, height: 2 })).toEqual([id(2)]);
    expect(selectInBounds(source, { x: 194, y: 5, width: 1, height: 1 })).toEqual([id(3)]);
    expect(selectInBounds(source, { x: -1, y: -10, width: 2, height: 1 })).toEqual([]);
    expect(boundsOfSelection(source, [id(3)])).toEqual({ x: 192, y: 3, width: 16, height: 16 });
  });
  it("captures pen extents beyond world coordinates without widening point or node coordinates", () => {
    const source = validateScene({ ...scene(), nodes: [], edges: [], strokes: [
      { ...stroke(1), width: 16, points: [{ x: -100000, y: -100000 }] },
      { ...stroke(2), width: 16, points: [{ x: 100000, y: 100000 }] }
    ] });
    expect(objectBounds(source, id(1))).toEqual({ x: -100008, y: -100008, width: 16, height: 16 });
    expect(objectBounds(source, id(2))).toEqual({ x: 99992, y: 99992, width: 16, height: 16 });
    const bounds = boundsOfSelection(source, [id(1), id(2)])!;
    expect(bounds).toEqual({ x: -100008, y: -100008, width: 200016, height: 200016 });
    expect(makePacket(source, [id(1), id(2)], bounds, "Capture visible pen extents").selection.bounds).toEqual(bounds);
    const singleBounds = objectBounds(source, id(1))!;
    expect(makePacket(source, [id(1)], singleBounds, "Capture one visible dot", { png_data_url: png(), width: 1, height: 1, bounds: singleBounds }).crop?.bounds).toEqual(singleBounds);
    expect(selectInBounds(source, { x: -100007, y: -100007, width: 1, height: 1 })).toEqual([id(1)]);
    expect(selectInBounds(source, { x: 100006, y: 100006, width: 1, height: 1 })).toEqual([id(2)]);
    expect(() => selectInBounds(source, { x: 102001, y: 0, width: 1, height: 1 })).toThrow();
    expect(() => validateScene({ ...source, strokes: [{ ...stroke(1), points: [{ x: 100001, y: 0 }] }] })).toThrow();
    expect(() => validateScene({ ...source, nodes: [node(3, 100001)] })).toThrow();
  });
  it("selects and captures the self-loop control box above and beside its node", () => {
    const source = { ...scene(), strokes: [], nodes: [node(3, 100, 100)], edges: [{ ...scene().edges[0]!, source: id(3), target: id(3) }] };
    const bounds = { x: 65, y: 20, width: 230, height: 160 };
    expect(objectBounds(source, id(5))).toEqual(bounds);
    expect(boundsOfSelection(source, [id(5)])).toEqual(bounds);
    expect(selectInBounds(source, { x: 175, y: 45, width: 10, height: 5 })).toEqual([id(5)]);
    expect(selectInBounds(source, { x: 70, y: 100, width: 5, height: 5 })).toEqual([id(5)]);
    expect(makePacket(source, [id(5)], bounds, "Capture complete self-loop", { png_data_url: png(), width: 1, height: 1, bounds }).crop?.bounds).toEqual(bounds);
    const shared = parity.self_loop_case, boundary = validateScene(shared.scene);
    expect(objectBounds(boundary, shared.edge_id)).toEqual(shared.expected_bounds);
    expect(makePacket(boundary, [shared.edge_id], shared.expected_bounds, "Capture boundary loop").selection.bounds).toEqual(shared.expected_bounds);
    expect(selectInBounds(boundary, { x: 100070, y: -100060, width: 20, height: 5 })).toEqual([shared.edge_id]);
  });
  it("validates PNG envelopes, dimensions, checksums, crop binding and untrusted sources", () => {
    const data = png();
    expect(pngArtwork(data, "One local pixel").png_data_url).toBe(data);
    for (const invalid of ["https://example.org/image.png", "data:image/svg+xml;base64,PHN2Zy8+", data + " ", "data:image/png;base64,AAAA", png(1025), png(1, 1, 524288)]) expect(() => pngArtwork(invalid, "local")).toThrow();
    const damaged = Buffer.from(data.split(",")[1]!, "base64"); damaged[damaged.length - 1]! ^= 1;
    expect(() => pngArtwork(`data:image/png;base64,${damaged.toString("base64")}`, "damaged")).toThrow(/checksum/);
    expect(() => makePacket(scene(), [id(1)], region, "Inspect", { png_data_url: data, width: 2, height: 1, bounds: region })).toThrow(/dimensions/);
    expect(() => makePacket(scene(), [id(1)], region, "Inspect", { png_data_url: data, width: 1, height: 1, bounds: { ...region, x: 1 } })).toThrow(/bounds/);
    expect(makePacket(scene(), [id(1)], region, "Inspect", { png_data_url: data, width: 1, height: 1, bounds: region }).crop?.width).toBe(1);
  });
  it("rejects animated PNG, invalid palettes, unknown critical chunks and discontinuous or empty image data", () => {
    const extra = (name: string, length = 0) => png(1, 1, 0, (chunks) => [chunks[0]!, { name, body: Buffer.alloc(length) }, ...chunks.slice(1)]);
    for (const invalid of [extra("acTL", 8), extra("fcTL", 26), extra("fdAT", 4), extra("ABCD"), extra("PLTE", 2),
      png(1, 1, 0, (chunks) => [chunks[0]!, { name: "IDAT", body: Buffer.alloc(0) }, chunks[2]!]),
      png(1, 1, 0, (chunks) => [chunks[0]!, chunks[1]!, { name: "tEXt", body: Buffer.from("a\0b") }, chunks[1]!, chunks[2]!]),
      png(1, 1, 0, (chunks) => [chunks[0]!, chunks[1]!, { name: "PLTE", body: Buffer.alloc(3) }, chunks[2]!])
    ]) expect(() => pngArtwork(invalid, "Untrusted image")).toThrow();
    const contiguous = png(1, 1, 0, (chunks) => [chunks[0]!, { name: "IDAT", body: chunks[1]!.body.subarray(0, 2) }, { name: "IDAT", body: chunks[1]!.body.subarray(2) }, chunks[2]!]);
    expect(pngArtwork(contiguous, "Two contiguous data chunks").png_data_url).toBe(contiguous);
    const data = png();
    const encoded = data.slice(data.indexOf(",") + 1), padding = encoded.endsWith("==") ? 2 : encoded.endsWith("=") ? 1 : 0;
    if (padding) {
      const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", position = encoded.length - padding - 1;
      const noncanonical = encoded.slice(0, position) + alphabet[alphabet.indexOf(encoded[position]!) | 1] + encoded.slice(position + 1);
      expect(atob(noncanonical)).toBe(atob(encoded));
      expect(() => pngArtwork(`data:image/png;base64,${noncanonical}`, "Invalid pad bits")).toThrow(/canonical/);
    }
  });
});

describe("atomic proposal review", () => {
  it("rejects stale, foreign or different selections, including duplicate scope IDs", () => {
    const captured = packet(), candidate = proposal(captured);
    for (const invalid of [
      { ...candidate, base_revision: 2 }, { ...candidate, scene_id: id(999) },
      { ...candidate, selection_ids: [id(1)] }, { ...candidate, selection_ids: [id(1), id(1)] },
      { ...candidate, unexpected: true }
    ]) expect(() => validateProposal(invalid, captured)).toThrow();
    expect(() => applyProposal({ ...captured.scene, revision: 2 }, candidate, captured)).toThrow(/changed/);
    expect(() => applyProposal(renameNode(captured.scene, id(4), "Uncommitted edit"), candidate, captured)).toThrow(/changed/);
  });
  it("rejects outside-selection writes, category reuse, invented sources and duplicate upserts", () => {
    const captured = packet(), candidate = proposal(captured);
    for (const invalid of [
      { ...candidate, nodes: [{ ...node(4), label: "Illegal outside edit" }] },
      { ...candidate, edges: [{ ...scene().edges[0]!, label: "Illegal outside edge edit" }] },
      { ...candidate, archive_stroke_ids: [id(2)] },
      { ...candidate, nodes: [node(1)] },
      { ...candidate, nodes: [node(5)] },
      { ...candidate, nodes: [node(9), node(9)] },
      { ...candidate, nodes: [{ ...node(9), source_stroke_ids: [id(999)] }] },
      { ...candidate, nodes: [{ ...node(9), source_stroke_ids: [id(2)] }] },
      { ...candidate, edges: [{ id: id(9), source: id(3), target: id(999), label: "Missing", source_stroke_ids: [] }] }
    ]) expect(() => validateProposal(invalid, captured)).toThrow();
  });
  it("applies all operations once to independent data and preserves external edges and source ink", () => {
    const captured = freeze(packet()), candidate = freeze(proposal(captured));
    const before = JSON.stringify(captured), result = applyProposal(captured.scene, candidate, captured);
    expect(result.nodes.find((n) => n.id === id(3))?.label).toBe("Reviewed label");
    expect(result.revision).toBe(captured.scene.revision + 1);
    expect(result.nodes.find((n) => n.id === id(4))).toEqual(captured.scene.nodes[1]);
    expect(result.edges).toEqual(captured.scene.edges);
    expect(result.strokes[0]!.archived).toBe(true);
    expect(result.strokes[0]!.points).toEqual(captured.scene.strokes[0]!.points);
    expect(JSON.stringify(captured)).toBe(before);
    result.strokes[0]!.points[0]!.x = 123;
    expect(captured.scene.strokes[0]!.points[0]!.x).toBe(10);
    const invalid = { ...candidate, nodes: [...candidate.nodes, node(4)] };
    expect(() => applyProposal(captured.scene, invalid, captured)).toThrow();
    expect(JSON.stringify(captured)).toBe(before);
  });
  it("allows an explicit new edge to a read-only external endpoint without changing it", () => {
    const captured = packet(), candidate = proposal(captured);
    candidate.nodes.push(node(9, 240, 160));
    candidate.edges.push({ id: id(10), source: id(9), target: id(4), label: "Explicit new connection", source_stroke_ids: [] });
    const result = applyProposal(captured.scene, candidate, captured);
    expect(result.edges).toHaveLength(2);
    expect(result.nodes.find((n) => n.id === id(4))).toEqual(captured.scene.nodes[1]);
  });
  it("retains existing archived source references but refuses new unselected provenance", () => {
    const source = scene(); source.nodes[0]!.source_stroke_ids = [id(2)];
    const captured = packet(source), candidate = proposal(captured);
    candidate.nodes[0]!.source_stroke_ids = [id(1), id(2)];
    expect(validateProposal(candidate, captured).nodes[0]!.source_stroke_ids).toEqual([id(1), id(2)]);
    const unselected = { ...source, strokes: [...source.strokes, stroke(9)] };
    expect(() => validateProposal({ ...candidate, nodes: [{ ...candidate.nodes[0]!, source_stroke_ids: [id(9)] }] }, packet(unselected))).toThrow(/selected visible/);
  });
});

describe("reversible local editing", () => {
  it("restores exact source ink and identities with fresh revisions through undo and redo", () => {
    const original = { format: "lychd.canvas.document/1" as const, scene: scene(), past: [], future: [] };
    const captured = packet(original.scene), applied = commit(original, applyProposal(original.scene, proposal(captured), captured));
    const restored = undo(applied), repeated = redo(restored);
    expect([original.scene.revision, applied.scene.revision, restored.scene.revision, repeated.scene.revision]).toEqual([1, 2, 3, 4]);
    expect(restored.scene.strokes).toEqual(original.scene.strokes);
    expect(repeated.scene.nodes.map((n) => n.id)).toEqual(applied.scene.nodes.map((n) => n.id));
    expect(repeated.scene.strokes[0]!.archived).toBe(true);
    expect(() => applyProposal(restored.scene, proposal(captured), captured)).toThrow(/changed/);
    expect(original.past).toEqual([]); expect(applied.scene.strokes[0]!.points).toEqual(original.scene.strokes[0]!.points);
  });
  it("bounds history, clears redo on a new edit and never reuses an imported revision", () => {
    let document = blankDocument();
    for (let index = 0; index < 25; index++) document = commit(document, { ...document.scene, title: `Edit ${index}` });
    expect(document.past).toHaveLength(20); expect(document.scene.revision).toBe(26);
    const undone = undo(document), forked = commit(undone, { ...undone.scene, title: "Different edit" });
    expect(forked.future).toEqual([]); expect(forked.scene.revision).toBe(28);
    const imported = { ...blankDocument(), past: [{ ...blankDocument().scene, revision: 90 }] };
    imported.past[0]!.id = imported.scene.id;
    expect(undo(imported).scene.revision).toBe(91);
    expect(() => commit(document, scene())).toThrow(/identity/);
  });
  it("moves selected world ink and nodes without moving other ink or disconnecting incident edges", () => {
    const source = freeze(scene()), moved = moveSelection(source, [id(1), id(3)], 20, -5);
    expect(moved.nodes[0]!.x).toBe(40); expect(moved.strokes[0]!.points[0]).toEqual({ x: 30, y: 5 });
    expect(moved.strokes[1]).toEqual(source.strokes[1]); expect(moved.nodes[1]).toEqual(source.nodes[1]); expect(moved.edges).toEqual(source.edges);
    expect(() => moveSelection(source, [id(3)], Infinity, 0)).toThrow();
    expect(() => moveSelection(source, [id(3)], 1000000, 0)).toThrow();
  });
  it("explicit deletion removes incident links and safely prunes deleted source references", () => {
    const source = scene(); source.nodes[0]!.source_stroke_ids = [id(1)]; source.edges[0]!.source_stroke_ids = [id(1)];
    const noInk = deleteSelection(source, [id(1)]);
    expect(noInk.nodes[0]!.source_stroke_ids).toEqual([]); expect(noInk.edges[0]!.source_stroke_ids).toEqual([]);
    const noNode = deleteSelection(source, [id(3)]);
    expect(noNode.nodes.map((n) => n.id)).toEqual([id(4)]); expect(noNode.edges).toEqual([]);
    expect(source.edges).toHaveLength(1);
    expect(renameNode(source, id(3), "DB").nodes[0]!.label).toBe("DB");
    expect(() => renameNode(source, id(999), "Missing")).toThrow();
  });
});

describe("truthful geometry helpers", () => {
  it("regularizes real box strokes, retains ambiguous arrows and ignores instruction semantics", () => {
    const document = exampleDocument(), source = document.scene;
    const captured = makePacket(source, source.strokes.map((s) => s.id), { x: 70, y: 80, width: 550, height: 180 }, "Turn this into a dancing GPU database");
    const result = tidyProposal(captured);
    expect(result.author).toContain("no model"); expect(result.nodes).toHaveLength(2);
    expect(result.nodes.map((n) => n.label)).toEqual(["Box 1", "Box 2"]); expect(result.edges).toEqual([]);
    expect(result.archive_stroke_ids).toEqual(source.strokes.slice(0, 2).map((s) => s.id));
    const applied = applyProposal(source, result, captured);
    expect(applied.strokes[2]!.archived).toBe(false); expect(source.strokes.every((s) => !s.archived)).toBe(true);
  });
  it("groups a box drawn as separate sides and refuses circles and open scribbles", () => {
    const sides = [
      [{ x: 0, y: 0 }, { x: 120, y: 0 }], [{ x: 120, y: 0 }, { x: 120, y: 80 }],
      [{ x: 120, y: 80 }, { x: 0, y: 80 }], [{ x: 0, y: 80 }, { x: 0, y: 0 }]
    ].map((points, i) => ({ ...stroke(10 + i), points }));
    const circle = { ...stroke(20), points: Array.from({ length: 33 }, (_, i) => ({ x: 300 + 60 * Math.cos(i * Math.PI / 16), y: 200 + 60 * Math.sin(i * Math.PI / 16) })) };
    const source = { ...scene(), strokes: [...sides, circle], nodes: [], edges: [] };
    const result = tidyProposal(packet(source, source.strokes.map((s) => s.id)));
    expect(result.nodes).toHaveLength(1); expect(result.nodes[0]!.source_stroke_ids).toEqual(sides.map((s) => s.id));
    expect(result.archive_stroke_ids).not.toContain(circle.id); expect(result.edges).toEqual([]);
  });
  it("does not turn a sparse self-crossing bow tie into a box", () => {
    const source = { ...scene(), strokes: [{ ...stroke(1), points: [{ x: 0, y: 0 }, { x: 120, y: 80 }, { x: 120, y: 0 }, { x: 0, y: 80 }, { x: 0, y: 0 }] }], nodes: [], edges: [] };
    const result = tidyProposal(packet(source, [id(1)]));
    expect(result.nodes).toEqual([]); expect(result.archive_stroke_ids).toEqual([]); expect(result.edges).toEqual([]);
  });
  it("uses full rectangles while preserving pins, outside nodes, raw ink, labels and images", () => {
    const source = scene();
    source.nodes = [{ ...node(3, 0, 0), width: 480, height: 200, pinned: true }, { ...node(4, 20, 20), width: 320, height: 150, artwork: pngArtwork(png(), "Symbol") }, node(6, 900, 300)];
    const before = JSON.stringify(source), result = arrangeScene(freeze(source), [id(4)]);
    expect(result.nodes[0]).toEqual(source.nodes[0]); expect(result.nodes[2]).toEqual(source.nodes[2]); expect(result.strokes).toEqual(source.strokes); expect(result.edges).toEqual(source.edges);
    const a = result.nodes[0]!, b = result.nodes[1]!;
    expect(a.x + a.width <= b.x || b.x + b.width <= a.x || a.y + a.height <= b.y || b.y + b.height <= a.y).toBe(true);
    expect(b.artwork).toEqual(source.nodes[1]!.artwork); expect(b.label).toBe(source.nodes[1]!.label); expect(JSON.stringify(source)).toBe(before);
    expect(arrangeScene(source, []).nodes).toEqual(source.nodes);
  });
  it("separates coincident movable rectangles deterministically with bounded finite coordinates", () => {
    const source = { ...scene(), nodes: [node(3, 0, 0), node(4, 0, 0)], edges: [] };
    const result = arrangeScene(source);
    expect(result).toEqual(arrangeScene(source));
    const [a, b] = result.nodes;
    expect(a!.y + a!.height <= b!.y || b!.y + b!.height <= a!.y || a!.x + a!.width <= b!.x || b!.x + b!.width <= a!.x).toBe(true);
    expect(result.nodes.every((n) => Number.isFinite(n.x) && Number.isFinite(n.y))).toBe(true);
    const connected = arrangeScene({ ...source, edges: scene().edges });
    expect(connected.nodes.every((n) => Number.isFinite(n.x) && Number.isFinite(n.y))).toBe(true);
  });
});
