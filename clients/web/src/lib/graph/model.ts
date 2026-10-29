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
  readonly attention?: "latest" | "cursor";
  readonly accent?: "rune" | "frost" | "heat" | "lich" | "primary";
}

export interface GraphEdge {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  readonly label: string;
  readonly relation: "permission" | "order" | "contains" | "selection";
}

export interface GraphProjection {
  readonly identity: string;
  readonly nodes: readonly GraphNode[];
  readonly edges: readonly GraphEdge[];
}
