import { z } from "zod";
import type { GraphProjection } from "$lib/graph/model";

export const kinds = ["agent", "object", "router", "subflow", "ledger"] as const;
export type Kind = (typeof kinds)[number];
const nodeSchema = z.object({
  id: z.string().min(1),
  parent: z.string(),
  kind: z.enum(kinds),
  name: z.string().trim().min(1),
  purpose: z.string(),
  inputs: z.string(),
  schema: z.string(),
  system: z.string(),
  user: z.string(),
  model: z.string(),
  temperature: z.number().min(0).max(2),
  fallback: z.string(),
  tools: z.string(),
});
export type DraftNode = z.infer<typeof nodeSchema>;
const relations = ["supplies", "dispatches", "produces", "guards", "records"] as const;
export { relations };
const edgeSchema = z.object({
  id: z.string().min(1),
  source: z.string(),
  target: z.string(),
  relation: z.enum(relations),
  label: z.string().trim().min(1),
});
const documentSchema = z.object({
  format: z.literal("loom-blueprint/1"),
  nodes: z.array(nodeSchema).min(1),
  edges: z.array(edgeSchema),
});
export type Blueprint = z.infer<typeof documentSchema>;

export function validate(value: unknown): Blueprint {
  const draft = documentSchema.parse(value);
  const nodes = new Map(draft.nodes.map((n) => [n.id, n]));
  if (nodes.size !== draft.nodes.length || new Set(draft.edges.map((e) => e.id)).size !== draft.edges.length)
    throw Error("Every node and connection needs a unique ID.");
  for (const n of draft.nodes) {
    const seen = new Set([n.id]);
    let parent = n.parent;
    while (parent) {
      const owner = nodes.get(parent);
      if (!owner || !["subflow", "router"].includes(owner.kind) || seen.has(parent))
        throw Error("Invalid enclosing flow for " + n.name);
      seen.add(parent);
      parent = owner.parent;
    }
    try {
      const schema = JSON.parse(n.schema);
      if (typeof schema !== "object" || schema === null || Array.isArray(schema)) throw Error();
    } catch {
      throw Error(n.name + " needs a JSON object for its output schema.");
    }
  }
  for (const edge of draft.edges) {
    const a = nodes.get(edge.source),
      b = nodes.get(edge.target);
    if (!a || !b || a.parent !== b.parent) throw Error("Invalid connection: " + edge.label);
  }
  return draft;
}

export function makeNode(id: string, kind: Kind, name: string, parent = "", purpose = ""): DraftNode {
  return {
    id,
    kind,
    name,
    parent,
    purpose,
    inputs: "",
    schema: '{"type":"object"}',
    system: "",
    user: "",
    model: "inherit",
    temperature: 0.2,
    fallback: "Return for review",
    tools: "",
  };
}

