import { act, render } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";

import type { LoomSummary, LoomView as LoomProjection } from "$lib/api/models";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/loom") }
}));
vi.mock("$lib/api/client", () => ({
  getLoomCatalogue: vi.fn(),
  getLoomPatternRevision: vi.fn(),
  getOrbRun: vi.fn()
}));

import { goto } from "$app/navigation";
import { getLoomCatalogue, getLoomPatternRevision } from "$lib/api/client";
import LoomView from "./LoomView.svelte";

const summary: LoomSummary = {
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
  vi.mocked(getLoomCatalogue).mockResolvedValue([summary]);
});

it("does not navigate when a Pattern revision resolves after destroy", async () => {
  const revision = deferred<LoomProjection>();
  vi.mocked(getLoomPatternRevision).mockReturnValue(revision.promise);
  const view = render(LoomView);
  await act(async () => {
    await Promise.resolve();
  });
  expect(getLoomPatternRevision).toHaveBeenCalledOnce();

  view.unmount();
  await act(() => revision.resolve(projection));

  expect(goto).not.toHaveBeenCalled();
});
