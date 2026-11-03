import { navigationId } from "$lib/navigation/instruments";

/** Layout preferences contain exact session identities only, never conversation content. */
export const bridgePinsStorageKey = "lychd.bridge-pins.v1";
export const bridgePinsLimit = 32;

export function parsePinnedConversations(raw: string | null): readonly string[] {
  if (raw === null || raw.length > 8192) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value) || value.length > bridgePinsLimit) return [];
    const pins = new Set<string>();
    for (const id of value) {
      if (typeof id !== "string" || navigationId(id) !== id) return [];
      pins.add(id);
    }
    return [...pins];
  } catch { return []; }
}

export function togglePinnedConversation(current: readonly string[], id: string): readonly string[] {
  if (navigationId(id) !== id) return current;
  if (current.includes(id)) return current.filter((pin) => pin !== id);
  return current.length < bridgePinsLimit ? [...current, id] : current;
}
