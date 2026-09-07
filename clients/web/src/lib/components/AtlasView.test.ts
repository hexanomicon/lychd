import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type { AtlasCatalogue, AtlasConcern, AtlasProject, AtlasReference } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn(), beforeNavigate: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class extends Error {
    constructor(message: string, readonly status?: number, readonly code?: string) { super(message); }
  },
  getAtlasProjects: vi.fn(),
  getAtlasProject: vi.fn(),
  createAtlasProject: vi.fn(),
  changeAtlasProject: vi.fn()
}));

import { beforeNavigate, goto } from "$app/navigation";
import {
  ApiError,
  changeAtlasProject,
  createAtlasProject,
  getAtlasProject,
  getAtlasProjects
} from "$lib/api/client";
import AtlasView from "./AtlasView.svelte";

const projectId = "11111111-1111-4111-8111-111111111111";
const otherProjectId = "22222222-2222-4222-8222-222222222222";
const concernId = "33333333-3333-4333-8333-333333333333";
const otherConcernId = "44444444-4444-4444-8444-444444444444";
const now = "2026-09-06T10:00:00Z";

const concern: AtlasConcern = {
  id: concernId,
  statement: "Can support recover a failed deployment?",
  criteria: "A documented recovery path is available.",
  revision: 1
};

function project(patch: Partial<AtlasProject> = {}): AtlasProject {
  return {
    id: projectId,
    title: "Care for the release",
    brief: "Keep the release supportable.",
    lifecycle: "active",
    next_action: "Review the recovery guide.",
    version: 1,
    brief_revision: 1,
    created_at: now,
    updated_at: now,
    concerns: [],
    assessments: [],
    decisions: [],
    references: [],
    ...patch
  };
}

