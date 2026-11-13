import type { OrbRunSnapshot } from "$lib/api/models";

type Evidence = OrbRunSnapshot["evidence"][number];
const accents = ["rune", "frost", "heat", "lich", "primary"] as const;
export type AnimatorAccent = typeof accents[number];

/** Stable presentation color; identity remains the supplied name, never the color. */
export function animatorAccent(name: string): AnimatorAccent {
  let hash = 0;
  for (const letter of name) hash = (Math.imul(hash, 31) + letter.codePointAt(0)!) >>> 0;
  return accents[hash % accents.length]!;
}

/** A loaded-record lens, not a reconstructed historical Run or readiness snapshot. */
export function evidenceAt(snapshot: OrbRunSnapshot, cursor: number | null): Pick<OrbRunSnapshot, "evidence" | "gaps"> {
  if (cursor === null) return { evidence: snapshot.evidence, gaps: snapshot.gaps };
  return {
    evidence: snapshot.evidence.filter((record) => record.seq <= cursor),
    gaps: snapshot.gaps.filter((gap) => gap.start_seq <= cursor)
      .map((gap) => ({ ...gap, end_seq: Math.min(gap.end_seq, cursor) }))
  };
}

export interface AnimatorObservation {
  readonly name: string;
  readonly accent: AnimatorAccent;
  readonly record: Evidence;
  readonly count: number;
  readonly atCursor: boolean;
}

/** Only dispatch records supply selection; no present-day Nexus data enters replay. */
export function animatorObservations(records: readonly Evidence[], cursor: number | null): AnimatorObservation[] {
  const rows = records.filter((record) => cursor === null || record.seq <= cursor).toSorted((a, b) => a.seq - b.seq);
  const head = cursor ?? rows.at(-1)?.seq;
  const byName = new Map<string, AnimatorObservation>();
  for (const record of rows) {
    if (record.kind !== "dispatch" || !record.animator_name) continue;
    byName.set(record.animator_name, {
      name: record.animator_name, accent: animatorAccent(record.animator_name), record,
      count: (byName.get(record.animator_name)?.count ?? 0) + 1,
      atCursor: record.seq === head
    });
  }
  return [...byName.values()];
}
