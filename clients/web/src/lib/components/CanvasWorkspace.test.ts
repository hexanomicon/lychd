import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { blankDocument, commit, exampleDocument, undo } from "$lib/canvas/engine";
import type { AtlasMutation, AtlasProject } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn(), goto: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class extends Error {
    constructor(message: string, readonly status?: number, readonly code?: string) { super(message); }
  },
  bootstrapCanvasWorkspace: vi.fn(), getAtlasProject: vi.fn(), createCanvasProject: vi.fn(), changeAtlasProject: vi.fn()
}));
import { beforeNavigate, goto } from "$app/navigation";
import { ApiError, bootstrapCanvasWorkspace, changeAtlasProject, createCanvasProject, getAtlasProject } from "$lib/api/client";
import CanvasWorkspace from "./CanvasWorkspace.svelte";

const id = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
function project(patch: Partial<AtlasProject> = {}): AtlasProject {
  return { id, title: "Saved canvas", brief: "", brief_revision: 1, lifecycle: "active", next_action: "", version: 1,
    created_at: "2026-11-01T10:00:00Z", updated_at: "2026-11-01T10:00:00Z", concerns: [], assessments: [], decisions: [], references: [],
    canvas_document: blankDocument("Saved canvas"), workspace_state: "kept", builtin: false, ...patch };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => { resolve = accept; });
  return { promise, resolve };
}
async function rename(title: string) {
  const input = screen.getByLabelText("Board title");
  await fireEvent.input(input, { target: { value: title } });
  await fireEvent.blur(input);
}
function mutation(index = 0): AtlasMutation { return vi.mocked(changeAtlasProject).mock.calls[index]![1]; }
function pointer(type: string, x: number, y: number) {
  const event = new MouseEvent(type, { clientX: x, clientY: y, button: 0, bubbles: true, cancelable: true });
  Object.defineProperty(event, "pointerId", { value: 1 }); return event;
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAtlasProject).mockReset().mockResolvedValue(project());
  vi.mocked(bootstrapCanvasWorkspace).mockReset().mockResolvedValue(project({ builtin: true, title: "LychD" }));
  vi.mocked(createCanvasProject).mockReset().mockImplementation(async (body) => project({ id: body.id, title: body.canvas_document.scene.title, canvas_document: body.canvas_document, workspace_state: "draft" }));
  vi.mocked(changeAtlasProject).mockReset().mockImplementation(async (_id, body) => project({ version: body.expected_version + 1,
    ...(body.change.kind === "canvas.save" ? { canvas_document: body.change.canvas_document } : {}),
    ...(body.change.kind === "project.keep" ? { workspace_state: "kept" } : {}),
    ...(body.change.kind === "project.discard" ? { workspace_state: "discarded" } : {}) }));
  vi.mocked(goto).mockResolvedValue();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("opens the server-designated LychD map without creating a user draft", async () => {
  render(CanvasWorkspace);
  expect(await screen.findByText("Pinned LychD project")).toBeTruthy();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByText(/Static architecture map/)).toBeTruthy();
  expect(bootstrapCanvasWorkspace).toHaveBeenCalledOnce();
  expect(createCanvasProject).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Project record" }).getAttribute("href")).toBe(`/atlas/${id}`);
  expect((screen.getByRole("button", { name: "Save board" }) as HTMLButtonElement).disabled).toBe(true);
});

it("creates one identifiable blank draft and moves to its stable route", async () => {
  const view = render(CanvasWorkspace, { newRequested: true });
  await screen.findByText("Draft project");
  expect(createCanvasProject).toHaveBeenCalledOnce();
  const body = vi.mocked(createCanvasProject).mock.calls[0]![0];
  expect(body.canvas_document.scene.nodes).toEqual([]);
  expect(body.canvas_document.scene.strokes).toEqual([]);
  expect(goto).toHaveBeenCalledWith(`/canvas/${body.id}`, { replaceState: true });
  expect(bootstrapCanvasWorkspace).not.toHaveBeenCalled();
  vi.mocked(getAtlasProject).mockResolvedValue(project({ id: body.id, canvas_document: body.canvas_document, workspace_state: "draft" }));
  await view.rerender({ projectId: body.id, newRequested: false });
  await screen.findByLabelText("Board title");
  expect(getAtlasProject).toHaveBeenCalledWith(body.id, expect.any(AbortSignal));
  expect(createCanvasProject).toHaveBeenCalledOnce();
});

it("retains the creation UUID and blank document when creation has an unknown outcome", async () => {
  vi.mocked(createCanvasProject).mockRejectedValueOnce(new TypeError("Creation response lost"))
    .mockRejectedValueOnce(new ApiError("Authentication changed", 403));
  render(CanvasWorkspace, { newRequested: true });
  await screen.findByRole("button", { name: "Retry same request" });
  const original = structuredClone(vi.mocked(createCanvasProject).mock.calls[0]![0]);
  await fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await screen.findByText("Authentication changed");
  await fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await screen.findByText("Draft project");
  expect(vi.mocked(createCanvasProject).mock.calls.map(([body]) => body)).toEqual([original, original, original]);
});

