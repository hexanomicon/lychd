import type { LoomView } from "$lib/api/models";
import type { GraphProjection } from "$lib/graph/model";

/** Declared permissions only: layout and Run observations belong to other layers. */
export function loomProjection(view: LoomView, level: "stations" | "pattern" = "stations"): GraphProjection {
  const identity = JSON.stringify([view.pattern_id, view.revision, view.digest]);
  if (level === "pattern") {
    return Object.freeze({
      identity,
      nodes: Object.freeze([Object.freeze({
        id: `pattern:${identity}`,
        label: view.title,
        detail: `${view.pattern_id}@${view.revision}`,
        kind: "pattern",
        count: view.nodes.length,
        members: Object.freeze(view.nodes.map((node) => node.key))
      })]),
      edges: Object.freeze([])
    });
  }
  return Object.freeze({
    identity,
    nodes: Object.freeze(view.nodes.map((node) => Object.freeze({
      id: node.key,
      label: node.label,
      detail: node.key,
      kind: node.kind,
      entry: node.key === view.entry_node
    }))),
    edges: Object.freeze(view.edges.map((edge) => Object.freeze({
      id: edge.key,
      source: edge.source,
      target: edge.target,
      label: edge.relation,
      relation: "permission" as const
    })))
  });
}
