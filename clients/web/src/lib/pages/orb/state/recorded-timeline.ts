import type { OrbRunSnapshot } from "$lib/api/models";
import type { OrbFieldLens } from "./orb";
import { conflictingStationAttempts } from "./orb-evidence";

type Evidence = OrbRunSnapshot["evidence"][number];
type Run = OrbRunSnapshot["run"];

export function recordedTimeline(runs: readonly Run[], lenses: ReadonlyMap<string, OrbFieldLens>) {
  const times = new Set<number>();
  const rows = runs.map(run => {
    const lens = lenses.get(run.run_id);
    const evidence = lens?.snapshot.evidence ?? [];
    const events = evidence.flatMap(record => {
      const at = Date.parse(record.occurred_at);
      if (!Number.isFinite(at)) return [];
      times.add(at);
      return [{ record, at }];
    });
    const conflicts = new Set(conflictingStationAttempts(evidence));
    const attempts = new Map<string, Evidence[]>();
    for (const record of evidence) {
      if (record.kind !== "node" || !record.occurrence_id || !record.subject_key || conflicts.has(record.occurrence_id)) continue;
      const group = attempts.get(record.occurrence_id) ?? [];
      group.push(record);
      attempts.set(record.occurrence_id, group);
    }
    const paired = new Set<string>();
    const bars = [...attempts.values()].flatMap(records => {
      const starts = records.filter(record => record.phase === "entered");
      const ends = records.filter(record => record.phase === "settled" || record.phase === "failed");
      if (starts.length !== 1 || ends.length !== 1) return [];
      const start = starts[0]!, end = ends[0]!;
      const from = Date.parse(start.occurred_at), to = Date.parse(end.occurred_at);
      if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from || end.seq <= start.seq) return [];
      paired.add(start.event_id);
      paired.add(end.event_id);
      return [{ record: end, from, to, label: lens?.pattern?.nodes.find(node => node.key === start.subject_key)?.label ?? start.subject_key! }];
    }).sort((a, b) => a.from - b.from);
    const laneEnds: number[] = [];
    const spans = bars.map(bar => {
      let lane = laneEnds.findIndex(end => end <= bar.from);
      if (lane < 0) lane = laneEnds.length;
      laneEnds[lane] = bar.to;
      return { ...bar, lane };
    });
    const marks = events.filter(event => !paired.has(event.record.event_id));
    return { run, spans, marks, lanes: Math.max(1, laneEnds.length) };
  });
  return { rows, times: [...times].sort((a, b) => a - b) };
}

export function atRecordedTime(lenses: ReadonlyMap<string, OrbFieldLens>, time: number) {
  const visible = new Map<string, OrbFieldLens>();
  for (const [id, lens] of lenses) {
    const evidence = lens.snapshot.evidence.filter(event => Date.parse(event.occurred_at) <= time);
    const through = Math.max(-1, ...evidence.map(event => event.seq));
    const gaps = lens.snapshot.gaps.filter(gap => gap.end_seq <= through);
    visible.set(id, { ...lens, snapshot: { ...lens.snapshot, evidence, gaps } });
  }
  return visible;
}
