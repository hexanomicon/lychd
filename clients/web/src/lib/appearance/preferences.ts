/** Browser-local decorative identity only; no runtime, evidence or status meaning. */
export const appearanceStorageKey = "lychd.altar.appearance.v1";
export const accentOptions = [
  { id: "violet", label: "Violet", color: "#b8a1d0" },
  { id: "iris", label: "Iris", color: "#aebcf0" },
  { id: "neutral", label: "Neutral", color: "#ccd1d9" }
] as const;
export type AccentId = typeof accentOptions[number]["id"];
export const defaultAccent: AccentId = "violet";

export function isAccentId(value: unknown): value is AccentId {
  return accentOptions.some((option) => option.id === value);
}

export function parseAppearance(raw: string | null): AccentId {
  if (!raw || raw.length > 128) return defaultAccent;
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object" || Array.isArray(value)) return defaultAccent;
    const record = value as Record<string, unknown>;
    if (Object.keys(record).length !== 2 || record.version !== 1 || !isAccentId(record.accent)) return defaultAccent;
    return record.accent;
  } catch { return defaultAccent; }
}

export function serializeAppearance(accent: AccentId): string {
  return JSON.stringify({ version: 1, accent });
}
