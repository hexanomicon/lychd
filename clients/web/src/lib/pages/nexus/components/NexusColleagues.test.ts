import { fireEvent, render, screen } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";
import type { NexusSnapshot } from "$lib/api/models";
import { setNexusPresence } from "$lib/api/client";
import NexusColleagues from "./NexusColleagues.svelte";

vi.mock("$lib/api/client", () => ({ setNexusPresence: vi.fn() }));

it("binds sharing to the displayed audience and hides expired or stale availability", async () => {
  const board: NonNullable<NexusSnapshot["presence"]> = {
    audience_id: "eb0065bf-c213-46d5-85c1-c69000f29121",
    sharing: "hidden", sharing_until: null,
    peers: [
      { name: "Ada", availability: "busy", observed_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 30000).toISOString(), publication: "waiting" },
      { name: "Lin", availability: "ready", observed_at: null, expires_at: null, publication: "waiting" }
    ]
  };
  vi.mocked(setNexusPresence).mockImplementation(async (_, choice) => ({
    ...board, sharing: choice
  }));
  const onrefresh = vi.fn().mockResolvedValue(undefined);
  const view = render(NexusColleagues, { board, stale: false, onrefresh });
  expect(screen.getByText(/one hour with Ada, Lin/)).toBeTruthy();
  expect(screen.getByText("Busy")).toBeTruthy();
  expect(screen.getByText("Availability unknown")).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Share ready" }));
  expect(setNexusPresence).toHaveBeenCalledWith(board.audience_id, "ready");
  expect(onrefresh).toHaveBeenCalledOnce();
  expect(screen.getByText("Sharing preference saved.")).toBeTruthy();
  await view.rerender({ board, stale: true, onrefresh });
  expect(screen.getAllByText("Availability unknown")).toHaveLength(2);
  expect((screen.getByRole("button", { name: "Share busy" }) as HTMLButtonElement).disabled).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Stop sharing" }));
  expect(setNexusPresence).toHaveBeenLastCalledWith(board.audience_id, "hidden");
});