it("retains the complete document history through save and leaves edits made during saving dirty", async () => {
  const saved = project({ canvas_document: exampleDocument() });
  vi.mocked(getAtlasProject).mockResolvedValue(saved);
  const response = deferred<AtlasProject>();
  vi.mocked(changeAtlasProject).mockReturnValueOnce(response.promise);
  render(CanvasWorkspace, { projectId: id });
  await screen.findByLabelText("Board title");
  await rename("First edit");
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  const first = mutation();
  expect(first.change.kind).toBe("canvas.save");
  if (first.change.kind !== "canvas.save") throw new Error("Expected board mutation");
  expect(first.change.canvas_document.past).toHaveLength(1);
  await rename("Later edit");
  await act(() => response.resolve(project({ version: 2, canvas_document: first.change.kind === "canvas.save" ? first.change.canvas_document : null })));
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe("Later edit");
  expect(screen.getByText("Local board changes have not been saved to LychD")).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Undo" }));
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe("First edit");
});

it("saves actual freehand ink, reopens it and retains Undo across the server document boundary", async () => {
  let retained = project();
  vi.mocked(changeAtlasProject).mockImplementation(async (_id, body) => {
    if (body.change.kind !== "canvas.save") throw new Error("Expected a document save");
    retained = project({ version: body.expected_version + 1, canvas_document: body.change.canvas_document });
    return retained;
  });
  const first = render(CanvasWorkspace, { projectId: id }); await screen.findByLabelText("Board title");
  await fireEvent.click(screen.getByRole("button", { name: "Draw tool (D)" }));
  const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
  await fireEvent(svg, pointer("pointerdown", 170, 180));
  await fireEvent(svg, pointer("pointermove", 210, 200));
  await fireEvent(svg, pointer("pointerup", 210, 200));
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await screen.findByText("Board retained in LychD · project version 2");
  expect(retained.canvas_document?.scene.strokes).toHaveLength(1);
  expect(retained.canvas_document?.scene.strokes[0]?.points).toEqual([{ x: 100, y: 100 }, { x: 140, y: 120 }]);
  first.unmount(); vi.mocked(getAtlasProject).mockResolvedValue(retained);
  render(CanvasWorkspace, { projectId: id }); await screen.findByLabelText("Board title");
  await fireEvent.click(screen.getByRole("button", { name: "Undo" }));
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await screen.findByText("Board retained in LychD · project version 3");
  expect(retained.canvas_document?.scene.strokes).toEqual([]);
  expect(retained.canvas_document?.future).toHaveLength(1);
  expect(retained.canvas_document?.future[0]?.strokes).toHaveLength(1);
});

it("keeps local edits unsaved after downloading a portable copy", async () => {
  vi.stubGlobal("URL", class extends URL { static override createObjectURL() { return "blob:canvas-copy"; } static override revokeObjectURL() {} });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  render(CanvasWorkspace, { projectId: id }); await screen.findByLabelText("Board title");
  await rename("Downloaded local edit");
  await fireEvent.click(screen.getByRole("button", { name: /^Download board/ }));
  expect(changeAtlasProject).not.toHaveBeenCalled();
  expect(screen.getByText("Local board changes have not been saved to LychD")).toBeTruthy();
  const unload = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
});

