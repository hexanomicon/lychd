import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError, cancelBridgeRun, decideConsent, deleteMarketObservation, filterMarketObservation, getMarketObservationConsent,
  getScavengerState, readMarketObservation, submitMarketObservation } from "$lib/api/client";
import { admissionId, otherId, runId, field, deferred } from "$lib/scavenger/observation.fixtures";
import ScavengerView from "./ScavengerView.svelte";

const hooks = vi.hoisted(() => ({ after: [] as Array<() => void> }));
vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn(), afterNavigate: (callback: () => void) => { hooks.after.push(callback); callback(); } }));
vi.mock("$lib/api/client", async (original) => ({ ...await original<typeof import("$lib/api/client")>(),
  cancelBridgeRun: vi.fn(), decideConsent: vi.fn(), deleteMarketObservation: vi.fn(), filterMarketObservation: vi.fn(), getMarketObservationConsent: vi.fn(),
  getScavengerState: vi.fn(), readMarketObservation: vi.fn(), submitMarketObservation: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks(); hooks.after = [];
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: field() });
  vi.mocked(readMarketObservation).mockResolvedValue(field());
  vi.mocked(filterMarketObservation).mockResolvedValue(field().view!);
  vi.mocked(getMarketObservationConsent).mockResolvedValue(null);
});
afterEach(() => vi.restoreAllMocks());

it("renders every occurrence with explicit coverage, duplicates/missing values and inert untrusted title/link text", async () => {
  const view = render(ScavengerView); await screen.findByRole("heading", { name: "Whole field" });
  expect(screen.getByText("<img src=x onerror=alert(1)> É GPU")).toBeTruthy();
  expect(view.container.querySelector("img")).toBeNull();
  expect(view.container.querySelector('a[href^="https://pc.bazos.sk"]')).toBeNull();
  expect(screen.getByText("Title missing")).toBeTruthy(); expect(screen.getByText("Keyboard")).toBeTruthy();
  expect(screen.getByText("Same link as occurrence 1")).toBeTruthy();
  expect(screen.getByText(/this response is not the entire market/)).toBeTruthy();
  expect(screen.getByText(/Price, condition, seller, eligibility and source freshness: not assessed/)).toBeTruthy();
  expect(submitMarketObservation).not.toHaveBeenCalled();
});

it("filters locally against the server's retained field and keeps the entire unmatched field available without refetch", async () => {
  render(ScavengerView); await screen.findByText("Keyboard");
  await fireEvent.click(screen.getByText("Filter this field locally"));
  expect((screen.getByLabelText("Literal title/link substring") as HTMLInputElement).value).toBe("é");
  await fireEvent.input(screen.getByLabelText("Literal title/link substring"), { target: { value: "é" } });
  await fireEvent.click(screen.getByRole("button", { name: "Apply local filter" }));
  await waitFor(() => expect(screen.queryByText("Keyboard")).toBeNull());
  expect(filterMarketObservation).toHaveBeenCalledOnce();
  expect(filterMarketObservation).toHaveBeenCalledWith(admissionId, { revision: "literal-casefold@1", query: "é" }, expect.any(AbortSignal));
  await fireEvent.click(screen.getByRole("button", { name: "Show entire field" }));
  expect(screen.getByText("Keyboard")).toBeTruthy();
  expect(getScavengerState).toHaveBeenCalledOnce(); expect(readMarketObservation).not.toHaveBeenCalled();
  expect(submitMarketObservation).not.toHaveBeenCalled();
});

