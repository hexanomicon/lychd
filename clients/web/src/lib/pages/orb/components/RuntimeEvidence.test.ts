import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";
import { projectRuntime } from "$lib/pages/orb/state/runtime-projection";
import { runtimeEvent, runtimeSnapshot } from "$lib/pages/orb/state/__fixtures__/runtime";
import RuntimeEvidence from "./RuntimeEvidence.svelte";
it("makes uninstrumented topology and non-Run call details readable without canvas or motion", async () => {
  const snapshot = runtimeSnapshot(), field = projectRuntime(snapshot);
  const selected = [...field.selections.values()].find(item => "activities" in item);
  const onselect = vi.fn();
  const view = render(RuntimeEvidence, { state: { snapshot, received: new Set<string>(), loading: false, error: "", stale: false }, field, selected, onselect, onrefresh: vi.fn() });
  const inspector = screen.getByRole("region", { name: "Selected runtime activity" });
  expect(within(inspector).getByText("No Run correlation supplied")).toBeTruthy();
  expect(within(inspector).getByText("HTTP status")).toBeTruthy();
  expect(within(inspector).getByText("Owner effect outcome")).toBeTruthy();
  expect(screen.getByText("gateway not instrumented")).toBeTruthy();
  const resource = screen.getByRole("button", { name: /resource.*service/ });
  await fireEvent.click(resource);
  expect(onselect).toHaveBeenCalledOnce();
  view.unmount();
});


it("keeps unresolved custody and foreign Run references explicit while showing supplied native correlations", () => {
  const event = runtimeEvent(7, { run_id: "isolated-run", producer_generation: "producer-generation", producer_seq: 4,
    station_key: "answer", step_id: "entered-step", native_event_id: "native-event", native_seq: 0 });
  const snapshot = runtimeSnapshot([event]);
  snapshot.sources[0]!.registrant_id = null;
  const field = projectRuntime(snapshot);
  const selected = [...field.selections.values()].find(item => "activities" in item);
  const view = render(RuntimeEvidence, { state: { snapshot, received: new Set<string>(), loading: false, error: "", stale: false }, field, selected, onselect: vi.fn(), onrefresh: vi.fn() });
  expect(screen.getByText("Unresolved custody")).toBeTruthy();
  const inspector = screen.getByRole("region", { name: "Selected runtime activity" });
  expect(within(inspector).getByText("isolated-run · attributed to fixture")).toBeTruthy();
  expect(inspector.querySelector('a[href^="/orb/"]')).toBeNull();
  for (const text of ["answer", "entered-step", "native-event", "producer-generation", "Native event sequence"]) {
    expect(within(inspector).getByText(text)).toBeTruthy();
  }
  expect(within(inspector).getByText("0")).toBeTruthy();
  view.unmount();
});
