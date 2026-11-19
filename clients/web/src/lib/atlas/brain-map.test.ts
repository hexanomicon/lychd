import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { AtlasProject, BridgeTurnView } from "$lib/api/models";
import { atlasTurnDigest, matchSource, scopedMap, turnSources, type Session } from "./brain-map";

const now = "2026-11-18T12:00:00Z";
const turn: BridgeTurnView = {
  role: "user",
  created_at: now,
  state: "settled",
  run_id: "run-a",
  content: "Where is the reference?",
};
const session: Session = {
  id: "session-a",
  title: "Bench review",
  created_at: now,
  pending_count: 0,
  turns: [turn],
};
const project: AtlasProject = {
  id: "project-a",
  title: "Calibration",
  brief: "Review the new sensor.",
  version: 2,
  brief_revision: 1,
  workspace_state: "kept",
  next_action: "",
  created_at: now,
  updated_at: now,
  builtin: false,
  lifecycle: "active",
  concerns: [
    { id: "concern-a", statement: "Can the reading be trusted?", criteria: "Compare plates", revision: 2 },
  ],
  assessments: [
    {
      id: "assessment-a",
      author: "operator",
      created_at: now,
      concern_id: "concern-a",
      rationale: "Compared",
      judgment: "sufficient",
      reference_ids: ["ref-b"],
      statement: "Former basis",
      criteria: "Original comparison",
      brief: "Earlier",
      brief_revision: 1,
      concern_revision: 1,
    },
  ],
  decisions: [],
  references: [
    {
      id: "ref-a",
      kind: "session",
      target_id: session.id,
      concern_id: null,
      note: "Bench meeting",
      author: "one",
      created_at: now,
    },
    {
      id: "ref-b",
      kind: "session",
      target_id: session.id,
      concern_id: "concern-a",
      note: "Plate comparison",
      author: "two",
      created_at: now,
    },
  ],
};
beforeEach(() => vi.stubGlobal("crypto", webcrypto));
afterEach(() => vi.unstubAllGlobals());

it("keeps each reference, shared target, recorded citation and stale judgment distinct", () => {
  const map = scopedMap(project, null, [], []);
  expect(map.nodes.filter((node) => node.kind === "séance")).toHaveLength(1);
  expect(map.nodes.filter((node) => node.kind === "reference")).toHaveLength(2);
  expect(map.edges.filter((edge) => edge.label === "cites").map((edge) => edge.target)).toEqual([
    "reference:ref-b",
  ]);
  expect(map.nodes.find((node) => node.kind === "assessment")?.facts).toContainEqual([
    "Judged basis",
    "Needs review",
  ]);
  expect(map.nodes.find((node) => node.kind === "séance")?.links?.[0]?.href).toBe(
    "/atlas/map?project=project-a&session=session-a",
  );
});

it("matches an exact unique source without putting its text in navigation or acquiring other sessions' material", async () => {
  const different = { ...turn, content: "A different question" };
  const reply = { ...turn, role: "agent" as const };
  const digest = await atlasTurnDigest(turn);
  expect(await matchSource([different, reply, turn], digest)).toBe(turn);
  expect(await matchSource([different, reply], digest)).toBeNull();
  expect(await matchSource([turn, { ...turn }], digest)).toBeNull();
  const local = {
    id: "sel",
    kind: "Open question" as const,
    note: "Recheck",
    sessionId: session.id,
    source: turn,
  };
  const sources = await turnSources([turn, reply]);
  const map = scopedMap(null, session, sources, [local, { ...local, id: "another", sessionId: "elsewhere" }]);
  const question = map.nodes.find((item) => item.id === `turn:${digest}`);
  expect(question?.links).toEqual([{ label: "Return to turn", href: `/bridge/session-a?source=${digest}` }]);
  expect(map.nodes.filter((node) => node.kind === "working material")).toHaveLength(1);
  expect(map.edges.find((edge) => edge.label === "quoted in")?.source).toBe(question?.id);
  expect(map.nodes.filter((node) => node.kind === "run")).toHaveLength(1);
  const ambiguous = scopedMap(null, session, await turnSources([turn, { ...turn }]), [local]);
  expect(ambiguous.nodes.find((node) => node.kind === "source turn")?.links?.[0]?.href).toBe(
    "/bridge/session-a",
  );
  expect(ambiguous.edges.some((edge) => edge.label === "quoted in")).toBe(false);
});
