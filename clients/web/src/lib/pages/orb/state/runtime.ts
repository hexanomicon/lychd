import { getOrbRuntime } from "$lib/api/orb-runtime";
import type { OrbRuntimeSnapshot } from "$lib/api/models";
import { advanceRuntimeHighWater, receivedRuntimeEvents } from "./runtime-projection";

export interface RuntimeReadState {
  readonly snapshot: OrbRuntimeSnapshot | null;
  readonly received: ReadonlySet<string>;
  readonly loading: boolean;
  readonly error: string;
  readonly stale: boolean;
}
export const emptyRuntimeState: RuntimeReadState = { snapshot: null, received: new Set(), loading: true, error: "", stale: false };

/** Owns polling lifetime only; a request or animation never proves execution. */
export function observeRuntime(onchange: (state: RuntimeReadState) => void) {
  let state = emptyRuntimeState, stopped = false, version = 0, continuous = false, blocked = false;
  let highWater: ReadonlyMap<string, number> = new Map();
  let controller: AbortController | undefined;
  let deadline: ReturnType<typeof setTimeout> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined, pulse: ReturnType<typeof setTimeout> | undefined;
  const emit = (next: RuntimeReadState) => { state = next; onchange(state); };
  async function refresh(automatic = false) {
    if (stopped || (automatic && (blocked || document.visibilityState !== "visible"))) return;
    clearTimeout(timer); clearTimeout(pulse); clearTimeout(deadline);
    if (!automatic) { blocked = false; continuous = false; }
    const current = ++version;
    controller?.abort();
    const requestController = new AbortController(); controller = requestController;
    deadline = setTimeout(() => requestController.abort(), 10000);
    emit({ ...state, received: new Set(), loading: true });
    try {
      const next = await getOrbRuntime(controller.signal);
      if (stopped || current !== version) return;
      const received = receivedRuntimeEvents(state.snapshot, next, continuous, highWater);
      highWater = advanceRuntimeHighWater(highWater, next);
      continuous = true;
      emit({ snapshot: next, received, loading: false, error: "", stale: false });
      if (received.size) pulse = setTimeout(() => { if (!stopped) emit({ ...state, received: new Set() }); }, 1800);
    } catch (cause) {
      if (stopped || current !== version) return;
      continuous = false;
      blocked = typeof cause === "object" && cause !== null && "status" in cause && (cause.status === 401 || cause.status === 403);
      if (blocked) highWater = new Map();
      emit({ ...state, snapshot: blocked ? null : state.snapshot, received: new Set(), loading: false, stale: !blocked && state.snapshot !== null,
        error: blocked ? "Runtime observation access refused. Protected observations were cleared." : "Runtime observations could not be refreshed. The last received window may be stale." });
    } finally {
      if (current === version) clearTimeout(deadline);
      if (!stopped && current === version && !blocked) timer = setTimeout(() => void refresh(true), 3000);
    }
  }
  function visibility() {
    continuous = false;
    clearTimeout(timer); clearTimeout(pulse); clearTimeout(deadline);
    if (document.visibilityState === "visible") void refresh(true);
    else {
      version++; controller?.abort();
      emit({ ...state, received: new Set(), loading: false });
    }
  }
  void refresh();
  return { refresh: () => void refresh(), visibility, clear() {
    highWater = new Map();
    blocked = true; continuous = false; version++; controller?.abort(); clearTimeout(timer); clearTimeout(pulse); clearTimeout(deadline);
    emit({ snapshot: null, received: new Set(), loading: false, stale: false, error: "Runtime observation access refused. Protected observations were cleared." });
  }, stop() { highWater = new Map(); stopped = true; version++; controller?.abort(); clearTimeout(timer); clearTimeout(pulse); clearTimeout(deadline); } };
}
