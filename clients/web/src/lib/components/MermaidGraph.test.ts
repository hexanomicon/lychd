import { act, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";

const renderer = vi.hoisted(() => {
  let finishImport!: () => void;
  const imported = new Promise<void>((resolve) => { finishImport = resolve; });
  return {
    imported,
    finishImport,
    initialize: vi.fn(),
    run: vi.fn<(options: { nodes: HTMLElement[]; suppressErrors: boolean }) => Promise<void>>()
  };
});

vi.mock("mermaid", async () => {
  await renderer.imported;
  return { default: { initialize: renderer.initialize, run: renderer.run } };
});

import MermaidGraph from "./MermaidGraph.svelte";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((accept) => { resolve = accept; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  renderer.run.mockResolvedValue(undefined);
});

it("does not start a diagram whose module loads after the lens is destroyed", async () => {
  const view = render(MermaidGraph, { source: "flowchart TD\nA --> B", label: "First score" });
  await act(async () => { await Promise.resolve(); });

  view.unmount();
  await act(() => renderer.finishImport());
  await vi.dynamicImportSettled();

  expect(renderer.initialize).not.toHaveBeenCalled();
  expect(renderer.run).not.toHaveBeenCalled();
});

it("keeps an earlier render from overwriting the replacement score", async () => {
  const first = deferred();
  const second = deferred();
  const targets: HTMLElement[] = [];
  renderer.run.mockImplementation(async ({ nodes }) => {
    const target = nodes[0];
    if (!target) throw new Error("A diagram target is required.");
    targets.push(target);
    const original = targets.length === 1;
    await (original ? first.promise : second.promise);
    target.textContent = original ? "Earlier diagram" : "Replacement diagram";
  });
  const view = render(MermaidGraph, { source: "flowchart TD\nA --> B", label: "First score" });
  await waitFor(() => expect(renderer.run).toHaveBeenCalledOnce());

  await view.rerender({ source: "flowchart TD\nC --> D", label: "Replacement score" });
  await waitFor(() => expect(renderer.run).toHaveBeenCalledTimes(2));
  await act(() => second.resolve());
  expect(screen.getByText("Replacement diagram")).toBeTruthy();
  await act(() => first.resolve());

  expect(screen.getByText("Replacement diagram")).toBeTruthy();
  expect(screen.queryByText("Earlier diagram")).toBeNull();
  expect(targets[0]?.isConnected).toBe(false);
  view.unmount();
});

it("reports a current render failure and clears it for a replacement score", async () => {
  renderer.run.mockRejectedValueOnce(new Error("Diagram failed"));
  const view = render(MermaidGraph, { source: "invalid score", label: "First score" });

  expect(await screen.findByRole("status")).toHaveProperty(
    "textContent", "Diagram unavailable. The semantic score remains authoritative."
  );
  await view.rerender({ source: "flowchart TD\nA --> B", label: "Replacement score" });
  await waitFor(() => expect(renderer.run).toHaveBeenCalledTimes(2));

  expect(screen.queryByRole("status")).toBeNull();
  expect(renderer.initialize).toHaveBeenLastCalledWith(expect.objectContaining({ securityLevel: "strict" }));
  view.unmount();
});
