import type { BridgeTurnView } from "$lib/api/models";
import { navigationId } from "$lib/navigation/instruments";

export const materialKinds = ["Topic", "Open question", "Selected material"] as const;
export type MaterialKind = typeof materialKinds[number];
export type SeanceMaterial = Readonly<{
  id: string;
  sessionId: string;
  source: BridgeTurnView;
  kind: MaterialKind;
  note: string;
}>;

/** A quotation match within a supplied read, never a durable turn identity. */
export function sourceSignature(turn: BridgeTurnView): string {
  return JSON.stringify([turn.role, turn.created_at, turn.run_id ?? null, turn.content]);
}

export function seanceHref(sessionId: string): `/seances/${string}` {
  return `/seances/${encodeURIComponent(sessionId)}`;
}

export function sourceHref(material: SeanceMaterial): string {
  const run = navigationId(material.source.run_id);
  return run ? `/bridge/${encodeURIComponent(material.sessionId)}?run=${encodeURIComponent(run)}`
    : seanceHref(material.sessionId);
}

export function materialMarkdown(title: string, materials: readonly SeanceMaterial[]): string {
  return [`# ${title.replaceAll("\n", " ")} — working material`,
    "Manually selected quotations and notes. Not admitted to memory.",
    ...materials.map((item) => [
      `## ${item.kind}`,
      `Source: ${sourceHref(item)}`,
      `Session: ${item.sessionId} · ${item.source.role} · ${item.source.created_at}`,
      ...(item.source.run_id ? [`Run: ${item.source.run_id}`] : []),
      item.source.content.split("\n").map((line) => `> ${line}`).join("\n"),
      ...(item.note ? [`Note: ${item.note}`] : [])
    ].join("\n\n"))
  ].join("\n\n") + "\n";
}