export function example(): Blueprint {
  const nodes: DraftNode[] = [];
  const edges: Blueprint["edges"] = [];
  function n(
    id: string,
    kind: Kind,
    name: string,
    purpose: string,
    parent = "",
    config: Partial<DraftNode> = {},
  ) {
    nodes.push({ ...makeNode(id, kind, name, parent, purpose), ...config });
  }
  function e(source: string, target: string, relation: (typeof relations)[number], label: string) {
    edges.push({ id: source + "-" + target, source, target, relation, label });
  }
  n("intent", "object", "Intent", "Retry a failed document without duplicating earlier writes.", "", {
    schema: '{"type":"object","required":["request"],"properties":{"request":{"type":"string"}}}',
  });
  n(
    "analysis",
    "subflow",
    "Semantic decomposition",
    "Compare target and current state. Emit guarded tasks with evidence requirements.",
  );
  n(
    "plan",
    "object",
    "Conditional task plan",
    "A checks document identity. B checks write outcome. C requires an unknown outcome.",
    "",
    {
      schema:
        '{"type":"object","required":["tasks"],"properties":{"tasks":{"type":"array","items":{"type":"object","required":["guard","dependencies","evidence"]}}}}',
    },
  );
  n(
    "parallel",
    "subflow",
    "Parallel Intent Task Orchestration",
    "Release eligible tasks in parallel and join the evidence.",
  );
  n(
    "review",
    "subflow",
    "Evidence & Crucible",
    "Bound further inquiry and reconcile the case for a scoped retry.",
  );
  n(
    "delivery",
    "subflow",
    "Implementation & verification",
    "Prepare a candidate edit and test for duplicate writes.",
  );
  n(
    "ledger",
    "ledger",
    "Decision ledger",
    "Record the evidence, unresolved objections, approval and verification outcome.",
  );
  e("intent", "analysis", "supplies", "Requested outcome");
  e("analysis", "plan", "produces", "Guarded tasks");
  e("plan", "parallel", "supplies", "TaskPlan");
  e("parallel", "review", "produces", "Evidence dossier");
  e("review", "delivery", "guards", "Reviewed proposal");
  e("delivery", "ledger", "records", "Verification receipt");
  n("target", "agent", "Target-state analyst", "Describe the desired observable behavior.", "analysis", {
    system: "Write measurable acceptance criteria.",
    user: "Which documents should change after retry?",
    inputs: "Intent.request",
  });
  n(
    "current",
    "agent",
    "Current-state analyst",
    "Identify current behavior from implementation and tests.",
    "analysis",
    { tools: "read_file", user: "Trace retry through the caller and importer." },
  );
  n("diff", "object", "Difference", "Compare whole-batch retry with a single-document retry.", "analysis");
  n(
    "decompose",
    "agent",
    "Task decomposition",
    "Emit dependencies, guards and expected evidence.",
    "analysis",
    {
      inputs: "Difference",
      system: "Decompose the gap into independently answerable questions.",
      user: "Plan identity, write-receipt and conditional recovery probes.",
    },
  );
  e("target", "diff", "produces", "Target report");
  e("current", "diff", "produces", "Current report");
  e("diff", "decompose", "supplies", "Gap and constraints");
  n("dispatch", "router", "Task dispatch", "Route ready tasks by type and dependency.", "parallel");
  n(
    "join",
    "object",
    "Joined evidence",
    "Collect eligible solver receipts and preserve unknown outcomes.",
    "parallel",
  );
  e("dispatch", "join", "produces", "Eligible solver receipts");
  n("identity", "agent", "Identity solver", "Find the document identity used for retries.", "dispatch", {
    inputs: "TaskPlan.document_ref",
    system: "Read the importer and identify the stable key used to deduplicate a document. Cite the source.",
    user: "Which key identifies {{document_ref}} across retries?",
    schema: '{"type":"object","properties":{"document_key":{"type":"string"},"source":{"type":"string"}},"required":["document_key","source"]}',
    tools: "read_file",
  });
  n("receipt", "agent", "Receipt solver", "Find the earlier write outcome.", "dispatch", {
    inputs: "TaskPlan.document_ref, TaskPlan.attempt",
    system: "Read the matching receipt. Report unknown when the record cannot establish a write outcome.",
    user: "Find the write outcome for {{document_ref}} in attempt {{attempt}}.",
    schema: '{"type":"object","properties":{"outcome":{"enum":["written","absent","unknown"]}},"required":["outcome"]}',
    tools: "read_file",
  });
  n(
    "outcome",
    "router",
    "Write outcome?",
    "A known outcome closes B. An unknown outcome releases C.",
    "dispatch",
  );
  n("identity-result", "object", "Identity evidence", "Stable document key and source location.", "dispatch");
  n("known", "object", "Known receipt", "Retain the observed outcome.", "dispatch");
  n("recover", "subflow", "Recovery solver", "Use a read-only lookup when available.", "dispatch");
  e("identity", "identity-result", "produces", "Stable identity");
  e("receipt", "outcome", "supplies", "Receipt status");
  e("outcome", "known", "guards", "Known outcome");
  e("outcome", "recover", "dispatches", "Unknown outcome");
  n("lookup", "router", "Lookup available?", "Select an admissible recovery path.", "recover");
  n("read", "object", "File read result", "receipts.log · doc=3 write=timeout receipt_key=r17", "recover", {
    schema: '{"type":"object","required":["path","excerpt","receipt_key"]}',
  });
  n(
    "unknown",
    "object",
    "Unresolved outcome",
    "Preserve the missing evidence and request owner review.",
    "recover",
  );
  e("lookup", "read", "guards", "Read access available");
  e("lookup", "unknown", "guards", "Lookup unavailable");
  n(
    "affect",
    "agent",
    "Bounded appraisal",
    "Allow one new probe for a discriminating observation. Stop on repetition.",
    "review",
    {
      inputs: "Evidence dossier",
      system: "State what new evidence could change the decision. Stop after one probe.",
      user: "Can a receipt distinguish failure from a lost acknowledgement?",
    },
  );
  n("pro", "agent", "Advocate", "Argue for retry after a confirmed failed write.", "review");
  n("con", "agent", "Challenger", "Test the lost-acknowledgement counterexample.", "review");
  n(
    "reconcile",
    "agent",
    "Crucible reconciler",
    "Retain both claims and request review for unknown writes.",
    "review",
  );
  e("affect", "pro", "supplies", "Supporting question");
  e("affect", "con", "supplies", "Counterexample");
  e("pro", "reconcile", "supplies", "Support");
  e("con", "reconcile", "supplies", "Objection");
  n("implement", "agent", "Candidate editor", "Prepare a scoped retry patch.", "delivery", {
    tools: "read_file, propose_edit",
    user: "Retry only confirmed failures.",
  });
  n("edit", "object", "File edit result", "retry.py · candidate conditional retry diff.", "delivery", {
    schema: '{"type":"object","required":["path","diff","base_revision"]}',
  });
  n(
    "verify",
    "agent",
    "Verifier",
    "Count additional writes on success, failure and unknown receipt cases.",
    "delivery",
    { inputs: "Candidate diff, acceptance criteria", tools: "run_tests" },
  );
  e("implement", "edit", "produces", "Candidate diff");
  e("edit", "verify", "supplies", "Patch under test");
  return validate({ format: "loom-blueprint/1", nodes, edges });
}

export function project(draft: Blueprint, parent: string): GraphProjection {
  const nodes = draft.nodes.filter((n) => n.parent === parent);
  const ids = new Set(nodes.map((n) => n.id));
  return {
    identity: "studio:" + parent,
    nodes: nodes.map((n) => ({ id: n.id, label: n.name, kind: n.kind, detail: n.purpose, state: n.kind })),
    edges: draft.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ ...e, relation: "declared" })),
  };
}

/** Keep neighbouring phases and the route into the active subflow on the canvas. */
export function projectLoomCanvas(draft: Blueprint, currentParent: string): GraphProjection {
  const expanded = new Set<string>([""]);
  const byId = new Map(draft.nodes.map(node => [node.id, node]));
  let owner = currentParent;
  while (owner && !expanded.has(owner)) {
    expanded.add(owner);
    owner = byId.get(owner)?.parent ?? "";
  }
  const visible = draft.nodes.filter(node => expanded.has(node.parent));
  const ids = new Set(visible.map(node => node.id));
  return {
    identity:"studio:canvas",
    nodes:visible.map(node => ({ id:node.id, label:node.name, kind:node.kind, detail:node.purpose, parent:node.parent })),
    edges:draft.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target)).map(edge => ({ ...edge, relation:"declared" }))
  };
}