function catalogue(p: AtlasProject): AtlasCatalogue {
  return {
    projects: [{
      id: p.id,
      title: p.title,
      brief: p.brief,
      lifecycle: p.lifecycle,
      next_action: p.next_action,
      version: p.version,
      updated_at: p.updated_at,
      concern_count: p.concerns.length,
      unassessed_count: p.concerns.length,
      review_needed_count: 0,
      insufficient_count: 0,
      disputed_count: 0
    }],
    total: 1,
    limit: 50,
    offset: 0
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => { resolve = accept; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAtlasProjects).mockReset().mockResolvedValue({ projects: [], total: 0, limit: 50, offset: 0 });
  vi.mocked(getAtlasProject).mockReset().mockResolvedValue(project());
  vi.mocked(createAtlasProject).mockReset().mockResolvedValue(project());
  vi.mocked(changeAtlasProject).mockReset().mockResolvedValue(project({ version: 2 }));
  vi.mocked(goto).mockReset().mockResolvedValue();
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("distinguishes a failed catalogue read from a genuinely empty Atlas", async () => {
  vi.mocked(getAtlasProjects).mockRejectedValueOnce(new ApiError("Unavailable", 503));
  render(AtlasView);
  expect((await screen.findByRole("alert")).textContent).toContain("Atlas could not be loaded");
  expect(screen.queryByText("A place for work that lasts")).toBeNull();

  await fireEvent.click(screen.getByRole("button", { name: "Retry loading" }));
  expect(await screen.findByText("A place for work that lasts")).toBeTruthy();
  expect(createAtlasProject).not.toHaveBeenCalled();
});

it("creates an project without starting a conversation and retries uncertain delivery unchanged", async () => {
  vi.mocked(createAtlasProject).mockRejectedValueOnce(new TypeError("Connection lost"));
  render(AtlasView);
  await screen.findByText("A place for work that lasts");
  await fireEvent.click(screen.getByRole("button", { name: "New project" }));
  const name = screen.getByLabelText(/Name required/) as HTMLInputElement;
  await fireEvent.input(name, { target: { value: "Watch the orchard" } });
  await fireEvent.input(screen.getByRole("textbox", { name: "Brief" }), { target: { value: "Care for the trees through the seasons." } });
  await fireEvent.submit(screen.getByRole("form", { name: "New project" }));

  await screen.findByRole("button", { name: "Retry same save" });
  expect(name.matches(":disabled")).toBe(true);
  const original = vi.mocked(createAtlasProject).mock.calls[0]![0];
  expect(original.title).toBe("Watch the orchard");
  expect(original.id).toMatch(/^[\da-f-]{36}$/i);
  await fireEvent.click(screen.getByRole("button", { name: "Retry same save" }));
  expect(createAtlasProject).toHaveBeenCalledTimes(2);
  expect(vi.mocked(createAtlasProject).mock.calls[1]![0]).toEqual(original);
  expect(goto).toHaveBeenCalledWith(`/atlas/${projectId}`);
  expect(changeAtlasProject).not.toHaveBeenCalled();
});

it("keeps an uncertain mutation's request identity, version, and payload for retry", async () => {
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new ApiError("Response lost", 502));
  render(AtlasView, { projectId });
  await screen.findByRole("heading", { level: 1, name: "Care for the release" });
  await fireEvent.click(screen.getByRole("button", { name: "Edit project" }));
  await fireEvent.input(screen.getByLabelText("Proposed next step"), { target: { value: "Ask support to review the guide." } });
  await fireEvent.submit(screen.getByRole("form", { name: "Edit project" }));
  await screen.findByRole("button", { name: "Retry same save" });
  const original = vi.mocked(changeAtlasProject).mock.calls[0]!;
  expect(original[1].expected_version).toBe(1);
  await fireEvent.click(screen.getByRole("button", { name: "Retry same save" }));
  expect(vi.mocked(changeAtlasProject).mock.calls[1]).toEqual(original);
  expect(await screen.findByText("Saved to Atlas.")).toBeTruthy();
});

it("preserves a conflict draft and requires explicit comparison before enabling a new save", async () => {
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new ApiError("Version changed", 409));
  const latest = project({ version: 7, brief_revision: 2, brief: "Another editor changed this brief.", next_action: "Another editor's next step." });
  vi.mocked(getAtlasProject).mockResolvedValueOnce(project()).mockResolvedValueOnce(latest);
  render(AtlasView, { projectId });
  await screen.findByRole("button", { name: "Edit project" });
  await fireEvent.click(screen.getByRole("button", { name: "Edit project" }));
  await fireEvent.input(screen.getByRole("textbox", { name: "Brief" }), { target: { value: "My carefully written brief." } });
  const form = screen.getByRole("form", { name: "Edit project" });
  await fireEvent.submit(form);
  await screen.findByRole("button", { name: "Load latest for comparison" });
  expect((screen.getByRole("textbox", { name: "Brief" }) as HTMLTextAreaElement).value).toBe("My carefully written brief.");
  expect((within(form).getByRole("button", { name: "Save" }) as HTMLButtonElement).disabled).toBe(true);
  await fireEvent.click(screen.getByRole("button", { name: "Load latest for comparison" }));
  const comparison = await screen.findByRole("region", { name: "Compare with saved values" });
  expect(within(comparison).getByText("Another editor changed this brief.")).toBeTruthy();
  await fireEvent.click(within(comparison).getByRole("button", { name: "Use saved proposed next step" }));
  expect(document.activeElement).toBe(screen.getByLabelText("Proposed next step"));
  await fireEvent.submit(form);
  expect(changeAtlasProject).toHaveBeenCalledTimes(1);
  await fireEvent.click(screen.getByRole("button", { name: "Use reviewed values" }));
  expect(changeAtlasProject).toHaveBeenCalledTimes(1);
  await fireEvent.submit(form);
  expect(changeAtlasProject).toHaveBeenCalledTimes(2);
  const [first, second] = vi.mocked(changeAtlasProject).mock.calls;
  if (!first || !second) throw new Error("Expected both save attempts.");
  expect(second[1].expected_version).toBe(7);
  expect(second[1].request_id).not.toBe(first[1].request_id);
  expect(second[1].change).toMatchObject({ kind: "project.update", brief: "My carefully written brief.", next_action: latest.next_action });
});

