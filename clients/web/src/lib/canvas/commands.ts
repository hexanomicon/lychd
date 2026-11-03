import { arrangeScene, moveSelection, objectBounds, renameNode, validateScene } from "./engine";
import type { Bounds, CanvasNode, Point, Scene } from "./types";

export const CANVAS_COMMAND_LIMITS = Object.freeze({ text: 4000, commands: 16, movement: 10000, placementAttempts: 4096 });
export const CANVAS_COMMAND_HELP = [
  "English Canvas commands; separate commands with then, semicolons or newlines. Preview, then Apply.",
  "add node Vessel then add database Postgres then connect Vessel to Postgres",
  'add service "API gateway" (also: node, database, person, note)',
  "rename selected to LABEL; connect selected to LABEL (select exactly one node)",
  "move selected by 40, -20; move selected right 80 (also: left, up, down); arrange selected",
  'Simple multiword labels work: add service API gateway. Quote ambiguous names containing then, to, and or command verbs.',
  "A period before a command verb also separates commands. Select native nodes for edits.",
  "Names match exactly after Unicode, spacing and case normalization; duplicate names are refused. No ink interpretation or arbitrary-language commands.",
].join("\n");

export class CanvasCommandError extends Error {
  constructor(message: string) { super(message); this.name = "CanvasCommandError"; }
}

export type CanvasCommandOptions = { origin?: Point; makeId?: () => string };
export type CanvasCommandPlan = {
  scene: Scene;
  summary: string;
  baseSceneId: string;
  baseRevision: number;
  selectionIds: string[];
  /** Exact canonical JSON strings, not lossy hashes or security credentials. */
  selectionFingerprint: string;
  baseSceneFingerprint: string;
  commandCount: number;
  createdIds: string[];
  updatedIds: string[];
};

type Token = { value: string; quoted: boolean };
type Command =
  | { kind: "add"; nodeKind: CanvasNode["kind"]; label: string }
  | { kind: "connect"; source: string | null; target: string }
  | { kind: "rename"; label: string }
  | { kind: "move"; dx: number; dy: number }
  | { kind: "arrange" };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const WORLD = 100000;
const GAP = 32;
const WIDTH = 192;
const HEIGHT = 96;
function fail(message: string): never { throw new CanvasCommandError(message); }
const normalized = (value: string): string => value.normalize("NFC").trim().replace(/\s+/gu, " ").toLowerCase();

/** Only advertised delimiters are recognized; quotes protect literal label text. */
function tokenize(text: string): Token[][] {
  if (typeof text !== "string" || text.length > CANVAS_COMMAND_LIMITS.text) fail("Use at most 4000 characters of Canvas commands.");
  const batches: Token[][] = [];
  const sentenceEnd = (offset: number) => /^\.(?:\s*$|\s+(?:add|connect|rename|move|arrange)\b)/i.test(text.slice(offset));
  let tokens: Token[] = [];
  const finish = () => {
    if (tokens.length) { batches.push(tokens); tokens = []; }
    if (batches.length > CANVAS_COMMAND_LIMITS.commands) fail("Use at most 16 Canvas commands per preview.");
  };
  for (let i = 0; i < text.length;) {
    const c = text[i]!;
    const spokenSeparator = /^then\s+(?=(?:add|connect|rename|move|arrange)\b)/i.exec(text.slice(i));
    if (spokenSeparator) { finish(); i += spokenSeparator[0].length; continue; }
    if (c === "." && sentenceEnd(i)) { finish(); i++; continue; }
    if (c === ";" || c === "\n") { finish(); i++; continue; }
    if (/\s/u.test(c)) { i++; continue; }
    if (c === ",") { tokens.push({ value: ",", quoted: false }); i++; continue; }
    if (c === '"') {
      const start = i++;
      let closed = false;
      while (i < text.length) {
        if (text[i] === "\\") { i += 2; continue; }
        if (text[i++] === '"') { closed = true; break; }
      }
      if (!closed) fail("Close the double-quoted label.");
      let value: string;
      try { value = JSON.parse(text.slice(start, i)) as string; }
      catch { return fail("Use a valid double-quoted label; escape embedded quotes as \\\"."); }
      if (i < text.length && !/[\s;,]/u.test(text[i]!) && !sentenceEnd(i)) fail("Separate the quoted label from the next word.");
      tokens.push({ value, quoted: true });
    } else {
      const start = i;
      while (i < text.length && !/[\s;,]/u.test(text[i]!)) {
        if (text[i] === "." && sentenceEnd(i)) break;
        if (text[i] === '"') fail("Put double quotes around the entire label.");
        i++;
      }
      tokens.push({ value: text.slice(start, i), quoted: false });
    }
  }
  finish();
  if (!batches.length) fail("Enter a Canvas command. Open command help for the supported English grammar.");
  return batches;
}

