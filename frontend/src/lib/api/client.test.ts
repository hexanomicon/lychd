import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RunEventEnvelope } from "./models";
import { listenToRun } from "./client";

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  onerror: ((event: Event) => void) | null = null;
  closeCalls = 0;
  private readonly listeners = new Map<string, EventListenerOrEventListenerObject[]>();

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: EventListenerOrEventListenerObject | null
  ) {
    if (!listener) return;
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  close() {
    this.closeCalls++;
  }

  emit(type: string, data: string) {
    const event = new MessageEvent<string>(type, { data });
    for (const listener of this.listeners.get(type) ?? []) {
      if (typeof listener === "function") listener(event);
      else listener.handleEvent(event);
    }
  }

  disconnect() {
    this.onerror?.(new Event("error"));
  }
}

function runEvent(seq: number): RunEventEnvelope {
  return {
    schema_version: 1,
    run_id: "run-a",
    event_id: "00000000-0000-4000-8000-000000000001",
    seq,
    kind: "token",
    occurred_at: "2026-07-28T00:00:00Z",
    payload: { text: "ash" }
  };
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("run stream lifecycle", () => {
  it("reports a hard close for invalid data but leaves transient reconnects alive", () => {
    const onFault = vi.fn();
    const onHardClose = vi.fn();
    listenToRun(
      "run-a",
      vi.fn(),
      onFault,
      async () => ({ cursor: 0, terminal: false }),
      { onHardClose }
    );
    const source = FakeEventSource.instances[0];
    if (!source) throw new Error("The EventSource was not opened.");

    source.disconnect();
    expect(onFault).toHaveBeenCalledWith("The run stream went quiet; reconnecting.");
    expect(onHardClose).not.toHaveBeenCalled();
    expect(source.closeCalls).toBe(0);

    source.emit("token", "{}");
    expect(onHardClose).toHaveBeenCalledOnce();
    expect(source.closeCalls).toBe(1);
    expect(onFault).toHaveBeenLastCalledWith("The Vessel emitted an invalid run event.");
  });

  it("hard-closes exactly once when an authoritative refetch fails", async () => {
    const onFault = vi.fn();
    const onHardClose = vi.fn();
    const onRefetch = vi.fn().mockRejectedValue(new Error("snapshot unavailable"));
    listenToRun("run-a", vi.fn(), onFault, onRefetch, { onHardClose });
    const source = FakeEventSource.instances[0];
    if (!source) throw new Error("The EventSource was not opened.");

    source.emit("token", JSON.stringify(runEvent(2)));

    await vi.waitFor(() => expect(onHardClose).toHaveBeenCalledOnce());
    expect(source.closeCalls).toBe(1);
    expect(onFault).toHaveBeenCalledWith(
      "The authoritative run snapshot could not be refreshed."
    );

    source.emit("token", "{}");
    expect(onHardClose).toHaveBeenCalledOnce();
  });
});
