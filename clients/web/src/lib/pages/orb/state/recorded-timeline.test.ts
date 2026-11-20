import { expect, it } from "vitest";
import { fixtureRun, pattern } from "./__fixtures__/snapshot";
import { atRecordedTime, recordedTimeline } from "./recorded-timeline";

it("lays overlapping attempts on separate lanes and keeps unpaired observations as records", () => {
  const snapshot = fixtureRun();
  const start = snapshot.evidence[0]!;
  function record(occurrence: string, seq: number, seconds: number, phase: "entered" | "settled") {
    return { ...start, event_id: String(seq), seq, occurrence_id: occurrence, phase,
      occurred_at: new Date(Date.parse(start.occurred_at) + seconds * 1000).toISOString() };
  }
  snapshot.evidence = [
    record("outer", 0, 0, "entered"), record("inner", 1, 2, "entered"),
    record("inner", 2, 3, "settled"), record("outer", 3, 4, "settled"),
    record("incomplete", 4, 5, "entered"), record("instant", 5, 5, "entered"),
    record("instant", 6, 5, "settled"),
  ];
  const lenses = new Map([[snapshot.run.run_id, { snapshot, pattern }]]);
  const { rows, times } = recordedTimeline([snapshot.run], lenses);
  expect(rows[0]!.spans.map(span => [span.lane, span.to - span.from])).toEqual([[0, 4000], [1, 1000]]);
  expect(rows[0]!.marks.map(mark => mark.record.seq)).toEqual([4, 5, 6]);
  expect(times).toHaveLength(5);
  const visible = atRecordedTime(lenses, times[1]!);
  expect(visible.get(snapshot.run.run_id)!.snapshot.evidence.map(event => event.seq)).toEqual([0, 1]);
  expect(snapshot.evidence).toHaveLength(7);
});
