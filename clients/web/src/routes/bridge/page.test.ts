import { fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";
vi.mock("$app/state", async () => { const { SvelteURL } = await import("svelte/reactivity"); return { page: { state: {}, url: new SvelteURL("http://localhost/bridge") } }; });
vi.mock("$app/navigation", () => ({ goto: vi.fn(), afterNavigate: vi.fn(), beforeNavigate: vi.fn() }));
vi.mock("$lib/api/client", () => ({ ApiError: class extends Error {}, getArchiveProfile: vi.fn().mockRejectedValue(new Error()), getArchiveBridgeDefault: vi.fn(), listArchiveNotes: vi.fn(), getArchiveNote: vi.fn(), admitArchiveNote: vi.fn(), promoteArchiveNote: vi.fn(), revokeArchiveNote: vi.fn(), registerArchiveGeneration: vi.fn(), deriveArchiveNote: vi.fn(), inspectArchiveDerivation: vi.fn(), discoverArchiveGeneration: vi.fn(), recallArchiveSemanticNotes: vi.fn(), inspectArchiveSemanticRecall: vi.fn(), resolveArchiveSemanticRecall: vi.fn() }));
import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { getArchiveProfile, admitArchiveNote, discoverArchiveGeneration, recallArchiveSemanticNotes, inspectArchiveSemanticRecall, resolveArchiveSemanticRecall } from "$lib/api/client";
import Page from "./+page.svelte";
import { createMemoryPanel, setMemoryPanel } from "$lib/memory/panel.svelte";
beforeEach(() => { vi.clearAllMocks(); });
it.each(["notes=new&notes=manage", "notes=invalid", "notes=new&investigation=new", "notes=manage&investigation=", "notes=recall&notes=recall", "notes=recall&notes=manage", "notes=recall&investigation=new", "notes=recall&investigation="])("rejects ambiguous focus %s without reads or admission", async (query) => {
  page.url.href = `http://localhost/bridge?${query}`; const view = render(Page);
  expect(screen.getByRole("heading", { name: "Public-note selection unavailable" })).toBeTruthy(); expect(getArchiveProfile).not.toHaveBeenCalled(); expect(admitArchiveNote).not.toHaveBeenCalled(); expect(discoverArchiveGeneration).not.toHaveBeenCalled(); expect(recallArchiveSemanticNotes).not.toHaveBeenCalled(); expect(inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(resolveArchiveSemanticRecall).not.toHaveBeenCalled(); view.unmount();
});
it.each(["manage", "new", "recall", "00000000-0000-4000-8000-000000000099"])("routes compatibility focus %s to the existing shell manager without mounting another", async (selection) => {
  const memory = createMemoryPanel();
  function Wrapper(...args: Parameters<typeof Page>) { setMemoryPanel(memory); return Page(...args); }
  page.url.href = `http://localhost/bridge?notes=${selection}`;
  const view = render(Wrapper);
  await fireEvent.click(screen.getByRole("button", { name: "Open Memory" }));
  expect(memory.section).toBe(selection === "recall" ? "recall" : "notes");
  expect(memory.notesSelection).toBe(selection === "recall" ? "manage" : selection);
  expect(getArchiveProfile).not.toHaveBeenCalled(); expect(admitArchiveNote).not.toHaveBeenCalled();
  expect(discoverArchiveGeneration).not.toHaveBeenCalled(); expect(recallArchiveSemanticNotes).not.toHaveBeenCalled();
  expect(inspectArchiveSemanticRecall).not.toHaveBeenCalled(); expect(resolveArchiveSemanticRecall).not.toHaveBeenCalled();
  view.unmount();
});