it("imports portable content into the retained board identity without losing ink, objects or history", async () => {
  const retained = project();
  const retainedSceneId = retained.canvas_document!.scene.id;
  let imported = exampleDocument();
  imported = commit(imported, { ...imported.scene, title: "Imported stage one" });
  imported = commit(imported, { ...imported.scene, title: "Imported stage two" });
  imported = undo(imported);
  expect(imported.scene.id).not.toBe(retainedSceneId);
  vi.mocked(getAtlasProject).mockResolvedValue(retained);
  vi.mocked(changeAtlasProject).mockImplementation(async (_id, body) => {
    if (body.change.kind !== "canvas.save") throw new Error("Expected a board save");
    const document = body.change.canvas_document;
    if ([document.scene, ...document.past, ...document.future].some((entry) => entry.id !== retainedSceneId)) {
      throw new ApiError("Retained board identity cannot change", 409, "atlas_write_rejected");
    }
    return project({ version: 2, canvas_document: document });
  });
  render(CanvasWorkspace, { projectId: id }); await screen.findByLabelText("Board title");
  const file = new File([JSON.stringify(imported)], "portable.canvas.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => JSON.stringify(imported) });
  await fireEvent.change(screen.getByLabelText("Open board document"), { target: { files: [file] } });
  await screen.findByText(/Imported portable.canvas.json into this project board/);
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await screen.findByText("Board retained in LychD · project version 2");
  const change = mutation().change;
  if (change.kind !== "canvas.save") throw new Error("Expected a board save");
  const expected = { ...imported, scene: { ...imported.scene, id: retainedSceneId },
    past: imported.past.map((entry) => ({ ...entry, id: retainedSceneId })),
    future: imported.future.map((entry) => ({ ...entry, id: retainedSceneId })) };
  const highestRevision = Math.max(...[retained.canvas_document!.scene, ...retained.canvas_document!.past, ...retained.canvas_document!.future,
    imported.scene, ...imported.past, ...imported.future].map((entry) => entry.revision));
  expect(change.canvas_document).toEqual({ ...expected, scene: { ...expected.scene, revision: highestRevision + 1 } });
  expect(change.canvas_document.scene.nodes).toEqual(imported.scene.nodes);
  expect(change.canvas_document.scene.strokes).toEqual(imported.scene.strokes);
});

it("retries an uncertain save unchanged after a later middleware refusal and preserves newer local edits", async () => {
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new TypeError("Response lost"))
    .mockRejectedValueOnce(new ApiError("Access refused", 403));
  render(CanvasWorkspace, { projectId: id });
  await screen.findByLabelText("Board title");
  await rename("Prepared edit");
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await screen.findByRole("button", { name: "Retry same request" });
  const prepared = structuredClone(mutation());
  await rename("Newer local edit");
  await fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await screen.findByText("Access refused");
  expect(screen.getByRole("button", { name: "Retry same request" })).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await screen.findByText(/Board saved to LychD/);
  expect(mutation(1)).toEqual(prepared); expect(mutation(2)).toEqual(prepared);
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe("Newer local edit");
  expect(screen.getByText("Local board changes have not been saved to LychD")).toBeTruthy();
});

it("keeps a conflicting local document and requires explicit comparison and a fresh save identity", async () => {
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new ApiError("Version changed", 409, "atlas_write_rejected"));
  vi.mocked(getAtlasProject).mockResolvedValueOnce(project()).mockResolvedValueOnce(project({ version: 7, canvas_document: blankDocument("Concurrent board") }));
  render(CanvasWorkspace, { projectId: id });
  await screen.findByLabelText("Board title"); await rename("My preserved board");
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await screen.findByText(/Your local board is preserved/);
  await fireEvent.click(screen.getByRole("button", { name: "Load saved version for comparison" }));
  await screen.findByText(/Saved project version 7/);
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe("My preserved board");
  await fireEvent.click(screen.getByRole("button", { name: "Use saved version as save basis" }));
  expect(changeAtlasProject).toHaveBeenCalledOnce();
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await waitFor(() => expect(changeAtlasProject).toHaveBeenCalledTimes(2));
  expect(mutation(1).expected_version).toBe(7);
  expect(mutation(1).request_id).not.toBe(mutation().request_id);
  expect(mutation(1).change).toMatchObject({ kind: "canvas.save", canvas_document: { scene: { title: "My preserved board" } } });
});

it("waits for a definitive discard outcome before leaving and never offers discard for kept projects", async () => {
  vi.mocked(getAtlasProject).mockResolvedValue(project({ workspace_state: "draft" }));
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new TypeError("Discard response lost"));
  render(CanvasWorkspace, { projectId: id });
  await screen.findByText("Draft project");
  await fireEvent.click(screen.getByRole("button", { name: "Discard draft" }));
  await screen.findByRole("button", { name: "Retry same request" });
  expect(goto).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await waitFor(() => expect(goto).toHaveBeenCalledWith("/atlas", undefined));
  expect(mutation(1)).toEqual(mutation());
});

it("fences a late project read after switching identities", async () => {
  const old = deferred<AtlasProject>();
  vi.mocked(getAtlasProject).mockReturnValueOnce(old.promise).mockResolvedValueOnce(project({ id: other, canvas_document: blankDocument("Other board") }));
  const view = render(CanvasWorkspace, { projectId: id });
  await view.rerender({ projectId: other });
  await screen.findByLabelText("Board title");
  await act(() => old.resolve(project({ canvas_document: blankDocument("Late old board") })));
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe("Other board");
});

it.each(["A".repeat(200), `${"A".repeat(119)}😀${"Z".repeat(80)}`])("attaches a Unicode-bounded board to a legacy project without changing its record identity or title", async (title) => {
  const boardTitle = Array.from(title).slice(0, 120).join("");
  vi.mocked(getAtlasProject).mockResolvedValue(project({ title, canvas_document: null }));
  render(CanvasWorkspace, { projectId: id });
  await screen.findByLabelText("Board title");
  expect((screen.getByLabelText("Board title") as HTMLInputElement).value).toBe(boardTitle);
  expect(screen.getByRole("heading", { name: title })).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Save board" }));
  await waitFor(() => expect(changeAtlasProject).toHaveBeenCalledOnce());
  expect(vi.mocked(changeAtlasProject).mock.calls[0]![0]).toBe(id);
  expect(mutation().change).toMatchObject({ kind: "canvas.save", canvas_document: { scene: { title: boardTitle } } });
  expect(mutation().change).not.toHaveProperty("title");
});

