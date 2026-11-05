import { render, screen } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";
vi.mock("$app/state", async () => { const { SvelteURL } = await import("svelte/reactivity"); return { page: { state: {}, url: new SvelteURL("http://localhost/bridge") } }; });
vi.mock("$app/navigation", () => ({ goto: vi.fn(), afterNavigate: vi.fn(), beforeNavigate: vi.fn() }));
vi.mock("$lib/api/client", () => ({ ApiError: class extends Error {}, getArchiveProfile: vi.fn().mockRejectedValue(new Error()), getArchiveBridgeDefault: vi.fn(), listArchiveNotes: vi.fn(), getArchiveNote: vi.fn(), admitArchiveNote: vi.fn(), promoteArchiveNote: vi.fn(), revokeArchiveNote: vi.fn(), registerArchiveGeneration: vi.fn(), deriveArchiveNote: vi.fn(), inspectArchiveDerivation: vi.fn(), discoverArchiveGeneration: vi.fn(), recallArchiveSemanticNotes: vi.fn(), inspectArchiveSemanticRecall: vi.fn(), resolveArchiveSemanticRecall: vi.fn() }));
import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { getArchiveProfile, admitArchiveNote, discoverArchiveGeneration, recallArchiveSemanticNotes, inspectArchiveSemanticRecall, resolveArchiveSemanticRecall } from "$lib/api/client";
import Page from "./+page.svelte";
beforeEach(() => { vi.clearAllMocks(); });
it.each(["notes=new&notes=manage", "notes=invalid", "notes=new&investigation=new", "notes=manage&investigation=", "notes=recall&notes=recall", "notes=recall&notes=manage", "notes=recall&investigation=new", "notes=recall&investigation="])("rejects ambiguous focus %s without reads or admission", async (query) => {
  page.url.href = `http://localhost/bridge?${query}`; const view = render(Page);
  expect(screen.getByRole("heading", { name: "Public-note selection unavailable" })).toBeTruthy(); expect(getArchiveProfile).not.toHaveBeenCalled(); expect(admitArchiveNote).not.toHaveBeenCalled(); expect(discoverArchiveGeneration).not.toHaveBeenCalled(); expect(recallArchiveSemanticNotes).not.toHaveBeenCalled(); expect(inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(resolveArchiveSemanticRecall).not.toHaveBeenCalled(); view.unmount();
});
it("dispatches closed notes focus to metadata independently from conversation", async () => {
  page.url.href = "http://localhost/bridge?notes=manage"; const view = render(Page); await screen.findByRole("heading", { name: "Public notes" }); expect(getArchiveProfile).toHaveBeenCalledTimes(1); expect(admitArchiveNote).not.toHaveBeenCalled(); view.unmount();
});

it("dispatches recall to its separate metadata-only source form with no semantic or management operation", async () => {
  vi.mocked(getArchiveProfile).mockResolvedValueOnce({ profile: "local-public-notes@1", namespace_id: "00000000-0000-4000-8000-000000000001", owner_subject: { identity: "owner" }, policy_revision: "policy" });
  vi.mocked(discoverArchiveGeneration).mockResolvedValueOnce({ generation_id: "00000000-0000-4000-8000-000000000002", manifest_digest: "a".repeat(64) });
  page.url.href = "http://localhost/bridge?notes=recall"; const view = render(Page);
  await screen.findByText("Configured profile and generation"); expect(screen.getByRole("heading", { name: "Recall public sources" })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Retained metadata" })).toBeNull();
  expect(getArchiveProfile).toHaveBeenCalledTimes(1); expect(discoverArchiveGeneration).toHaveBeenCalledTimes(1);
  expect(admitArchiveNote).not.toHaveBeenCalled(); expect(recallArchiveSemanticNotes).not.toHaveBeenCalled(); expect(inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(resolveArchiveSemanticRecall).not.toHaveBeenCalled(); view.unmount();
});