it("distinguishes no local matches, empty response, unknown custody and unconfigured application", async () => {
  vi.mocked(filterMarketObservation).mockResolvedValue({ ...field().view!, visible_ordinals: [], visible_count: 0, unmatched_count: 3 });
  const first = render(ScavengerView); await screen.findByText("Keyboard");
  await fireEvent.click(screen.getByText("Filter this field locally"));
  await fireEvent.click(screen.getByRole("button", { name: "Apply local filter" }));
  await screen.findByText(/No local matches/); first.unmount();
  const empty = field(); empty.observation!.items = []; empty.view = { ...empty.view!, total_count: 0, visible_count: 0,
    unmatched_count: 0, duplicate_count: 0, missing_title_count: 0, visible_ordinals: [] };
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: empty });
  const second = render(ScavengerView); await screen.findByText(/This is an empty field/); second.unmount();
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1",
    current: { ...field(), observation: null, view: null, status: "unknown", terminal_disposition: "unknown" } });
  const third = render(ScavengerView); await screen.findByText(/Acquisition outcome is unknown/);
  expect(screen.queryByRole("button", { name: "Delete this payload" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Submit new observation for review" })).toBeNull(); third.unmount();
  vi.mocked(getScavengerState).mockResolvedValue({ configured: false, profile: null, current: null });
  render(ScavengerView); await screen.findByText(/Scavenger is not configured/);
});

it("requires explicit terminal-delete confirmation and clears the complete payload only after the exact acknowledgement", async () => {
  vi.mocked(deleteMarketObservation).mockResolvedValue({ admission_id: admissionId, request_digest: field().request_digest,
    observation_digest: field().observation_digest, status: "deleted" });
  render(ScavengerView); await screen.findByText("Keyboard");
  const button = screen.getByRole("button", { name: "Delete this payload" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  await fireEvent.click(screen.getByRole("checkbox", { name: "I intend to delete this exact retained payload." }));
  await fireEvent.click(button); await screen.findByText(/Deleted: the application seed and item payload were removed/);
  expect(screen.queryByText("Keyboard")).toBeNull();
  expect(screen.queryByText(/Private need é/)).toBeNull();
  expect(deleteMarketObservation).toHaveBeenCalledWith(admissionId,
    { request_digest: field().request_digest, observation_digest: field().observation_digest });
  expect(submitMarketObservation).not.toHaveBeenCalled();
});

it("clears private content after a read refusal and fences a late response after changed/invalid selection", async () => {
  const pending = deferred<ReturnType<typeof field>>();
  const view = render(ScavengerView); await screen.findByText("Keyboard");
  vi.mocked(readMarketObservation).mockRejectedValueOnce(new ApiError("Denied", 403));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh retained state" }));
  await screen.findByText(/Current access was refused/); expect(screen.queryByText("Keyboard")).toBeNull();
  vi.mocked(readMarketObservation).mockReturnValueOnce(pending.promise);
  await view.rerender({ admissionId }); hooks.after.at(-1)!();
  await view.rerender({ admissionId: "invalid" }); hooks.after.at(-1)!();
  await act(() => pending.resolve(field()));
  expect(screen.queryByText("Keyboard")).toBeNull(); expect(screen.getByText(/selection must be one UUID/)).toBeTruthy();
});

it("focuses local validation errors without posting an incomplete seed", async () => {
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: null });
  render(ScavengerView); await screen.findByRole("form", { name: "New feed observation" });
  await fireEvent.click(screen.getByRole("button", { name: "Submit new observation for review" }));
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Check the supplied facts" })));
  expect(submitMarketObservation).not.toHaveBeenCalled();
});

it("uses the existing native review card and exact Core review-binding verdict before refreshing authoritative state", async () => {
  const waiting = { ...field(), status: "awaiting_consent" as const, run_status: "awaiting_consent" as const,
    terminal_disposition: "pending" as const, observation: null, view: null };
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: waiting });
  const card = { id: otherId, run_id: runId, can_decide: true, state: "pending_consent" as const,
    tool_name: "scout_public_feed", vision: "Acquire one bounded feed", args: {}, native_review_status: "available" as const,
    review_binding_digest: "a".repeat(64), native_review: { title: "Review feed", facts: [{ key: "scope", label: "Scope", value: "Title/link only" }] } };
  vi.mocked(getMarketObservationConsent).mockResolvedValue(card);
  vi.mocked(decideConsent).mockResolvedValue({ consent: { ...card, state: "consented" }, pending_count: 0 });
  render(ScavengerView); await screen.findByText("Title/link only");
  await fireEvent.click(screen.getByRole("button", { name: "Consecrate" }));
  await screen.findByText("Keyboard");
  expect(decideConsent).toHaveBeenCalledWith(otherId, "approve", "a".repeat(64));
  expect(readMarketObservation).toHaveBeenCalledWith(admissionId, expect.any(AbortSignal));
  expect(submitMarketObservation).not.toHaveBeenCalled();
});

it("renders exact canonical integer facts as text without rounding through JavaScript numbers", async () => {
  const retained = field();
  retained.seed_document = '{"budget_minor":9223372036854775807,"need":"Literal <b>need</b>"}';
  retained.seed!.budget_minor = Number("9223372036854775807");
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: retained });
  const view = render(ScavengerView); await screen.findByRole("heading", { name: "Whole field" });
  await fireEvent.click(screen.getByText("Complete retained campaign facts"));
  expect(screen.getByText(retained.seed_document)).toBeTruthy();
  expect(view.container.querySelector('pre b')).toBeNull();
  expect(view.container.querySelector("pre")!.textContent).not.toContain("9223372036854776000");
});

it("confirms cancellation of the exact native Run and preserves an uncertain outcome without retry or deletion", async () => {
  const waiting = { ...field(), status: "awaiting_consent" as const, run_status: "awaiting_consent" as const,
    terminal_disposition: "pending" as const, observation: null, view: null };
  vi.mocked(getScavengerState).mockResolvedValue({ configured: true, profile: "bazos-pc-title-link@1", current: waiting });
  vi.mocked(cancelBridgeRun).mockRejectedValueOnce(new TypeError("Lost cancellation acknowledgement"));
  render(ScavengerView); await screen.findByRole("heading", { name: "Cancel pending work" });
  const button = screen.getByRole("button", { name: "Cancel this Run" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  await fireEvent.click(screen.getByRole("checkbox", { name: "I intend to cancel this Run." }));
  await fireEvent.click(button);
  await screen.findByRole("complementary", { name: "Unconfirmed cancellation" });
  expect(cancelBridgeRun).toHaveBeenCalledExactlyOnceWith(runId);
  expect(deleteMarketObservation).not.toHaveBeenCalled();
  expect(submitMarketObservation).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Delete this payload" })).toBeNull();
});
