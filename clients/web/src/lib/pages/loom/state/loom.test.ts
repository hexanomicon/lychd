import { expect, it } from "vitest";

import type { LoomView } from "$lib/api/models";
import { loomProjection } from "./loom";

const pattern: LoomView = {
  schema_version: 1,
  pattern_id: "review",
  revision: "2",
  digest: "sha256:exact",
  title: "Review",
  description: "Declared review stations.",
  publication: "published",
  checkpoint_schema: "review@1",
  implementation_revision: "source",
  entry_node: "prepare",
  trigger_hint: "review",
  mermaid_source: "flowchart LR",
  nodes: [
    { key: "prepare", label: "Prepare", kind: "step" },
    { key: "review", label: "Review", kind: "gate" },
    { key: "finish", label: "Finish", kind: "terminal" }
  ],
  edges: [
    { key: "prepare-review", source: "prepare", target: "review", relation: "permits" },
    { key: "review-review", source: "review", target: "review", relation: "re-entry" },
    { key: "review-prepare", source: "review", target: "prepare", relation: "permits" },
    { key: "review-finish", source: "review", target: "finish", relation: "permits" }
  ]
};

it("retains declared identities, relation labels, return paths, and self-loops without inventing execution", () => {
  const graph = loomProjection(pattern);
  expect(graph.nodes.map((node) => [node.id, node.kind, node.entry])).toEqual([
    ["prepare", "step", true], ["review", "gate", false], ["finish", "terminal", false]
  ]);
  expect(graph.edges).toEqual(pattern.edges.map((edge) => ({
    id: edge.key,
    source: edge.source,
    target: edge.target,
    label: edge.relation,
    relation: "permission"
  })));
  expect(graph.nodes.every((node) => node.state === undefined)).toBe(true);
  expect(Object.isFrozen(graph)).toBe(true);
  expect(Object.isFrozen(graph.nodes)).toBe(true);
  expect(Object.isFrozen(graph.nodes[0])).toBe(true);
  expect(Object.isFrozen(graph.edges[0])).toBe(true);
});

it("folds only the supplied Pattern membership and keeps its identity across detail levels", () => {
  const detail = loomProjection(pattern);
  const folded = loomProjection(pattern, "pattern");
  expect(folded.identity).toBe(detail.identity);
  expect(folded.nodes).toHaveLength(1);
  expect(folded.nodes[0]).toMatchObject({
    label: "Review", detail: "review@2", kind: "pattern", count: 3,
    members: ["prepare", "review", "finish"]
  });
  expect(Object.isFrozen(folded.nodes[0]?.members)).toBe(true);
  expect(folded.edges).toEqual([]);
  expect(loomProjection(pattern).nodes).toEqual(detail.nodes);
});

it("fences replacements by exact Pattern, revision, and digest", () => {
  const original = loomProjection(pattern).identity;
  expect(loomProjection({ ...pattern, pattern_id: "other" }).identity).not.toBe(original);
  expect(loomProjection({ ...pattern, revision: "3" }).identity).not.toBe(original);
  expect(loomProjection({ ...pattern, digest: "sha256:changed" }).identity).not.toBe(original);
  expect(loomProjection({ ...pattern, title: "Display title" }).identity).toBe(original);
});
