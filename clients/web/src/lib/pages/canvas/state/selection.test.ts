import { describe, expect, it } from "vitest";
import { blankDocument } from "./engine";
import { LASSO_POINT_LIMIT, selectInLasso } from "./selection";
import type { CanvasNode, Point, Stroke } from "./types";

const box: Point[] = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
function stroke(points: Point[], width = 2): Stroke {
  return { id: crypto.randomUUID(), points, width, color: "#ffffff", archived: false };
}
function node(x: number, y: number, width = 40, height = 40): CanvasNode {
  return { id: crypto.randomUUID(), x, y, width, height, label: "Node", kind: "box", pinned: false, source_stroke_ids: [], artwork: null };
}

describe("freehand lasso selection", () => {
  it("selects real ink through a concave contour rather than its bounding rectangle", () => {
    const scene = blankDocument().scene;
    const inside = stroke([{ x: 10, y: 10 }, { x: 20, y: 20 }]);
    const outside = stroke([{ x: 70, y: 70 }, { x: 80, y: 80 }]);
    const archived = { ...inside, id: crypto.randomUUID(), archived: true };
    scene.strokes = [inside, outside, archived];
    const before = structuredClone(scene);
    const l = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 30 }, { x: 30, y: 30 }, { x: 30, y: 100 }, { x: 0, y: 100 }];
    expect(selectInLasso(scene, l)).toEqual([inside.id]);
    expect(scene).toEqual(before);
  });

  it("closes open contours and catches crossings and painted caps with endpoints outside", () => {
    const scene = blankDocument().scene;
    const crossing = stroke([{ x: -20, y: 50 }, { x: 120, y: 50 }]);
    const cap = stroke([{ x: -1, y: 20 }], 4);
    const untouched = stroke([{ x: -5, y: 40 }, { x: -5, y: 60 }], 2);
    scene.strokes = [crossing, cap, untouched];
    expect(selectInLasso(scene, box)).toEqual([crossing.id, cap.id]);
  });

  it("selects a filled node containing the loop and a connector crossing the loop", () => {
    const scene = blankDocument().scene;
    const covering = node(-50, -50, 200, 200), left = node(-200, 25), right = node(200, 25);
    const edge = { id: crypto.randomUUID(), source: left.id, target: right.id, label: "link", source_stroke_ids: [] };
    scene.nodes = [covering, left, right]; scene.edges = [edge];
    expect(selectInLasso(scene, box)).toEqual([covering.id, edge.id]);
    // This sits inside the union of endpoint bounds, away from the actual connector.
    expect(selectInLasso(scene, [{ x: -140, y: 26 }, { x: -125, y: 26 }, { x: -125, y: 35 }, { x: -140, y: 35 }])).toEqual([]);
  });

  it("selects the visible self-loop above its node without selecting its empty control box", () => {
    const scene = blankDocument().scene, n = node(0, 100, 160, 80);
    const edge = { id: crypto.randomUUID(), source: n.id, target: n.id, label: "loop", source_stroke_ids: [] };
    scene.nodes = [n]; scene.edges = [edge];
    expect(selectInLasso(scene, [{ x: 70, y: 35 }, { x: 90, y: 35 }, { x: 90, y: 45 }, { x: 70, y: 45 }])).toEqual([edge.id]);
    expect(selectInLasso(scene, [{ x: -30, y: 25 }, { x: -20, y: 25 }, { x: -20, y: 35 }, { x: -30, y: 35 }])).toEqual([]);
  });

  it("refuses degenerate, nonfinite and unbounded contours", () => {
    const scene = blankDocument().scene; scene.nodes = [node(0, 0)];
    for (const invalid of [[], box.slice(0, 2), [{ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 20, y: 20 }],
      [...box, { x: NaN, y: 10 }], Array.from({ length: LASSO_POINT_LIMIT + 1 }, (_, i) => box[i % box.length]!)]) {
      expect(selectInLasso(scene, invalid)).toEqual([]);
    }
  });

  it("excludes a person's empty rounded corners while selecting the visible silhouette", () => {
    const scene = blankDocument().scene, person = { ...node(0, 0, 100, 100), kind: "person" as const };
    scene.nodes = [person];
    expect(selectInLasso(scene, [{ x: 0, y: 0 }, { x: 8, y: 0 }, { x: 8, y: 8 }, { x: 0, y: 8 }])).toEqual([]);
    expect(selectInLasso(scene, [{ x: 40, y: 40 }, { x: 60, y: 40 }, { x: 60, y: 60 }, { x: 40, y: 60 }])).toEqual([person.id]);
  });
});
