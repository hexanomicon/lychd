import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";

import type { LoomSummary, LoomView as LoomProjection, OrbRunSnapshot } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/loom") }
}));
vi.mock("$lib/api/client", () => ({
  getLoomCatalogue: vi.fn(),
  getLoomPatternRevision: vi.fn(),
  getOrbRun: vi.fn()
}));

import { page as appPage } from "$app/state";
const page = appPage as Omit<typeof appPage, "url"> & { url: import("svelte/reactivity").SvelteURL };
import { goto } from "$app/navigation";
import { getLoomCatalogue, getLoomPatternRevision, getOrbRun } from "$lib/api/client";
import LoomView from "./LoomView.svelte";
import { createWorkCommandRegistry, workCommandKey } from "$lib/pages/bridge/state/work-commands";

const summary: LoomSummary = {
  publication: "published",
  active: true,
  default: true,
  description: "A test pattern.",
  detail_path: "/loom/bridge_chat/1",
  digest: "sha256:test",
  entry_node: "start",
  implementation_revision: "test",
  pattern_id: "bridge_chat",
  revision: "1",
  route_rank: 0,
  title: "Bridge chat",
  trigger_hint: "test"
};

const projection: LoomProjection = {
  checkpoint_schema: "test@1",
  description: summary.description,
  digest: summary.digest,
  edges: [],
  entry_node: summary.entry_node,
  implementation_revision: summary.implementation_revision,
  mermaid_source: "flowchart TD",
  nodes: [],
  pattern_id: summary.pattern_id,
  publication: "published",
  revision: summary.revision,
  schema_version: 1,
  title: summary.title,
  trigger_hint: summary.trigger_hint
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  page.url.href = "http://localhost/loom";
  vi.mocked(getLoomCatalogue).mockResolvedValue([summary]);
  vi.stubGlobal("matchMedia", vi.fn(() => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn()
  })));
  vi.stubGlobal("ResizeObserver", class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
});

const score: LoomProjection = {
  ...projection,
  nodes: [
    { key: "start", label: "Start", kind: "step" },
    { key: "compose", label: "Compose reply", kind: "step" },
    { key: "wait", label: "Await input", kind: "gate" },
    { key: "close", label: "Close", kind: "terminal" }
  ],
  edges: [
    { key: "start-compose", source: "start", target: "compose", relation: "permits" },
    { key: "compose-wait", source: "compose", target: "wait", relation: "permits" },
    { key: "wait-wait", source: "wait", target: "wait", relation: "permits" },
    { key: "wait-compose", source: "wait", target: "compose", relation: "permits" },
    { key: "compose-close", source: "compose", target: "close", relation: "permits" }
  ]
};

function mountCommands() {
  const registry = createWorkCommandRegistry();
  const component = render(LoomView, {
    props: { patternId: "bridge_chat", revision: "1" },
    context: new Map([[workCommandKey, registry]])
  });
  return { registry, component };
}

it("registers only after the exact Pattern loads and exposes the read-only vocabulary", async () => {
  const pending = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockReturnValue(pending.promise);
  const { registry, component } = mountCommands();
  expect(registry.capture()).toBeNull();
  await act(() => pending.resolve(score));
  expect(await screen.findByRole("heading", { name: "Bridge chat" })).toBeTruthy();
  expect(registry.capture()).toMatchObject({
    instrument: "loom", id: JSON.stringify(["bridge_chat", "1"]),
    label: "Loom · bridge_chat@1", commands: ["inspect STATION", "focus STATION", "show pattern", "show stations"]
  });
  component.unmount();
  expect(registry.capture()).toBeNull();
});

it("inspects exact keys and normalized unique labels with visible semantic focus", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  for (const command of ["inspect wait", "focus   COMPOSE   reply"]) {
    let result;
    await act(async () => { result = await registry.execute(command, registry.capture()); });
    expect(result).toMatchObject({ status: "applied" });
    const inspector = screen.getByRole("complementary", { name: "Selected station" });
    expect(document.activeElement).toBe(within(inspector).getByRole("heading", { level: 3 }));
    expect(screen.getByRole("list", { name: "Declared stations" })).toBeTruthy();
  }
  expect(within(screen.getByRole("complementary", { name: "Selected station" })).getByRole("heading", { level: 3 }).textContent).toBe("Compose reply");
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  component.unmount();
});

it("changes only the displayed level for show commands", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  for (const [command, button] of [["show pattern", "Whole Pattern"], ["show stations", "Stations"]]) {
    await act(async () => {
      expect(await registry.execute(command!, registry.capture())).toMatchObject({ status: "applied" });
    });
    expect(screen.getByRole("button", { name: button! }).getAttribute("aria-pressed")).toBe("true");
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Pattern graph" }));
  }
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  component.unmount();
});

it("rejects ambiguous labels, fuzzy guesses, and workflow effects without changing inspection", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue({ ...score, nodes: [...score.nodes, { key: "other", label: "Await input", kind: "step" }] });
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  const before = screen.getByRole("complementary", { name: "Selected station" }).textContent;
  for (const command of ["inspect Await input", "focus comp", "connect start to close", "delete wait", "publish pattern", "execute workflow"]) {
    expect(await registry.execute(command, registry.capture())).toMatchObject({ status: "unsupported" });
    expect(screen.getByRole("complementary", { name: "Selected station" }).textContent).toBe(before);
  }
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();
  component.unmount();
});

it("fences captures after selection and after a level away-and-back", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  const original = registry.capture();
  await fireEvent.click(screen.getByRole("button", { name: "Whole Pattern" }));
  await fireEvent.click(screen.getByRole("button", { name: "Stations" }));
  expect(await registry.execute("inspect wait", original)).toMatchObject({ status: "stale" });
  const selected = registry.capture();
  await fireEvent.click(await screen.findByRole("button", { name: "Inspect Await input" }));
  expect(await registry.execute("inspect close", selected)).toMatchObject({ status: "stale" });
  component.unmount();
});

it("rejects commands interrupted before their first presentation mutation", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  const pending = registry.execute("inspect wait", registry.capture());
  registry.invalidate();
  expect(await pending).toMatchObject({ status: "stale" });
  expect(within(screen.getByRole("complementary", { name: "Selected station" })).getByRole("heading", { level: 3 }).textContent).toBe("Start");
  component.unmount();
});

it("clears registrations during reload and ignores a late response after unmount", async () => {
  const pending = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockResolvedValueOnce(score).mockReturnValueOnce(pending.promise);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  const old = registry.capture();
  await component.rerender({ patternId: "bridge_chat", revision: "2" });
  expect(registry.capture()).toBeNull();
  expect(await registry.execute("inspect wait", old)).toMatchObject({ status: "stale" });
  component.unmount();
  await act(() => pending.resolve({ ...score, revision: "2" }));
  expect(registry.capture()).toBeNull();
});

it("leaves a newer surface registered when an older Loom unmounts", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue(score);
  const { registry, component } = mountCommands();
  await screen.findByRole("heading", { name: "Bridge chat" });
  const cleanup = registry.register({
    instrument: "orb", id: "run-new", label: "New Run",
    snapshot: () => ({ revisionKey: "1", commands: ["show run"] }),
    execute: () => ({ status: "applied", summary: "Presentation only" })
  });
  component.unmount();
  expect(registry.capture()?.id).toBe("run-new");
  cleanup();
});

it("never registers a failed or mismatched response", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue({ ...score, revision: "other" });
  const { registry, component } = mountCommands();
  expect((await screen.findByRole("alert")).textContent).toContain("does not match the exact requested identity and source profile");
  expect(registry.capture()).toBeNull();
  component.unmount();
});
