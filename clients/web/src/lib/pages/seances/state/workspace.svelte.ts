import { createContext } from "svelte";
import { SvelteMap } from "svelte/reactivity";
import type { BridgeTurnView } from "$lib/api/models";
import { sourceSignature, type MaterialKind, type SeanceMaterial } from "./material";

/** Shell lifetime only: no browser storage, Archive writes, or second chat store. */
export const materialLimit = 32;
export const materialCharacterLimit = 128_000;

export function createSeancesWorkspace(continueInBridge: (id: string) => void | Promise<void>) {
  const materials = new SvelteMap<string, readonly SeanceMaterial[]>();
  let sequence = 0;
  const all = () => [...materials.values()].flat();
  const characters = () => all().reduce((sum, item) => sum + item.source.content.length + item.note.length, 0);
  return {
    materials,
    continueInBridge,
    add(sessionId: string, source: BridgeTurnView) {
      const current = materials.get(sessionId) ?? [];
      if (current.some((item) => sourceSignature(item.source) === sourceSignature(source))) return "This quotation is already in Working material.";
      if (all().length >= materialLimit) return `Working material is limited to ${materialLimit} selections in this tab. Remove a selection first.`;
      if (characters() + source.content.length > materialCharacterLimit) return `Working material is limited to ${materialCharacterLimit.toLocaleString("en")} quotation and note characters in this tab. Nothing was added.`;
      materials.set(sessionId, [...current, {
        id: `selection-${++sequence}`, sessionId,
        source: { role: source.role, content: source.content, created_at: source.created_at, run_id: source.run_id, state: source.state },
        kind: "Selected material", note: ""
      }]);
      return null;
    },
    update(sessionId: string, id: string, change: { kind?: MaterialKind; note?: string }) {
      const item = materials.get(sessionId)?.find((item) => item.id === id);
      if (!item) return "This selection is unavailable.";
      if (change.note !== undefined && characters() - item.note.length + change.note.length > materialCharacterLimit) return `Working material is limited to ${materialCharacterLimit.toLocaleString("en")} quotation and note characters in this tab. The note was not changed.`;
      materials.set(sessionId, (materials.get(sessionId) ?? []).map((item) => item.id === id ? { ...item, ...change } : item));
      return null;
    },
    remove(sessionId: string, id: string) {
      const next = (materials.get(sessionId) ?? []).filter((item) => item.id !== id);
      if (next.length) materials.set(sessionId, next);
      else materials.delete(sessionId);
    },
    get needsUnloadWarning() { return materials.size > 0; }
  };
}
export type SeancesWorkspace = ReturnType<typeof createSeancesWorkspace>;
export const [getSeancesWorkspace, setSeancesWorkspace, hasSeancesWorkspace] = createContext<SeancesWorkspace>();
