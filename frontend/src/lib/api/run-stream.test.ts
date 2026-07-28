import { describe, expect, it } from "vitest";

import type { RunEventEnvelope } from "./models";
import { initialRunEventCursor, reduceRunEventCursor } from "./run-stream";

function event(seq: number, kind: RunEventEnvelope["kind"] = "token"): RunEventEnvelope {
  return {
    schema_version: 1,
    run_id: "run-a",
    event_id: `00000000-0000-4000-8000-${seq.toString().padStart(12, "0")}`,
    seq,
    kind,
    occurred_at: "2026-07-28T00:00:00Z",
    payload: {}
  };
}

describe("run event cursor", () => {
  it("admits contiguous events and ignores replay duplicates", () => {
    const first = reduceRunEventCursor(initialRunEventCursor(), event(0));
    const duplicate = reduceRunEventCursor(first.cursor, event(0));
    const next = reduceRunEventCursor(duplicate.cursor, event(1));

    expect(first).toMatchObject({ deliver: true, refetch: false });
    expect(duplicate).toMatchObject({ deliver: false, refetch: false });
    expect(next).toMatchObject({ deliver: true, refetch: false });
  });

  it("continues after a cursor restored from the Bridge snapshot", () => {
    const restored = initialRunEventCursor(17);
    const replay = reduceRunEventCursor(restored, event(17));
    const continuation = reduceRunEventCursor(replay.cursor, event(18));

    expect(replay).toMatchObject({ deliver: false, refetch: false });
    expect(continuation).toMatchObject({ deliver: true, refetch: false });
  });

  it("gates a numeric gap without advancing or delivering it", () => {
    const cursor = { lastSeq: 3 };
    const result = reduceRunEventCursor({ lastSeq: 3 }, event(7));

    expect(result).toEqual({
      cursor,
      deliver: false,
      refetch: true
    });
  });

  it("accepts an explicit resync boundary and resumes from a fetched cursor", () => {
    const reset = reduceRunEventCursor({ lastSeq: 99 }, event(41, "resync"));
    const replay = reduceRunEventCursor(initialRunEventCursor(43), event(44));

    expect(reset).toEqual({
      cursor: { lastSeq: 41 },
      deliver: false,
      refetch: true
    });
    expect(replay).toMatchObject({ deliver: true, refetch: false });
  });
});
