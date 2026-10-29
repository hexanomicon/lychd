import { describe, expect, it } from "vitest";
import { fixtureRun, pattern } from "./__fixtures__/snapshot";
import { appendFieldFrame, fieldFrameAt, pruneFieldRun, trimFieldFrames, type FieldFrame } from "./field-history";
import type { OrbFieldLens } from "$lib/graph/orb";

function capture(snapshot = fixtureRun(), at = 1000, frames: readonly FieldFrame[] = [], seconds = 90, cap = 300) {
  return appendFieldFrame(frames, [snapshot.run], new Map([[snapshot.run.run_id, { snapshot, pattern }]]), at, seconds, cap);
}

describe("tab field observation history", () => {
  it("copies input containers and holds prior immutable projections while new receipts arrive", () => {
    const snapshot = fixtureRun();
    const run = snapshot.run;
    const runs = [run];
    const lenses = new Map<string, OrbFieldLens>([[run.run_id, { snapshot, pattern }]]);
    const frames = appendFieldFrame([], runs, lenses, 1000, 90);
    const paused = frames[0]!;
    runs.length = 0; lenses.clear();
    const changed = { ...snapshot, run: { ...run, status: "done" } };
    const next = capture(changed, 2000, frames);
    expect(paused.runs).toEqual([run]);
    expect(paused.lenses.get(run.run_id)?.snapshot).toBe(snapshot);
    expect(next.at(-1)?.runs[0]?.status).toBe("done");
    expect(paused.runs[0]?.status).toBe("running");
    expect(next.map((frame) => frame.id)).toEqual([1, 2]);
  });

  it("ignores receipt metadata and transport fields but captures corrections at the same evidence identity", () => {
    const snapshot = fixtureRun();
    const frames = capture(snapshot);
    const refreshed = { snapshot: { ...snapshot, snapshot_at: "2026-10-29T01:00:00Z" }, pattern, connection: "closed" };
    expect(appendFieldFrame(frames, [{ ...snapshot.run }], new Map([[snapshot.run.run_id, refreshed]]), 2000, 90)).toBe(frames);
    expect(appendFieldFrame(frames, [snapshot.run], new Map([[snapshot.run.run_id, { ...refreshed, trimmed: true }]]), 2001, 90)).toHaveLength(2);
    const correction = { ...snapshot, evidence: snapshot.evidence.map((item) => ({ ...item, summary: "Corrected served summary" })) };
    const next = capture(correction, 2100, frames);
    expect(next).toHaveLength(2);
    expect(next[1]?.changedRunIds).toEqual([snapshot.run.run_id]);
    expect(next[0]?.lenses.get(snapshot.run.run_id)?.snapshot.evidence[0]?.summary).toBe("Inspect entered");
  });

  it("captures gaps, declared manifest and lens closure independently of evidence count", () => {
    const snapshot = fixtureRun();
    let frames = capture(snapshot);
    const withGap = { ...snapshot, gaps: [{ start_seq: 1, end_seq: 2, classification: "unknown_or_omitted" as const }] };
    frames = capture(withGap, 2000, frames);
    const changedPattern = { ...pattern, nodes: pattern.nodes.map((node) => ({ ...node, label: `${node.label} changed` })) };
    frames = appendFieldFrame(frames, [snapshot.run], new Map([[snapshot.run.run_id, { snapshot: withGap, pattern: changedPattern }]]), 3000, 90);
    frames = appendFieldFrame(frames, [snapshot.run], new Map(), 4000, 90);
    expect(frames).toHaveLength(4);
    expect(frames.every((frame) => frame.changedRunIds.includes(snapshot.run.run_id))).toBe(true);
    expect(frames.at(-1)?.lenses.size).toBe(0);
  });

  it("orders late producer evidence by local receipt and keeps receipt time monotonic across clock rollback", () => {
    const snapshot = fixtureRun();
    const before = capture(snapshot, 5000);
    const late = { ...snapshot, evidence: [...snapshot.evidence, { ...snapshot.evidence[0]!, event_id: "late", seq: 1, occurred_at: "2000-01-01T00:00:00Z" }] };
    const frames = capture(late, 1000, before);
    expect(frames.map((frame) => frame.observedAt)).toEqual([5000, 5001]);
    expect(fieldFrameAt(frames, 5000)?.id).toBe(1);
    expect(fieldFrameAt(frames, -1)?.id).toBe(1);
    expect(fieldFrameAt(frames, 9000)?.id).toBe(2);
    expect(fieldFrameAt([], 0)).toBeUndefined();
  });

  it("bounds frame count and time, preserves pinned references, and never resurrects discarded frames", () => {
    let frames: readonly FieldFrame[] = [];
    const snapshot = fixtureRun();
    let pinned: FieldFrame | undefined;
    for (let i = 0; i < 305; i++) {
      frames = capture({ ...snapshot, run: { ...snapshot.run, status: String(i) } }, i * 1000, frames, 3600);
      if (!i) pinned = frames[0];
    }
    expect(frames).toHaveLength(300);
    expect(frames[0]?.id).toBe(6);
    expect(pinned?.id).toBe(1);
    expect(pinned?.runs[0]?.status).toBe("0");
    const narrow = trimFieldFrames(frames, 30);
    expect(narrow).toHaveLength(31);
    expect(trimFieldFrames(narrow, 3600)).toBe(narrow);
    const next = capture({ ...snapshot, run: { ...snapshot.run, status: "next" } }, 400000, narrow, 30);
    expect(next).toHaveLength(1);
    expect(next[0]?.id).toBe(306);
  });

  it("scrubs closed lens evidence without mutating captures or removing catalogue identity", () => {
    const snapshot = fixtureRun();
    const original = capture(snapshot);
    const scrubbed = pruneFieldRun(original, snapshot.run.run_id);
    expect(original[0]?.lenses.size).toBe(1);
    expect(scrubbed[0]?.lenses.size).toBe(0);
    expect(scrubbed[0]?.runs[0]).toBe(snapshot.run);
    expect(scrubbed[0]?.changedRunIds).toEqual([]);
    expect(pruneFieldRun(scrubbed, snapshot.run.run_id)).toBe(scrubbed);
    expect(appendFieldFrame([], [], new Map(), 0, 90)).toEqual([]);
  });
});
