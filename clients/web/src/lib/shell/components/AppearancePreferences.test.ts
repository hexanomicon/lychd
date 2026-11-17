import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { appearanceStorageKey } from "$lib/appearance/preferences";
import AppearancePreferences from "./AppearancePreferences.svelte";

beforeEach(() => { localStorage.clear(); delete document.documentElement.dataset.altarAccent; });
afterEach(() => { vi.restoreAllMocks(); delete document.documentElement.dataset.altarAccent; });

it("restores a closed preference and persists only the selected ID and version", async () => {
  localStorage.setItem(appearanceStorageKey, '{"version":1,"accent":"iris"}');
  render(AppearancePreferences);
  const opener = screen.getByText("Appearance", { selector: "summary" });
  await fireEvent.click(opener);
  expect((screen.getByRole("radio", { name: "Iris" }) as HTMLInputElement).checked).toBe(true);
  await fireEvent.click(screen.getByRole("radio", { name: "Neutral" }));
  expect(document.documentElement.dataset.altarAccent).toBe("neutral");
  expect(JSON.parse(localStorage.getItem(appearanceStorageKey)!)).toEqual({ version: 1, accent: "neutral" });
  await fireEvent.click(screen.getByRole("button", { name: "Reset to LychD Dark" }));
  expect(document.documentElement.dataset.altarAccent).toBe("violet");
  expect(localStorage.getItem(appearanceStorageKey)).toBeNull();
});

it("keeps an explicit choice usable when browser storage refuses writes", async () => {
  render(AppearancePreferences);
  await fireEvent.click(screen.getByText("Appearance", { selector: "summary" }));
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("unavailable"); });
  await fireEvent.click(screen.getByRole("radio", { name: "Iris" }));
  expect(document.documentElement.dataset.altarAccent).toBe("iris");
  expect(screen.getByRole("status").textContent).toContain("Kept for this tab");
});

it("restores focus on Escape and accepts only supported cross-tab values", async () => {
  const view = render(AppearancePreferences);
  const opener = screen.getByText("Appearance", { selector: "summary" });
  await fireEvent.click(opener);
  (screen.getByRole("radio", { name: "Violet" }) as HTMLElement).focus();
  await fireEvent.keyDown(window, { key: "Escape" });
  expect(opener.closest("details")?.open).toBe(false);
  expect(document.activeElement).toBe(opener);
  await fireEvent(window, new StorageEvent("storage", { key: appearanceStorageKey, newValue: '{"version":1,"accent":"neutral"}' }));
  expect(document.documentElement.dataset.altarAccent).toBe("neutral");
  await fireEvent(window, new StorageEvent("storage", { key: appearanceStorageKey, newValue: '{"version":1,"accent":"display:none"}' }));
  expect(document.documentElement.dataset.altarAccent).toBe("violet");
  view.unmount();
  expect(document.documentElement.dataset.altarAccent).toBeUndefined();
});
