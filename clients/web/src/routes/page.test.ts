import { render, waitFor } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";

vi.mock("$app/navigation", () => ({ goto: vi.fn().mockResolvedValue(undefined) }));

import { goto } from "$app/navigation";
import Page from "./+page.svelte";

it("opens Orb from the static root without retaining a redirect in browser history", async () => {
  const view = render(Page);
  await waitFor(() => expect(goto).toHaveBeenCalledWith("/orb", { replaceState: true }));
  expect(goto).toHaveBeenCalledTimes(1);
  view.unmount();
});