it("does not treat a successful historical judgment as current after requirements change", async () => {
  vi.mocked(getAtlasProject).mockResolvedValue(project({
    brief_revision: 2,
    concerns: [concern],
    assessments: [{
      id: "55555555-5555-4555-8555-555555555555",
      concern_id: concernId,
      concern_revision: 1,
      brief_revision: 1,
      statement: concern.statement,
      criteria: concern.criteria,
      brief: "The earlier brief.",
      judgment: "sufficient",
      rationale: "The first guide was accepted.",
      reference_ids: [],
      author: "Magus",
      created_at: now
    }]
  }));
  render(AtlasView, { projectId });
  expect(await screen.findByText("Review needed")).toBeTruthy();
  expect(screen.queryByText("Recorded sufficient")).toBeNull();
  expect(screen.getByText("The earlier brief.")).toBeTruthy();
  expect(screen.getAllByText("The first guide was accepted.").length).toBeGreaterThan(0);
});

it("lets an assessment cite only whole-project or matching-concern activity", async () => {
  const references: AtlasReference[] = [
    { id: "55555555-5555-4555-8555-555555555555", kind: "run", target_id: "run:one", concern_id: null, note: "Shared result", author: "Magus", created_at: now },
    { id: "66666666-6666-4666-8666-666666666666", kind: "session", target_id: "session:two", concern_id: concernId, note: "Recovery discussion", author: "Magus", created_at: now },
    { id: "77777777-7777-4777-8777-777777777777", kind: "run", target_id: "run:three", concern_id: otherConcernId, note: "Different concern", author: "Magus", created_at: now }
  ];
  vi.mocked(getAtlasProject).mockResolvedValue(project({ concerns: [concern], references }));
  render(AtlasView, { projectId });
  await screen.findByRole("button", { name: "Record assessment" });
  await fireEvent.click(screen.getByRole("button", { name: "Record assessment" }));
  const form = screen.getByRole("form", { name: "Record assessment" });
  const card = screen.getByRole("heading", { name: concern.statement }).closest("li");
  expect(card?.contains(form)).toBe(true);
  expect(within(form).getAllByRole("checkbox")).toHaveLength(2);
  expect(within(form).queryByText(/Different concern/)).toBeNull();
  await fireEvent.change(within(form).getByLabelText("Judgment"), { target: { value: "sufficient" } });
  await fireEvent.input(within(form).getByLabelText(/Reason required/), { target: { value: "Support reviewed the recovery path." } });
  await fireEvent.click(within(form).getByRole("checkbox", { name: /run:one/ }));
  const source = within(form).getByRole("link", { name: /Open Run .*run:one in new tab/ });
  expect(source.getAttribute("target")).toBe("_blank");
  expect(source.getAttribute("href")).toBe("/orb/run%3Aone");
  await fireEvent.submit(form);
  expect(vi.mocked(changeAtlasProject).mock.calls[0]![1].change).toEqual({
    kind: "concern.assess", concern_id: concernId, judgment: "sufficient",
    rationale: "Support reviewed the recovery path.", reference_ids: [references[0]!.id]
  });
});

it("shows a failed refresh as stale while retaining the last loaded project", async () => {
  render(AtlasView, { projectId });
  await screen.findByRole("heading", { level: 1, name: "Care for the release" });
  vi.mocked(getAtlasProject).mockRejectedValueOnce(new ApiError("Read failed", 503));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Showing the last loaded information");
  expect(screen.getByRole("heading", { level: 1, name: "Care for the release" })).toBeTruthy();
});