function label(token: Token | undefined): string {
  if (!token || !normalized(token.value) || [...token.value].length > 240 || /[\p{Cc}\p{Cs}]/u.test(token.value)) fail("Use a nonempty label of at most 240 valid characters without control characters.");
  return token.value;
}
function phrase(tokens: Token[]): string {
  if (tokens.length === 1 && tokens[0]!.quoted) return label(tokens[0]);
  if (!tokens.length || tokens.some((token) => token.quoted || /^(?:then|and|to|add|connect|rename|move|arrange|,)$/i.test(token.value))) fail("Ambiguous label. Put the complete label in double quotes; use then between commands.");
  return label({ value: tokens.map((token) => token.value).join(" "), quoted: false });
}
function amount(token: Token | undefined): number {
  if (!token || token.quoted || !/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(token.value)) fail("Movement needs decimal numbers, for example: move selected by 40, -20.");
  const result = Number(token.value);
  if (!Number.isFinite(result) || Math.abs(result) > CANVAS_COMMAND_LIMITS.movement) fail("Movement must be finite and at most 10000 units per axis.");
  return result;
}
function parse(tokens: Token[]): Command {
  const word = (index: number) => tokens[index]?.quoted ? "" : tokens[index]?.value.toLowerCase();
  const kinds: Record<string, CanvasNode["kind"]> = { node: "box", database: "database", service: "service", person: "person", note: "note" };
  if (word(0) === "add" && tokens.length >= 3 && Object.hasOwn(kinds, word(1) ?? "")) return { kind: "add", nodeKind: kinds[word(1)!]!, label: phrase(tokens.slice(2)) };
  if (word(0) === "connect") {
    const separators = tokens.map((_token, index) => word(index) === "to" ? index : -1).filter((index) => index >= 0);
    if (separators.length !== 1) fail("Connect needs exactly one unquoted to between two node names. Quote names containing to.");
    const divider = separators[0]!;
    const source = tokens.slice(1, divider), target = tokens.slice(divider + 1);
    return { kind: "connect", source: source.length === 1 && word(1) === "selected" ? null : phrase(source), target: phrase(target) };
  }
  if (word(0) === "rename" && word(1) === "selected" && word(2) === "to" && tokens.length >= 4) return { kind: "rename", label: phrase(tokens.slice(3)) };
  if (word(0) === "arrange" && word(1) === "selected" && tokens.length === 2) return { kind: "arrange" };
  if (word(0) === "move" && word(1) === "selected") {
    if (word(2) === "by" && tokens.length === 6 && word(4) === ",") return { kind: "move", dx: amount(tokens[3]), dy: amount(tokens[5]) };
    if (tokens.length === 4 && ["left", "right", "up", "down"].includes(word(2) ?? "")) {
      const distance = amount(tokens[3]);
      if (distance <= 0) fail("Directional movement needs a positive number of units.");
      return { kind: "move", dx: word(2) === "left" ? -distance : word(2) === "right" ? distance : 0, dy: word(2) === "up" ? -distance : word(2) === "down" ? distance : 0 };
    }
  }
  return fail("Unsupported Canvas command. Use command help; quote ambiguous labels. No changes were made.");
}

