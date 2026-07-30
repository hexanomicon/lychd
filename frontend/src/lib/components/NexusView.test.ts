import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NexusSnapshot, SwapTicket, TransitionPlan } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/nexus") }
}));
vi.mock("$lib/api/client", () => ({
  createNexusSwap: vi.fn(),
  getNexusPlan: vi.fn(),
  getNexusSnapshot: vi.fn(),
  getNexusSwap: vi.fn(),
  getNexusTransition: vi.fn(),
  listenToSwap: vi.fn()
}));

import {
  createNexusSwap,
  getNexusPlan,
  getNexusSnapshot,
  getNexusSwap,
  listenToSwap
} from "$lib/api/client";
import NexusView from "./NexusView.svelte";

const snapshot: NexusSnapshot = {
  snapshot_at: "2026-07-30T00:00:00Z",
  containment_reason: null,
  board: {
    covens: [
      [
        "local",
        [
          {
            animator_name: "local",
            capability_key: "chat:local",
            checked_at: "2026-07-30T00:00:00Z",
            dedicated: false,
            family: "chat",
            health: "ready",
            is_active: true,
            model_id: "model-a",
            persistent_resident: false,
            reason: null,
            runtime: "local",
            state: "active",
            warm: true
          }
        ]
      ]
    ],
    portals: []
  },
  delegated_runtimes: [],
  transitions: []
};

const plan: TransitionPlan = {
  action_type: "SOFT_SWAP",
  evict_coven_ids: [],
  launch_coven_ids: ["local"],
  policy: "test",
  total_metabolic_cost: 0
};

function ticket(state: SwapTicket["state"] = "warming"): SwapTicket {
  return {
    id: "ticket-a",
    request_id: "request-a",
    target: "chat:local",
    state,
    phase: state,
    action_type: "SOFT_SWAP",
    total_metabolic_cost: 0,
    physical_transition_id: null,
    compensation_transition_id: null
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.mocked(getNexusSnapshot).mockResolvedValue(snapshot);
  vi.mocked(getNexusPlan).mockResolvedValue(plan);
  vi.mocked(createNexusSwap).mockResolvedValue({ ticket: ticket() });
  vi.mocked(getNexusSwap).mockResolvedValue({ ticket: ticket() });
  vi.mocked(listenToSwap).mockImplementation(() => vi.fn());
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Nexus refresh ownership", () => {
  it("schedules the next poll only after the current refresh completes", async () => {
    vi.useFakeTimers();
    const first = deferred<NexusSnapshot>();
    vi.mocked(getNexusSnapshot).mockReturnValueOnce(first.promise);
    const view = render(NexusView);

    expect(getNexusSnapshot).toHaveBeenCalledOnce();
    await act(() => vi.advanceTimersByTime(5000));
    expect(getNexusSnapshot).toHaveBeenCalledOnce();

    await act(() => first.resolve(snapshot));
    await act(() => vi.advanceTimersByTime(4999));
    expect(getNexusSnapshot).toHaveBeenCalledOnce();
    await act(() => vi.advanceTimersByTime(1));
    expect(getNexusSnapshot).toHaveBeenCalledTimes(2);
    view.unmount();
  });
});

describe("Nexus projection and focus", () => {
  it("returns focus to the capability that opened a preview", async () => {
    const view = render(NexusView);
    const opener = await screen.findByRole("button", { name: "Preview" });

    await fireEvent.click(opener);
    const close = await screen.findByRole("button", { name: "Close" });
    expect(close).toBeTruthy();
    await fireEvent.click(close);

    expect(document.activeElement).toBe(opener);
    view.unmount();
  });

  it("marks a hard-closed ticket stale and performs only one recovery", async () => {
    const recovery = deferred<{ ticket: SwapTicket }>();
    vi.mocked(getNexusSwap).mockReturnValue(recovery.promise);
    const view = render(NexusView);

    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    const firstCall = vi.mocked(listenToSwap).mock.calls[0];
    const firstHardClose = firstCall?.[3]?.onHardClose;
    if (!firstHardClose) throw new Error("The ticket stream has no hard-close hook.");

    await act(() => firstHardClose("invalid transition"));
    expect(screen.getByText("projection stale")).toBeTruthy();
    expect(getNexusSwap).toHaveBeenCalledOnce();

    await act(() => recovery.resolve({ ticket: ticket() }));
    expect(screen.getByText("warming")).toBeTruthy();
    expect(listenToSwap).toHaveBeenCalledTimes(2);

    const secondHardClose = vi.mocked(listenToSwap).mock.calls[1]?.[3]?.onHardClose;
    if (!secondHardClose) throw new Error("The recovered ticket stream has no hard-close hook.");
    await act(() => secondHardClose("invalid transition again"));
    expect(screen.getByText("projection stale")).toBeTruthy();
    expect(getNexusSwap).toHaveBeenCalledOnce();
    view.unmount();
  });
});
