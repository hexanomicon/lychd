import type { GraphNode, GraphProjection } from "$lib/graph/model";
import type { Point } from "./layout";

export const ORB_NODE_WIDTH = 128;
export const ORB_NODE_HEIGHT = 84;
const MAX_RETAINED_POSITIONS = 4096;
const MAX_RETAINED_ISLANDS = 512;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export interface OrbLayoutMemory {
  readonly positions: Map<string, Point>;
  readonly islands: Map<string, Point>;
  readonly slots: Map<string, number>;
  nextIsland: number;
}

export interface OrbTerritory {
  readonly id: string;
  readonly label: string;
  readonly path: string;
  readonly labelPosition: Point;
  readonly tone: "blue" | "purple";
}

export function createOrbLayoutMemory(): OrbLayoutMemory {
  return { positions: new Map(), islands: new Map(), slots: new Map(), nextIsland: 0 };
}

function hash(value: string): number {
  let result = 2166136261;
  for (const character of value) result = Math.imul(result ^ character.charCodeAt(0), 16777619);
  return result >>> 0;
}

function islandAnchor(group: string, memory: OrbLayoutMemory): Point {
  const retained = memory.islands.get(group);
  if (retained) return retained;
  const slot = memory.nextIsland++;
  // Reserve stable cells before detail is loaded; incoming Runs never repack old islands.
  // The first three use a wide row, then the remaining axial hex neighbors and rings.
  const firstRing: readonly Point[] = [
    { x: 1, y: 0 }, { x: -1, y: 0 }, { x: 1, y: -1 },
    { x: 0, y: -1 }, { x: 0, y: 1 }, { x: -1, y: 1 }
  ];
  let axial: Point = { x: 0, y: 0 };
  if (slot > 0 && slot <= 6) axial = firstRing[slot - 1]!;
  else if (slot > 6) {
    let ring = 2, offset = slot - 7;
    while (offset >= ring * 6) { offset -= ring * 6; ring++; }
    const directions: readonly Point[] = [
      { x: -1, y: 1 }, { x: -1, y: 0 }, { x: 0, y: -1 },
      { x: 1, y: -1 }, { x: 1, y: 0 }, { x: 0, y: 1 }
    ];
    axial = { x: ring, y: 0 };
    for (const direction of directions) {
      const steps = Math.min(ring, offset);
      axial = { x: axial.x + direction.x * steps, y: axial.y + direction.y * steps };
      offset -= steps;
      if (!offset) break;
    }
  }
  const jitter = hash(group) % 41 - 20;
  const anchor = {
    x: 320 + (axial.x + axial.y / 2) * 1000 + (slot ? jitter : 0),
    y: 220 + axial.y * Math.sqrt(3) / 2 * 1000 + (slot ? jitter * 0.7 : 0)
  };
  memory.islands.set(group, anchor);
  return anchor;
}

