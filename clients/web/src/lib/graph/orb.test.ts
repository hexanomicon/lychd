import { describe, expect, it } from "vitest";
import { fixtureRun, pattern } from "$lib/orb/__fixtures__/snapshot";
import { matchesOrbPattern, mergeOrbEvidence, mergeOrbGaps, orbEvidenceNodeId, projectOrb, projectOrbField } from "./orb";

describe("Orb semantic graph", () => {
  it("shares only explicitly recorded Animator selections across Run groups", () => {
    const a = fixtureRun(), b = fixtureRun("run-b");
    a.evidence = [{ ...a.evidence[0]!, kind: "dispatch", animator_name: "local-reasoner", subject_key: "chat" }];
    b.evidence = [{ ...b.evidence[0]!, kind: "dispatch", animator_name: "local-reasoner", subject_key: "chat" }];
    const lenses = new Map([[a.run.run_id, { snapshot: a, pattern }], [b.run.run_id, { snapshot: b, pattern }]]);
    for (const level of ["runs", "stations", "occurrences", "records"] as const) {
      const graph = projectOrbField([a.run, b.run], lenses, level).projection;
      const sources = graph.nodes.filter((node) => node.kind === "animator");
      expect(sources).toHaveLength(1);
      expect(sources[0]).toMatchObject({ id: "animator:local-reasoner", count: 2, group: "animators" });
      expect(sources[0]!.detail).toContain("call activity and availability are not supplied");
      const selections = graph.edges.filter((edge) => edge.relation === "selection");
      expect(selections).toHaveLength(2);
      expect(selections.every((edge) => graph.nodes.some((node) => node.id === edge.source) && edge.target === sources[0]!.id)).toBe(true);
      expect(graph.nodes.some((node) => node.kind === "file" || node.kind === "agent")).toBe(false);
    }
  });
  it("keeps suffix coverage when later stream metadata has no older-page flag", () => {
    const snapshot = fixtureRun();
    const field = projectOrbField([snapshot.run], new Map([[snapshot.run.run_id, { snapshot, pattern, trimmed: true }]]), "runs");
    expect(field.projection.nodes[0]!.detail).toContain("More retained history exists outside this lens");
    expect(snapshot.has_more).toBe(false);
  });
  it("keeps declared permissions distinct from supplied records, including a return edge", () => {
    const snapshot = fixtureRun();
    const graph = projectOrb(snapshot, pattern);
    expect(graph.edges).toHaveLength(2);
    expect(graph.edges.every((edge) => edge.relation === "permission")).toBe(true);
    expect(graph.nodes.find((node) => node.id === "station:inspect")?.count).toBe(1);
    expect(graph.nodes.find((node) => node.id === "station:revise")?.detail).toContain("no recorded phase");
    expect(graph.nodes.find((node) => node.id === "station:revise")?.state).toBe("unknown");
  });
  it("does not relabel a dispatch subject as a station and keeps unknowns and gaps explicit", () => {
    const snapshot = fixtureRun();
    snapshot.evidence = [{ ...snapshot.evidence[0]!, kind: "dispatch" }, { ...snapshot.evidence[0]!, event_id: "unknown", seq: 2, subject_key: null }];
    snapshot.gaps = [{ start_seq: 1, end_seq: 1, classification: "unknown_or_omitted" }];
    const graph = projectOrb(snapshot, pattern);
    expect(graph.nodes.find((node) => node.id === "station:inspect")?.count).toBe(0);
    expect(graph.nodes.some((node) => node.label === "Unknown subject")).toBe(true);
    expect(graph.nodes.some((node) => node.kind === "gap")).toBe(true);
    expect(orbEvidenceNodeId(snapshot.evidence[0]!, pattern)).toMatch(/^subject:dispatch:/);
  });
  it("requires exact pinned manifest identity before adding workflow edges", () => {
    const snapshot = fixtureRun();
    expect(matchesOrbPattern(snapshot, pattern)).toBe(true);
    expect(matchesOrbPattern(snapshot, { ...pattern, digest: "different" })).toBe(false);
    expect(projectOrb(snapshot, null).edges).toEqual([]);
  });
  it("unfolds exact Run/subject/occurrence/record membership without a causal edge", () => {
    const a = fixtureRun(), b = fixtureRun("run-b");
    const lenses = new Map([["run-a", { snapshot: a, pattern }], ["run-b", { snapshot: b, pattern }]]);
    const collapsed = projectOrbField([a.run, b.run], lenses, "runs");
    const unfolded = projectOrbField([a.run, b.run], lenses, "records");
    expect(collapsed.projection.nodes).toHaveLength(2);
    expect(collapsed.projection.nodes[0]!.members).toContain("run:run-a|record%3Arun-a-event-0");
    expect(unfolded.projection.identity).toBe(collapsed.projection.identity);
    expect(unfolded.projection.nodes.filter((node) => node.kind === "occurrence")).toHaveLength(2);
    expect(unfolded.projection.nodes.filter((node) => node.kind === "event")).toHaveLength(2);
    expect(new Set(unfolded.projection.nodes.map((node) => node.id)).size).toBe(unfolded.projection.nodes.length);
    expect(unfolded.projection.edges.every((edge) => ["permission", "contains"].includes(edge.relation))).toBe(true);
    expect([...unfolded.selections.values()].some((item) => item.runId === "run-b" && item.eventId === "run-b-event-0")).toBe(true);
  });
  it("deduplicates replayed immutable identities and keeps supplied sequence order", () => {
    const event = fixtureRun().evidence[0]!;
    expect(mergeOrbEvidence([event], [{ ...event, event_id: "second", seq: 1 }, event]).map((item) => item.event_id)).toEqual([event.event_id, "second"]);
  });

  it("merges exact gap intervals without sorting or mutating supplied pages", () => {
    const first = Object.freeze({ start_seq: 8, end_seq: 9, classification: "unknown_or_omitted" as const });
    const earlier = Object.freeze({ start_seq: 1, end_seq: 2, classification: "unknown_or_omitted" as const });
    const replacement = Object.freeze({ ...first });
    const overlapping = Object.freeze({ ...first, end_seq: 10 });
    const history = Object.freeze([first, earlier]);
    const next = Object.freeze([replacement, overlapping]);

    const merged = mergeOrbGaps(history, next);

    expect(merged).toEqual([replacement, earlier, overlapping]);
    expect(merged[0]).toBe(replacement);
    expect(history).toEqual([first, earlier]);
    expect(history[0]).toBe(first);
    expect(next).toEqual([replacement, overlapping]);
  });

  it.each(["runs", "stations", "occurrences", "records"] as const)("labels unloaded evidence at %s depth without changing Run identity or status", (level) => {
    const snapshot = fixtureRun();
    const field = projectOrbField([snapshot.run], new Map(), level);
    expect(field.projection.nodes).toHaveLength(1);
    expect(field.projection.nodes[0]).toMatchObject({
      id: "run:run-a", group: "run-a", state: "running",
      detail: "run-a · recorded: running · Evidence not loaded"
    });
    expect(field.projection.nodes[0]!.count).toBeUndefined();
    expect(field.selections.get("run:run-a")).toEqual({ runId: "run-a" });
  });

  it.each(["runs", "stations", "occurrences", "records"] as const)("preserves loaded coverage and supplied gaps at %s depth", (level) => {
    const snapshot = fixtureRun();
    const record = snapshot.evidence[0]!;
    snapshot.evidence = [{ ...record, seq: 2 }, { ...record, event_id: "later", seq: 5 }];
    snapshot.gaps = [
      { start_seq: 0, end_seq: 1, classification: "unknown_or_omitted" },
      { start_seq: 3, end_seq: 4, classification: "unknown_or_omitted" }
    ];
    Object.assign(snapshot, { ledger_head_seq: 99, page_end_seq: 5, next_after_seq: 5, has_more: true });
    snapshot.run.status = "done";
    const before = structuredClone(snapshot);
    const field = projectOrbField([{ ...snapshot.run, status: "running" }], new Map([["run-a", { snapshot, pattern }]]), level);
    expect(field.projection.nodes.find((node) => node.id === "run:run-a")).toMatchObject({
      id: "run:run-a", group: "run-a", state: "done", count: 2,
      detail: "run-a · recorded: done · 2 loaded records · 2 supplied gaps · More retained history exists outside this lens"
    });
    expect(field.selections.get("run:run-a")).toEqual({ runId: "run-a" });
    expect(snapshot).toEqual(before);
  });

  it.each(["runs", "stations", "occurrences", "records"] as const)("preserves supplied omissions without sequence gaps at %s depth", (level) => {
    const snapshot = fixtureRun();
    snapshot.known_omissions = ["Older delegated jobs omitted.", "Provider trace unavailable."];
    const field = projectOrbField([snapshot.run], new Map([["run-a", { snapshot, pattern }]]), level);
    expect(field.projection.nodes[0]!.detail).toBe(
      "run-a · recorded: running · 1 loaded record · 0 supplied gaps · Known omissions: Older delegated jobs omitted. Provider trace unavailable."
    );
    expect(field.projection.nodes[0]!.count).toBe(1);
  });

  it.each([0, 1])("describes %i loaded records without claiming a complete history", (count) => {
    const snapshot = fixtureRun();
    snapshot.evidence = count ? [{ ...snapshot.evidence[0]!, seq: 42 }] : [];
    snapshot.gaps = count ? [{ start_seq: 0, end_seq: 41, classification: "unknown_or_omitted" }] : [];
    Object.assign(snapshot, { ledger_head_seq: count ? 42 : -1, page_end_seq: count ? 42 : null });
    const field = projectOrbField([snapshot.run], new Map([["run-a", { snapshot, pattern }]]), "runs");
    expect(field.projection.nodes[0]!.detail).toBe(count
      ? "run-a · recorded: running · 1 loaded record · 1 supplied gap"
      : "run-a · recorded: running · 0 loaded records · 0 supplied gaps");
    expect(field.projection.nodes[0]!.count).toBe(count);
  });
});
