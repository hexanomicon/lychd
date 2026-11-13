/** Closed English presentation vocabulary; no Run or service operations. */
export type OrbPresentationCommand =
  | { readonly kind: 'camera'; readonly action: 'zoom-in' | 'zoom-out' | 'fit' }
  | { readonly kind: 'pause' | 'live' }
  | { readonly kind: 'seek'; readonly seconds: number };

export const orbPresentationExamples = Object.freeze([
  'zoom in', 'zoom out', 'fit graph', 'pause', 'go live',
  'go back 10 seconds', 'go forward 10 seconds'
]);

export function parseOrbPresentationCommand(text: string): OrbPresentationCommand | null {
  const input = text.trim().replace(/[.!?]$/u, "").trimEnd().toLowerCase();
  if (input === 'zoom in') return { kind: 'camera', action: 'zoom-in' };
  if (input === 'zoom out') return { kind: 'camera', action: 'zoom-out' };
  if (input === 'fit graph') return { kind: 'camera', action: 'fit' };
  if (input === 'pause') return { kind: 'pause' };
  if (input === 'go live') return { kind: 'live' };
  const seek = /^go (back|forward) ([1-9]\d{0,3}) seconds$/.exec(input);
  if (!seek) return null;
  const seconds = Number(seek[2]);
  return seconds <= 3600 ? { kind: 'seek', seconds: seek[1] === 'back' ? -seconds : seconds } : null;
}

/** Chooses an actual retained receipt, never clamps an unavailable requested time. */
export function seekObservationFrame<T extends { readonly id: number; readonly observedAt: number }>(
  frames: readonly T[], cursorId: number | null, seconds: number
): T | undefined {
  if (!Number.isInteger(seconds) || Math.abs(seconds) < 1 || Math.abs(seconds) > 3600) return;
  const first = frames[0], latest = frames.at(-1);
  const cursor = cursorId === null ? latest : frames.find(frame => frame.id === cursorId);
  if (!first || !latest || !cursor) return;
  const target = cursor.observedAt + seconds * 1000;
  if (target < first.observedAt || target > latest.observedAt) return;
  return frames.reduce((nearest, frame) =>
    Math.abs(frame.observedAt - target) < Math.abs(nearest.observedAt - target) ? frame : nearest, first);
}
