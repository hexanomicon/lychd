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
  await fireEvent.keyDown(separator, { key: "ArrowRight" });
  expect(separator.getAttribute("aria-valuenow")).toBe("720");
  await fireEvent.keyDown(separator, { key: "Home" });
  expect(separator.getAttribute("aria-valuenow")).toBe("320");
  await fireEvent.click(screen.getByRole("button", { name: "Dock Bridge right" }));
  await fireEvent.keyDown(separator, { key: "ArrowLeft" });
  expect(separator.getAttribute("aria-valuenow")).toBe("344");
  await fireEvent.click(screen.getByRole("button", { name: "Collapse Bridge" }));
  expect(JSON.parse(localStorage.getItem(bridgeDockStorageKey)!)).toEqual({ width: 344, side: "right", open: false });
  expect(document.querySelector("textarea")).toBeTruthy();
  view.unmount();
});

it("resizes through the pointer without changing the conversation node", async () => {
  const view = render(BridgeDock, { children });
  const textarea = screen.getByLabelText("Retained draft");
  const separator = screen.getByRole("separator", { name: "Bridge width" });
  await fireEvent.pointerDown(separator, { button: 0, pointerId: 1, clientX: 700 });
  await fireEvent.pointerMove(separator, { pointerId: 1, clientX: 800 });
  await fireEvent.pointerUp(separator, { pointerId: 1, clientX: 800 });
  expect(separator.getAttribute("aria-valuenow")).toBe("540");
  expect(screen.getByLabelText("Retained draft")).toBe(textarea);
  view.unmount();
});

it("contains narrow focus, closes with Escape, and returns focus to the opener", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  // JSDOM has no layout; expose visible rectangles for this DOM focus test.
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockReturnValue([{}] as unknown as DOMRectList);
  const view = render(BridgeDock, { children });
  await act(() => Promise.resolve());
  const opener = screen.getByRole("button", { name: "Expand Bridge" });
  opener.focus();
  await fireEvent.click(opener);
  const dialog = screen.getByRole("dialog", { name: "Bridge" });
  const first = screen.getByRole("button", { name: "Collapse Bridge" });
  const last = screen.getByLabelText("Retained draft");
  last.focus();
  await fireEvent.keyDown(window, { key: "Tab" });
  expect(document.activeElement).toBe(first);
  await fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(last);
  await fireEvent.keyDown(window, { key: "Escape" });
  expect(dialog.getAttribute("role")).toBeNull();
  expect(document.getElementById("bridge-dock")?.closest("[hidden]")).toBeTruthy();
  expect(document.activeElement).toBe(opener);
  view.unmount(); vi.restoreAllMocks();
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


it.each(["left", "right"] as const)("keeps the %s edge control mounted through collapse and preserves the conversation draft", async (side) => {
  localStorage.setItem(bridgeDockStorageKey, JSON.stringify({ width: 440, side, open: true }));
  const view = render(BridgeDock, { children });
  const toggle = screen.getByRole("button", { name: "Collapse Bridge" });
  const draft = screen.getByLabelText("Retained draft") as HTMLTextAreaElement;
  await fireEvent.input(draft, { target: { value: "Unsent work" } });
  expect(toggle.id).toBe("bridge-toggle");
  expect(toggle.getAttribute("aria-controls")).toBe("bridge-dock");
  expect(toggle.getAttribute("aria-expanded")).toBe("true");
  expect(toggle.textContent).toBe(side === "left" ? "<<" : ">>");
  await fireEvent.click(toggle);
  expect(screen.getByRole("button", { name: "Expand Bridge" })).toBe(toggle);
  expect(toggle.closest("[hidden]")).toBeNull();
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
  expect(toggle.textContent).toBe(side === "left" ? ">>" : "<<");
  expect(document.activeElement).toBe(toggle);
  expect(JSON.parse(localStorage.getItem(bridgeDockStorageKey)!)).toEqual({ width: 440, side, open: false });
  await fireEvent.click(toggle);
  expect(screen.getByRole("button", { name: "Collapse Bridge" })).toBe(toggle);
  expect(screen.getByLabelText("Retained draft")).toBe(draft);
  expect(draft.value).toBe("Unsent work");
  view.unmount();
});

it("starts on the left when no side has been saved and still allows docking right", async () => {
  const view = render(BridgeDock, { children });
  const toggle = screen.getByRole("button", { name: "Collapse Bridge" });
  expect(toggle.closest(".dock-shell")?.classList.contains("dock-left")).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Dock Bridge right" }));
  expect(toggle.closest(".dock-shell")?.classList.contains("dock-left")).toBe(false);
  expect(toggle.textContent).toBe(">>");
  view.unmount();
});
