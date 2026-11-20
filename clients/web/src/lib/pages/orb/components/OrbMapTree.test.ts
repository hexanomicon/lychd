import { fireEvent, render, within } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";
import { fixtureRun, pattern } from "../state/__fixtures__/snapshot";
import OrbMapTree from "./OrbMapTree.svelte";

it("opens the selected occurrence and follows only records supplied in the viewed lens", async () => {
  const snapshot = fixtureRun("import-review");
  const first = snapshot.evidence[0]!;
  const later = { ...first, event_id: "retry", seq: 1, occurrence_id: "second", summary: "Retry entered" };
  const onevent = vi.fn();
  const common = {
    runs: [snapshot.run],
    selectedRun: snapshot.run.run_id,
    selectedEvent: first.event_id,
    selectedNode: null,
    runtime: { nodes: [], edges: [], identity: "runtime" },
    onevent,
    onrun: vi.fn(),
    onruntime: vi.fn(),
  };
  const earlier = new Map([[snapshot.run.run_id, { snapshot, pattern }]]);
  const view = render(OrbMapTree, { ...common, lenses: earlier });
  const tree = within(view.container);
  await fireEvent.click(tree.getByRole("button", { name: "#0 · Inspect entered" }));
  expect(onevent).toHaveBeenCalledWith("import-review", first.event_id, expect.any(HTMLElement));
  expect(tree.queryByText(/Retry entered/)).toBeNull();
  await view.rerender({
    ...common,
    selectedEvent: later.event_id,
    lenses: new Map([
      [snapshot.run.run_id, { snapshot: { ...snapshot, evidence: [first, later] }, pattern }],
    ]),
  });
  expect(tree.getByRole("button", { name: "#1 · Retry entered" }).getAttribute("aria-pressed")).toBe("true");
  await view.rerender({ ...common, lenses: earlier });
  expect(tree.queryByText(/Retry entered/)).toBeNull();
  view.unmount();
});
