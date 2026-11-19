import type { GraphNode, GraphProjection } from "$lib/graph/model";
import type { Point } from "./layout";

export const ORB_NODE_WIDTH = 164;
export const ORB_NODE_HEIGHT = 64;
export const ORB_RUN_WIDTH = 438;
const COLUMN = 178;
const ROW = 80;
const LANE = COLUMN * 3 + 44;
const MAX_RETAINED_POSITIONS = 4096;
const MAX_RETAINED_LANES = 512;

export interface OrbLayoutMemory {
  readonly positions: Map<string, Point>;
  readonly lanes: Map<string, number>;
  nextLane: number;
}

export function createOrbLayoutMemory(): OrbLayoutMemory {
  return { positions: new Map(), lanes: new Map(), nextLane: 0 };
}

export function orbNodeWidth(node: GraphNode): number {
  return node.kind === "run" ? ORB_RUN_WIDTH : ORB_NODE_WIDTH;
}

/** Place real Run members in parallel reading lanes. Edges choose the reading order;
 * the layout never supplies a missing relation. Positions survive disclosure and playback. */
export function layoutOrbProjection(projection: GraphProjection, memory: OrbLayoutMemory): Map<string, Point> {
  const result = new Map<string, Point>();
  const groups = new Map<string, GraphNode[]>();
  const byId = new Map(projection.nodes.map(node => [node.id, node]));
  const children = new Map<string, GraphNode[]>();
  for (const node of projection.nodes) {
    const key = node.group ?? projection.identity;
    const members = groups.get(key) ?? [];
    members.push(node);
    groups.set(key, members);
  }
  for (const edge of projection.edges) {
    const parent = byId.get(edge.source), child = byId.get(edge.target);
    if (!parent || !child || parent.group !== child.group || parent === child) continue;
    const branches = children.get(parent.id) ?? [];
    branches.push(child);
    children.set(parent.id, branches);
  }

  for (const [key, members] of groups) {
    let lane = memory.lanes.get(key);
    if (lane === undefined) { lane = memory.nextLane++; memory.lanes.set(key, lane); }
    const center = lane * LANE;
    // Reserve all retained positions first, so a newly arrived record cannot claim
    // the cell of a previously displayed sibling, even when records arrive out of order.
    const occupied: Point[] = members.flatMap(node => {
      const point = memory.positions.get(node.id);
      return point ? [{ x: point.x + orbNodeWidth(node) / 2, y: point.y }] : [];
    });
    const run = members.find(node => node.kind === "run");
    const entry = members.find(node => node.entry);
    const roots = [run, entry, ...members].filter((node): node is GraphNode => !!node);
    const pending = new Set(members.map(node => node.id));
    for (const root of roots) {
      if (!pending.has(root.id)) continue;
      const queue = [{ node: root, column: 0, row: run && run !== root ? 1 : 0 }];
      for (let index = 0; index < queue.length; index++) {
        const { node, column, row } = queue[index]!;
        if (!pending.delete(node.id)) continue;
        let point = memory.positions.get(node.id);
        if (!point) {
          const x = center + column * COLUMN;
          let y = row * ROW;
          while (occupied.some(p => Math.abs(p.x - x) < COLUMN - 8 && Math.abs(p.y - y) < ROW - 6)) y += ROW;
          point = { x: x - orbNodeWidth(node) / 2, y };
          occupied.push({ x, y });
          memory.positions.set(node.id, point);
        }
        result.set(node.id, { ...point });
        const branches = children.get(node.id) ?? [];
        const observed = [...branches].sort((a, b) => Number(!!b.entry) - Number(!!a.entry));
        for (const [branch, child] of observed.entries()) {
          if (!pending.has(child.id)) continue;
          let nextColumn = column;
          if (branch || child.kind === "animator" || child.kind === "Reach operation") {
            nextColumn = column === 0 ? (branch % 2 ? -1 : 1) : 0;
          }
          queue.push({ node: child, column: nextColumn, row: Math.round(point.y / ROW) + 1 });
        }
      }
    }
  }
  const visible = new Set(result.keys());
  for (const id of memory.positions.keys()) {
    if (memory.positions.size <= MAX_RETAINED_POSITIONS) break;
    if (!visible.has(id)) memory.positions.delete(id);
  }
  for (const group of memory.lanes.keys()) {
    if (memory.lanes.size <= MAX_RETAINED_LANES) break;
    if (!groups.has(group)) memory.lanes.delete(group);
  }
  return result;
}
