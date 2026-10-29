import type { OrbRunSnapshot } from "$lib/api/models";
import type { OrbFieldLens } from "$lib/graph/orb";

type Run = OrbRunSnapshot["run"];
export const FIELD_HISTORY_WINDOWS = [30, 90, 300, 3600] as const;
export const FIELD_HISTORY_MAX_FRAMES = 300;

/** One served field projection received in this tab, not a producer-time event. */
export interface FieldFrame {
  readonly id: number;
  readonly observedAt: number;
  readonly runs: readonly Run[];
  readonly lenses: ReadonlyMap<string, OrbFieldLens>;
  readonly changedRunIds: readonly string[];
}

interface RunKeys { readonly run: string | null; readonly lens: string | null }
interface FieldKeys { readonly order: string; readonly runs: ReadonlyMap<string, RunKeys> }
const frameKeys = new WeakMap<FieldFrame, FieldKeys>();
const lensKeys = new WeakMap<OrbFieldLens, string>();
const runKeys = new WeakMap<Run, string>();

function stableKey(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => item !== null && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item).sort(([left], [right]) => left.localeCompare(right))) : item);
}

function runKey(run: Run): string {
  let key = runKeys.get(run);
  if (key === undefined) { key = stableKey(run); runKeys.set(run, key); }
  return key;
}

function lensKey(lens: OrbFieldLens | undefined): string | null {
  if (!lens) return null;
  let key = lensKeys.get(lens);
  if (key === undefined) {
    // DTOs contain the served safe projection. Transport state and receipt metadata
    // are deliberately absent; corrected or late evidence still changes this key.
    const { snapshot_at: _receipt, ...snapshot } = lens.snapshot;
    key = stableKey([snapshot, lens.pattern, "trimmed" in lens ? lens.trimmed ?? false : false]);
    lensKeys.set(lens, key);
  }
  return key;
}

function keysFor(runs: readonly Run[], lenses: ReadonlyMap<string, OrbFieldLens>): FieldKeys {
  const keys = new Map<string, RunKeys>();
  for (const run of runs) keys.set(run.run_id, { run: runKey(run), lens: lensKey(lenses.get(run.run_id)) });
  for (const [id, lens] of lenses) if (!keys.has(id)) keys.set(id, { run: null, lens: lensKey(lens) });
  return { order: JSON.stringify(runs.map((run) => run.run_id)), runs: keys };
}

function keysOf(frame: FieldFrame): FieldKeys {
  let keys = frameKeys.get(frame);
  if (!keys) { keys = keysFor(frame.runs, frame.lenses); frameKeys.set(frame, keys); }
  return keys;
}

/** Retention is measured from the newest actual receipt, never an invented clock tick.
 * The newest capture remains the baseline. Widening a window cannot restore evicted captures.
 */
export function trimFieldFrames(
  frames: readonly FieldFrame[], windowSeconds: number, maxFrames = FIELD_HISTORY_MAX_FRAMES
): readonly FieldFrame[] {
  const latest = frames.at(-1);
  if (!latest) return frames;
  const seconds = Number.isFinite(windowSeconds) ? Math.max(0, windowSeconds) : 90;
  const cap = Number.isFinite(maxFrames) ? Math.max(1, Math.min(FIELD_HISTORY_MAX_FRAMES, Math.floor(maxFrames))) : FIELD_HISTORY_MAX_FRAMES;
  const cutoff = latest.observedAt - seconds * 1000;
  const start = Math.max(frames.findIndex((frame) => frame.observedAt >= cutoff), frames.length - cap);
  return start > 0 ? Object.freeze(frames.slice(start)) : frames;
}

/** Inputs must be immutable snapshots replaced as units by the owner. Containers are
 * copied here; retaining a selected frame separately keeps it frozen after eviction.
 */
export function appendFieldFrame(
  frames: readonly FieldFrame[], runs: readonly Run[], lenses: ReadonlyMap<string, OrbFieldLens>,
  observedAt: number, windowSeconds: number, maxFrames = FIELD_HISTORY_MAX_FRAMES
): readonly FieldFrame[] {
  const previous = frames.at(-1);
  if (!previous && !runs.length && !lenses.size) return frames;
  const keys = keysFor(runs, lenses);
  const before = previous ? keysOf(previous) : undefined;
  const changed = [...new Set([...(before?.runs.keys() ?? []), ...keys.runs.keys()])]
    .filter((id) => {
      const previousKeys = before?.runs.get(id), nextKeys = keys.runs.get(id);
      return previousKeys?.run !== nextKeys?.run || previousKeys?.lens !== nextKeys?.lens;
    });
  if (previous && !changed.length && before?.order === keys.order) return frames;
  const receipt = Number.isFinite(observedAt) ? observedAt : previous?.observedAt ?? 0;
  const frame: FieldFrame = Object.freeze({
    id: (previous?.id ?? 0) + 1,
    observedAt: previous ? Math.max(receipt, previous.observedAt + 1) : receipt,
    runs: Object.freeze([...runs]), lenses: new Map(lenses), changedRunIds: Object.freeze(changed)
  });
  frameKeys.set(frame, keys);
  return trimFieldFrames(Object.freeze([...frames, frame]), windowSeconds, maxFrames);
}

/** Closest retained receipt at or before a seek time; endpoints stay bounded. */
export function fieldFrameAt(frames: readonly FieldFrame[], observedAt: number): FieldFrame | undefined {
  if (!frames.length) return undefined;
  let low = 0, high = frames.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (frames[middle]!.observedAt <= observedAt) low = middle;
    else high = middle - 1;
  }
  return frames[low];
}

/** Authority refusal or explicit removal clears evidence from all retained tab captures.
 * Catalogue summaries remain; callers must scrub any separately pinned frame too.
 */
export function pruneFieldRun(frames: readonly FieldFrame[], runId: string): readonly FieldFrame[] {
  let changed = false;
  const next = frames.map((frame) => {
    if (!frame.lenses.has(runId) && !frame.changedRunIds.includes(runId)) return frame;
    changed = true;
    const lenses = new Map(frame.lenses); lenses.delete(runId);
    return Object.freeze({ ...frame, lenses, changedRunIds: Object.freeze(frame.changedRunIds.filter((id) => id !== runId)) });
  });
  return changed ? Object.freeze(next) : frames;
}
