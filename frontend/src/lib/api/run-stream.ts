import type { RunEventEnvelope } from "./models";

export type RunEventCursor = {
  lastSeq: number;
};

export type RunEventDisposition = {
  cursor: RunEventCursor;
  deliver: boolean;
  refetch: boolean;
};

export function initialRunEventCursor(lastSeq = -1): RunEventCursor {
  return { lastSeq };
}

/**
 * Admit only contiguous events, ignore replay duplicates, and gate every loss.
 *
 * An explicit `resync` marker establishes the server's replacement boundary.
 * A numeric gap is never applied speculatively: both cases require an
 * authoritative run snapshot before later events can be reduced.
 */
export function reduceRunEventCursor(
  cursor: RunEventCursor,
  event: RunEventEnvelope
): RunEventDisposition {
  if (event.kind === "resync") {
    return {
      cursor: { lastSeq: event.seq },
      deliver: false,
      refetch: true
    };
  }
  if (event.seq <= cursor.lastSeq) {
    return { cursor, deliver: false, refetch: false };
  }
  if (event.seq !== cursor.lastSeq + 1) {
    return { cursor, deliver: false, refetch: true };
  }
  return {
    cursor: { lastSeq: event.seq },
    deliver: true,
    refetch: false
  };
}
