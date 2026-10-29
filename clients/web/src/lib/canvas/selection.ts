import { objectBounds } from "./engine";
import type { CanvasEdge, CanvasNode, Point, Scene } from "./types";

export const LASSO_POINT_LIMIT = 512;
const EPSILON = 1e-7;
const cross = (a: Point, b: Point, c: Point) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

function distanceSquared(point: Point, a: Point, b: Point): number {
  const dx = b.x - a.x, dy = b.y - a.y;
  const length = dx * dx + dy * dy;
  const t = length ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length)) : 0;
  return (point.x - a.x - t * dx) ** 2 + (point.y - a.y - t * dy) ** 2;
}

function onSegment(point: Point, a: Point, b: Point): boolean {
  return distanceSquared(point, a, b) <= EPSILON ** 2;
}

function segmentsMeet(a: Point, b: Point, c: Point, d: Point): boolean {
  const abC = cross(a, b, c), abD = cross(a, b, d), cdA = cross(c, d, a), cdB = cross(c, d, b);
  return ((abC > 0 && abD < 0 || abC < 0 && abD > 0) && (cdA > 0 && cdB < 0 || cdA < 0 && cdB > 0)) ||
    onSegment(c, a, b) || onSegment(d, a, b) || onSegment(a, c, d) || onSegment(b, c, d);
}

/** Even/odd fill, including the contour; the pointer need not finish at its start. */
function contains(polygon: readonly Point[], point: Point): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[j]!, b = polygon[i]!;
    if (onSegment(point, a, b)) return true;
    if ((a.y > point.y) !== (b.y > point.y) && point.x < a.x + (point.y - a.y) * (b.x - a.x) / (b.y - a.y)) inside = !inside;
  }
  return inside;
}

function segmentTouches(polygon: readonly Point[], a: Point, b: Point, radius: number): boolean {
  if (contains(polygon, a) || contains(polygon, b)) return true;
  for (let i = 0; i < polygon.length; i++) {
    const c = polygon[i]!, d = polygon[(i + 1) % polygon.length]!;
    if (segmentsMeet(a, b, c, d) || Math.min(distanceSquared(a, c, d), distanceSquared(b, c, d),
      distanceSquared(c, a, b), distanceSquared(d, a, b)) <= radius ** 2) return true;
  }
  return false;
}

function pathTouches(polygon: readonly Point[], points: readonly Point[], radius: number): boolean {
  if (points.length === 1) return segmentTouches(polygon, points[0]!, points[0]!, radius);
  for (let i = 1; i < points.length; i++) if (segmentTouches(polygon, points[i - 1]!, points[i]!, radius)) return true;
  return false;
}

function nodeOutline(node: CanvasNode): Point[] {
  const radius = node.kind === "person" ? Math.min(node.width, node.height) / 2 : node.kind === "note" ? 2 : 4;
  const centers = [{ x: node.x + node.width - radius, y: node.y + radius },
    { x: node.x + node.width - radius, y: node.y + node.height - radius },
    { x: node.x + radius, y: node.y + node.height - radius }, { x: node.x + radius, y: node.y + radius }];
  return centers.flatMap((center, corner) => Array.from({ length: 17 }, (_, step) => {
    const angle = (corner - 1) * Math.PI / 2 + step * Math.PI / 32;
    return { x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) };
  }));
}

function endpoint(node: CanvasNode, other: CanvasNode): Point {
  const dx = other.x + other.width / 2 - node.x - node.width / 2;
  const dy = other.y + other.height / 2 - node.y - node.height / 2;
  const scale = 1 / Math.max(Math.abs(dx) / (node.width / 2), Math.abs(dy) / (node.height / 2), 1);
  return { x: node.x + node.width / 2 + dx * scale, y: node.y + node.height / 2 + dy * scale };
}

function edgePoints(edge: CanvasEdge, nodes: Map<string, CanvasNode>): Point[] {
  const source = nodes.get(edge.source), target = nodes.get(edge.target);
  if (!source || !target) return [];
  if (source.id !== target.id) return [endpoint(source, target), endpoint(target, source)];
  const a = { x: source.x + source.width * .3, y: source.y }, b = { x: source.x - 35, y: source.y - 80 };
  const c = { x: source.x + source.width + 35, y: source.y - 80 }, d = { x: source.x + source.width * .7, y: source.y };
  return Array.from({ length: 33 }, (_, i) => {
    const t = i / 32, u = 1 - t;
    return { x: u ** 3 * a.x + 3 * u ** 2 * t * b.x + 3 * u * t ** 2 * c.x + t ** 3 * d.x,
      y: u ** 3 * a.y + 3 * u ** 2 * t * b.y + 3 * u * t ** 2 * c.y + t ** 3 * d.y };
  });
}

/** Presentation selection only. The polygon is never added to the board's retained ink. */
export function selectInLasso(scene: Scene, polygon: readonly Point[]): string[] {
  if (polygon.length < 3 || polygon.length > LASSO_POINT_LIMIT || polygon.some((p) => !Number.isFinite(p.x) || !Number.isFinite(p.y))) return [];
  const first = polygon[0]!, second = polygon.find((p) => !onSegment(p, first, first));
  if (!second || !polygon.some((p) => Math.abs(cross(first, second, p)) > EPSILON)) return [];
  const bounds = { x: Math.min(...polygon.map((p) => p.x)), y: Math.min(...polygon.map((p) => p.y)), width: 0, height: 0 };
  bounds.width = Math.max(...polygon.map((p) => p.x)) - bounds.x;
  bounds.height = Math.max(...polygon.map((p) => p.y)) - bounds.y;
  const near = (id: string) => {
    const box = objectBounds(scene, id);
    return box && box.x <= bounds.x + bounds.width && box.x + box.width >= bounds.x &&
      box.y <= bounds.y + bounds.height && box.y + box.height >= bounds.y;
  };
  const selected: string[] = [];
  for (const stroke of scene.strokes) {
    if (!stroke.archived && near(stroke.id) && pathTouches(polygon, stroke.points, stroke.width / 2)) selected.push(stroke.id);
  }
  for (const node of scene.nodes) {
    if (!near(node.id)) continue;
    const points = nodeOutline(node);
    if (pathTouches(polygon, [...points, points[0]!], .5) || polygon.some((p) => contains(points, p))) selected.push(node.id);
  }
  const nodes = new Map(scene.nodes.map((node) => [node.id, node]));
  for (const edge of scene.edges) if (near(edge.id) && pathTouches(polygon, edgePoints(edge, nodes), 1)) selected.push(edge.id);
  return selected;
}