function selection(scene: Scene, ids: readonly string[]): string[] {
  if (!Array.isArray(ids) || ids.length > 128 || new Set(ids).size !== ids.length) fail("Select at most 128 unique visible objects.");
  const visible = new Set([...scene.nodes, ...scene.edges, ...scene.strokes.filter((stroke) => !stroke.archived)].map((object) => object.id));
  if (ids.some((id) => !visible.has(id))) fail("The selection contains a missing or archived object. Select again.");
  return [...ids].sort();
}
function selectedNodes(scene: Scene, ids: readonly string[], exactlyOne = false): CanvasNode[] {
  const nodes = ids.map((id) => scene.nodes.find((node) => node.id === id));
  if (!nodes.length || nodes.some((node) => !node) || (exactlyOne && nodes.length !== 1)) fail(exactlyOne ? "Select exactly one native node for this command." : "Select one or more native nodes only; ink and edges are not editable by this command.");
  return nodes as CanvasNode[];
}
function uniqueNode(scene: Scene, name: string): CanvasNode {
  const matches = scene.nodes.filter((node) => normalized(node.label) === normalized(name));
  if (matches.length !== 1) fail(matches.length ? `Ambiguous node name “${name}”. Rename duplicate nodes first.` : `No node named “${name}”. Add it explicitly or correct the name.`);
  return matches[0]!;
}
function requireAvailableName(scene: Scene, name: string, except?: string): void {
  if (scene.nodes.some((node) => node.id !== except && normalized(node.label) === normalized(name))) fail(`A node named “${name}” already exists. Use a unique name.`);
}
function overlaps(left: Bounds, right: Bounds): boolean {
  return left.x < right.x + right.width + GAP && left.x + left.width + GAP > right.x && left.y < right.y + right.height + GAP && left.y + left.height + GAP > right.y;
}
function placement(scene: Scene, origin: Point): Point {
  const obstacles = [...scene.nodes, ...scene.edges, ...scene.strokes.filter((stroke) => !stroke.archived)].map((object) => objectBounds(scene, object.id)!);
  // Finite square spiral around the supplied viewport/world origin, in stable order.
  let x = 0, y = 0, dx = 0, dy = -1;
  for (let attempt = 0; attempt < CANVAS_COMMAND_LIMITS.placementAttempts; attempt++) {
    const point = { x: origin.x + x * (WIDTH + GAP), y: origin.y + y * (HEIGHT + GAP) };
    const candidate = { ...point, width: WIDTH, height: HEIGHT };
    if (point.x >= -WORLD && point.y >= -WORLD && point.x + WIDTH <= WORLD && point.y + HEIGHT <= WORLD && !obstacles.some((box) => overlaps(candidate, box))) return point;
    if (x === y || (x < 0 && x === -y) || (x > 0 && x === 1 - y)) { const oldDx = dx; dx = -dy; dy = oldDx; }
    x += dx; y += dy;
  }
  return fail("No clear placement found within the bounded search. Move the view origin or clear space and try again.");
}

