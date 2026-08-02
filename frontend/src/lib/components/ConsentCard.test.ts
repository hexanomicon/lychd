import { fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ConsentCard as ConsentCardModel } from "$lib/api/models";

vi.mock("$lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("$lib/api/client")>();
  return { ...original, decideConsent: vi.fn() };
});

import { decideConsent } from "$lib/api/client";
import ConsentCard from "./ConsentCard.svelte";

const consent: ConsentCardModel = {
  args: { target: "chat:local" },
  id: "consent-a",
  run_id: "run-a",
  session_id: "session-a",
  state: "pending_consent",
  tool_name: "request_coven_swap",
  vision: "Change the active capability"
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Consent decision uncertainty", () => {
  it("permits only the same verdict after an ambiguous response", async () => {
    vi.mocked(decideConsent).mockRejectedValue(new TypeError("network lost"));
    const onrefresh = vi.fn();
    render(ConsentCard, { consent, onauthority: () => 7, ondecided: vi.fn(), onrefresh });

    const approve = screen.getByRole("button", { name: "Consecrate" }) as HTMLButtonElement;
    const deny = screen.getByRole("button", { name: "Refuse" }) as HTMLButtonElement;
    await fireEvent.click(approve);

    expect(approve.disabled).toBe(false);
    expect(deny.disabled).toBe(true);
    expect(onrefresh).toHaveBeenCalledOnce();

    await fireEvent.click(deny);
    await fireEvent.click(approve);
    expect(decideConsent).toHaveBeenCalledTimes(2);
    expect(decideConsent).toHaveBeenNthCalledWith(1, consent.id, "approve");
    expect(decideConsent).toHaveBeenNthCalledWith(2, consent.id, "approve");
  });

  it("presents Run cancellation without attributing a human refusal", () => {
    render(ConsentCard, {
      consent: { ...consent, state: "cancelled" },
      onauthority: () => 7,
      ondecided: vi.fn(),
      onrefresh: vi.fn()
    });

    expect(screen.getByText("cancelled")).toBeTruthy();
    expect(screen.getByText("the Run withdrew this request")).toBeTruthy();
    expect(screen.getByRole("group", { name: "cancelled consent" })).toBeTruthy();
    expect(screen.queryByText("the Magus has spoken")).toBeNull();
  });
});