/** A bounded, static presentation layout. Supplied membership is never inferred from geometry. */
export function layoutOrbProjection(projection: GraphProjection, memory: OrbLayoutMemory): Map<string, Point> {
  const result = new Map<string, Point>();
  const groups = new Map<string, GraphNode[]>();
  for (const node of projection.nodes) {
    const group = node.group ?? projection.identity;
    const members = groups.get(group) ?? [];
    members.push(node);
    groups.set(group, members);
  }
  for (const [group, members] of groups) {
    const anchor = group === "animators" ? { x: -350, y: -420 } : islandAnchor(group, memory);
    const occupied = members.flatMap(node => memory.positions.has(node.id) ? [memory.positions.get(node.id)!] : []);
    // Stable semantic sorting only assigns slots to new identities. Existing identities never move.
    for (const node of members.toSorted((a, b) => Number(b.kind === "run") - Number(a.kind === "run") || a.id.localeCompare(b.id))) {
      let point = memory.positions.get(node.id);
      if (!point) {
        const slot = memory.slots.get(group) ?? 0;
        memory.slots.set(group, slot + 1);
        if (group === "animators") point = { x: anchor.x, y: anchor.y + slot * 128 };
        else if (node.kind === "run") point = { ...anchor };
        else {
          const knownMembers = (node.members ?? []).flatMap(id => memory.positions.has(id) ? [memory.positions.get(id)!] : []);
          if (knownMembers.length) point = {
            x: knownMembers.reduce((sum, item) => sum + item.x, 0) / knownMembers.length,
            y: knownMembers.reduce((sum, item) => sum + item.y, 0) / knownMembers.length
          };
          else {
            const seed = (hash(group) % 628) / 100;
            // Local placement makes at most 80 attempts and never runs a perpetual simulation.
            for (let attempt = 0; attempt < 80; attempt++) {
              const index = slot + attempt;
              const radius = 105 + Math.sqrt(index + 1) * 64;
              const angle = index * GOLDEN_ANGLE + seed;
              point = { x: anchor.x + Math.cos(angle) * radius * 1.12, y: anchor.y + Math.sin(angle) * radius * 0.83 };
              if (occupied.every(other => Math.abs(point!.x - other.x) > 122 || Math.abs(point!.y - other.y) > 94)) break;
            }
          }
        }
        memory.positions.set(node.id, point!);
        occupied.push(point!);
      }
      result.set(node.id, { ...point! });
    }
  }
  // Retain folded and temporarily filtered nodes, while bounding this tab's disposable cache.
  const visible = new Set(projection.nodes.map(node => node.id));
  for (const id of memory.positions.keys()) {
    if (memory.positions.size <= MAX_RETAINED_POSITIONS) break;
    if (!visible.has(id)) memory.positions.delete(id);
  }
  for (const group of memory.islands.keys()) {
    if (memory.islands.size <= MAX_RETAINED_ISLANDS) break;
    if (!groups.has(group)) { memory.islands.delete(group); memory.slots.delete(group); }
  }
  return result;
}

function roundedBoundary(points: readonly Point[]): string {
  const middle = (a: Point, b: Point) => `${(a.x + b.x) / 2} ${(a.y + b.y) / 2}`;
  return `M ${middle(points.at(-1)!, points[0]!)} ` + points.map((point, index) =>
    `Q ${point.x} ${point.y} ${middle(point, points[(index + 1) % points.length]!)}`).join(" ") + " Z";
}

/** Decorative envelopes follow explicit Run groups; they supply no extra graph relation. */
export function orbTerritories(projection: GraphProjection, positions: ReadonlyMap<string, Point>): OrbTerritory[] {
  const result: OrbTerritory[] = [];
  for (const run of projection.nodes.filter(node => node.kind === "run" && node.group)) {
    const members = projection.nodes.filter(node => node.group === run.group);
    if (members.length < 2) continue;
    const points = members.flatMap(node => positions.has(node.id) ? [{
      x: positions.get(node.id)!.x + ORB_NODE_WIDTH / 2,
      y: positions.get(node.id)!.y + 25
    }] : []);
    if (!points.length) continue;
    const left = Math.min(...points.map(point => point.x));
    const right = Math.max(...points.map(point => point.x));
    const top = Math.min(...points.map(point => point.y));
    const bottom = Math.max(...points.map(point => point.y));
    const center = { x: (left + right) / 2, y: (top + bottom) / 2 };
    const phase = hash(run.id) / 0xffffffff * Math.PI * 2;
    const outline = Array.from({ length: 24 }, (_, index) => {
      const angle = index / 24 * Math.PI * 2;
      const c = Math.cos(angle), s = Math.sin(angle);
      const support = Math.max(...points.map(point => (point.x - center.x) * c + (point.y - center.y) * s));
      const radius = Math.max(85, support + 95 + Math.sin(angle * 3 + phase) * 16);
      return { x: center.x + c * radius, y: center.y + s * radius };
    });
    result.push({ id: run.id, label: run.label, path: roundedBoundary(outline),
      labelPosition: { x: left - 8, y: top - 104 }, tone: hash(run.id) % 2 ? "purple" : "blue" });
  }
  return result;
}
