import { describe, expect, it } from "vitest";
import type { NexusCovenRow, NexusSnapshot, TransitionPlan } from "$lib/api/models";
import { createNexusMap } from "./map";

function row(capability_key: string, animator_name = "animator-a"): NexusCovenRow {
  return { capability_key, animator_name, checked_at: null, dedicated: false, family: "chat", health: "unknown", is_active: false,
    model_id: "model-a", persistent_resident: false, reason: null, runtime: "local", state: "cold", warm: false };
}

function snapshot(): NexusSnapshot {
  return { snapshot_at: "2026-11-02T00:00:00Z", containment_reason: null,
    board: { covens: [["display-a", [row("chat:a"), row("embed:a")]], ["display-b", [row("chat:a"), row("chat:b", "animator-b")]]],
      portals: [row("chat:a")] },
    delegated_runtimes: [{ runtime_id: "animator-a", display_name: "Delegate", capacity_posture: "not_configured", coffin_profiles: [], delivery: "Designed",
      limitations: [], provider_gate: "not_required", registrant_id: "delegate", runnable: false, transport: "reference" }], transitions: [] };
}

const plan: TransitionPlan = { action_type: "HARD_SWAP", evict_coven_ids: ["animator-a"], launch_coven_ids: ["animator-b"], policy: "test", total_metabolic_cost: 1 };

describe("Nexus observation map", () => {
  it("deduplicates Animators across display groups and connects only reported managed ownership", () => {
    const map = createNexusMap(snapshot());
    const animators = map.objects.filter((object) => object.kind === "animator");
    expect(animators).toHaveLength(2);
    expect(animators.find((object) => object.animator === "animator-a")?.groups).toEqual(["display-a", "display-b"]);
    expect(map.edges).toHaveLength(3);
    for (const edge of map.edges) {
      const from = map.objects.find((object) => object.id === edge.from);
      const to = map.objects.find((object) => object.id === edge.to);
      expect(from?.kind).toBe("animator");
      expect(to?.kind).toBe("capability");
      if (from?.kind === "animator" && to?.kind === "capability") {
        expect(to.scope).toBe("managed");
        expect(to.row.animator_name).toBe(from.animator);
      }
    }
  });

  it("keeps scoped identities collision-proof and plan impact on exact managed Animator names", () => {
    const map = createNexusMap(snapshot(), plan, "chat:a");
    expect(new Set(map.objects.map((object) => object.id)).size).toBe(map.objects.length);
    expect(map.objects.filter((object) => object.kind === "capability" && object.label === "chat:a")).toHaveLength(2);
    for (const object of map.objects) {
      if (object.kind === "delegated" || (object.kind === "capability" && object.scope === "portal")) expect(object.impact).toBeNull();
      else if (object.kind === "animator") expect(object.impact).toBe(object.animator === "animator-a" ? "evict" : "launch");
      else expect(object.impact).toBe(object.row.animator_name === "animator-a" ? "evict" : "launch");
    }
    const groupNamePlan = { ...plan, evict_coven_ids: ["display-a"], launch_coven_ids: ["chat:a"] };
    expect(createNexusMap(snapshot(), groupNamePlan).objects.every((object) => object.impact === null)).toBe(true);
  });

  it("keeps identity, geometry and edges stable through input order and nonbinding preview changes", () => {
    const source = snapshot();
    const before = structuredClone(source);
    const reversed = { ...source, board: { covens: [...source.board.covens].reverse().map(([name, rows]): [string, NexusCovenRow[]] => [name, [...rows].reverse()]), portals: [...source.board.portals].reverse() } };
    const first = createNexusMap(source);
    const second = createNexusMap(reversed, plan, "chat:b");
    expect(second.objects.map((object) => object.id)).toEqual(first.objects.map((object) => object.id));
    expect(second.nodes).toEqual(first.nodes);
    expect(second.edges).toEqual(first.edges);
    expect(source).toEqual(before);
  });

  it("preserves unknown observations without inventing ownership or capacity", () => {
    const source = snapshot();
    source.board.covens = [["unbound", [row("chat:unknown", "")]]];
    const map = createNexusMap(source);
    expect(map.objects.some((object) => object.kind === "animator")).toBe(false);
    expect(map.edges).toEqual([]);
    expect(map.objects.find((object) => object.kind === "capability" && object.scope === "managed")).toMatchObject({ row: { animator_name: "", checked_at: null, health: "unknown" } });
    const empty = createNexusMap({ ...source, board: { covens: [], portals: [] }, delegated_runtimes: [] });
    expect(empty.objects).toEqual([]);
    expect(empty.sections[0]?.note).toBe("No managed capabilities reported");
    expect(empty.bounds.height).toBeGreaterThan(0);
  });

  it("marks overlapping preview actions explicitly without adding relations", () => {
    const map = createNexusMap(snapshot(), { ...plan, launch_coven_ids: ["animator-a", "missing"] });
    const animator = map.objects.find((object) => object.kind === "animator" && object.animator === "animator-a");
    expect(animator?.impact).toBe("both");
    expect(map.objects.some((object) => object.kind === "animator" && object.animator === "missing")).toBe(false);
    expect(map.edges).toEqual(createNexusMap(snapshot()).edges);
  });
});
