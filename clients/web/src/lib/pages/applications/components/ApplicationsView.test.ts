import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ApplicationsHarness from "./ApplicationsHarness.test.svelte";

vi.mock("$app/navigation", () => ({ afterNavigate: vi.fn() }));

beforeEach(() => localStorage.clear());

describe("Applications dashboard", () => {
  it("combines area and name filters, and restores results when cleared", async () => {
    render(ApplicationsHarness);
    const area = screen.getByRole("combobox", { name: "Area" });
    const search = screen.getByRole("searchbox", { name: "Search" });
    expect(screen.getAllByRole("article")).toHaveLength(6);
    await fireEvent.change(area, { target: { value: "Creative Works" } });
    expect(screen.getAllByRole("article")).toHaveLength(5);
    await fireEvent.input(search, { target: { value: "  CANV  " } });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Open boards" }).getAttribute("href")).toBe("/canvas");
    await fireEvent.change(area, { target: { value: "Stewardship & Acquisition" } });
    expect(screen.getByRole("status").textContent).toContain("No applications match");
    await fireEvent.change(area, { target: { value: "" } });
    await fireEvent.input(search, { target: { value: "" } });
    expect(screen.getAllByRole("article")).toHaveLength(6);
  });

  it("synchronizes card pins, rail shortcuts, and the quick list across reloads", async () => {
    const view = render(ApplicationsHarness);
    const rail = () => within(screen.getByRole("banner", { name: "Altar navigation" }));
    expect(rail().queryByRole("link", { name: "Canvas" })).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: "Pin Canvas" }));
    expect(rail().getByRole("link", { name: "Canvas" }).getAttribute("href")).toBe("/canvas");
    view.unmount();
    render(ApplicationsHarness);
    const pin = screen.getByRole("button", { name: "Unpin Canvas" });
    expect(pin.getAttribute("aria-pressed")).toBe("true");
    expect(rail().getByRole("link", { name: "Canvas" })).toBeTruthy();
    await fireEvent.click(pin);
    expect(rail().queryByRole("link", { name: "Canvas" })).toBeNull();
    await fireEvent.click(rail().getByRole("button", { name: "Quick applications list" }));
    const quick = within(rail().getByRole("navigation", { name: "Quick applications list" }));
    expect(quick.getByRole("link", { name: "Canvas" }).getAttribute("href")).toBe("/canvas");
    expect(quick.queryByRole("link", { name: "Atelier" })).toBeNull();
  });
});
