import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { NamingView } from "$lib/api/models";
vi.mock("$lib/api/client", () => ({
  ApiError: class ApiError extends Error { constructor(message: string, readonly status?: number) { super(message); } },
  getNaming: vi.fn(), acceptNaming: vi.fn(), getNamingSuggestions: vi.fn()
}));
import { acceptNaming, ApiError, getNaming, getNamingSuggestions } from "$lib/api/client";
import NamingCeremony from "./NamingCeremony.svelte";
const read = vi.mocked(getNaming), save = vi.mocked(acceptNaming), suggest = vi.mocked(getNamingSuggestions);
beforeEach(() => {
  vi.resetAllMocks();
  read.mockResolvedValue({ current: null });
  suggest.mockResolvedValue({ names: ["Aster Vale", "Ember Dawn"] });
  save.mockImplementation(async (body) => ({ current: { ...body.names, revision: body.expected_revision + 1 } }));
});
afterEach(cleanup);
async function ready() { await waitFor(() => expect((screen.getByRole("button", { name: "Review names" }) as HTMLButtonElement).disabled).toBe(false)); }
async function edit(label: string, value: string) { await fireEvent.input(screen.getByLabelText(label), { target: { value } }); }

it("allows deferral without writes and saves an own name with neutral Primus only after explicit review", async () => {
  const close = vi.fn(), ask = vi.fn();
  render(NamingCeremony, { onclose: close, onask: ask }); await ready();
  await fireEvent.click(screen.getByRole("button", { name: /Later/ }));
  expect(close).toHaveBeenCalledOnce(); expect(save).not.toHaveBeenCalled();
  await edit("Your name · Magus", "  Élan  ");
  expect(screen.queryByRole("button", { name: "Save names" })).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Review names" }));
  expect(save).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Save names" }));
  await screen.findByText(/Names saved/);
  expect(save).toHaveBeenCalledWith({ expected_revision: 0, names: { magus_name: "Élan", primus_name: "Primus", magus_origin: "manual", primus_origin: "manual" } }, expect.any(AbortSignal));
  expect(ask).not.toHaveBeenCalled();
});

it("keeps local dictionary proposals inert and carries the selected method on acceptance", async () => {
  const ask = vi.fn(); render(NamingCeremony, { onclose: vi.fn(), onask: ask }); await ready();
  await fireEvent.click(screen.getByRole("button", { name: "Suggest companion name locally" }));
  await fireEvent.click(await screen.findByRole("button", { name: "Ember Dawn" }));
  expect((screen.getByLabelText("Companion name · Primus") as HTMLInputElement).value).toBe("Ember Dawn");
  expect(save).not.toHaveBeenCalled(); expect(ask).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Review names" }));
  await fireEvent.click(screen.getByRole("button", { name: "Save names" }));
  expect(save.mock.calls[0]?.[0].names.primus_origin).toBe("dictionary");
});

it("uses an explicit ordinary Bridge request with optional volunteered details, without accepting a reply", async () => {
  const ask = vi.fn().mockResolvedValue(undefined);
  render(NamingCeremony, { onclose: vi.fn(), onask: ask }); await ready();
  await edit("Your name · Magus", "Aster Vale");
  await fireEvent.click(screen.getByText("Explore names together in Bridge"));
  await edit("Optional preferences or details you want to share", "winter stars");
  await fireEvent.click(screen.getByRole("button", { name: "Invite Primus to propose a name" }));
  await screen.findByText(/Request sent to Bridge/);
  expect(ask).toHaveBeenCalledOnce();
  expect(ask.mock.calls[0]?.[0]).toContain('"magus_name":"Aster Vale"');
  expect(ask.mock.calls[0]?.[0]).toContain('"volunteered_details":"winter stars"');
  expect(save).not.toHaveBeenCalled();
  ask.mockRejectedValueOnce(new Error("A reply is still running."));
  await fireEvent.click(screen.getByRole("button", { name: "Ask for help with my name" }));
  await screen.findByText("A reply is still running.");
  expect((screen.getByLabelText("Your name · Magus") as HTMLInputElement).value).toBe("Aster Vale");
});

it("refuses stale overwrites and retains the draft through authoritative reload and fresh review", async () => {
  const saved: NamingView = { current: { revision: 4, magus_name: "Old", primus_name: "Companion", magus_origin: "manual", primus_origin: "self_chosen" } };
  read.mockResolvedValueOnce(saved).mockResolvedValue({ current: { ...saved.current!, revision: 5, magus_name: "Elsewhere" } });
  save.mockRejectedValueOnce(new ApiError("Stale", 409));
  render(NamingCeremony, { onclose: vi.fn(), onask: vi.fn() }); await ready();
  await edit("Your name · Magus", "My draft");
  await fireEvent.click(screen.getByRole("button", { name: "Review names" }));
  await fireEvent.click(screen.getByRole("button", { name: "Save names" }));
  await screen.findByText(/Names changed since/);
  expect((screen.getByRole("button", { name: "Review names" }) as HTMLButtonElement).disabled).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Reload saved names" })); await ready();
  expect((screen.getByLabelText("Your name · Magus") as HTMLInputElement).value).toBe("My draft");
  await screen.findByText("Elsewhere");
  await fireEvent.click(screen.getByRole("button", { name: "Review names" }));
  await fireEvent.click(screen.getByRole("button", { name: "Save names" }));
  await screen.findByText(/Names saved/);
  expect(save.mock.calls[1]?.[0].expected_revision).toBe(5);
});

it("requires reload after an ambiguous save and aborts reads on unmount without claiming success", async () => {
  save.mockRejectedValueOnce(new TypeError("network"));
  const view = render(NamingCeremony, { onclose: vi.fn(), onask: vi.fn() }); await ready();
  await fireEvent.click(screen.getByRole("button", { name: "Review names" }));
  await fireEvent.click(screen.getByRole("button", { name: "Save names" }));
  await screen.findByText(/save outcome is unknown/);
  expect(screen.queryByText(/Names saved/)).toBeNull();
  let finish!: (value: NamingView) => void;
  read.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
  await fireEvent.click(screen.getByRole("button", { name: "Reload saved names" }));
  const signal = read.mock.calls.at(-1)?.[0];
  view.unmount();
  expect(signal?.aborted).toBe(true);
  await act(() => finish({ current: null }));
  expect(screen.queryByRole("heading", { name: "Naming ceremony" })).toBeNull();
});


it("keeps a typed draft when the initial read fails and is retried", async () => {
  read.mockRejectedValueOnce(new TypeError("network")).mockResolvedValueOnce({ current: null });
  render(NamingCeremony, { onclose: vi.fn(), onask: vi.fn() });
  await screen.findByText(/Saved names could not be read/);
  await edit("Your name · Magus", "Keep this draft");
  await fireEvent.click(screen.getByRole("button", { name: "Reload saved names" })); await ready();
  expect((screen.getByLabelText("Your name · Magus") as HTMLInputElement).value).toBe("Keep this draft");
  expect(save).not.toHaveBeenCalled();
});
