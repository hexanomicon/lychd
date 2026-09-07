import type { AtlasReference } from "$lib/api/models";

/** A prefilled link draft, not saved Project membership or model Context. */
export type AtlasLinkIntent = {
  kind: AtlasReference["kind"];
  targetId: string;
};

/** Parse an explicit navigation hint without changing the activity identity. */
export function parseAtlasLink(
  kind?: string | null,
  id?: string | null
): AtlasLinkIntent | null {
  if (kind !== "session" && kind !== "run") return null;
  if (typeof id !== "string" || id.length === 0 || id.length > 128 || id.trim() !== id) {
    return null;
  }
  return { kind, targetId: id };
}

/** Build a local Atlas destination; linking remains an explicit action on that page. */
export function atlasHref(projectId?: string, intent?: AtlasLinkIntent | null): string {
  const path = projectId ? `/atlas/${encodeURIComponent(projectId)}` : "/atlas";
  const validIntent = parseAtlasLink(intent?.kind, intent?.targetId);
  if (!validIntent) return path;
  return `${path}?link_kind=${encodeURIComponent(validIntent.kind)}&link_id=${encodeURIComponent(validIntent.targetId)}`;
}
