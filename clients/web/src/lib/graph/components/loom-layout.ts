import type { GraphNode, GraphProjection } from "$lib/graph/model";
import { layoutProjection, type Point } from "./layout";

const width = 180, height = 56;
export interface LoomFrame extends Point { id: string; title: string; width: number; height: number; }
interface Group { width: number; height: number; positions: Map<string, Point>; frames: LoomFrame[]; }

/** A container owns precisely its visible children. Reserve its bounds before placing
 * the next rank so expanded subflows keep their neighbours and boundary connections. */
export function layoutLoom(projection: GraphProjection): Group {
  const children = new Map<string, GraphNode[]>();
  for (const node of projection.nodes) {
    const parent = node.parent ?? "";
    const members = children.get(parent) ?? [];
    members.push(node);
    children.set(parent, members);
  }
  function arrange(parent: string): Group {
    const nodes = children.get(parent) ?? [];
    const ranks = layoutProjection({ identity:projection.identity, nodes, edges:projection.edges });
    const levels = new Map<number, GraphNode[]>();
    const nested = new Map<string, Group>();
    for (const node of nodes) {
      const rank = ranks.get(node.id)?.x ?? 0;
      const peers = levels.get(rank) ?? [];
      peers.push(node); levels.set(rank, peers);
      if (children.has(node.id)) nested.set(node.id, arrange(node.id));
    }
    const extent = (node: GraphNode) => {
      const inner = nested.get(node.id);
      return inner ? { width:Math.max(width, inner.width) + 48, height:height + inner.height + 85 } : { width, height };
    };
    const rows = [...levels].sort(([a], [b]) => a-b).map(([, peers]) => ({
      peers,
      width: peers.reduce((sum, node) => sum + extent(node).width, 0) + (peers.length - 1) * 54,
      height: Math.max(...peers.map(node => extent(node).height))
    }));
    const fieldWidth = Math.max(0, ...rows.map(row => row.width));
    const positions = new Map<string, Point>(), frames: LoomFrame[] = [];
    let y = 0;
    for (const row of rows) {
      let x = (fieldWidth - row.width) / 2;
      for (const node of row.peers) {
        const size = extent(node), inner = nested.get(node.id);
        positions.set(node.id, { x: x + (size.width-width) / 2, y:y + (inner ? 24 : 0) });
        if (inner) {
          frames.push({id:node.id,title:node.label,x,y,width:size.width,height:size.height});
          const left = x + (size.width - inner.width) / 2, top = y + height + 60;
          for (const [id, point] of inner.positions) positions.set(id, { x:left + point.x, y:top + point.y });
          for (const frame of inner.frames) frames.push({ ...frame, x:left + frame.x, y:top + frame.y });
        }
        x += size.width + 54;
      }
      y += row.height + 50;
    }
    return { width:fieldWidth, height:Math.max(0,y-50), positions, frames };
  }
  return arrange("");
}
