import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";
import type { BridgeSnapshot, BridgeTurnView } from "$lib/api/models";
import { createSeancesWorkspace } from "$lib/seances/workspace.svelte";
vi.mock("$lib/api/client", () => ({ ApiError: class ApiError extends Error { constructor(message: string, public status?: number) { super(message); } }, getBridgeSnapshot: vi.fn() }));
import { ApiError, getBridgeSnapshot } from "$lib/api/client";
import WorkingMaterial from "./WorkingMaterial.svelte";
const turn: BridgeTurnView = { role: "agent", content: "Exact quotation\n é ", run_id: "run-a", created_at: "2026-11-10T10:00:00Z", state: "settled" };
function source(turns: BridgeTurnView[]): BridgeSnapshot { return { session: { id: "source-a", title: "Source A", created_at: turn.created_at, pending_count: 0, turns }, sessions: [], active_runs: [], pending_consents: [], pending_count: 0 }; }
beforeEach(() => vi.clearAllMocks());
it("checks exact supplied source bytes explicitly and reports a changed source without replacing the quotation", async () => {
  const work = createSeancesWorkspace(vi.fn()); work.add("source-a", turn);
  vi.mocked(getBridgeSnapshot).mockResolvedValue(source([{ ...turn, content: "Changed source" }]));
  const view = render(WorkingMaterial, { work }); expect(getBridgeSnapshot).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Inspect source" }));
  await screen.findByText(/captured bytes have not been replaced/);
  expect(work.materials.get("source-a")![0]!.source.content).toBe(turn.content);
  expect(screen.getByRole("link", { name: "Open source séance" }).getAttribute("href")).toBe("/seances/source-a");
  expect(work.continueInBridge).not.toHaveBeenCalled(); view.unmount();
});
it("clears the whole protected collection on a current source refusal and fences an older refusal", async () => {
  const work = createSeancesWorkspace(vi.fn()); work.add("source-a", turn); work.add("source-b", turn);
  vi.mocked(getBridgeSnapshot).mockRejectedValueOnce(new ApiError("Denied", 403));
  const view = render(WorkingMaterial, { work });
  await fireEvent.click(screen.getAllByRole("button", { name: "Inspect source" })[0]!);
  await screen.findByText(/exact source is unavailable/);
  expect(work.materials.size).toBe(0); expect(work.accessEpoch).toBe(1);
  await act(() => { work.add("source-a", turn); });
  let reject!: (cause: unknown) => void;
  vi.mocked(getBridgeSnapshot).mockReturnValueOnce(new Promise((_, no) => { reject = no; }));
  await fireEvent.click(screen.getByRole("button", { name: "Inspect source" }));
  await act(() => { work.refuseAccess(); work.add("source-a", { ...turn, content: "Fresh authorized quotation" }); });
  await act(() => reject(new ApiError("Old denied", 403)));
  expect(work.materials.get("source-a")![0]!.source.content).toBe("Fresh authorized quotation");
  expect(screen.queryByText("Old denied")).toBeNull(); view.unmount();
});

it("keeps a failed source check separate from a current authorization refusal", async () => {
  const work = createSeancesWorkspace(vi.fn()); work.add("source-a", turn);
  vi.mocked(getBridgeSnapshot).mockRejectedValueOnce(new Error("Network down"));
  const view = render(WorkingMaterial, { work });
  await fireEvent.click(screen.getByRole("button", { name: "Inspect source" }));
  await screen.findByText(/exact source check failed/);
  expect(work.materials.get("source-a")![0]!.source.content).toBe(turn.content);
  expect(work.accessEpoch).toBe(0); expect(screen.queryByText("Network down")).toBeNull();
  view.unmount();
});
