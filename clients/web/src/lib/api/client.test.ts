import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RunEventEnvelope, TransitionEventEnvelope } from "./models";
import { listenToRun, listenToSwap } from "./client";

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

function transitionEvent(ticketId: string): TransitionEventEnvelope {
  return {
    schema_version: 1,
    seq: 0,
    ticket: {
      id: ticketId,
      request_id: "request-a",
      target: "chat:local",
      state: "warming",
      phase: "warming",
      action_type: "SWAP",
      total_metabolic_cost: 1,
      physical_transition_id: null,
      compensation_transition_id: null
    }
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

  it("hard-closes a structurally valid event from another run", () => {
    const onEvent = vi.fn();
    const onFault = vi.fn();
    const onHardClose = vi.fn();
    listenToRun("run-a", onEvent, onFault, vi.fn(), { onHardClose });
    const source = FakeEventSource.instances[0];
    if (!source) throw new Error("The EventSource was not opened.");

    source.emit("token", JSON.stringify({ ...runEvent(0), run_id: "run-b" }));

    expect(onEvent).not.toHaveBeenCalled();
    expect(onHardClose).toHaveBeenCalledWith(
      "The Vessel emitted a run event for another Run."
    );
    expect(onFault).toHaveBeenCalledWith(
      "The Vessel emitted a run event for another Run."
    );
    expect(source.closeCalls).toBe(1);
  });
});

describe("transition stream lifecycle", () => {
  it("hard-closes a structurally valid event from another ticket", () => {
    const onEvent = vi.fn();
    const onFault = vi.fn();
    const onHardClose = vi.fn();
    listenToSwap("ticket-a", onEvent, onFault, { onHardClose });
    const source = FakeEventSource.instances[0];
    if (!source) throw new Error("The EventSource was not opened.");

    source.emit("transition", JSON.stringify(transitionEvent("ticket-b")));

    expect(onEvent).not.toHaveBeenCalled();
    expect(onHardClose).toHaveBeenCalledWith(
      "The Vessel emitted a transition event for another ticket."
    );
    expect(onFault).toHaveBeenCalledWith(
      "The Vessel emitted a transition event for another ticket."
    );
    expect(source.closeCalls).toBe(1);
  });

  it("ignores queued transition callbacks after the stream reaches terminal truth", () => {
    const onEvent = vi.fn();
    listenToSwap("ticket-a", onEvent, vi.fn());
    const source = FakeEventSource.instances[0];
    if (!source) throw new Error("The EventSource was not opened.");
    const settled = transitionEvent("ticket-a");
    settled.ticket.state = "settled";

    source.emit("transition", JSON.stringify(settled));
    source.emit("transition", JSON.stringify(transitionEvent("ticket-a")));

    expect(onEvent).toHaveBeenCalledOnce();
    expect(onEvent).toHaveBeenCalledWith(settled);
    expect(source.closeCalls).toBe(1);
  });
});
