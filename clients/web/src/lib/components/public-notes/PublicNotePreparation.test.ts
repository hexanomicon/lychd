import { fireEvent, render, screen } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";
import { initialPreparationState, type PublicNotePreparation as Controller, type PreparationTarget } from "$lib/archive/preparation";
import PublicNotePreparation from "./PublicNotePreparation.svelte";
const id = "00000000-0000-4000-8000-000000000001";
const target: PreparationTarget = { profile: { profile: "local-public-notes@1", namespace_id: id, owner_subject: { identity: "<script>owner</script>" }, policy_revision: "p" },
  request: { generation: { generation_id: id, manifest_digest: "a".repeat(64) }, source: { record_id: id, revision_digest: "b".repeat(64), lifecycle_version: 2 } },
  sourceKey: "<script>source</script>", sourceRevision: "r1", sourceDigest: "c".repeat(64) };
function controller() { return { contextVersion: 0, review: vi.fn(), cancelReview: vi.fn(), prepare: vi.fn().mockResolvedValue(undefined), register: vi.fn().mockResolvedValue(undefined),
  loadGeneration: vi.fn().mockResolvedValue(undefined), check: vi.fn().mockResolvedValue(undefined) } as unknown as Controller; }
it("uses native independently named controls and escapes reviewed source/profile identities", async () => {
  const actions = controller(), state = { ...initialPreparationState(), generation: target.request.generation, configuration: "configured" as const, eligible: true, review: target };
  const view = render(PublicNotePreparation, { state, controller: actions, blocked: false, recordAvailable: true });
  expect(document.querySelector("script")).toBeNull(); expect(screen.getByText(target.sourceKey + " · r1")).toBeTruthy();
  expect(screen.getByText(/Another attempt may repeat compute/)).toBeTruthy(); expect(screen.getByText(/no occurrence UUID/)).toBeTruthy();
  expect(actions.prepare).not.toHaveBeenCalled(); expect(actions.register).not.toHaveBeenCalled(); expect(actions.check).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Review preparation" })); expect(screen.getByRole("heading", { name: "Review exact preparation" })).toBe(document.activeElement);
  await fireEvent.click(screen.getByRole("button", { name: "Prepare this promoted revision" })); expect(actions.prepare).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("heading", { name: "Latest preparation metadata" })).toBe(document.activeElement);
  await fireEvent.click(screen.getByRole("button", { name: "Register configured generation" })); expect(actions.register).toHaveBeenCalledTimes(1);
  await fireEvent.click(screen.getByRole("button", { name: "Check preparation" })); expect(actions.check).toHaveBeenCalledWith(); view.unmount();
});
it("keeps frozen/historical Check separate from current metadata and never presents lost invocation as settled", async () => {
  const actions = controller(); const state = { ...initialPreparationState(), generation: target.request.generation, configuration: "configured" as const,
    frozen: target, historical: { ...target, request: { ...target.request, source: { ...target.request.source, lifecycle_version: 1 } } }, unknown: true };
  const view = render(PublicNotePreparation, { state, controller: actions, blocked: false, recordAvailable: false });
  expect((screen.getByRole("button", { name: "Check preparation" }) as HTMLButtonElement).disabled).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Check frozen preparation reference" })); expect(actions.check).toHaveBeenLastCalledWith("frozen");
  await fireEvent.click(screen.getByRole("button", { name: "Check previous historical reference" })); expect(actions.check).toHaveBeenLastCalledWith("historical");
  expect(screen.getByText(/Earlier preparation outcome remains unknown/)).toBeTruthy(); expect(screen.getByText(/no historical lifecycle version is guessed/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Open separate public-source recall" }).getAttribute("href")).toBe("/bridge?notes=recall");
  view.unmount();
});
it.each(["preparing", "registering", "checking"] as const)("disables duplicate controls during %s without making a request", (operation) => {
  const actions = controller(); const state = { ...initialPreparationState(), generation: target.request.generation, configuration: "configured" as const, review: target, eligible: true, operation };
  const view = render(PublicNotePreparation, { state, controller: actions, blocked: false, recordAvailable: true });
  expect([...document.querySelectorAll("button")].every((button) => button.disabled)).toBe(true); expect(actions.prepare).not.toHaveBeenCalled(); expect(actions.check).not.toHaveBeenCalled(); view.unmount();
});
it("an old rendered effectful gesture cannot use a newer controller context", async () => {
  const actions = controller(); const state = { ...initialPreparationState(), generation: target.request.generation, configuration: "configured" as const, review: target, eligible: true };
  const view = render(PublicNotePreparation, { state, controller: actions, blocked: false, recordAvailable: true });
  Object.defineProperty(actions, "contextVersion", { value: 1 });
  await fireEvent.click(screen.getByRole("button", { name: "Register configured generation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Prepare this promoted revision" }));
  expect(actions.register).not.toHaveBeenCalled(); expect(actions.prepare).not.toHaveBeenCalled(); view.unmount();
});
