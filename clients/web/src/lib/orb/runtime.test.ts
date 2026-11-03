import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { runtimeSnapshot, runtimeEvent } from "./__fixtures__/runtime";
vi.mock("$lib/api/orb-runtime", () => ({ getOrbRuntime: vi.fn() }));
import { getOrbRuntime } from "$lib/api/orb-runtime";
import { observeRuntime, type RuntimeReadState } from "./runtime";

beforeEach(() => { vi.useFakeTimers(); vi.resetAllMocks(); Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" }); });
afterEach(() => vi.useRealTimers());

it("does not flash snapshot history, duplicate polls, refresh or reconnection", async () => {
  const states: RuntimeReadState[] = [];
  vi.mocked(getOrbRuntime).mockResolvedValue(runtimeSnapshot());
  const reader = observeRuntime(state => states.push(state));
  await vi.advanceTimersByTimeAsync(0);
  expect(states.at(-1)?.received.size).toBe(0);
  vi.mocked(getOrbRuntime).mockResolvedValue(runtimeSnapshot([runtimeEvent(), runtimeEvent(2)]));
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.received.size).toBe(1);
  await vi.advanceTimersByTimeAsync(1800);
  expect(states.at(-1)?.received.size).toBe(0);
  await vi.advanceTimersByTimeAsync(1200);
  expect(states.at(-1)?.received.size).toBe(0);
  vi.mocked(getOrbRuntime).mockRejectedValueOnce(new Error("offline"));
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.stale).toBe(true);
  vi.mocked(getOrbRuntime).mockResolvedValue(runtimeSnapshot([runtimeEvent(3)]));
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.received.size).toBe(0);
  reader.refresh(); await vi.advanceTimersByTimeAsync(0);
  expect(states.at(-1)?.received.size).toBe(0);
  reader.stop();
});

it("clears protected data on refusal and aborts all work at teardown", async () => {
  const states: RuntimeReadState[] = [];
  vi.mocked(getOrbRuntime).mockResolvedValue(runtimeSnapshot());
  const reader = observeRuntime(state => states.push(state));
  await vi.advanceTimersByTimeAsync(0);
  vi.mocked(getOrbRuntime).mockRejectedValue(Object.assign(new Error("denied"), { status: 403 }));
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.snapshot).toBeNull();
  const calls = vi.mocked(getOrbRuntime).mock.calls.length;
  await vi.advanceTimersByTimeAsync(9000);
  expect(getOrbRuntime).toHaveBeenCalledTimes(calls);
  reader.stop();
  expect(vi.getTimerCount()).toBe(0);
});

it("discards a late response after a visibility pause and silently rebases on return", async () => {
  let finish!: (value: ReturnType<typeof runtimeSnapshot>) => void;
  vi.mocked(getOrbRuntime).mockReturnValueOnce(new Promise(resolve => finish = resolve));
  const states: RuntimeReadState[] = [];
  const reader = observeRuntime(state => states.push(state));
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
  reader.visibility(); finish(runtimeSnapshot()); await vi.advanceTimersByTimeAsync(0);
  expect(states.at(-1)?.snapshot).toBeNull();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  vi.mocked(getOrbRuntime).mockResolvedValue(runtimeSnapshot([runtimeEvent(9)]));
  reader.visibility(); await vi.advanceTimersByTimeAsync(0);
  expect(states.at(-1)?.received.size).toBe(0);
  reader.stop();
});

it("keeps the source-generation high-water mark across 10 → 5 → 10 windows and only pulses 11", async () => {
  const states: RuntimeReadState[] = [];
  vi.mocked(getOrbRuntime)
    .mockResolvedValueOnce(runtimeSnapshot([runtimeEvent(10)]))
    .mockResolvedValueOnce(runtimeSnapshot([runtimeEvent(5)]))
    .mockResolvedValueOnce(runtimeSnapshot([runtimeEvent(10)]))
    .mockResolvedValueOnce(runtimeSnapshot([runtimeEvent(11)]));
  const reader = observeRuntime(state => states.push(state));
  await vi.advanceTimersByTimeAsync(0);
  expect(states.at(-1)?.snapshot?.sources[0]?.coverage.last_seq).toBe(10);
  expect(states.at(-1)?.received.size).toBe(0);
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.snapshot?.sources[0]?.coverage.last_seq).toBe(5);
  expect(states.at(-1)?.received.size).toBe(0);
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.snapshot?.sources[0]?.coverage.last_seq).toBe(10);
  expect(states.at(-1)?.received.size).toBe(0);
  await vi.advanceTimersByTimeAsync(3000);
  expect(states.at(-1)?.snapshot?.sources[0]?.coverage.last_seq).toBe(11);
  expect(states.at(-1)?.received.size).toBe(1);
  expect(getOrbRuntime).toHaveBeenCalledTimes(4);
  reader.stop();
});
