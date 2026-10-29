import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import BridgeDock from "./BridgeDock.svelte";
import { bridgeDockStorageKey } from "$lib/navigation/dock";

const children = createRawSnippet(() => ({ render: () => '<div><button type="button">Conversation action</button><textarea aria-label="Retained draft"></textarea></div>' }));
beforeEach(() => { vi.stubGlobal("PointerEvent", MouseEvent); vi.stubGlobal("innerWidth", 1280); localStorage.clear(); vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false }))); });
afterEach(() => { vi.unstubAllGlobals(); });

it("bounds keyboard width, switches sides, and stores layout fields only", async () => {
  const view = render(BridgeDock, { children });
  const separator = screen.getByRole("separator", { name: "Bridge width" });
  await fireEvent.keyDown(separator, { key: "End" });
  expect(separator.getAttribute("aria-valuenow")).toBe("720");
  await fireEvent.keyDown(separator, { key: "ArrowLeft" });
  expect(separator.getAttribute("aria-valuenow")).toBe("720");
  await fireEvent.keyDown(separator, { key: "Home" });
  expect(separator.getAttribute("aria-valuenow")).toBe("320");
  await fireEvent.click(screen.getByRole("button", { name: "Dock Bridge left" }));
  await fireEvent.keyDown(separator, { key: "ArrowRight" });
  expect(separator.getAttribute("aria-valuenow")).toBe("344");
  await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
  expect(JSON.parse(localStorage.getItem(bridgeDockStorageKey)!)).toEqual({ width: 344, side: "left", open: false });
  expect(document.querySelector("textarea")).toBeTruthy();
  view.unmount();
});

it("resizes through the pointer without changing the conversation node", async () => {
  const view = render(BridgeDock, { children });
  const textarea = screen.getByLabelText("Retained draft");
  const separator = screen.getByRole("separator", { name: "Bridge width" });
  await fireEvent.pointerDown(separator, { button: 0, pointerId: 1, clientX: 700 });
  await fireEvent.pointerMove(separator, { pointerId: 1, clientX: 600 });
  await fireEvent.pointerUp(separator, { pointerId: 1, clientX: 600 });
  expect(separator.getAttribute("aria-valuenow")).toBe("540");
  expect(screen.getByLabelText("Retained draft")).toBe(textarea);
  view.unmount();
});

it("contains narrow focus, closes with Escape, and returns focus to the opener", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  // JSDOM has no layout; expose visible rectangles for this DOM focus test.
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockReturnValue([{}] as unknown as DOMRectList);
  const opener = document.createElement("button");
  opener.id = "bridge-toggle"; opener.textContent = "Bridge opener";
  document.body.append(opener); opener.focus();
  const view = render(BridgeDock, { children, forceOpen: true });
  await act(() => Promise.resolve());
  const dialog = screen.getByRole("dialog", { name: "Bridge" });
  const first = screen.getByRole("button", { name: "Dock Bridge left" });
  const last = screen.getByLabelText("Retained draft");
  last.focus();
  await fireEvent.keyDown(window, { key: "Tab" });
  expect(document.activeElement).toBe(first);
  await fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(last);
  await fireEvent.keyDown(window, { key: "Escape" });
  expect(dialog.closest("[hidden]")).toBeTruthy();
  expect(document.activeElement).toBe(opener);
  view.unmount(); opener.remove(); vi.restoreAllMocks();
});

it("starts a new narrow workbench collapsed while honoring an explicit Bridge destination", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  const view = render(BridgeDock, { children });
  await act(() => Promise.resolve());
  expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
  view.unmount();
  localStorage.clear();
  const explicit = render(BridgeDock, { children, forceOpen: true });
  await act(() => Promise.resolve());
  expect(screen.getByRole("dialog", { name: "Bridge" })).toBeTruthy();
  explicit.unmount();
});

it("reports and resizes the actual allocation when a stored width exceeds the workbench cap", async () => {
  vi.stubGlobal("innerWidth", 1000);
  localStorage.setItem(bridgeDockStorageKey, JSON.stringify({ width: 720, side: "right", open: true }));
  const view = render(BridgeDock, { children });
  await act(() => Promise.resolve());
  const separator = screen.getByRole("separator", { name: "Bridge width" });
  expect(separator.getAttribute("aria-valuenow")).toBe("600");
  expect(separator.getAttribute("aria-valuemax")).toBe("600");
  expect(JSON.parse(localStorage.getItem(bridgeDockStorageKey)!).width).toBe(720);
  await fireEvent.pointerDown(separator, { button: 0, pointerId: 1, clientX: 700 });
  await fireEvent.pointerMove(separator, { pointerId: 1, clientX: 750 });
  await fireEvent.pointerUp(separator, { pointerId: 1, clientX: 750 });
  expect(separator.getAttribute("aria-valuenow")).toBe("550");
  await fireEvent.keyDown(separator, { key: "End" });
  expect(separator.getAttribute("aria-valuenow")).toBe("600");
  await fireEvent.keyDown(separator, { key: "ArrowRight" });
  expect(separator.getAttribute("aria-valuenow")).toBe("576");
  view.unmount();
});
