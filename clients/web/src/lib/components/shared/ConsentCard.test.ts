import { fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ConsentCard as ConsentCardModel } from "$lib/api/models";

vi.mock("$lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("$lib/api/client")>();
  return { ...original, decideConsent: vi.fn() };
});

import { decideConsent } from "$lib/api/client";
import ConsentCard from "./ConsentCard.svelte";
import { createBridgeWorkspace } from "$lib/bridge/workspace.svelte";

const consent: ConsentCardModel = {
  args: { target: "chat:local" },
  can_decide: true,
  native_review_status: "not_required",
  id: "consent-a",
  run_id: "run-a",
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
    render(ConsentCard, { consent, sessionId: "session-a", decisions: createBridgeWorkspace().consentDecisions, onauthority: () => 7, ondecided: vi.fn(), onrefresh });

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
      sessionId: "session-a",
      decisions: createBridgeWorkspace().consentDecisions,
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

const digest = "a".repeat(64);
const nativeConsent: ConsentCardModel = {
  ...consent,
  native_review_status: "available",
  review_binding_digest: digest,
  native_review: {
    title: "Review <b>placement</b>",
    facts: [
      { key: "target", label: "Destination", value: "<img src=x onerror=alert(1)>\n  second line" },
      { key: "effect", label: "Effect", value: "x".repeat(8192) }
    ]
  }
};

function mountConsent(card = nativeConsent, work = createBridgeWorkspace()) {
  const onrefresh = vi.fn();
  const ondecided = vi.fn();
  const view = render(ConsentCard, {
    consent: card, sessionId: "session-a", decisions: work.consentDecisions,
    onauthority: () => 7, ondecided, onrefresh
  });
  return { ...view, work, onrefresh, ondecided };
}

function verdictButtons() {
  return ["Consecrate", "Refuse"].map((name) => screen.getByRole("button", { name }) as HTMLButtonElement);
}

describe("Required native review", () => {
  it("preserves an owner-authorized whitespace-only fact and permits its verdict", async () => {
    vi.mocked(decideConsent).mockRejectedValueOnce(new TypeError("response lost"));
    const value = " \n\t ";
    mountConsent({ ...nativeConsent, native_review: {
      title: "Literal review", facts: [{ key: "literal", label: "Literal value", value }]
    } });
    const approve = screen.getByRole("button", { name: "Consecrate" }) as HTMLButtonElement;
    expect(approve.disabled).toBe(false);
    expect(screen.getByRole("region", { name: "Required review" }).querySelector("dd")?.textContent).toBe(value);
    await fireEvent.click(approve);
    expect(decideConsent).toHaveBeenCalledWith(consent.id, "approve", digest);
  });

  it("renders the entire ordered review as text with semantic labels", () => {
    const view = mountConsent();
    const review = screen.getByRole("region", { name: "Required review" });
    expect(screen.getByRole("heading", { name: nativeConsent.native_review!.title })).toBeTruthy();
    expect([...review.querySelectorAll("dt")].map((node) => node.textContent)).toEqual(["Destination", "Effect"]);
    expect([...review.querySelectorAll("dd")].map((node) => node.textContent)).toEqual(nativeConsent.native_review!.facts.map((fact) => fact.value));
    expect(review.querySelector("img, b, a, script")).toBeNull();
    expect(view.container.querySelector(".args")?.textContent).toContain("chat:local");
  });

  it.each([
    { native_review_status: "unavailable", native_review: null },
    { native_review_status: "available", native_review: null },
    { review_binding_digest: null },
    { review_binding_digest: "" },
    { native_review: { title: "Incomplete", facts: [] } },
    { native_review: { title: "Incomplete", facts: [{ key: "x", label: "", value: "x" }] } },
    { native_review: { title: "Repeated keys", facts: [
      { key: "x", label: "First", value: "x" }, { key: "x", label: "Second", value: "y" }
    ] } }
  ] satisfies Partial<ConsentCardModel>[])("blocks judgment for an unavailable or incomplete review: %j", async (patch) => {
    const view = mountConsent({ ...nativeConsent, ...patch });
    expect(verdictButtons().every((button) => button.disabled)).toBe(true);
    for (const button of verdictButtons()) await fireEvent.click(button);
    expect(decideConsent).not.toHaveBeenCalled();
    expect(screen.getByText(/required review is unavailable or incomplete/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Refresh review" }));
    expect(view.onrefresh).toHaveBeenCalledOnce();
  });

  it("keeps an authorized review visible while judgment is read-only", async () => {
    mountConsent({ ...nativeConsent, can_decide: false });
    expect(screen.getByRole("region", { name: "Required review" })).toBeTruthy();
    expect(screen.getByText(/Read-only/)).toBeTruthy();
    expect(verdictButtons().every((button) => button.disabled)).toBe(true);
    for (const button of verdictButtons()) await fireEvent.click(button);
    expect(decideConsent).not.toHaveBeenCalled();
  });

  it.each([["Consecrate", "approve"], ["Refuse", "deny"]] as const)("binds %s to exactly the displayed review", async (label, verdict) => {
    vi.mocked(decideConsent).mockRejectedValueOnce(new TypeError("response lost"));
    const view = mountConsent();
    await fireEvent.click(screen.getByRole("button", { name: label }));
    expect(decideConsent).toHaveBeenCalledWith(consent.id, verdict, digest);
    expect(view.work.consentDecisions.get(consent.id)).toMatchObject({ verdict, reviewBindingDigest: digest, sending: false });
    expect(view.work.needsUnloadWarning).toBe(true);
  });

  it("keeps verdict and review identity across remount and a later middleware refusal", async () => {
    const { ApiError } = await import("$lib/api/client");
    vi.mocked(decideConsent).mockRejectedValueOnce(new TypeError("response lost"))
      .mockRejectedValueOnce(new ApiError("Scope refused", 403))
      .mockResolvedValueOnce({ consent: { ...nativeConsent, state: "consented" }, pending_count: 0 });
    const first = mountConsent();
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    first.unmount();
    const second = mountConsent(nativeConsent, first.work);
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    await fireEvent.click(screen.getByRole("button", { name: "Refuse" }));
    expect(first.work.consentDecisions.get(consent.id)).toMatchObject({ verdict: "approve", reviewBindingDigest: digest });
    expect(first.work.needsUnloadWarning).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    expect(vi.mocked(decideConsent).mock.calls).toEqual(Array(3).fill([consent.id, "approve", digest]));
    expect(second.ondecided).toHaveBeenCalledWith({ ...nativeConsent, state: "consented" }, 0, 7);
  });

  it.each([
    { ...nativeConsent, review_binding_digest: "b".repeat(64), native_review: { title: "New review", facts: [{ key: "new", label: "New fact", value: "New value" }] } },
    { ...nativeConsent, native_review_status: "unavailable", native_review: null },
    { ...consent },
    { ...nativeConsent, can_decide: false }
  ] satisfies ConsentCardModel[])("cannot retry or replace an unresolved decision against changed review or permission: %j", async (changed) => {
    vi.mocked(decideConsent).mockRejectedValueOnce(new TypeError("response lost"));
    const first = mountConsent();
    await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
    first.unmount();
    const second = mountConsent(changed, first.work);
    expect(verdictButtons().every((button) => button.disabled)).toBe(true);
    for (const button of verdictButtons()) await fireEvent.click(button);
    expect(decideConsent).toHaveBeenCalledOnce();
    expect(first.work.consentDecisions.get(consent.id)).toMatchObject({ verdict: "approve", reviewBindingDigest: digest });
    expect(first.work.consentDecisions.get(consent.id)).not.toHaveProperty("native_review");
    if (changed.can_decide) {
      expect(screen.getByText(/previous approval is unconfirmed.*review has changed or is unavailable/)).toBeTruthy();
      expect(screen.queryByRole("heading", { name: nativeConsent.native_review!.title })).toBeNull();
    }
    await fireEvent.click(screen.getByRole("button", { name: "Refresh outcome" }));
    expect(second.onrefresh).toHaveBeenCalledOnce();
  });
});
