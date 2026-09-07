import { act, cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AtlasSummary } from "$lib/api/models";
import { atlasHref, parseAtlasLink } from "$lib/atlas/navigation";

vi.mock("$lib/api/client", () => ({ getAtlasReferences: vi.fn() }));
import { getAtlasReferences } from "$lib/api/client";
import AtlasLinks from "./AtlasLinks.svelte";

afterEach(() => { cleanup(); vi.resetAllMocks(); });

const project: AtlasSummary = {
  id: "11111111-1111-4111-8111-111111111111", title: "The record", brief: "", lifecycle: "active",
  next_action: "", version: 1, updated_at: "2026-09-06T00:00:00Z", concern_count: 0,
  unassessed_count: 0, review_needed_count: 0, insufficient_count: 0, disputed_count: 0
};

it("never applies one activity's delayed membership to another activity", async () => {
  let settle!: (value: AtlasSummary[]) => void;
  vi.mocked(getAtlasReferences).mockReturnValueOnce(new Promise((resolve) => { settle = resolve; }))
    .mockResolvedValueOnce([]);
  const view = render(AtlasLinks, { kind: "session", targetId: "first" });
  await act(async () => {});
  const oldSignal = vi.mocked(getAtlasReferences).mock.calls[0]?.[2];
  await view.rerender({ kind: "session", targetId: "second" });
  await act(() => settle([project]));
  expect(screen.queryByRole("link", { name: "The record" })).toBeNull();
  expect(getAtlasReferences).toHaveBeenLastCalledWith("session", "second", expect.any(AbortSignal));
  expect(oldSignal?.aborted).toBe(true);
  expect(screen.getByRole("link", { name: "Link to project" }).getAttribute("href"))
    .toBe("/atlas?link_kind=session&link_id=second");
});

it("shows persisted membership and aborts its owned read on teardown", async () => {
  vi.mocked(getAtlasReferences).mockResolvedValue([project]);
  const view = render(AtlasLinks, { kind: "run", targetId: "run-a" });
  const link = await screen.findByRole("link", { name: "The record" });
  expect(link.getAttribute("href")).toBe(`/atlas/${project.id}`);
  expect(screen.getByRole("link", { name: "Link to another project" }).getAttribute("href"))
    .toBe("/atlas?link_kind=run&link_id=run-a");
  const signal = vi.mocked(getAtlasReferences).mock.calls[0]?.[2];
  view.unmount();
  expect(signal?.aborted).toBe(true);
});

it("retains earlier links with a stale notice when focus refresh fails", async () => {
  vi.mocked(getAtlasReferences).mockResolvedValueOnce([project])
    .mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValueOnce([]);
  render(AtlasLinks, { kind: "session", targetId: "session-a" });
  await screen.findByRole("link", { name: "The record" });
  await fireEvent.focus(window);
  await screen.findByText(/Showing earlier links/);
  expect(screen.getByRole("link", { name: "The record" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Link to another project" })).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Retry Atlas links" }));
  expect(screen.queryByRole("link", { name: "The record" })).toBeNull();
  expect(screen.queryByText(/Showing earlier links/)).toBeNull();
  expect(screen.getByRole("link", { name: "Link to project" })).toBeTruthy();
});

it("offers ordinary linking navigation while membership is still loading", async () => {
  vi.mocked(getAtlasReferences).mockReturnValue(new Promise(() => {}));
  render(AtlasLinks, { kind: "run", targetId: "run:one/two?x=1&y=2" });
  expect(screen.getByRole("link", { name: "Link to project" }).getAttribute("href"))
    .toBe("/atlas?link_kind=run&link_id=run%3Aone%2Ftwo%3Fx%3D1%26y%3D2");
  expect(getAtlasReferences).toHaveBeenCalledTimes(1);
});

it("keeps linking navigation available after an initial membership read failure", async () => {
  vi.mocked(getAtlasReferences).mockRejectedValue(new Error("Unavailable"));
  render(AtlasLinks, { kind: "session", targetId: "session-a" });
  await screen.findByRole("status");
  expect(screen.getByRole("link", { name: "Link to project" }).getAttribute("href"))
    .toBe("/atlas?link_kind=session&link_id=session-a");
  expect(screen.queryByText(/Showing earlier links/)).toBeNull();
});

it("updates the link kind without waiting for the new membership response", async () => {
  vi.mocked(getAtlasReferences).mockResolvedValueOnce([project])
    .mockReturnValueOnce(new Promise(() => {}));
  const view = render(AtlasLinks, { kind: "session", targetId: "shared-id" });
  await screen.findByRole("link", { name: "The record" });
  await view.rerender({ kind: "run", targetId: "shared-id" });
  expect(screen.queryByRole("link", { name: "The record" })).toBeNull();
  expect(screen.getByRole("link", { name: "Link to project" }).getAttribute("href"))
    .toBe("/atlas?link_kind=run&link_id=shared-id");
});

describe("Atlas navigation hints", () => {
  it.each(["session", "run"])("accepts the exact %s kind without changing its ID", (kind) => {
    expect(parseAtlasLink(kind, "retained:id / one"))
      .toEqual({ kind, targetId: "retained:id / one" });
  });

  it.each([undefined, null, "", "RUN", "Session", " session", "run ", "project"])(
    "rejects an unsupported kind %s", (kind) => {
      expect(parseAtlasLink(kind, "id")).toBeNull();
    }
  );

  it.each([undefined, null, "", " ", "\tid", "id\n", " id", "id ", "\u00a0id", "id\u00a0"])(
    "rejects a missing or padded identity %s", (id) => {
      expect(parseAtlasLink("run", id)).toBeNull();
    }
  );

  it("accepts an ID at the bound and rejects one beyond it", () => {
    expect(parseAtlasLink("run", "x".repeat(128)))
      .toEqual({ kind: "run", targetId: "x".repeat(128) });
    expect(parseAtlasLink("run", "x".repeat(129))).toBeNull();
  });

  it("builds plain board and encoded project paths when no valid hint exists", () => {
    expect(atlasHref()).toBe("/atlas");
    expect(atlasHref(undefined, null)).toBe("/atlas");
    expect(atlasHref("folder/name?x=1#anchor")).toBe("/atlas/folder%2Fname%3Fx%3D1%23anchor");
    expect(atlasHref(project.id, { kind: "run", targetId: " padded " })).toBe(`/atlas/${project.id}`);
    expect(atlasHref(undefined, { kind: "session", targetId: "x".repeat(129) })).toBe("/atlas");
  });

  it("encodes path and query separately and round-trips the activity identity", () => {
    const intent = { kind: "session" as const, targetId: "session/a?x=1&y=#z+% café" };
    const href = atlasHref("project/a?view=1", intent);
    expect(href).toBe("/atlas/project%2Fa%3Fview%3D1?link_kind=session&link_id=session%2Fa%3Fx%3D1%26y%3D%23z%2B%25%20caf%C3%A9");
    const url = new URL(href, "https://altar.invalid");
    expect(url.origin).toBe("https://altar.invalid");
    expect(url.hash).toBe("");
    expect([...url.searchParams.keys()]).toEqual(["link_kind", "link_id"]);
    expect(parseAtlasLink(url.searchParams.get("link_kind"), url.searchParams.get("link_id")))
      .toEqual(intent);
  });
});
