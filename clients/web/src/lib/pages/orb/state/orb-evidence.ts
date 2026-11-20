import type { OrbRunSnapshot } from "$lib/api/models";

type Evidence = OrbRunSnapshot["evidence"][number];

export function subjectIdentity(event: Evidence): string {
  return JSON.stringify([event.kind, event.subject_key]);
}

export function attemptIdentity(event: Evidence): string {
  return JSON.stringify(event.occurrence_id ?? null);
}

export function loadedSubjects(evidence: readonly Evidence[]) {
  type Subject = { kind: string; subject: string | null; records: Evidence[] };
  const groups = new Map<string, Subject>();
  for (const event of evidence) {
    const key = subjectIdentity(event);
    const group: Subject = groups.get(key) ?? { kind: event.kind, subject: event.subject_key ?? null, records: [] };
    group.records.push(event);
    groups.set(key, group);
  }
  return [...groups].map(([key, group]) => {
    const attempts = new Map<string, { key: string; label: string; count: number }>();
    if (group.kind === "node") {
      for (const event of group.records) {
        const key = attemptIdentity(event);
        const attempt = attempts.get(key) ?? {
          key,
          label: event.occurrence_id == null ? "No recorded attempt" : `Station attempt ${event.occurrence_id}`,
          count: 0
        };
        attempt.count++;
        attempts.set(key, attempt);
      }
    }
    const kind = group.kind === "node" ? "Station observations" : group.kind === "dispatch" ? "Capability dispatches" : group.kind;
    return { key, ...group, label: `${kind} · ${group.subject ?? "No recorded subject"}`, attempts: [...attempts.values()] };
  });
}

export function conflictingStationAttempts(evidence: readonly Evidence[]): string[] {
  const stations = new Map<string, Set<string | null>>();
  for (const event of evidence) {
    if (event.kind !== "node" || event.occurrence_id == null) continue;
    const subjects = stations.get(event.occurrence_id) ?? new Set<string | null>();
    subjects.add(event.subject_key ?? null);
    stations.set(event.occurrence_id, subjects);
  }
  return [...stations].filter(([, subjects]) => subjects.size > 1).map(([id]) => id);
}

/** Each completed station attempt contributes only its own recorded interval. */
export function stationDurations(evidence: readonly Evidence[]) {
  const groups = new Map<string, Evidence[]>();
  const conflicts = new Set(conflictingStationAttempts(evidence));
  for (const item of evidence) {
    if (item.kind !== "node" || !item.subject_key || !item.occurrence_id || conflicts.has(item.occurrence_id)) continue;
    const group = groups.get(item.occurrence_id) ?? [];
    group.push(item);
    groups.set(item.occurrence_id, group);
  }
  const totals = new Map<string, number>();
  for (const records of groups.values()) {
    const starts = records.filter(item => item.phase === "entered");
    const ends = records.filter(item => item.phase === "settled" || item.phase === "failed");
    if (starts.length !== 1 || ends.length !== 1) continue;
    const start = starts[0]!, end = ends[0]!;
    const elapsed = Date.parse(end.occurred_at) - Date.parse(start.occurred_at);
    if (end.seq <= start.seq || !Number.isFinite(elapsed) || elapsed < 0) continue;
    totals.set(start.subject_key!, (totals.get(start.subject_key!) ?? 0) + elapsed);
  }
  return totals;
}

export function durationLabel(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)}ms` : `${+(ms / 1000).toFixed(2)}s`;
}