/** Inert local plan only. The owner must recheck scene/selection and explicitly commit once. */
export function planCanvasCommand(input: Scene, selectedIds: readonly string[], text: string, options: CanvasCommandOptions = {}): CanvasCommandPlan {
  const base = validateScene(input);
  const selectionIds = selection(base, selectedIds);
  const commands = tokenize(text).map(parse);
  const origin = options.origin ?? { x: 80, y: 80 };
  if (!Number.isFinite(origin.x) || !Number.isFinite(origin.y) || Math.abs(origin.x) > WORLD || Math.abs(origin.y) > WORLD) fail("Placement origin must be finite and within the Canvas world.");
  if (base.revision >= Number.MAX_SAFE_INTEGER) fail("Scene revision limit reached.");
  const used = new Set([base.id, ...base.nodes.map((node) => node.id), ...base.edges.map((edge) => edge.id), ...base.strokes.map((stroke) => stroke.id)]);
  let serial = 1;
  const nextId = () => {
    let id: string;
    if (options.makeId) id = options.makeId();
    else {
      // Scene-local deterministic identities; no clock, random source or external call.
      do {
        const hex = `c4a00000${base.revision.toString(16).padStart(14, "0")}${(serial++).toString(16).padStart(10, "0")}`;
        id = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
      } while (used.has(id));
    }
    if (typeof id !== "string" || !UUID.test(id) || used.has(id)) fail("The ID factory must return a fresh canonical lowercase UUID.");
    used.add(id); return id;
  };
  let scene = base;
  const createdIds: string[] = [];
  const edited = new Set<string>();
  for (const command of commands) {
    if (command.kind === "add") {
      if (scene.nodes.length >= 128) fail("Canvas supports at most 128 nodes.");
      requireAvailableName(scene, command.label);
      const point = placement(scene, origin), id = nextId();
      scene = { ...scene, nodes: [...scene.nodes, { id, ...point, width: WIDTH, height: HEIGHT, label: command.label, kind: command.nodeKind, pinned: false, source_stroke_ids: [], artwork: null }] };
      createdIds.push(id);
    } else if (command.kind === "connect") {
      if (scene.edges.length >= 256) fail("Canvas supports at most 256 connections.");
      const source = command.source === null ? selectedNodes(scene, selectionIds, true)[0]! : uniqueNode(scene, command.source);
      const target = uniqueNode(scene, command.target);
      if (source.id === target.id) fail("This command profile does not create self-connections.");
      if (scene.edges.some((edge) => edge.source === source.id && edge.target === target.id)) fail("That directed connection already exists.");
      const id = nextId();
      scene = { ...scene, edges: [...scene.edges, { id, source: source.id, target: target.id, label: "", source_stroke_ids: [] }] };
      createdIds.push(id);
    } else if (command.kind === "rename") {
      const node = selectedNodes(scene, selectionIds, true)[0]!;
      requireAvailableName(scene, command.label, node.id);
      scene = renameNode(scene, node.id, command.label); edited.add(node.id);
    } else {
      const nodes = selectedNodes(scene, selectionIds);
      if (command.kind === "move") {
        if (nodes.some((node) => node.pinned)) fail("Unpin selected nodes before moving them.");
        scene = moveSelection(scene, selectionIds, command.dx, command.dy);
      } else scene = arrangeScene(scene, selectionIds);
      nodes.forEach((node) => edited.add(node.id));
    }
  }
  const baseSceneFingerprint = JSON.stringify(base);
  if (JSON.stringify(scene) === baseSceneFingerprint) fail("The commands would make no change. Adjust the command or selection.");
  const updatedIds = base.nodes.filter((node) => edited.has(node.id) && JSON.stringify(node) !== JSON.stringify(scene.nodes.find((candidate) => candidate.id === node.id))).map((node) => node.id);
  const result = validateScene({ ...scene, revision: base.revision + 1 });
  const newNodes = result.nodes.length - base.nodes.length, newEdges = result.edges.length - base.edges.length;
  return { scene: result, summary: `Local English commands: ${newNodes} node(s) added, ${newEdges} connection(s) added, ${updatedIds.length} selected node(s) changed. Review before applying; original ink is retained.`, baseSceneId: base.id, baseRevision: base.revision, selectionIds, selectionFingerprint: JSON.stringify(selectionIds), baseSceneFingerprint, commandCount: commands.length, createdIds, updatedIds };
}

/** Exact stale check, including same-revision edits and selection changes. No application effect. */
export function isCanvasCommandCurrent(plan: CanvasCommandPlan, input: Scene, selectedIds: readonly string[]): boolean {
  try {
    const scene = validateScene(input);
    return scene.id === plan.baseSceneId && scene.revision === plan.baseRevision && JSON.stringify(selection(scene, selectedIds)) === plan.selectionFingerprint && JSON.stringify(scene) === plan.baseSceneFingerprint;
  } catch { return false; }
}
