import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NexusSnapshot, SwapTicket, TransitionPlan } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/nexus") }
}));
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      readonly status?: number
    ) {
      super(message);
    }
  },
  createNexusSwap: vi.fn(),
  getNexusPlan: vi.fn(),
  getNexusSnapshot: vi.fn(),
  getNexusSwap: vi.fn(),
  getNexusTransition: vi.fn(),
  listenToSwap: vi.fn()
}));

import {
  ApiError,
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

function transition(phase: string): NexusSnapshot["transitions"][number] {
  return {
    action_type: "SOFT_SWAP",
    bridge_path: null,
    compensation_transition_id: null,
    detail: null,
    observed_at: "2026-07-30T00:00:01Z",
    occurrence_id: "occurrence-a",
    orb_path: null,
    phase,
    physical_transition_id: "physical-a",
    priority: 70,
    request_id: "request-a",
    requested_at: "2026-07-30T00:00:00Z",
    run_id: null,
    source: "operator",
    target_capability_key: "chat:local"
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((accept, decline) => {
    resolve = accept;
    reject = decline;
  });
  return { promise, reject, resolve };
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

  it("marks a retained board stale and fences lifecycle mutations after a poll fails", async () => {
    vi.useFakeTimers();
    const first = deferred<NexusSnapshot>();
    vi.mocked(getNexusSnapshot)
      .mockReturnValueOnce(first.promise)
      .mockRejectedValueOnce(new Error("Poll failed"));
    const view = render(NexusView);

    await act(() => first.resolve(snapshot));
    const previewTrigger = screen.getByRole("button", { name: "Preview" }) as HTMLButtonElement;
    await fireEvent.click(previewTrigger);
    const request = (await screen.findByRole("button", {
      name: "Request transition"
    })) as HTMLButtonElement;

    expect(previewTrigger.disabled).toBe(false);
    expect(request.disabled).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(screen.getByText(/The Nexus board is stale/)).toBeTruthy();
    expect(previewTrigger.isConnected).toBe(true);
    expect(previewTrigger.disabled).toBe(false);
    expect(request.disabled).toBe(true);

    await fireEvent.click(request);
    expect(createNexusSwap).not.toHaveBeenCalled();
    view.unmount();
  });

  it("runs one trailing refresh when ticket settlement arrives during a board read", async () => {
    vi.useFakeTimers();
    const view = render(NexusView);
    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    const onTicket = vi.mocked(listenToSwap).mock.calls[0]?.[1];
    if (!onTicket) throw new Error("The ticket stream has no event handler.");

    const delayedBoard = deferred<NexusSnapshot>();
    vi.mocked(getNexusSnapshot)
      .mockReturnValueOnce(delayedBoard.promise)
      .mockResolvedValue(snapshot);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(getNexusSnapshot).toHaveBeenCalledTimes(2);

    await act(() => onTicket({ ticket: ticket("settled") } as never));
    expect(getNexusSnapshot).toHaveBeenCalledTimes(2);
    await act(async () => {
      delayedBoard.resolve(snapshot);
      for (let index = 0; index < 10; index++) await Promise.resolve();
    });

    expect(getNexusSnapshot).toHaveBeenCalledTimes(3);
    view.unmount();
  });
});

describe("Nexus projection and focus", () => {
  it("fences preview identity while a transition admission is unresolved", async () => {
    const admission = deferred<{ ticket: SwapTicket }>();
    const firstRow = snapshot.board.covens[0]?.[1][0];
    if (!firstRow) throw new Error("The fixture has no capability row.");
    vi.mocked(getNexusSnapshot).mockResolvedValue({
      ...snapshot,
      board: {
        ...snapshot.board,
        covens: [
          [
            "local",
            [firstRow, { ...firstRow, capability_key: "chat:other", model_id: "model-b" }]
          ]
        ]
      }
    });
    vi.mocked(createNexusSwap).mockReturnValue(admission.promise);
    const view = render(NexusView);
    const previews = await screen.findAllByRole("button", { name: "Preview" });
    const firstPreview = previews[0];
    const secondPreview = previews[1];
    if (!firstPreview || !secondPreview) throw new Error("Both preview controls are required.");

    await fireEvent.click(firstPreview);
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    expect((secondPreview as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.click(secondPreview);
    expect(getNexusPlan).toHaveBeenCalledTimes(1);

    await act(() => admission.resolve({ ticket: ticket() }));
    expect(screen.getByText("chat:local", { selector: ".swap-ticket span" })).toBeTruthy();
    view.unmount();
  });

  it("reuses one transition identity after an uncertain admission", async () => {
    vi.mocked(createNexusSwap)
      .mockRejectedValueOnce(new TypeError("network lost"))
      .mockResolvedValueOnce({ ticket: ticket() });
    const view = render(NexusView);

    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    const request = await screen.findByRole("button", { name: "Request transition" });
    await fireEvent.click(request);
    await screen.findByText("network lost");
    await fireEvent.click(request);

    expect(createNexusSwap).toHaveBeenCalledTimes(2);
    expect(vi.mocked(createNexusSwap).mock.calls[0]?.[1]).toBe(
      vi.mocked(createNexusSwap).mock.calls[1]?.[1]
    );
    view.unmount();
  });

  it("retains the fenced identity after a lost-ticket conflict", async () => {
    vi.mocked(createNexusSwap)
      .mockRejectedValueOnce(new ApiError("The admitted ticket is no longer retained.", 409))
      .mockRejectedValueOnce(new ApiError("The admitted ticket is no longer retained.", 409));
    const view = render(NexusView);

    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    const request = await screen.findByRole("button", { name: "Request transition" });
    await fireEvent.click(request);
    await screen.findByText("The admitted ticket is no longer retained.");
    await fireEvent.click(request);

    const calls = vi.mocked(createNexusSwap).mock.calls;
    expect(calls).toHaveLength(2);
    expect(calls[0]?.[1]).toBe(calls[1]?.[1]);
    view.unmount();
  });

  it("rebinds the inspector from the refreshed terminal transition", async () => {
    const before = { ...snapshot, transitions: [transition("actuating")] };
    const after = { ...snapshot, transitions: [transition("settled")] };
    vi.mocked(getNexusSnapshot).mockResolvedValueOnce(before).mockResolvedValue(after);
    const view = render(NexusView);

    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    const onTicket = vi.mocked(listenToSwap).mock.calls[0]?.[1];
    if (!onTicket) throw new Error("The ticket stream has no event handler.");
    await act(() => onTicket({ ticket: ticket("settled") } as never));

    const phase = await screen.findByText("phase", { selector: "dt" });
    await waitFor(() => expect(phase.nextElementSibling?.textContent).toBe("settled"));
    view.unmount();
  });

  it("retains an uncertain transition identity while previewing another target", async () => {
    const firstRow = snapshot.board.covens[0]?.[1][0];
    if (!firstRow) throw new Error("The fixture has no capability row.");
    vi.mocked(getNexusSnapshot).mockResolvedValue({
      ...snapshot,
      board: {
        ...snapshot.board,
        covens: [
          [
            "local",
            [firstRow, { ...firstRow, capability_key: "chat:other", model_id: "model-b" }]
          ]
        ]
      }
    });
    vi.mocked(createNexusSwap)
      .mockRejectedValueOnce(new TypeError("first response lost"))
      .mockRejectedValueOnce(new TypeError("second response lost"))
      .mockResolvedValueOnce({ ticket: ticket() });
    const view = render(NexusView);
    const previews = await screen.findAllByRole("button", { name: "Preview" });
    const firstPreview = previews[0];
    const secondPreview = previews[1];
    if (!firstPreview || !secondPreview) throw new Error("Both preview controls are required.");

    await fireEvent.click(firstPreview);
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    await screen.findByText("first response lost");
    await fireEvent.click(secondPreview);
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    await screen.findByText("second response lost");
    await fireEvent.click(firstPreview);
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));

    const calls = vi.mocked(createNexusSwap).mock.calls;
    expect(calls[0]?.[1]).toBe(calls[2]?.[1]);
    expect(calls[1]?.[1]).not.toBe(calls[0]?.[1]);
    view.unmount();
  });

  it("does not follow a swap admitted after the Nexus is destroyed", async () => {
    const admission = deferred<{ ticket: SwapTicket }>();
    vi.mocked(createNexusSwap).mockReturnValue(admission.promise);
    const view = render(NexusView);
    await fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));

    view.unmount();
    await act(() => admission.resolve({ ticket: ticket() }));

    expect(listenToSwap).not.toHaveBeenCalled();
  });

  it("does not resurrect a delayed preview after selecting transition evidence", async () => {
    const firstRow = snapshot.board.covens[0]?.[1][0];
    if (!firstRow) throw new Error("The fixture has no capability row.");
    vi.mocked(getNexusSnapshot).mockResolvedValue({
      ...snapshot,
      board: {
        ...snapshot.board,
        covens: [
          [
            "local",
            [firstRow, { ...firstRow, capability_key: "chat:other", model_id: "model-b" }]
          ]
        ]
      }
    });
    const delayedPlan = deferred<TransitionPlan>();
    vi.mocked(getNexusPlan)
      .mockResolvedValueOnce(plan)
      .mockReturnValueOnce(delayedPlan.promise);
    const view = render(NexusView);
    const previews = await screen.findAllByRole("button", { name: "Preview" });
    const firstPreview = previews[0];
    const secondPreview = previews[1];
    if (!firstPreview || !secondPreview) throw new Error("Both preview controls are required.");

    await fireEvent.click(firstPreview);
    await fireEvent.click(await screen.findByRole("button", { name: "Request transition" }));
    await fireEvent.click(secondPreview);
    const onTicket = vi.mocked(listenToSwap).mock.calls[0]?.[1];
    if (!onTicket) throw new Error("The ticket stream has no event handler.");
    await act(() => onTicket({ ticket: ticket("settled") } as never));
    await act(() => delayedPlan.resolve(plan));

    expect(screen.queryByRole("button", { name: "Request transition" })).toBeNull();
    view.unmount();
  });

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
