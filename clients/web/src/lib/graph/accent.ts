/**
 * Graph and animator projections name a semantic accent; the active theme owns its colour.
 * The explicit role map keeps projection vocabulary independent of CSS token names, so a
 * token rename or a new theme can never silently drop a node or edge colour.
 */
export type GraphAccent = "rune" | "frost" | "heat" | "lich" | "primary";

const ACCENT_ROLE: Readonly<Record<GraphAccent, string>> = {
  rune: "--color-interactive",
  primary: "--color-interactive",
  frost: "--color-status-ready",
  lich: "--color-status-active",
  heat: "--color-status-threshold",
};

export function accentColor(accent: GraphAccent = "rune"): string {
  return `var(${ACCENT_ROLE[accent]})`;
}
