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