it("does not replace a new project with a late read from the previous route", async () => {
  const oldRead = deferred<AtlasProject>();
  vi.mocked(getAtlasProject).mockReturnValueOnce(oldRead.promise)
    .mockResolvedValueOnce(project({ id: otherProjectId, title: "The new project" }));
  const view = render(AtlasView, { projectId });
  await act(async () => { await Promise.resolve(); });
  await view.rerender({ projectId: otherProjectId });
  await screen.findByRole("heading", { level: 1, name: "The new project" });
  await act(() => oldRead.resolve(project()));
  expect(screen.queryByRole("heading", { level: 1, name: "Care for the release" })).toBeNull();
});

it("ignores a late mutation result after the route identity changes", async () => {
  const save = deferred<AtlasProject>();
  vi.mocked(changeAtlasProject).mockReturnValueOnce(save.promise);
  const view = render(AtlasView, { projectId });
  await screen.findByRole("button", { name: "Edit project" });
  await fireEvent.click(screen.getByRole("button", { name: "Edit project" }));
  await fireEvent.input(screen.getByRole("textbox", { name: "Brief" }), { target: { value: "Old route draft" } });
  await fireEvent.submit(screen.getByRole("form", { name: "Edit project" }));
  vi.mocked(getAtlasProject).mockResolvedValueOnce(project({ id: otherProjectId, title: "Other work" }));
  await view.rerender({ projectId: otherProjectId });
  await screen.findByRole("heading", { level: 1, name: "Other work" });
  await act(() => save.resolve(project({ version: 2, brief: "Old route draft" })));
  expect(screen.queryByText("Saved to Atlas.")).toBeNull();
  expect(screen.queryByText("Old route draft")).toBeNull();
});

it("does not navigate for a creation that resolves after component destruction", async () => {
  const save = deferred<AtlasProject>();
  vi.mocked(createAtlasProject).mockReturnValueOnce(save.promise);
  const view = render(AtlasView);
  await screen.findByText("A place for work that lasts");
  await fireEvent.click(screen.getByRole("button", { name: "New project" }));
  await fireEvent.input(screen.getByLabelText(/Name required/), { target: { value: "A draft" } });
  await fireEvent.submit(screen.getByRole("form", { name: "New project" }));
  view.unmount();
  await act(() => save.resolve(project()));
  expect(goto).not.toHaveBeenCalled();
});

it("guards unsaved drafts from navigation and refresh", async () => {
  render(AtlasView, { projectId });
  await screen.findByRole("button", { name: "Edit project" });
  await fireEvent.click(screen.getByRole("button", { name: "Edit project" }));
  await fireEvent.input(screen.getByRole("textbox", { name: "Brief" }), { target: { value: "Keep this draft" } });
  vi.mocked(window.confirm).mockReturnValue(false);
  const guard = vi.mocked(beforeNavigate).mock.calls[0]![0];
  const cancel = vi.fn();
  guard({ willUnload: false, cancel } as unknown as Parameters<typeof guard>[0]);
  expect(cancel).toHaveBeenCalledOnce();
  await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  expect(getAtlasProject).toHaveBeenCalledOnce();
  expect((screen.getByRole("textbox", { name: "Brief" }) as HTMLTextAreaElement).value).toBe("Keep this draft");
});

it("links only to encoded local activity paths", async () => {
  vi.mocked(getAtlasProject).mockResolvedValue(project({ references: [{
    id: "55555555-5555-4555-8555-555555555555",
    kind: "session", target_id: "session/a?redirect=https://example.invalid",
    concern_id: null, note: "Context", author: "Magus", created_at: now
  }] }));
  render(AtlasView, { projectId });
  const link = await screen.findByRole("link", { name: "Conversation in Bridge →" });
  expect(link.getAttribute("href")).toBe(`/bridge/${encodeURIComponent("session/a?redirect=https://example.invalid")}`);
});

