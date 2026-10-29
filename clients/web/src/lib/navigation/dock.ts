/** Bounded, layout-only preferences. Never store conversation or authority state here. */
export const bridgeDockStorageKey = "lychd.bridge-dock.layout.v1";
export const dockMinimumWidth = 320;
export const dockMaximumWidth = 720;
export interface DockLayout { width: number; side: "left" | "right"; open: boolean }
export const defaultDockLayout: DockLayout = { width: 440, side: "left", open: true };
export function boundedDockWidth(width: number): number {
  return Math.round(Math.min(dockMaximumWidth, Math.max(dockMinimumWidth, width)));
}
export function parseDockLayout(raw: string | null): DockLayout {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (typeof value !== "object" || value === null) return { ...defaultDockLayout };
    const layout = value as Record<string, unknown>;
    return {
      width: typeof layout.width === "number" && Number.isFinite(layout.width)
        ? boundedDockWidth(layout.width) : defaultDockLayout.width,
      side: layout.side === "left" || layout.side === "right" ? layout.side : defaultDockLayout.side,
      open: typeof layout.open === "boolean" ? layout.open : defaultDockLayout.open
    };
  } catch { return { ...defaultDockLayout }; }
}
