import { describe, expect, it } from "vitest";
import { CANVAS_COMMAND_HELP, CANVAS_COMMAND_LIMITS, CanvasCommandError, isCanvasCommandCurrent, planCanvasCommand } from "./commands";
import { commit, objectBounds, redo, undo, validateScene } from "./engine";
import type { Bounds, CanvasNode, Document, Scene, Stroke } from "./types";

const id = (n: number) => `00000000-0000-0000-0000-${n.toString().padStart(12, "0")}`;
const node = (n: number, label: string, x = 20, y = 20): CanvasNode => ({ id: id(n), label, x, y, width: 160, height: 80, kind: "box", pinned: false, artwork: null, source_stroke_ids: [] });
const stroke = (n: number, archived = false): Stroke => ({ id: id(n), archived, points: [{ x: 10, y: 10 }, { x: 200, y: 10 }, { x: 200, y: 200 }], width: 3, color: "#abcdef" });
function blank(): Scene { return { format: "lychd.canvas/1", id: id(900), revision: 1, title: "Command test", nodes: [], edges: [], strokes: [] }; }
function populated(): Scene {
  return { ...blank(), nodes: [node(1, "Vessel"), node(2, "Postgres", 500), node(3, "Outside", 900)], strokes: [stroke(5), stroke(6, true)], edges: [{ id: id(4), source: id(2), target: id(3), label: "Existing", source_stroke_ids: [id(5)] }] };
}
function freeze<T>(value: T): T {
  if (value && typeof value === "object") { Object.freeze(value); Object.values(value).forEach(freeze); }
  return value;
}
const disjoint = (a: Bounds, b: Bounds) => a.x + a.width <= b.x || b.x + b.width <= a.x || a.y + a.height <= b.y || b.y + b.height <= a.y;

