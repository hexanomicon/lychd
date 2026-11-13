import type { GraphProjection } from "$lib/graph/model";

export interface Point { x: number; y: number }
export const NODE_WIDTH = 240;
export const NODE_HEIGHT = 142;

/** Rank strongly connected stations together; geometry never changes edge meaning. */
export function layoutProjection(projection: GraphProjection): Map<string, Point> {
  const positions = new Map<string, Point>();
  const groups = new Map<string, string[]>();
  for (const node of projection.nodes) {
    const group = node.group ?? "";
    groups.set(group, [...(groups.get(group) ?? []), node.id]);
  }
  let groupY = 100;
  for (const ids of groups.values()) {
    const members = new Set(ids);
    const successors = new Map(ids.map(id => [id, [] as string[]]));
    for (const edge of projection.edges) {
      if (members.has(edge.source) && members.has(edge.target)) successors.get(edge.source)?.push(edge.target);
    }
    let cursor = 0;
    const indices = new Map<string, number>();
    const low = new Map<string, number>();
    const stack: string[] = [];
    const active = new Set<string>();
    const components: string[][] = [];
    function visit(id: string) {
      indices.set(id, cursor); low.set(id, cursor++); stack.push(id); active.add(id);
      for (const next of successors.get(id) ?? []) {
        if (!indices.has(next)) {
          visit(next);
          low.set(id, Math.min(low.get(id)!, low.get(next)!));
        } else if (active.has(next)) low.set(id, Math.min(low.get(id)!, indices.get(next)!));
      }
      if (low.get(id) !== indices.get(id)) return;
      const component: string[] = [];
      let member: string;
      do {
        member = stack.pop()!; active.delete(member); component.push(member);
      } while (member !== id);
      components.push(component);
    }
    ids.forEach(id => { if (!indices.has(id)) visit(id); });
    const owner = new Map<string, number>();
    components.forEach((part, index) => part.forEach(id => owner.set(id, index)));
    const parents = components.map(() => new Set<number>());
    for (const edge of projection.edges) {
      const source = owner.get(edge.source), target = owner.get(edge.target);
      if (source !== undefined && target !== undefined && source !== target) parents[target]!.add(source);
    }
    const ranks = new Map<number, number>();
    function rank(part: number): number {
      const known = ranks.get(part);
      if (known !== undefined) return known;
      const value = Math.max(0, ...[...parents[part]!].map(parent => rank(parent) + 1));
      ranks.set(part, value); return value;
    }
    const columns = new Map<number, string[]>();
    for (const id of ids) {
      const column = rank(owner.get(id)!);
      columns.set(column, [...(columns.get(column) ?? []), id]);
    }
    const rows = Math.max(1, ...[...columns.values()].map(column => column.length));
    for (const [column, columnIds] of columns) {
      columnIds.forEach((id, row) => positions.set(id, {
        x: 100 + column * 350,
        y: groupY + (row + (rows - columnIds.length) / 2) * 220
      }));
    }
    groupY += rows * 220 + 140;
  }
  return positions;
}
