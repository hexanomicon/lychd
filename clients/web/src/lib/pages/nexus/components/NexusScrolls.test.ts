import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, expect, it, vi } from "vitest";
import type { LoomSummary, LoomView } from "$lib/api/models";
import { getLoomCatalogue, getLoomPatternRevision } from "$lib/api/client";
import NexusScrolls from "./NexusScrolls.svelte";

vi.mock("$lib/api/client", () => ({getLoomCatalogue: vi.fn(), getLoomPatternRevision: vi.fn()}));
const registered: LoomSummary = {
  pattern_id: "bridge_chat", revision: "1", implementation_revision: "py.1",
  entry_node: "start", digest: "sha256:exact", title: "Bridge Chat", description: "Local workflow",
  trigger_hint: "Default", detail_path: "/loom/bridge_chat/1", active:true, default:true,
  route_rank:null, publication:"published"
};
const contract: LoomView = {
  ...registered, mermaid_source:"", schema_version:2, checkpoint_schema:"bridge-state",
  nodes:[{key:"ask",kind:"gate",label:"Review proposed action"}, {key:"finish",kind:"terminal",label:"Finish"}],
  edges:[{key:"answered",source:"ask",target:"finish",relation:"approved"}]
};
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getLoomCatalogue).mockResolvedValue([registered, {...registered, title:"External observation", publication:"observed", detail_path:"/loom/external/2"}]);
  vi.mocked(getLoomPatternRevision).mockResolvedValue(contract);
});

it("keeps the local registry out of the public advertised inventory and exports explicit fields", async () => {
  render(NexusScrolls, {mode:"skills"});
  expect(await screen.findByText("1 registered revision")).toBeTruthy();
  expect(screen.getByText("0 published here")).toBeTruthy();
  expect(screen.queryByRole("option",{name:/External observation/})).toBeNull();
  expect(screen.queryByRole("link",{name:"Export proposal"})).toBeNull();
  for (const [label, value] of [["Public skill or material","Public review"],["Task schema and version","review@1"],["Intended audience","Enrolled peers"]] as const) {
    await fireEvent.input(screen.getByLabelText(label), {target:{value}});
  }
  const link = screen.getByRole("link",{name:"Export proposal"});
  const payload = JSON.parse(decodeURIComponent(link.getAttribute("href")!.split(",")[1]!));
  expect(payload.proposed_public_fields).toEqual({skill:"Public review",task_schema:"review@1",audience:"Enrolled peers"});
  expect(payload.local_target.digest).toBe(registered.digest);
});

it("exposes an absent offer feed and verifies the complete selected revision before gate display", async () => {
  const view = render(NexusScrolls, {mode:"offers"});
  expect(await screen.findByText("Inventory unavailable")).toBeTruthy();
  await view.rerender({mode:"checkpoints"});
  expect(await screen.findByText("Review proposed action")).toBeTruthy();
  expect(screen.getByText("approved → Finish")).toBeTruthy();
  expect(getLoomPatternRevision).toHaveBeenCalledWith("bridge_chat","1",undefined);
  expect(screen.getByRole("link",{name:/pending Run decisions/}).getAttribute("href")).toContain("/bridge");
});

it("shows an unavailable exact contract when the response digest differs", async () => {
  vi.mocked(getLoomPatternRevision).mockResolvedValue({...contract,digest:"sha256:different"});
  render(NexusScrolls,{mode:"checkpoints"});
  await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/could not be verified/));
  expect(screen.queryByText("Review proposed action")).toBeNull();
});