describe("bounded local Canvas commands", () => {
  it("creates two editable native nodes and one directed connection from a blank board", () => {
    const source = freeze(blank());
    const plan = planCanvasCommand(source, [], "add node Vessel; add database Postgres; connect Vessel to Postgres");
    expect(plan.scene.nodes.map((n) => [n.label, n.kind])).toEqual([["Vessel", "box"], ["Postgres", "database"]]);
    expect(plan.scene.edges).toEqual([{ id: plan.createdIds[2], source: plan.scene.nodes[0]!.id, target: plan.scene.nodes[1]!.id, label: "", source_stroke_ids: [] }]);
    expect(plan.scene.nodes.every((n) => n.artwork === null && !n.pinned && n.source_stroke_ids.length === 0)).toBe(true);
    expect(disjoint(plan.scene.nodes[0]!, plan.scene.nodes[1]!)).toBe(true);
    expect(plan.scene.revision).toBe(2); expect(plan.baseRevision).toBe(1); expect(plan.baseSceneId).toBe(source.id);
    expect(plan.selectionIds).toEqual([]); expect(plan.commandCount).toBe(3); expect(plan.createdIds).toHaveLength(3);
    expect(plan.scene).toEqual(validateScene(plan.scene)); expect(source.nodes).toEqual([]);
    expect(plan).toEqual(planCanvasCommand(source, [], "add node Vessel; add database Postgres; connect Vessel to Postgres"));
    expect(CANVAS_COMMAND_HELP).toContain("add node Vessel then add database Postgres then connect Vessel to Postgres");
  });

  it("plans inertly and fits the existing one-commit Undo/Redo document lifecycle", () => {
    const initial: Document = { format: "lychd.canvas.document/1", scene: populated(), past: [], future: [] };
    const before = structuredClone(initial);
    const plan = planCanvasCommand(freeze(initial.scene), [], "add note Review");
    expect(initial).toEqual(before);
    const applied = commit(initial, plan.scene);
    expect(applied.past).toHaveLength(1);
    const undone = undo(applied);
    expect({ ...undone.scene, revision: before.scene.revision }).toEqual(before.scene);
    expect({ ...redo(undone).scene, revision: plan.scene.revision }).toEqual(plan.scene);
  });

  it("preserves every preexisting object and places new nodes away from nodes, edge bounds and visible ink", () => {
    const source = freeze(populated());
    const plan = planCanvasCommand(source, [], "add node Added; add service Worker");
    expect(plan.scene.nodes.slice(0, source.nodes.length)).toEqual(source.nodes);
    expect(plan.scene.edges).toEqual(source.edges); expect(plan.scene.strokes).toEqual(source.strokes);
    const obstacleIds = [...source.nodes, ...source.edges, ...source.strokes.filter((s) => !s.archived)].map((o) => o.id);
    for (const added of plan.scene.nodes.slice(source.nodes.length)) for (const obstacle of obstacleIds) expect(disjoint(added, objectBounds(source, obstacle)!)).toBe(true);
    expect(plan.updatedIds).toEqual([]);
  });

  it("supports quoted labels without interpreting command words inside the label", () => {
    const plan = planCanvasCommand(blank(), [], 'ADD service "API gateway"\nadd note "to; add node pretend"; connect "api   gateway" to "to; add node pretend"');
    expect(plan.scene.nodes.map((n) => n.label)).toEqual(["API gateway", "to; add node pretend"]);
    expect(plan.scene.edges).toHaveLength(1);
    const composed = { ...blank(), nodes: [node(1, "Café"), node(2, "Target")] };
    expect(planCanvasCommand(composed, [], 'connect "CAFÉ" to target').scene.edges).toHaveLength(1);
    expect(planCanvasCommand(blank(), [], 'add note "Say \\"hello\\""').scene.nodes[0]!.label).toBe('Say "hello"');
  });

  it("supports spoken then and sentence separators, preserving .NET and quoted delimiter text", () => {
    const spoken = planCanvasCommand(blank(), [], "add node Vessel then add database Postgres then connect Vessel to Postgres");
    const typed = planCanvasCommand(blank(), [], "add node Vessel; add database Postgres; connect Vessel to Postgres");
    expect(spoken).toEqual(typed);
    expect(planCanvasCommand(blank(), [], "Add node Vessel. Add database Postgres. Connect Vessel to Postgres.")).toEqual(typed);
    expect(planCanvasCommand(blank(), [], 'add node "API gateway".').scene.nodes[0]?.label).toBe("API gateway");
    const sentences = planCanvasCommand(blank(), [], 'add service .NET API. add database Data store. connect .NET API to Data store');
    expect(sentences.scene.nodes.map((n) => n.label)).toEqual([".NET API", "Data store"]);
    expect(sentences.scene.edges).toHaveLength(1);
    const quoted = planCanvasCommand(blank(), [], 'add node "A. add B then connect C". add node Destination then connect "A. add B then connect C" to Destination');
    expect(quoted.scene.nodes.map((n) => n.label)).toEqual(["A. add B then connect C", "Destination"]);
    expect(quoted.commandCount).toBe(3);
    expect(() => planCanvasCommand(blank(), [], "add node A then launch something")).toThrow(/Ambiguous/);
    expect(() => planCanvasCommand(blank(), [], "add node A then add node B then connect A to Missing")).toThrow(/No node named/);
    expect(() => planCanvasCommand(blank(), [], Array.from({ length: 17 }, (_, n) => `add node N${n}`).join(" then "))).toThrow(/16/);
  });

  it("refuses ambiguous and missing names, duplicate names, duplicate links and self-links", () => {
    const duplicate = { ...populated(), nodes: [...populated().nodes, node(7, " vessel ")] };
    expect(() => planCanvasCommand(duplicate, [], "connect Vessel to Postgres")).toThrow(/Ambiguous/);
    expect(() => planCanvasCommand(populated(), [], "connect Missing to Postgres")).toThrow(/No node named/);
    expect(() => planCanvasCommand(populated(), [], "add database POSTGRES")).toThrow(/already exists/);
    expect(() => planCanvasCommand(populated(), [id(1)], "rename selected to Postgres")).toThrow(/already exists/);
    expect(() => planCanvasCommand(populated(), [], "connect Postgres to Outside")).toThrow(/already exists/);
    expect(() => planCanvasCommand(populated(), [], "connect Vessel to Vessel")).toThrow(/self-connections/);
    expect(() => planCanvasCommand(blank(), [], "add node Café; add node CAFÉ")).toThrow(/already exists/);
  });

  it("never guesses endpoint direction from multiple selected nodes", () => {
    expect(() => planCanvasCommand(populated(), [id(1), id(2)], "connect selected to Outside")).toThrow(/exactly one/);
    expect(() => planCanvasCommand(populated(), [id(1), id(2)], "connect selected")).toThrow(/exactly one unquoted to/);
    const plan = planCanvasCommand(populated(), [id(1)], "connect selected to Postgres");
    expect(plan.scene.edges.at(-1)?.source).toBe(id(1)); expect(plan.scene.edges.at(-1)?.target).toBe(id(2));
    expect(plan.scene.nodes).toEqual(populated().nodes);
  });

  it("renames and moves only captured native nodes while retaining all raw ink and edge records", () => {
    const source = freeze(populated());
    const plan = planCanvasCommand(source, [id(1)], 'rename selected to "New Vessel"; move selected by 40, -20; move selected right 80');
    expect(plan.scene.nodes[0]).toEqual({ ...source.nodes[0], label: "New Vessel", x: 140, y: 0 });
    expect(plan.scene.nodes.slice(1)).toEqual(source.nodes.slice(1));
    expect(plan.scene.strokes).toEqual(source.strokes); expect(plan.scene.edges).toEqual(source.edges);
    expect(plan.updatedIds).toEqual([id(1)]);
    expect(plan.selectionIds).toEqual([id(1)]);
    expect(() => planCanvasCommand(source, [id(1), id(5)], "move selected right 10")).toThrow(/native nodes only/);
    expect(() => planCanvasCommand(source, [id(4)], "move selected right 10")).toThrow(/native nodes only/);
  });

  it("arranges selected nodes with existing engine semantics, preserving pins, unselected nodes and ink", () => {
    const source = populated();
    source.nodes = [{ ...node(1, "Pinned", 0, 0), pinned: true, width: 480 }, node(2, "Movable", 0, 0), node(3, "Outside", 900, 200)];
    const plan = planCanvasCommand(freeze(source), [id(1), id(2)], "arrange selected");
    expect(plan.scene.nodes[0]).toEqual(source.nodes[0]); expect(plan.scene.nodes[2]).toEqual(source.nodes[2]);
    expect(plan.scene.edges).toEqual(source.edges); expect(plan.scene.strokes).toEqual(source.strokes);
    expect(disjoint(plan.scene.nodes[0]!, plan.scene.nodes[1]!)).toBe(true);
    expect(plan.updatedIds).toEqual([id(2)]);
    expect(plan).toEqual(planCanvasCommand(source, [id(2), id(1)], "arrange selected"));
    expect(() => planCanvasCommand(source, [id(1)], "move selected right 40")).toThrow(/Unpin/);
  });

  it("rejects duplicate, missing, archived, excessive and absent selections", () => {
    for (const ids of [[id(1), id(1)], [id(999)], [id(6)], Array.from({ length: 129 }, (_, n) => id(n))]) expect(() => planCanvasCommand(populated(), ids, "add note Valid")).toThrow();
    for (const text of ["rename selected to Name", "move selected by 2, 3", "arrange selected", "connect selected to Postgres"]) expect(() => planCanvasCommand(populated(), [], text)).toThrow(/Select/);
  });

  it("fails a multi-command plan atomically when a later syntax or semantic command fails", () => {
    const source = freeze(populated()), before = JSON.stringify(source);
    for (const command of ["add node New; connect New to Absent", "rename selected to Changed; launch workflow", "move selected right 10; rename selected to Postgres", "add node New; add node new"]) {
      expect(() => planCanvasCommand(source, [id(1)], command)).toThrow();
      expect(JSON.stringify(source)).toBe(before);
    }
  });

  it("refuses unsupported natural language explicitly without a chat or interpretation fallback", () => {
    for (const text of ["make me a useful diagram", "add node A and add node B", "delete everything", "connect Vessel and Postgres", "arrange all", 'add note "unterminated', 'add note "A"B', 'add note "bad\\nlabel"', "add node API to gateway"]) expect(() => planCanvasCommand(populated(), [], text)).toThrow(CanvasCommandError);
    for (const text of ["", " ; \n ", "x".repeat(CANVAS_COMMAND_LIMITS.text + 1), Array.from({ length: 17 }, (_, n) => `add node N${n}`).join(";")]) expect(() => planCanvasCommand(blank(), [], text)).toThrow(CanvasCommandError);
    const boundary = Array.from({ length: 16 }, (_, n) => `add node N${n}`).join(";");
    expect(planCanvasCommand(blank(), [], boundary).scene.nodes).toHaveLength(16);
  });

  it("enforces finite movement, world, object, revision, label and placement-search bounds", () => {
    for (const text of ["move selected by Infinity, 1", "move selected by NaN, 1", "move selected by 10001, 0", "move selected left -5"]) expect(() => planCanvasCommand(populated(), [id(1)], text)).toThrow();
    expect(() => planCanvasCommand({ ...blank(), nodes: [node(1, "Edge", 99999, 99999)] }, [id(1)], "move selected right 2")).toThrow();
    expect(() => planCanvasCommand(blank(), [], "add node A", { origin: { x: Infinity, y: 0 } })).toThrow(/origin/);
    expect(() => planCanvasCommand(blank(), [], "add node A", { origin: { x: 100001, y: 0 } })).toThrow(/origin/);
    expect(() => planCanvasCommand({ ...blank(), revision: Number.MAX_SAFE_INTEGER }, [], "add node A")).toThrow(/revision limit/);
    expect(() => planCanvasCommand(blank(), [], `add node ${"x".repeat(241)}`)).toThrow(/label/);
    const full = { ...blank(), nodes: Array.from({ length: 128 }, (_, n) => node(n, `N${n}`)) };
    expect(() => planCanvasCommand(full, [], "add node Extra")).toThrow(/128/);
    const edges = { ...populated(), edges: Array.from({ length: 256 }, (_, n) => ({ id: id(n + 1000), source: id(2), target: id(3), label: "", source_stroke_ids: [] })) };
    expect(() => planCanvasCommand(edges, [], "connect Vessel to Postgres")).toThrow(/256/);
    const blocked = { ...blank(), strokes: [{ ...stroke(1), points: [{ x: -100000, y: -100000 }, { x: 100000, y: 100000 }] }] };
    expect(() => planCanvasCommand(blocked, [], "add node A")).toThrow(/No clear placement/);
    const boundary = planCanvasCommand(blank(), [], "add node A", { origin: { x: 100000, y: 100000 } });
    expect(boundary.scene.nodes[0]!.x + boundary.scene.nodes[0]!.width).toBeLessThanOrEqual(100000);
  });

  it("validates injected IDs and uses an explicit origin without affecting input", () => {
    let sequence = 100;
    const plan = planCanvasCommand(blank(), [], "add node A; add node B; connect A to B", { origin: { x: 1500, y: 800 }, makeId: () => id(sequence++) });
    expect(plan.createdIds).toEqual([id(100), id(101), id(102)]);
    expect(plan.scene.nodes[0]).toMatchObject({ x: 1500, y: 800 });
    expect(() => planCanvasCommand(populated(), [], "add node Added", { makeId: () => id(1) })).toThrow(/fresh canonical/);
    expect(() => planCanvasCommand(blank(), [], "add node Added", { makeId: () => "bad-id" })).toThrow(/fresh canonical/);
    expect(() => planCanvasCommand(blank(), [], "add node A; add node B", { makeId: () => id(100) })).toThrow(/fresh canonical/);
    expect(() => planCanvasCommand(blank(), [], "add node Added", { makeId: () => blank().id })).toThrow(/fresh canonical/);
  });

  it("binds previews to exact scene content, scene identity, revision and unordered selection identities", () => {
    const source = populated(), ids = [id(1), id(2)];
    const plan = planCanvasCommand(source, ids, "move selected down 10");
    expect(isCanvasCommandCurrent(plan, source, [id(2), id(1)])).toBe(true);
    expect(isCanvasCommandCurrent(plan, source, [])).toBe(false);
    expect(isCanvasCommandCurrent(plan, source, [id(1), id(1)])).toBe(false);
    expect(isCanvasCommandCurrent(plan, { ...source, revision: 2 }, ids)).toBe(false);
    expect(isCanvasCommandCurrent(plan, { ...source, id: id(901) }, ids)).toBe(false);
    expect(isCanvasCommandCurrent(plan, { ...source, title: "Changed without revision" }, ids)).toBe(false);
    const originalIds = [id(1)];
    const captured = planCanvasCommand(source, originalIds, "move selected right 5");
    originalIds.push(id(2));
    expect(captured.selectionIds).toEqual([id(1)]);
    const creation = planCanvasCommand(blank(), [], "add node First");
    expect(isCanvasCommandCurrent(creation, blank(), [])).toBe(true);
  });

  it("does not create empty review revisions for a no-op", () => {
    expect(() => planCanvasCommand(populated(), [id(1)], "move selected by 0, 0")).toThrow(/no change/);
    expect(() => planCanvasCommand(populated(), [id(1)], "rename selected to Vessel")).toThrow(/no change/);
  });
});