it("keeps paused projects visible with their unresolved concern counts", async () => {
  const item = project({ lifecycle: "paused", concerns: [concern] });
  vi.mocked(getAtlasProjects).mockResolvedValue(catalogue(item));
  render(AtlasView);
  await screen.findByRole("link", { name: /Care for the release/ });
  expect(screen.getByText("1 concern · 1 unassessed")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Paused 1" })).toBeTruthy();
  expect(screen.queryByText(/100%/)).toBeNull();
  expect(screen.queryByRole("navigation", { name: "Project pages" })).toBeNull();
});

it("carries activity from a board choice into a prefilled form without saving automatically", async () => {
  vi.mocked(getAtlasProjects).mockResolvedValue(catalogue(project()));
  const view = render(AtlasView, { linkKind: "session", linkId: "session:one" });
  const choice = await screen.findByRole("link", { name: /Care for the release/ });
  expect(choice.getAttribute("href")).toBe(`/atlas/${projectId}?link_kind=session&link_id=session%3Aone`);
  expect(changeAtlasProject).not.toHaveBeenCalled();
  await view.rerender({ projectId, linkKind: "session", linkId: "session:one" });
  const form = await screen.findByRole("form", { name: "Link existing activity" });
  expect((within(form).getByLabelText(/Existing ID/) as HTMLInputElement).value).toBe("session:one");
  expect(changeAtlasProject).not.toHaveBeenCalled();
  await fireEvent.submit(form);
  expect(vi.mocked(changeAtlasProject).mock.calls[0]?.[1].change).toMatchObject({
    kind: "reference.add", reference_kind: "session", target_id: "session:one"
  });
});

it("does not reopen a cancelled incoming link on refresh or override it with a late read", async () => {
  const late = deferred<AtlasProject>();
  vi.mocked(getAtlasProject).mockReturnValueOnce(late.promise).mockResolvedValue(project());
  const view = render(AtlasView, { projectId, linkKind: "session", linkId: "first" });
  await view.rerender({ projectId, linkKind: "run", linkId: "second" });
  const form = await screen.findByRole("form", { name: "Link existing activity" });
  await act(() => late.resolve(project()));
  expect((within(form).getByLabelText(/Existing ID/) as HTMLInputElement).value).toBe("second");
  expect((within(form).getByLabelText("Activity") as HTMLSelectElement).value).toBe("run");
  await fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  expect(screen.queryByRole("form")).toBeNull();
  expect(changeAtlasProject).not.toHaveBeenCalled();
});

it("filters current judgments separately from historical judgments and keeps same-page jumps draft-safe", async () => {
  const nextConcern = { ...concern, id: otherConcernId, statement: "What happens after a power cut?" };
  const assessment = {
    id: "55555555-5555-4555-8555-555555555555", concern_id: concernId, concern_revision: 1,
    brief_revision: 1, statement: concern.statement, criteria: concern.criteria, brief: project().brief,
    judgment: "insufficient" as const, rationale: "A recovery run is still needed.", reference_ids: [],
    author: "magus", created_at: now
  };
  vi.mocked(getAtlasProject).mockResolvedValue(project({ concerns: [concern, nextConcern], assessments: [assessment] }));
  render(AtlasView, { projectId });
  const filter = await screen.findByRole("combobox", { name: "Assessment" });
  await fireEvent.change(filter, { target: { value: "insufficient" } });
  expect(screen.getByRole("heading", { name: concern.statement })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: nextConcern.statement })).toBeNull();
  await fireEvent.change(filter, { target: { value: "unassessed" } });
  expect(screen.getByRole("heading", { name: nextConcern.statement })).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Record assessment" }));
  await fireEvent.input(screen.getByLabelText(/Reason required/), { target: { value: "Keep this reasoning" } });
  expect((filter as HTMLSelectElement).disabled).toBe(true);
  const guard = vi.mocked(beforeNavigate).mock.calls.at(-1)?.[0];
  if (!guard) throw new Error("Expected the navigation guard");
  const cancel = vi.fn();
  const url = new URL(`https://altar.invalid/atlas/${projectId}`);
  guard({ willUnload: false, from: { url }, to: { url: new URL(`${url}#decisions`) }, cancel } as unknown as Parameters<typeof guard>[0]);
  expect(cancel).not.toHaveBeenCalled();
  expect(window.confirm).not.toHaveBeenCalled();
  expect((screen.getByLabelText(/Reason required/) as HTMLTextAreaElement).value).toBe("Keep this reasoning");
});