it("reconciles two legacy tabs by retaining the first attached scene identity and preserving the second tab's local content", async () => {
  let retained = project({ canvas_document: null });
  vi.mocked(getAtlasProject).mockImplementation(async () => structuredClone(retained));
  vi.mocked(changeAtlasProject).mockImplementation(async (_id, body) => {
    if (body.expected_version !== retained.version) throw new ApiError("Version changed", 409, "atlas_write_rejected");
    if (body.change.kind !== "canvas.save") throw new Error("Expected a document save");
    if (retained.canvas_document && body.change.canvas_document.scene.id !== retained.canvas_document.scene.id) {
      throw new ApiError("Retained board identity cannot change", 409, "atlas_write_rejected");
    }
    retained = { ...retained, version: retained.version + 1, canvas_document: structuredClone(body.change.canvas_document) };
    return structuredClone(retained);
  });
  const first = render(CanvasWorkspace, { projectId: id });
  await within(first.container).findByLabelText("Board title");
  const second = render(CanvasWorkspace, { projectId: id });
  const local = within(second.container);
  const title = await local.findByLabelText("Board title");
  await fireEvent.input(title, { target: { value: "Second tab's ink" } }); await fireEvent.blur(title);
  await fireEvent.click(local.getByRole("button", { name: "Draw tool (D)" }));
  const svg = local.getByRole("application", { name: "Canvas drawing surface" });
  await fireEvent(svg, pointer("pointerdown", 170, 180)); await fireEvent(svg, pointer("pointermove", 210, 200)); await fireEvent(svg, pointer("pointerup", 210, 200));
  await fireEvent.click(within(first.container).getByRole("button", { name: "Save board" }));
  await within(first.container).findByText("Board retained in LychD · project version 2");
  const primaryId = retained.canvas_document!.scene.id;
  await fireEvent.click(local.getByRole("button", { name: "Save board" }));
  await local.findByText(/Your local board is preserved/);
  const refused = mutation(1).change;
  if (refused.kind !== "canvas.save") throw new Error("Expected a document save");
  expect(refused.canvas_document.scene.id).not.toBe(primaryId);
  await fireEvent.click(local.getByRole("button", { name: "Load saved version for comparison" }));
  await local.findByText(/Saved project version 2/);
  await fireEvent.click(local.getByRole("button", { name: "Use saved version as save basis" }));
  expect((local.getByLabelText("Board title") as HTMLInputElement).value).toBe("Second tab's ink");
  await fireEvent.click(local.getByRole("button", { name: "Save board" }));
  await local.findByText("Board retained in LychD · project version 3");
  const accepted = mutation(2).change;
  if (accepted.kind !== "canvas.save") throw new Error("Expected a document save");
  expect(accepted.canvas_document.scene.id).toBe(primaryId);
  expect(accepted.canvas_document.scene.revision).toBeGreaterThan(refused.canvas_document.scene.revision);
  expect(accepted.canvas_document.scene.nodes).toEqual(refused.canvas_document.scene.nodes);
  expect(accepted.canvas_document.scene.strokes).toEqual(refused.canvas_document.scene.strokes);
  expect(accepted.canvas_document.past).toEqual(refused.canvas_document.past.map((entry) => ({ ...entry, id: primaryId })));
  expect(mutation(2).request_id).not.toBe(mutation(1).request_id);
});

it("blocks replacement during an active gesture and warns on unsaved local edits", async () => {
  render(CanvasWorkspace, { projectId: id }); await screen.findByLabelText("Board title");
  await rename("Unsaved board");
  const unload = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Draw tool (D)" }));
  const svg = screen.getByRole("application", { name: "Canvas drawing surface" });
  const pointer = new MouseEvent("pointerdown", { clientX: 170, clientY: 180, button: 0, bubbles: true });
  Object.defineProperty(pointer, "pointerId", { value: 1 });
  await fireEvent(svg, pointer);
  expect((screen.getByRole("button", { name: "New canvas" }) as HTMLButtonElement).disabled).toBe(true);
  const cancel = vi.fn();
  const callback = vi.mocked(beforeNavigate).mock.calls[0]![0];
  callback({ cancel, type: "link", willUnload: false, to: null, from: null } as unknown as Parameters<typeof callback>[0]);
  expect(cancel).toHaveBeenCalledOnce();
});
