import type { Edge, Node } from "@xyflow/svelte";
import type { GraphNode } from "$lib/graph/model";

export type RenderNode = Node<{
  semantic: GraphNode;
  select: (id: string, opener: HTMLElement, pointer?: boolean) => void;
}>;

function sameRecord(left: object | undefined, right: object | undefined): boolean {
  if (left === right) return true;
  if (!left || !right) return false;
  const entries = Object.entries(left);
  return entries.length === Object.keys(right).length && entries.every(([key, value]) => value === Reflect.get(right, key));
}

function sameSemantic(left: GraphNode, right: GraphNode): boolean {
  const { members: a, ...before } = left;
  const { members: b, ...after } = right;
  return sameRecord(before, after) && (a === b || !!a && !!b && a.length === b.length && a.every((id, index) => id === b[index]));
}

/** Reconcile owned semantic inputs with public, disposable renderer state. Dropping
 * measured on a same-geometry replacement invalidates XYFlow's measured handles.
 */
export function reconcileNodes(previous: RenderNode[], incoming: RenderNode[]): RenderNode[] {
  const known = new Map(previous.map((node) => [node.id, node]));
  const next = incoming.map((node) => {
    const before = known.get(node.id);
    if (!before || before.type !== node.type || before.width !== node.width || before.height !== node.height) return node;
    const position = before.position.x === node.position.x && before.position.y === node.position.y ? before.position : node.position;
    const data = before.data.select === node.data.select && sameSemantic(before.data.semantic, node.data.semantic) ? before.data : node.data;
    const updated = { ...before, ...node, position, data };
    return Object.keys(node).every((key) => Reflect.get(before, key) === Reflect.get(updated, key)) ? before : updated;
  });
  return previous.length === next.length && next.every((node, index) => node === previous[index]) ? previous : next;
}

export function reconcileEdges(previous: Edge[], incoming: Edge[]): Edge[] {
  const known = new Map(previous.map((edge) => [edge.id, edge]));
  const next = incoming.map((edge) => {
    const before = known.get(edge.id);
    if (!before) return edge;
    const sameMarker = typeof before.markerEnd === "object" && typeof edge.markerEnd === "object"
      ? sameRecord(before.markerEnd, edge.markerEnd) : before.markerEnd === edge.markerEnd;
    const updated = { ...edge, data: sameRecord(before.data, edge.data) ? before.data : edge.data,
      markerEnd: sameMarker ? before.markerEnd : edge.markerEnd };
    return sameRecord(before, updated) ? before : updated;
  });
  return previous.length === next.length && next.every((edge, index) => edge === previous[index]) ? previous : next;
}
