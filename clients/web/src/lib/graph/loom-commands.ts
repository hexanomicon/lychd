/** Closed read-only Loom grammar. No fuzzy resolution, execution, or workflow editing. */
export type LoomCommand =
  | { kind: "station"; action: "inspect" | "focus"; key: string }
  | { kind: "level"; level: "pattern" | "stations" }
  | { kind: "unsupported"; summary: string };

function normalizedLabel(value: string): string {
  return value.trim().replace(/\s+/gu, " ").toLowerCase();
}

export function parseLoomCommand(
  text: string,
  stations: readonly { readonly key: string; readonly label: string }[]
): LoomCommand {
  const input = text.trim().replace(/[.!?]$/u, "").trimEnd();
  const level = /^show\s+(pattern|stations)$/i.exec(input);
  if (level) return { kind: "level", level: level[1]!.toLowerCase() as "pattern" | "stations" };
  const station = /^(inspect|focus)\s+(.+)$/i.exec(input);
  if (station) {
    const target = station[2]!.trim();
    const exact = stations.filter((node) => node.key === target);
    const matches = exact.length ? exact : stations.filter((node) => normalizedLabel(node.label) === normalizedLabel(target));
    if (matches.length !== 1) return {
      kind: "unsupported",
      summary: matches.length ? "That station label is ambiguous. Use an exact station key." : "No exact station key or unambiguous label matches. Use the declared station outline."
    };
    return { kind: "station", action: station[1]!.toLowerCase() as "inspect" | "focus", key: matches[0]!.key };
  }
  if (/^(edit|create|add|delete|remove|connect|disconnect|publish|execute|run|start|save)\b/i.test(input)) {
    return { kind: "unsupported", summary: "Loom is read-only. Workflow editing, publication, connections, deletion and execution are unavailable." };
  }
  return { kind: "unsupported", summary: "Use deterministic English commands: inspect STATION, focus STATION, show pattern, or show stations." };
}
