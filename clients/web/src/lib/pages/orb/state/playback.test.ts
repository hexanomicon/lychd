import { describe, expect, it } from "vitest";
import { fixtureRun, pattern } from "./__fixtures__/snapshot";
import { animatorAccent, animatorObservations, evidenceAt } from "./playback";
import { projectOrb } from "$lib/pages/orb/state/orb";

describe("recorded graph cursor", () => {
  const snapshot = fixtureRun();
  const base = snapshot.evidence[0]!;
  snapshot.evidence.push(
    { ...base, event_id: "grant-a", seq: 2, kind: "dispatch", subject_key: "chat-a", animator_name: "reasoner", grant_id: "g-a", model_id: "m-a", phase: "warm" },
    { ...base, event_id: "future", seq: 4, kind: "dispatch", subject_key: "chat-b", animator_name: "swift", grant_id: "g-b", phase: "warm" },
    { ...base, event_id: "settled", seq: 5, phase: "settled" }
  );
  snapshot.gaps = [{ start_seq: 1, end_seq: 1, classification: "unknown_or_omitted" }, { start_seq: 3, end_seq: 3, classification: "unknown_or_omitted" }];

  it("excludes future observations and gaps while retaining the declared score", () => {
    const viewed = evidenceAt(snapshot, 2);
    expect(viewed.evidence.map((record) => record.seq)).toEqual([0, 2]);
    expect(viewed.gaps).toHaveLength(1);
    const graph = projectOrb(snapshot, pattern, 2);
    expect(graph.nodes.find((node) => node.id === "station:inspect")?.state).toBe("entered");
    expect(graph.nodes.some((node) => node.label === "chat-b")).toBe(false);
    expect(graph.nodes.filter((node) => node.attention).map((node) => node.label)).toEqual(["chat-a"]);
    expect(graph.edges).toHaveLength(2);
    expect(projectOrb(snapshot, pattern, 3).nodes.some((node) => node.attention)).toBe(false);
    expect(snapshot.evidence).toHaveLength(4);
  });

  it("shows only retained Animator selections at the cursor and never extends a grant into uptime", () => {
    expect(animatorObservations(snapshot.evidence, 0)).toEqual([]);
    const atGrant = animatorObservations(snapshot.evidence, 2);
    expect(atGrant.map((row) => row.name)).toEqual(["reasoner"]);
    expect(atGrant[0]?.atCursor).toBe(true);
    expect(animatorObservations(snapshot.evidence, 3)[0]?.atCursor).toBe(false);
    expect(animatorObservations(snapshot.evidence, null).every((row) => !row.atCursor)).toBe(true);
    expect(atGrant[0]?.accent).toBe(animatorAccent("reasoner"));
    expect(animatorObservations([{ ...base, animator_name: "not-a-dispatch" }], null)).toEqual([]);
  });
});
