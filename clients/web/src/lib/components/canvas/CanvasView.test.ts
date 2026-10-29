import { Blob as NodeBlob } from "node:buffer";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { blankDocument, exampleDocument } from "$lib/canvas/engine";
import type { Document as BoardDocument, Packet, Proposal } from "$lib/canvas/types";
import CanvasSurface from "./CanvasSurface.svelte";
import CanvasView from "../CanvasView.svelte";

vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn() }));
let downloads: NodeBlob[];
beforeEach(() => {
  downloads = [];
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  vi.stubGlobal("Blob", NodeBlob);
  vi.stubGlobal("URL", class extends URL {
    static override createObjectURL(blob: Blob | MediaSource) { downloads.push(blob as unknown as NodeBlob); return "blob:canvas-test"; }
    static override revokeObjectURL() {}
  });
  vi.stubGlobal("Image", class { onerror?: () => void; set src(_value: string) { queueMicrotask(() => this.onerror?.()); } });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function pointer(type: string, x: number, y: number, id = 1, shiftKey = false) {
  const event = new MouseEvent(type, { clientX: x, clientY: y, button: 0, bubbles: true, cancelable: true, shiftKey });
  Object.defineProperty(event, "pointerId", { value: id });
  return event;
}
function surface(tool: "draw" | "select" | "lasso" = "draw") {
  const onchange = vi.fn(), onselect = vi.fn(() => true), onerror = vi.fn();
  const view = render(CanvasSurface, { scene: blankDocument().scene, tool, selected: [], onselect, onchange, onbusy: vi.fn(), onerror, onedit: vi.fn() });
  const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
  return { view, svg, onchange, onselect, onerror };
}
async function objectList() {
  await fireEvent.click(screen.getByRole("button", { name: /^Objects/ }));
  return screen.getByRole("list", { name: "Board objects" });
}
async function selectObject(list: HTMLElement, label: string) {
  const row = within(list).getByText(label).closest("li")!;
  await fireEvent.click(within(row).getByRole("checkbox"));
}
function jsonFile(value: unknown, read?: () => Promise<string>) {
  const file = new File([JSON.stringify(value)], "import.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: read ?? (async () => JSON.stringify(value)) });
  return file;
}
async function downloadBoard(): Promise<BoardDocument> {
  await fireEvent.click(screen.getByRole("button", { name: /^Download board/ }));
  return JSON.parse(await downloads.at(-1)!.text()) as BoardDocument;
}

describe("Canvas native authoring", () => {
  it("circles original ink without adding selection marks to the document, and discards a canceled lasso", async () => {
    const document = blankDocument();
    const inside = { id: crypto.randomUUID(), points: [{ x: 100, y: 100 }, { x: 140, y: 120 }], width: 2, color: "#ffffff", archived: false };
    const outside = { ...inside, id: crypto.randomUUID(), points: [{ x: 300, y: 300 }, { x: 340, y: 320 }] };
    document.scene.strokes = [inside, outside];
    const onselect = vi.fn(() => true), onchange = vi.fn();
    render(CanvasSurface, { scene: document.scene, tool: "lasso", selected: [], onselect, onchange, onbusy: vi.fn(), onerror: vi.fn(), onedit: vi.fn() });
    const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
    // Initial camera translates world by 70,80; circle only the first stroke.
    await fireEvent(svg, pointer("pointerdown", 150, 160));
    for (const [x, y] of [[230, 160], [230, 230], [150, 230], [150, 160]]) await fireEvent(svg, pointer("pointermove", x!, y!));
    await fireEvent(svg, pointer("pointerup", 150, 160));
    expect(onselect).toHaveBeenLastCalledWith([inside.id]);
    expect(onchange).not.toHaveBeenCalled();
    expect(document.scene.strokes).toEqual([inside, outside]);
    onselect.mockClear();
    await fireEvent(svg, pointer("pointerdown", 150, 160));
    await fireEvent(svg, pointer("pointermove", 230, 230));
    await fireEvent(svg, pointer("pointercancel", 230, 230));
    expect(onselect).not.toHaveBeenCalled();
    expect(onchange).not.toHaveBeenCalled();
  });

  it("commits real world-coordinate ink once, and discards a canceled gesture", async () => {
    const { svg, onchange } = surface();
    await fireEvent(svg, pointer("pointerdown", 170, 180));
    await fireEvent(svg, pointer("pointermove", 210, 200));
    await fireEvent(svg, pointer("pointerup", 210, 200));
    expect(onchange).toHaveBeenCalledTimes(1);
    expect(onchange.mock.calls[0]![0].strokes[0].points).toEqual([{ x: 100, y: 100 }, { x: 140, y: 120 }]);
    await fireEvent(svg, pointer("pointerdown", 170, 180));
    await fireEvent(svg, pointer("pointermove", 250, 250));
    await fireEvent(svg, pointer("pointercancel", 250, 250));
    expect(onchange).toHaveBeenCalledTimes(1);
  });

  it("saves bounded ink at the sample limit and makes the stopping condition visible", async () => {
    const { svg, onchange, onerror } = surface();
    await act(() => {
      svg.dispatchEvent(pointer("pointerdown", 170, 180));
      for (let index = 1; index <= 2050; index++) svg.dispatchEvent(pointer("pointermove", 170 + index * 2, 180));
      svg.dispatchEvent(pointer("pointerup", 4300, 180));
    });
    expect(onchange).toHaveBeenCalledTimes(1);
    expect(onchange.mock.calls[0]![0].strokes[0].points).toHaveLength(2048);
    expect(onerror).toHaveBeenCalledExactlyOnceWith(expect.stringContaining("2,048-point limit"));
  });

  it("aborts an over-limit Shift-drag before moving any refused object, and still permits an accepted drag", async () => {
    const document = blankDocument();
    document.scene.nodes = Array.from({ length: 128 }, (_, index) => ({ id: crypto.randomUUID(), x: 100 + index * 40, y: 100, width: 32, height: 32, label: `Node ${index + 1}`, kind: "box", pinned: false, artwork: null, source_stroke_ids: [] }));
    const outside = { id: crypto.randomUUID(), points: [{ x: 800, y: 400 }, { x: 850, y: 400 }], color: "#b7efff", width: 2, archived: false };
    document.scene.strokes = [outside];
    const selected = document.scene.nodes.map((node) => node.id);
    const onselect = vi.fn((ids: string[]) => ids.length <= 128), onchange = vi.fn(), onbusy = vi.fn();
    render(CanvasSurface, { scene: document.scene, tool: "select", selected, onselect, onchange, onbusy, onerror: vi.fn(), onedit: vi.fn() });
    const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
    const stroke = svg.querySelector(`[data-object-id="${outside.id}"] polyline`)!;
    await fireEvent(stroke, pointer("pointerdown", 870, 480, 1, true));
    await fireEvent(svg, pointer("pointermove", 920, 530, 1, true));
    expect(onselect).toHaveBeenCalledWith([...selected, outside.id]);
    expect(stroke.getAttribute("points")).toBe("800,400 850,400");
    expect(onbusy).not.toHaveBeenCalledWith(true);
    await fireEvent(svg, pointer("pointerup", 920, 530, 1, true));
    expect(onchange).not.toHaveBeenCalled();

    const node = svg.querySelector(`[data-object-id="${selected[0]}"] rect`)!;
    await fireEvent(node, pointer("pointerdown", 170, 180));
    await fireEvent(svg, pointer("pointermove", 180, 180));
    await fireEvent(svg, pointer("pointerup", 180, 180));
    expect(onchange).toHaveBeenCalledTimes(1);
    expect(onchange.mock.calls[0]![0].nodes[0].x).toBe(110);
    expect(onchange.mock.calls[0]![0].strokes).toEqual([outside]);
  });

  it("keeps raw sources until Apply, restores them exactly with Undo, and guards undownloaded edits", async () => {
    render(CanvasView);
    const list = await objectList();
    await selectObject(list, "Stroke 1"); await selectObject(list, "Stroke 2");
    await fireEvent.click(screen.getByRole("button", { name: /^Tidy/ }));
    expect(screen.getByRole("region", { name: "Proposal review" })).toBeTruthy();
    expect(within(list).getByText("Stroke 1")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Apply change" }));
    expect(within(list).queryByText("Stroke 2")).toBeNull();
    const unload = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    const restored = await downloadBoard();
    expect(restored.scene.strokes).toEqual(exampleDocument().scene.strokes);
    expect(restored.scene.nodes).toEqual(exampleDocument().scene.nodes);
    const downloaded = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(downloaded);
    expect(downloaded.defaultPrevented).toBe(false);
  });

  it("captures records honestly when PNG capture fails and refuses a proposal after the board changes", async () => {
    render(CanvasView);
    const list = await objectList(); await selectObject(list, "Illustrative context");
    await fireEvent.input(screen.getByLabelText("Instruction for a model packet"), { target: { value: "Move the selected note below the sketch." } });
    await fireEvent.click(screen.getByRole("button", { name: /^Capture selection packet/ }));
    await screen.findByText(/records only · PNG unavailable/);
    expect(screen.getByRole("alert").textContent).toContain("records only");
    await fireEvent.click(screen.getByRole("button", { name: "Download packet" }));
    const captured = JSON.parse(await downloads.at(-1)!.text()) as Packet;
    expect(captured.instruction).toBe("Move the selected note below the sketch.");
    expect(captured.selection.revision).toBe(captured.scene.revision);
    expect(captured.crop).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: "+ Add node" }));
    expect(screen.getByText("Captured packet is stale")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Import proposal" }) as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.change(screen.getByLabelText("Import proposal document"), { target: { files: [jsonFile({})] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("stale"));
    expect(screen.queryByRole("region", { name: "Proposal review" })).toBeNull();
  });

  it("defers a proposal that finishes reading during a stroke without losing the in-progress ink", async () => {
    render(CanvasView);
    const list = await objectList(); await selectObject(list, "Illustrative context");
    await fireEvent.input(screen.getByLabelText("Instruction for a model packet"), { target: { value: "Rename the note." } });
    await fireEvent.click(screen.getByRole("button", { name: /^Capture selection packet/ }));
    await screen.findByText(/records only · PNG unavailable/);
    await fireEvent.click(screen.getByRole("button", { name: "Download packet" }));
    const captured = JSON.parse(await downloads.at(-1)!.text()) as Packet;
    const proposal: Proposal = { format: "lychd.canvas.proposal/1", id: crypto.randomUUID(), scene_id: captured.scene.id, base_revision: captured.scene.revision, selection_ids: captured.selection.object_ids, author: "Deferred import fixture", summary: "Rename the selected note.", nodes: [{ ...captured.scene.nodes[0]!, label: "Imported label" }], edges: [], archive_stroke_ids: [] };
    let finishRead!: (text: string) => void;
    const text = new Promise<string>((resolve) => { finishRead = resolve; });
    const file = jsonFile(proposal, () => text);
    await fireEvent.change(screen.getByLabelText("Import proposal document"), { target: { files: [file] } });
    await fireEvent.click(screen.getByRole("button", { name: "Draw tool (D)" }));
    const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
    await fireEvent(svg, pointer("pointerdown", 170, 180));
    await fireEvent(svg, pointer("pointermove", 210, 200));
    await act(() => finishRead(JSON.stringify(proposal)));
    expect(screen.getByRole("alert").textContent).toContain("gesture, capture or preview began");
    expect(screen.queryByRole("region", { name: "Proposal review" })).toBeNull();
    await fireEvent(svg, pointer("pointerup", 210, 200));
    const saved = await downloadBoard();
    expect(saved.scene.strokes).toHaveLength(captured.scene.strokes.length + 1);
    expect(saved.scene.strokes.at(-1)!.points).toEqual([{ x: 100, y: 100 }, { x: 140, y: 120 }]);
    expect(saved.scene.nodes).toEqual(captured.scene.nodes);
  });

  it("rejects a malformed local document atomically and makes offline capability limits visible", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    render(CanvasView);
    expect(screen.getByText(/Voice, live model interpretation & image generation unavailable/)).toBeTruthy();
    await fireEvent.change(screen.getByLabelText("Open board document"), { target: { files: [jsonFile({ format: "other", scene: {} })] } });
    await screen.findByRole("alert");
    expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe(exampleDocument().scene.title);
    expect(fetch).not.toHaveBeenCalled();
  });
});
