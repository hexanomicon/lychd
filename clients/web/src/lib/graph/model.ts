import type { LoomView, OrbRunSnapshot } from "$lib/api/models";

/** Immutable semantic input shared by the Loom and Orb renderer adapters.
 * Coordinates and renderer drafts never become Pattern or Run authority.
 */
export interface GraphNode {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
  readonly kind: string;
  readonly entry?: boolean;
  readonly state?: string;
  readonly count?: number;
  readonly group?: string;
  /** Exact known members of a folded presentation group, never an inferred cluster. */
  readonly members?: readonly string[];
  readonly attention?: "latest" | "cursor" | "received";
  /** Resolved build-owned asset URL, never a source-supplied URL. */
  readonly icon?: string;
  readonly accent?: "rune" | "frost" | "heat" | "lich" | "primary";
}

export interface GraphEdge {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  readonly label: string;
  readonly relation: "permission" | "order" | "contains" | "selection" | "declared" | "activity";
  readonly attention?: "received";
}

export interface GraphProjection {
  readonly identity: string;
  readonly nodes: readonly GraphNode[];
  readonly edges: readonly GraphEdge[];
}

/** Whether a Run snapshot exactly matches this Pattern id, revision and digest. */
export function matchesOrbPattern(snapshot: OrbRunSnapshot, pattern: LoomView): boolean {
  return snapshot.pattern.exact && snapshot.pattern.digest !== null &&
    snapshot.pattern.pattern_id === pattern.pattern_id && snapshot.pattern.revision === pattern.revision &&
    snapshot.pattern.digest === pattern.digest;
}