it.each(["assessment", "search"])("keeps a conflicting inline draft visible when another edit changes the %s filter result", async (filterKind) => {
  const nextConcern = { ...concern, id: otherConcernId, statement: "Second support concern" };
  const original = project({ concerns: [concern, nextConcern] });
  const latest = project({ version: 2, concerns: filterKind === "search" ? [{ ...concern, statement: "Changed question", criteria: "Changed conditions", revision: 2 }, nextConcern] : original.concerns, assessments: [{
    id: "55555555-5555-4555-8555-555555555555", concern_id: concernId, concern_revision: 1,
    brief_revision: 1, statement: concern.statement, criteria: concern.criteria, brief: original.brief,
    judgment: "sufficient", rationale: "Another editor assessed this.", reference_ids: [], author: "magus", created_at: now
  }] });
  vi.mocked(getAtlasProject).mockResolvedValueOnce(original).mockResolvedValueOnce(latest);
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new ApiError("Version changed", 409));
  render(AtlasView, { projectId });
  if (filterKind === "assessment") {
    await fireEvent.change(await screen.findByRole("combobox", { name: "Assessment" }), { target: { value: "unassessed" } });
  } else {
    await fireEvent.input(await screen.findByRole("searchbox", { name: "Find a concern" }), { target: { value: "support" } });
  }
  const card = screen.getByRole("heading", { name: concern.statement }).closest("li");
  if (!card) throw new Error("Expected concern card");
  await fireEvent.click(within(card).getByRole("button", { name: "Record assessment" }));
  await fireEvent.change(screen.getByLabelText("Judgment"), { target: { value: "disputed" } });
  await fireEvent.input(screen.getByLabelText(/Reason required/), { target: { value: "The result needs another look." } });
  await fireEvent.submit(screen.getByRole("form", { name: "Record assessment" }));
  await fireEvent.click(await screen.findByRole("button", { name: "Load latest for comparison" }));
  expect(await screen.findByRole("button", { name: "Use reviewed values" })).toBeTruthy();
  expect(within(card).getByRole("form", { name: "Record assessment" })).toBeTruthy();
  expect(screen.getByText("The concern being edited stays visible while you compare changes.")).toBeTruthy();
  expect((screen.getByLabelText(/Reason required/) as HTMLTextAreaElement).value).toBe("The result needs another look.");
  expect(screen.getByRole("heading", { name: nextConcern.statement })).toBeTruthy();
});

