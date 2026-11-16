import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NexusCovenRow, NexusSnapshot } from "$lib/api/models";
import { createNexusMap } from "$lib/pages/nexus/state/map";
import NexusMap from "./NexusMap.svelte";

function row(capability_key: string): NexusCovenRow {
  return { animator_name: "animator-a", capability_key, checked_at: null, dedicated: false, family: "chat", health: "ready", is_active: true,
    model_id: "model-a", persistent_resident: false, reason: null, runtime: "local", state: "active", warm: true };
}

function snapshot(keys = ["chat:a"]): NexusSnapshot {
  return { snapshot_at: "2026-11-02T00:00:00Z", containment_reason: null,
    board: { covens: [["display-a", keys.map(row)]], portals: [] }, delegated_runtimes: [], transitions: [] };
}

function plane(container: HTMLElement) {
  const element = container.querySelector<HTMLElement>(".map-plane");
  if (!element) throw new Error("Map workplane is missing");
  return element;
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
  // JSDOM has no layout or PointerEvent implementation; retain the real DOM event path.
  vi.spyOn(Element.prototype, "clientWidth", "get").mockReturnValue(608);
  vi.spyOn(Element.prototype, "clientHeight", "get").mockReturnValue(464);
  vi.stubGlobal("PointerEvent", class extends MouseEvent {
    readonly pointerId: number;
    constructor(type: string, options: PointerEventInit = {}) {
      super(type, options);
      this.pointerId = options.pointerId ?? 1;
    }
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Nexus native map interactions", () => {
  it("retains the operator's zoom and pan across replacement snapshots", async () => {
    const onselect = vi.fn();
    const view = render(NexusMap, { model: createNexusMap(snapshot()), selectedId: null, onselect });
    await fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    await fireEvent.click(screen.getByRole("button", { name: "Pan down" }));
    const camera = plane(view.container).style.transform;
    expect(screen.getByLabelText("Map zoom").textContent).toBe("120%");

    const updated = snapshot(["chat:a", "chat:b"]);
    updated.snapshot_at = "2026-11-02T00:00:05Z";
    await view.rerender({ model: createNexusMap(updated), selectedId: null, onselect });

    expect(plane(view.container).style.transform).toBe(camera);
    expect(screen.getByLabelText("Map zoom").textContent).toBe("120%");
    expect(screen.getByRole("button", { name: "Inspect managed capability chat:b" })).toBeTruthy();
    expect(onselect).not.toHaveBeenCalled();
  });

  it("pans from the background without selecting and returns the exact clicked identity", async () => {
    const model = createNexusMap(snapshot());
    const onselect = vi.fn();
    const view = render(NexusMap, { model, selectedId: null, onselect });
    const viewport = screen.getByRole("group", { name: "Nexus observation map" });
    const capture = vi.fn();
    Object.defineProperty(viewport, "setPointerCapture", { value: capture });
    const before = plane(view.container).style.transform;
    await fireEvent.pointerDown(viewport, { button: 0, pointerId: 7, clientX: 100, clientY: 100 });
    await fireEvent.pointerMove(viewport, { pointerId: 7, clientX: 150, clientY: 180 });
    await fireEvent.pointerUp(viewport, { pointerId: 7, clientX: 150, clientY: 180 });
    expect(capture).toHaveBeenCalledWith(7);
    expect(plane(view.container).style.transform).not.toBe(before);
    expect(onselect).not.toHaveBeenCalled();

    const button = screen.getByRole("button", { name: "Inspect managed capability chat:a" });
    const capability = model.objects.find((object) => object.kind === "capability" && object.scope === "managed");
    await fireEvent.pointerDown(button, { button: 0, pointerId: 8, clientX: 200, clientY: 200 });
    await fireEvent.click(button);
    expect(capture).toHaveBeenCalledTimes(1);
    expect(onselect).toHaveBeenCalledExactlyOnceWith(capability?.id, button);
  });

  it("labels retained observations stale and removes actual-active emphasis", async () => {
    const model = createNexusMap(snapshot());
    const onselect = vi.fn();
    const view = render(NexusMap, { model, selectedId: null, onselect });
    const capability = screen.getByRole("button", { name: "Inspect managed capability chat:a" });
    expect(capability.getAttribute("data-active")).toBe("true");
    expect(within(capability).getByText("● active · ready")).toBeTruthy();

    await view.rerender({ model, selectedId: null, onselect, stale: true });

    expect(screen.getByText(/Retained snapshot · stale/)).toBeTruthy();
    expect(view.container.querySelector('.map-object[data-active="true"]')).toBeNull();
    expect(within(capability).getByText("active · ready")).toBeTruthy();
    expect(within(capability).queryByText(/●/)).toBeNull();
    expect(within(capability).getByText("Freshness unknown")).toBeTruthy();
  });

  it("reveals an offscreen object on keyboard focus and exposes its full identity", async () => {
    const fullIdentity = "chat:zz-last-capability-with-a-long-untruncated-domain-identity";
    const model = createNexusMap(snapshot(["chat:a", "chat:b", "chat:c", "chat:d", "chat:e", fullIdentity]));
    const onselect = vi.fn();
    const view = render(NexusMap, { model, selectedId: null, onselect });
    const button = screen.getByRole("button", { name: `Inspect managed capability ${fullIdentity}` });
    const node = model.nodes.find((item) => model.objects.find((object) => object.id === item.objectId)?.label === fullIdentity);
    expect(node).toBeDefined();
    expect(node!.y).toBeGreaterThan(464);
    const before = plane(view.container).style.transform;

    // Moving focus is the browser's result of Tab; JSDOM does not perform default Tab navigation.
    await act(() => button.focus());

    expect(document.activeElement).toBe(button);
    const transform = plane(view.container).style.transform;
    expect(transform).not.toBe(before);
    const match = /translate\(([-\d.]+)px, ([-\d.]+)px\) scale\(([-\d.]+)\)/.exec(transform);
    expect(match).not.toBeNull();
    const translateY = Number(match![2]), zoom = Number(match![3]);
    expect(node!.y * zoom + translateY).toBeGreaterThanOrEqual(0);
    expect((node!.y + node!.height) * zoom + translateY).toBeLessThanOrEqual(464);
    expect(button.getAttribute("aria-label")).toContain(fullIdentity);
    expect(onselect).not.toHaveBeenCalled();
  });
});
