import { SvelteMap } from "svelte/reactivity";

export const bridgeWorkspaceKey = Symbol("Bridge workspace");

/** Original text and retry identity stay fixed until admission is resolved. */
export type PendingOffering = Readonly<{
  text: string;
  requestId: string;
  uncertain: boolean;
  sending: boolean;
  error: string;
}>;

/**
 * Root-layout context, keyed by exact session, that outlives instrument mounts.
 * An unresolved envelope cannot be replaced by a later draft or middleware refusal;
 * late responses must settle it even after Bridge unmounts. Entries are replaced
 * as values, rather than mutating fields inside a SvelteMap value.
 *
 * This is open-document recovery, not persistence across reload or browser exit.
 * Run lifecycle and admission remain server-owned. See the Bridge operating guide
 * and ADR 15's browser lifetime and request-identity sections.
 */
export function createBridgeWorkspace() {
  const drafts = new SvelteMap<string, string>();
  const pending = new SvelteMap<string, PendingOffering>();
  const refused = new SvelteMap<string, ReadonlyArray<{ requestId: string; text: string; error: string }>>();
  // Local response generations fence reads overtaken by admission; not Run cursors.
  const settlements = new SvelteMap<string, number>();
  return {
    drafts,
    pending,
    settlements,
    refused,
    setDraft(sessionId: string, text: string) {
      if (text) drafts.set(sessionId, text);
      else drafts.delete(sessionId);
    },
    get needsUnloadWarning() { return drafts.size > 0 || pending.size > 0 || refused.size > 0; }
  };
}

export type BridgeWorkspace = ReturnType<typeof createBridgeWorkspace>;