it("keeps an ambiguous creation identity when a later retry is denied", async () => {
  vi.mocked(createAtlasProject)
    .mockRejectedValueOnce(new ApiError("Response lost", 502))
    .mockRejectedValueOnce(new ApiError("Token expired", 403))
    .mockResolvedValueOnce(project());
  render(AtlasView);
  await screen.findByText("A place for work that lasts");
  await fireEvent.click(screen.getByRole("button", { name: "New project" }));
  await fireEvent.input(screen.getByLabelText(/Name required/), { target: { value: "One project" } });
  await fireEvent.submit(screen.getByRole("form", { name: "New project" }));
  await fireEvent.click(screen.getByRole("button", { name: "Retry same save" }));
  expect(screen.getByText("The save may already have reached Atlas.")).toBeTruthy();
  expect(screen.queryByText("The change was not saved.")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry same save" }));
  const calls = vi.mocked(createAtlasProject).mock.calls;
  expect(calls).toHaveLength(3);
  expect(calls[1]).toEqual(calls[0]);
  expect(calls[2]).toEqual(calls[0]);
});

it("reconciles an uncertain write when Atlas subsequently confirms a version conflict", async () => {
  const latest = project({ version: 2, brief: "Another tab's brief" });
  vi.mocked(getAtlasProject).mockResolvedValueOnce(project()).mockResolvedValueOnce(latest);
  vi.mocked(changeAtlasProject)
    .mockRejectedValueOnce(new ApiError("Response lost", 502))
    .mockRejectedValueOnce(new ApiError("Proxy conflict", 409))
    .mockRejectedValueOnce(new ApiError("Version changed", 409, "atlas_write_rejected"))
    .mockResolvedValueOnce(project({ version: 3 }));
  render(AtlasView, { projectId });
  await fireEvent.click(await screen.findByRole("button", { name: "Edit project" }));
  await fireEvent.input(screen.getByRole("textbox", { name: "Brief" }), { target: { value: "Keep my draft" } });
  const form = screen.getByRole("form", { name: "Edit project" });
  await fireEvent.submit(form);
  await fireEvent.click(await screen.findByRole("button", { name: "Retry same save" }));
  expect(screen.queryByRole("button", { name: "Load latest for comparison" })).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry same save" }));
  await fireEvent.click(await screen.findByRole("button", { name: "Load latest for comparison" }));
  await fireEvent.click(await screen.findByRole("button", { name: "Use reviewed values" }));
  expect((screen.getByRole("textbox", { name: "Brief" }) as HTMLTextAreaElement).value).toBe("Keep my draft");
  await fireEvent.submit(form);
  const calls = vi.mocked(changeAtlasProject).mock.calls;
  expect(calls[1]).toEqual(calls[0]);
  expect(calls[2]).toEqual(calls[0]);
  expect(calls[3]?.[1].expected_version).toBe(2);
  expect(calls[3]?.[1].request_id).not.toBe(calls[0]?.[1].request_id);
});

it("reconciles a competing supersession without losing the decision draft", async () => {
  const firstId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const nextId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const original = { id: firstId, statement: "Ship in June", rationale: "Initial plan", supersedes_id: null, author: "magus", created_at: now };
  const replacement = { ...original, id: nextId, statement: "Ship in July", supersedes_id: firstId };
  vi.mocked(getAtlasProject).mockResolvedValueOnce(project({ decisions: [original] }))
    .mockResolvedValueOnce(project({ version: 2, decisions: [original, replacement] }));
  vi.mocked(changeAtlasProject).mockRejectedValueOnce(new ApiError("Already superseded", 409))
    .mockResolvedValueOnce(project({ version: 3, decisions: [original, replacement] }));
  render(AtlasView, { projectId });
  const opener = await screen.findByRole("button", { name: "Supersede" });
  opener.focus();
  await fireEvent.click(opener);
  await fireEvent.input(screen.getByLabelText(/Decision required/), { target: { value: "Add a review before release" } });
  await fireEvent.input(screen.getByLabelText(/Reason required/), { target: { value: "Keep the review visible" } });
  await fireEvent.submit(screen.getByRole("form", { name: "Record decision" }));
  await fireEvent.click(screen.getByRole("button", { name: "Load latest for comparison" }));
  await fireEvent.click(await screen.findByRole("button", { name: "Use reviewed values" }));
  await fireEvent.change(screen.getByLabelText("Replaces decision"), { target: { value: "" } });
  await fireEvent.submit(screen.getByRole("form", { name: "Record decision" }));
  expect(vi.mocked(changeAtlasProject).mock.calls[1]?.[1].change).toMatchObject({
    kind: "decision.record", statement: "Add a review before release", rationale: "Keep the review visible", supersedes_id: null
  });
  expect(document.activeElement?.tagName).toBe("H1");
});


it("groups conversation destinations while retaining project and concern relations", async () => {
  const references: AtlasReference[] = [
    { id: "55555555-5555-4555-8555-555555555555", kind: "session", target_id: "session:shared", concern_id: null, note: "Whole project", author: "Magus", created_at: now },
    { id: "66666666-6666-4666-8666-666666666666", kind: "session", target_id: "session:shared", concern_id: concernId, note: "Recovery relation", author: "Magus", created_at: now },
    { id: "77777777-7777-4777-8777-777777777777", kind: "session", target_id: "session:shared", concern_id: otherConcernId, note: "Support relation", author: "Magus", created_at: now }
  ];
  vi.mocked(getAtlasProject).mockResolvedValue(project({
    concerns: [concern, { ...concern, id: otherConcernId, statement: "Can support explain recovery?" }], references
  }));
  render(AtlasView, { projectId });
  const navigation = await screen.findByRole("navigation", { name: "Continue in Bridge" });
  const conversationLinks = within(navigation).getAllByRole("link").filter((link) => link.getAttribute("href") === `/bridge/session%3Ashared?project=${projectId}`);
  expect(conversationLinks).toHaveLength(1);
  expect(conversationLinks[0]!.textContent).toContain("Whole project");
  const activity = screen.getByRole("region", { name: "Linked activity" });
  expect(within(activity).getAllByRole("link", { name: "Conversation in Bridge →" })).toHaveLength(3);
  await fireEvent.click(screen.getAllByRole("button", { name: "Record assessment" })[0]!);
  const form = screen.getByRole("form", { name: "Record assessment" });
  expect(within(form).getAllByRole("checkbox")).toHaveLength(2);
  expect(within(form).getByRole("checkbox", { name: /Whole project/ })).toBeTruthy();
  expect(within(form).getByRole("checkbox", { name: /Recovery relation/ })).toBeTruthy();
  expect(within(form).queryByRole("checkbox", { name: /Support relation/ })).toBeNull();
  expect(changeAtlasProject).not.toHaveBeenCalled();
});

it("shows and filters current negative judgments separately from stale review and lifecycle", async () => {
  const baseline = catalogue(project()).projects[0]!;
  vi.mocked(getAtlasProjects).mockResolvedValue({
    projects: [
      { ...baseline, id: projectId, title: "Recovery missing", lifecycle: "paused", concern_count: 1, insufficient_count: 1 },
      { ...baseline, id: otherProjectId, title: "Recovery disputed", concern_count: 1, disputed_count: 1 },
      { ...baseline, id: concernId, title: "Requirements changed", concern_count: 1, review_needed_count: 1 },
      { ...baseline, id: otherConcernId, title: "Recovery sufficient", concern_count: 1 }
    ], total: 4, limit: 50, offset: 0
  });
  render(AtlasView);
  await screen.findByRole("link", { name: /Recovery missing/ });
  expect(screen.getByText("1 current insufficient judgment")).toBeTruthy();
  expect(screen.getByText("1 current disputed judgment")).toBeTruthy();
  expect(screen.getByText("1 assessment needs review")).toBeTruthy();
  const insufficient = screen.getByRole("checkbox", { name: "Current insufficient judgments" });
  await fireEvent.click(insufficient);
  expect(screen.getByRole("link", { name: /Recovery missing/ })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Paused 1" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: /Recovery disputed|Requirements changed|Recovery sufficient/ })).toBeNull();
  await fireEvent.click(insufficient);
  await fireEvent.click(screen.getByRole("checkbox", { name: "Current disputed judgments" }));
  expect(screen.getByRole("link", { name: /Recovery disputed/ })).toBeTruthy();
  expect(screen.queryByRole("link", { name: /Recovery missing|Requirements changed|Recovery sufficient/ })).toBeNull();
  expect(changeAtlasProject).not.toHaveBeenCalled();
});
