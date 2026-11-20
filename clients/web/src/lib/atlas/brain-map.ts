import type {
  ArchiveRunRecall,
  AtlasCatalogue,
  AtlasProject,
  BridgeSnapshot,
  BridgeTurnView,
  SessionPage,
} from "$lib/api/models";
import type { GraphEdge, GraphNode, GraphProjection } from "$lib/graph/model";
import { sourceSignature, type SeanceMaterial } from "$lib/seances/material";
import { atlasHref, atlasMapHref } from "./navigation";

export type Session = NonNullable<BridgeSnapshot["session"]>;
type Fact = readonly [string, string];
type Destination = { label: string; href: string };
export type AtlasObject = GraphNode & {
  origin: string;
  facts?: readonly Fact[];
  links?: readonly Destination[];
  recallRun?: string;
};
export interface AtlasMap extends GraphProjection {
  nodes: AtlasObject[];
  edges: GraphEdge[];
}
export type TurnSource = { turn: BridgeTurnView; key: string; digest: string | null; count: number };

/** An ephemeral match against a retained read. No source text travels in a URL. */
export async function atlasTurnDigest(turn: BridgeTurnView): Promise<string> {
  const bytes = new TextEncoder().encode(sourceSignature(turn));
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function turnSources(turns: readonly BridgeTurnView[]): Promise<TurnSource[]> {
  const groups = new Map<string, { turn: BridgeTurnView; count: number }>();
  for (const turn of turns) {
    const signature = sourceSignature(turn);
    const group = groups.get(signature);
    if (group) group.count++;
    else groups.set(signature, { turn, count: 1 });
  }
  return Promise.all(
    [...groups.values()].map(async ({ turn, count }, index) => {
      const digest = globalThis.crypto?.subtle ? await atlasTurnDigest(turn) : null;
      return { turn, count, digest, key: `turn:${digest ?? `read-local-${index}`}` };
    }),
  );
}

export async function matchSource(
  turns: readonly BridgeTurnView[],
  hint: string,
): Promise<BridgeTurnView | null> {
  if (!/^[a-f0-9]{64}$/.test(hint)) return null;
  const matches = (await turnSources(turns)).filter((entry) => entry.digest === hint && entry.count === 1);
  return matches.length === 1 ? matches[0]!.turn : null;
}

function mapBuilder(identity: string) {
  const map: AtlasMap = { identity, nodes: [], edges: [] };
  const known = new Map<string, AtlasObject>();
  function add(item: AtlasObject) {
    if (!known.has(item.id)) {
      known.set(item.id, item);
      map.nodes.push(item);
    }
    return item.id;
  }
  function edge(source: string, target: string, label: string, relation: GraphEdge["relation"] = "contains") {
    const id = JSON.stringify([source, target, label]);
    map.edges.push({ id, source, target, label, relation });
  }
  return { map, add, edge };
}

const bridgeHref = (id: string) => `/bridge/${encodeURIComponent(id)}`;
const orbHref = (id: string) => `/orb/${encodeURIComponent(id)}`;
const shortId = (id: string) => (id.length > 16 ? id.slice(0, 8) : id);

export function catalogueMap(projects: AtlasCatalogue, sessions: SessionPage): AtlasMap {
  const { map, add, edge } = mapBuilder("atlas-catalogue");
  add({
    id: "projects",
    kind: "catalogue",
    label: "Projects",
    origin: "Atlas catalogue",
    detail: "Projects on the loaded catalogue page.",
  });
  add({
    id: "sessions",
    kind: "catalogue",
    label: "Séances",
    origin: "Bridge catalogue",
    detail: "Conversations on the loaded catalogue page.",
  });
  const unique = new Map(
    [...(projects.pinned ? [projects.pinned] : []), ...projects.projects].map((p) => [p.id, p]),
  );
  for (const project of unique.values()) {
    const id = add({
      id: `project:${project.id}`,
      kind: "project",
      label: project.title,
      detail: project.brief,
      origin: "Atlas catalogue",
      facts: [
        ["Project", project.id],
        ["Lifecycle", project.lifecycle],
      ],
      links: [{ label: "Open project map", href: atlasMapHref(project.id) }],
    });
    edge("projects", id, "lists");
  }
  for (const session of sessions.sessions) {
    const id = add({
      id: `session:${session.id}`,
      kind: "séance",
      label: session.title,
      detail: "",
      origin: "Bridge catalogue",
      facts: [
        ["Séance", session.id],
        ["Created", session.created_at],
      ],
      links: [{ label: "Open séance map", href: atlasMapHref(null, session.id) }],
    });
    edge("sessions", id, "lists");
  }
  return map;
}

export function scopedMap(
  project: AtlasProject | null,
  session: Session | null,
  sources: readonly TurnSource[],
  material: readonly SeanceMaterial[],
  recalls: readonly ArchiveRunRecall[] = [],
): AtlasMap {
  const { map, add, edge } = mapBuilder(JSON.stringify([project?.id, session?.id]));
  const root = project ? `project:${project.id}` : "";
  const seance = session ? `session:${session.id}` : "";
  function run(id: string) {
    return add({
      id: `run:${id}`,
      kind: "run",
      label: `Run ${shortId(id)}`,
      detail: "",
      origin: "Recorded Run reference",
      facts: [["Run", id]],
      recallRun: id,
      links: [{ label: "Inspect Run in Orb", href: orbHref(id) }],
    });
  }
  if (project) {
    add({
      id: root,
      kind: "project",
      label: project.title,
      detail: project.brief,
      origin: "Atlas project record",
      facts: [
        ["Project", project.id],
        ["Lifecycle", project.lifecycle],
        ["Revision", String(project.version)],
      ],
      links: [{ label: "Open Project record", href: atlasHref(project.id) }],
    });
  }
  if (session) {
    add({
      id: seance,
      kind: "séance",
      label: session.title,
      detail: "",
      origin: "Retained Bridge conversation",
      facts: [
        ["Séance", session.id],
        ["Created", session.created_at],
      ],
      links: [{ label: "Open conversation in Bridge", href: bridgeHref(session.id) }],
    });
  }
  if (project) {
    const references = project.references.filter(
      (ref) => !session || (ref.kind === "session" && ref.target_id === session.id),
    );
    for (const concern of project.concerns.filter(
      (item) => !session || references.some((ref) => ref.concern_id === item.id),
    )) {
      const id = add({
        id: `concern:${concern.id}`,
        kind: "concern",
        label: concern.statement,
        detail: concern.criteria,
        origin: "Atlas project record",
        facts: [
          ["Concern", concern.id],
          ["Revision", String(concern.revision)],
        ],
      });
      edge(root, id, "raises");
    }
    for (const ref of references) {
      const id = add({
        id: `reference:${ref.id}`,
        kind: "reference",
        label: ref.note || `Linked ${ref.kind === "session" ? "séance" : "Run"}`,
        detail: ref.note,
        origin: "Atlas activity reference",
        facts: [
          ["Reference", ref.id],
          ["Author", ref.author],
          ["Recorded", ref.created_at],
        ],
      });
      edge(ref.concern_id ? `concern:${ref.concern_id}` : root, id, "links");
      const target =
        ref.kind === "run"
          ? run(ref.target_id)
          : add({
              id: `session:${ref.target_id}`,
              kind: "séance",
              label: `Séance ${shortId(ref.target_id)}`,
              detail: "",
              origin: "Atlas session reference",
              facts: [["Séance", ref.target_id]],
              links: [{ label: "Open séance map", href: atlasMapHref(project.id, ref.target_id) }],
            });
      edge(id, target, "points to", "declared");
    }
    if (!session) {
      for (const assessment of project.assessments) {
        const concern = project.concerns.find((item) => item.id === assessment.concern_id);
        const stale =
          assessment.brief_revision !== project.brief_revision ||
          assessment.concern_revision !== concern?.revision;
        const id = add({
          id: `assessment:${assessment.id}`,
          kind: "assessment",
          label: assessment.judgment,
          detail: assessment.rationale,
          origin: "Recorded Atlas judgment",
          facts: [
            ["Assessment", assessment.id],
            ["Author", assessment.author],
            ["Recorded", assessment.created_at],
            ["Judged brief", assessment.brief],
            ["Judged concern", assessment.statement],
            ["Judged criteria", assessment.criteria],
            ["Judged basis", stale ? "Needs review" : "Current"],
          ],
        });
        edge(`concern:${assessment.concern_id}`, id, "assessed by");
        for (const cited of assessment.reference_ids) edge(id, `reference:${cited}`, "cites", "selection");
      }
      for (const decision of project.decisions) {
        const id = add({
          id: `decision:${decision.id}`,
          kind: "decision",
          label: decision.statement,
          detail: decision.rationale,
          origin: "Atlas decision record",
          facts: [
            ["Decision", decision.id],
            ["Author", decision.author],
            ["Recorded", decision.created_at],
          ],
        });
        edge(root, id, "records");
        if (decision.supersedes_id) edge(id, `decision:${decision.supersedes_id}`, "supersedes", "declared");
      }
    }
  }
  if (session) {
    const bySignature = new Map<string, string>();
    for (const { turn, key, digest, count } of sources) {
      const where = bridgeHref(session.id);
      const exact = digest && count === 1;
      const title = turn.content.trim() || (turn.role === "user" ? "User turn" : "Agent turn");
      add({
        id: key,
        kind: "source turn",
        label: title,
        detail: turn.content,
        origin: "Retained Bridge turn",
        facts: [
          ["Role", turn.role],
          ["Recorded", turn.created_at],
          ["State", turn.state],
          ...(count > 1 ? [["Identical source matches", String(count)] as Fact] : []),
        ],
        links: [
          {
            label: exact ? "Return to turn" : "Open séance",
            href: exact ? `${where}?source=${digest}` : where,
          },
        ],
      });
      edge(seance, key, "contains");
      if (turn.run_id) edge(key, run(turn.run_id), "names Run", "declared");
      if (count === 1) bySignature.set(sourceSignature(turn), key);
    }
    for (const item of material.filter((item) => item.sessionId === session.id)) {
      const source = bySignature.get(sourceSignature(item.source));
      const id = add({
        id: `material:${item.id}`,
        kind: "working material",
        label: item.note || item.kind,
        detail: item.source.content,
        origin: "Document-local selection",
        facts: [
          ["Classification", item.kind],
          ["Visibility", "This tab"],
          ["Source", source ? "Matched retained turn" : "Exact source unavailable in this read"],
        ],
      });
      edge(source ?? seance, id, source ? "quoted in" : "selected in", "selection");
    }
  }
  const runIds = new Set(map.nodes.flatMap((node) => (node.recallRun ? [node.recallRun] : [])));
  for (const result of recalls) {
    if (
      !runIds.has(result.run_id) ||
      result.status !== "recorded" ||
      result.receipt?.run_id !== result.run_id
    )
      continue;
    const receipt = result.receipt;
    const id = add({
      id: `recall:${receipt.receipt_id}`,
      kind: "recall",
      label: "Recall receipt",
      detail: receipt.purpose,
      origin: "Archive Run Recall",
      facts: [
        ["Receipt", receipt.receipt_id],
        ["Profile", receipt.profile],
        ["Recorded", receipt.created_at],
        ["Receipt digest", receipt.receipt_digest],
      ],
    });
    edge(`run:${result.run_id}`, id, "has receipt");
    for (const item of receipt.selected) {
      const ref = item.reference;
      const note = add({
        id: JSON.stringify([
          "note",
          receipt.namespace_id,
          ref.record_id,
          ref.revision_digest,
          ref.lifecycle_version,
        ]),
        kind: "public note",
        label: item.source_key,
        detail: "",
        origin: "Public-source revision selected at Recall",
        facts: [
          ["Record", ref.record_id],
          ["Source revision", item.source_revision],
          ["Revision digest", ref.revision_digest],
          ["Source digest", item.source_digest],
          ["Lifecycle version at Recall", String(ref.lifecycle_version)],
        ],
      });
      edge(id, note, "selected", "selection");
    }
  }
  return map;
}
