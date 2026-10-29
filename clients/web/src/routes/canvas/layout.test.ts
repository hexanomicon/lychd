import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("$app/navigation", () => ({ goto: vi.fn(), replaceState: vi.fn(), beforeNavigate: vi.fn(), afterNavigate: vi.fn() }));
vi.mock("$app/state", () => ({ page: { url: new URL("http://localhost/canvas") } }));
vi.mock("$lib/api/client", async (original) => ({
  ...await original<typeof import("$lib/api/client")>(),
  getAltarStatus: vi.fn(),
  getBridgeSnapshot: vi.fn()
}));

import { getAltarStatus, getBridgeSnapshot } from "$lib/api/client";
import Layout from "../+layout.svelte";

afterEach(() => { vi.restoreAllMocks(); vi.clearAllMocks(); });

it("opens the offline development Canvas without a protected status request or sign-in challenge", () => {
  const children = createRawSnippet(() => ({ render: () => "<p>Offline Canvas draft</p>" }));
  const view = render(Layout, { children });
  expect(screen.getByText("Offline Canvas draft")).toBeTruthy();
  expect(getAltarStatus).not.toHaveBeenCalled();
  expect(getBridgeSnapshot).not.toHaveBeenCalled();
  expect(screen.getByRole("navigation", { name: "Instruments" })).toBeTruthy();
  expect(screen.getByText("Bridge is offline")).toBeTruthy();
  view.unmount();
});

it("connects protected shell reads only after an explicit operator action", async () => {
  vi.mocked(getAltarStatus).mockResolvedValue({ csrf: { cookie_name: "csrf", header_name: "X-CSRF-Token" }, pending_consents: 0 });
  vi.mocked(getBridgeSnapshot).mockResolvedValue({ sessions: [], session: null, active_runs: [], pending_consents: [], pending_count: 0 });
  const children = createRawSnippet(() => ({ render: () => "<p>Offline Canvas draft</p>" }));
  const view = render(Layout, { children });
  expect(getAltarStatus).not.toHaveBeenCalled();
  expect(getBridgeSnapshot).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Connect to LychD" }));
  await act(() => Promise.resolve());
  expect(getAltarStatus).toHaveBeenCalled();
  expect(getBridgeSnapshot).toHaveBeenCalledWith(undefined);
  view.unmount();
});
