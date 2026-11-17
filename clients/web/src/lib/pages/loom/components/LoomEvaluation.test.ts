import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { webcrypto } from "node:crypto";
import { beforeEach, expect, it, vi } from "vitest";
import type { BridgeSnapshot, BridgeTurnView, LoomView, OrbRunSnapshot } from "$lib/api/models";
import { canonical, digest, exportJson, exportMarkdown, validateRun } from "$lib/pages/loom/state/evaluation/review";
import { createEvaluationWorkspace, setEvaluationWorkspace, type EvaluationWorkspace } from "$lib/pages/loom/state/evaluation/workspace.svelte";

vi.mock("$lib/api/client", () => ({ getOrbRun: vi.fn(), getBridgeSnapshot: vi.fn() }));
import { getBridgeSnapshot, getOrbRun } from "$lib/api/client";
import LoomEvaluation from "./LoomEvaluation.svelte";

const score: LoomView = {
  schema_version: 1, pattern_id: "bridge_chat", revision: "1", digest: "sha256:score", implementation_revision: "impl-1", checkpoint_schema: "test@1", entry_node: "start", nodes: [{ key: "start", kind: "step", label: "Start" }], edges: [], title: "Bridge chat", description: "A score", publication: "published", mermaid_source: "flowchart TD", trigger_hint: "chat"
};
const turn: BridgeTurnView = { role: "agent", content: "Exact output\nwith Ω and trailing space ", created_at: "2026-11-01T10:00:00Z", run_id: "run-a", state: "settled" };
const run: OrbRunSnapshot = {
  schema_version: 1, snapshot_at: "2026-11-01T10:01:00Z", capture: "durable_best_effort", ledger_head_seq: 0, page_end_seq: 0, live_tail: "ledger_poll", workflow: score, next_after_seq: null, has_more: true, known_omissions: ["Token history is not retained."], delegated_jobs: [], gaps: [], evidence: [],
  pattern: { pattern_id: score.pattern_id, revision: score.revision, digest: score.digest, exact: true, loom_path: "/loom/bridge_chat/1" },
  run: { run_id: "run-a", session_id: "session-a", workflow_name: "bridge_chat", status: "done", created_at: "2026-11-01T10:00:00Z", started_at: null, finished_at: null, error_present: false, bridge_path: "/bridge/session-a" }
};
const session = (turns: BridgeTurnView[] = [turn], id = "session-a"): BridgeSnapshot => ({ session: { id, title: "Conversation", created_at: turn.created_at, pending_count: 0, turns }, sessions: [], active_runs: [], pending_consents: [], pending_count: 0 });
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((accept, decline) => { resolve = accept; reject = decline; }); return { promise, resolve, reject }; }
function mount(workspace = createEvaluationWorkspace(), linkedRunId: string | null = null) {
  function Wrapper(...args: Parameters<typeof LoomEvaluation>) { setEvaluationWorkspace(workspace); return LoomEvaluation(...args); }
  return { workspace, component: render(Wrapper, { score, linkedRunId }) };
}
async function frozenContract(workspace: EvaluationWorkspace) {
  workspace.start(score);
  const id = workspace.activeId!;
  workspace.editContract(id, { goal: "Explain the output precisely", reviewer: "Reviewer A (self-declared)", criteria: [{ id: "criterion-1", statement: "Preserve exact output", evidence: "An exact supporting quotation", missing: "UNKNOWN when the source cannot establish it" }] });
  await workspace.freezeContract(id);
  return id;
}
async function frozenSource(workspace: EvaluationWorkspace) {
  const id = await frozenContract(workspace);
  workspace.editRun(id, "run-a"); await workspace.loadSource(id, score); workspace.selectTurn(id, 0); await workspace.freezeSource(id);
  return id;
}
beforeEach(() => { vi.restoreAllMocks(); vi.clearAllMocks(); vi.stubGlobal("crypto", webcrypto); vi.mocked(getOrbRun).mockResolvedValue(run); vi.mocked(getBridgeSnapshot).mockResolvedValue(session()); });

it("uses the linked Run only as an explicit identity hint without fetching or grading it", async () => {
  const workspace = createEvaluationWorkspace();
  await frozenContract(workspace);
  const { component } = mount(workspace, "run-a");
  await fireEvent.click(screen.getByRole("button", { name: "Use linked Run" }));
  expect((screen.getByLabelText("Exact Run ID") as HTMLInputElement).value).toBe("run-a");
  expect(getOrbRun).not.toHaveBeenCalled();
  expect(getBridgeSnapshot).not.toHaveBeenCalled();
  expect(workspace.active?.source).toBeNull();
  expect(workspace.active?.judgments[0]?.verdict).toBe("UNKNOWN");
  component.unmount();
});

it("performs no source read on opening and completes a manual review through explicit controls", async () => {
  const { component, workspace } = mount();
  expect(getOrbRun).not.toHaveBeenCalled(); expect(getBridgeSnapshot).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "New review for this score" }));
  await fireEvent.input(screen.getByLabelText("Goal (up to 4,000 characters)"), { target: { value: "Describe exact output" } });
  await fireEvent.input(screen.getByLabelText("Self-declared reviewer (up to 256 characters)"), { target: { value: "A" } });
  await fireEvent.input(screen.getByLabelText("Expected or forbidden behavior"), { target: { value: "Contains exact output" } });
  await fireEvent.input(screen.getByLabelText("Evidence requirements"), { target: { value: "Exact quotation" } });
  await fireEvent.click(screen.getByRole("button", { name: "Freeze review contract" }));
  const runInput = await screen.findByLabelText("Exact Run ID");
  expect(getOrbRun).not.toHaveBeenCalled();
  await fireEvent.input(runInput, { target: { value: "run-a" } });
  await fireEvent.click(screen.getByRole("button", { name: "Load exact Run output" }));
  const radio = await screen.findByRole("radio");
  expect(getOrbRun).toHaveBeenCalledWith("run-a", { limit: 1 });
  expect(getBridgeSnapshot).toHaveBeenCalledWith("session-a");
  expect(screen.getByRole("button", { name: "Freeze selected output" }).hasAttribute("disabled")).toBe(true);
  await fireEvent.click(radio); await fireEvent.click(screen.getByRole("button", { name: "Freeze selected output" }));
  expect((await screen.findByLabelText("Verdict for criterion 1") as HTMLSelectElement).value).toBe("UNKNOWN");
  await fireEvent.input(screen.getByLabelText("Rationale for criterion 1"), { target: { value: "The retained text supports the criterion." } });
  await fireEvent.input(screen.getByLabelText("Exact supporting quotation for criterion 1"), { target: { value: "Exact output" } });
  await fireEvent.click(screen.getByRole("button", { name: "Finish and freeze review" }));
  expect(await screen.findByRole("button", { name: "Export JSON" })).toBeTruthy();
  expect(workspace.active?.record?.judgments[0]?.verdict).toBe("UNKNOWN");
  expect(workspace.active?.record?.source.content).toBe(turn.content);
  expect(workspace.needsUnloadWarning).toBe(true);
  component.unmount();
});

it("requires declared criteria before reading, with every evidence requirement and missing-evidence policy", async () => {
  const workspace = createEvaluationWorkspace(); workspace.start(score); const id = workspace.activeId!;
  workspace.editRun(id, "run-a"); await workspace.loadSource(id, score); await workspace.freezeContract(id);
  expect(workspace.active?.contract).toBeNull(); expect(workspace.active?.error).toContain("Declare the goal");
  expect(getOrbRun).not.toHaveBeenCalled();
  workspace.editContract(id, { goal: "Goal", reviewer: "A", criteria: [{ id: "a", statement: "Criterion", evidence: "", missing: "" }] });
  await workspace.freezeContract(id); expect(workspace.active?.error).toContain("Every criterion requires");
});

it("locks contract edits and criterion removal while its digest is pending", async () => {
  const workspace = createEvaluationWorkspace(); workspace.start(score); const id = workspace.activeId!;
  const criteria = [{ id: "criterion-1", statement: "Original criterion", evidence: "Required evidence", missing: "UNKNOWN" }];
  workspace.editContract(id, { goal: "Original goal", reviewer: "A", criteria });
  const hash = deferred<ArrayBuffer>(); vi.spyOn(crypto.subtle, "digest").mockReturnValueOnce(hash.promise);
  const { component } = mount(workspace);
  await fireEvent.click(screen.getByRole("button", { name: "Freeze review contract" }));
  expect(screen.getByRole("group", { name: "Review declaration" }).hasAttribute("disabled")).toBe(true);
  workspace.editContract(id, { goal: "Changed goal", criteria: [] });
  expect(workspace.active?.goal).toBe("Original goal"); expect(workspace.active?.criteria).toEqual(criteria);
  await act(() => hash.resolve(new ArrayBuffer(32)));
  expect(workspace.active?.contract?.goal).toBe("Original goal"); expect(workspace.active?.contract?.criteria).toEqual(criteria);
  component.unmount();
});

it("locks supplied-turn selection while exact output bytes are being digested", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  vi.mocked(getBridgeSnapshot).mockResolvedValue(session([turn, { ...turn, content: "Second output" }]));
  await workspace.loadSource(id, score); workspace.selectTurn(id, 0);
  const { component } = mount(workspace);
  const hash = deferred<ArrayBuffer>(); vi.spyOn(crypto.subtle, "digest").mockReturnValueOnce(hash.promise);
  await fireEvent.click(screen.getByRole("button", { name: "Freeze selected output" }));
  expect(screen.getAllByRole("radio").every(radio => radio.hasAttribute("disabled"))).toBe(true);
  workspace.selectTurn(id, 1); expect(workspace.active?.selectedTurn).toBe(0);
  await act(() => hash.resolve(new ArrayBuffer(32)));
  expect(workspace.active?.source?.content).toBe(turn.content); component.unmount();
});

it("requires server full-manifest resolution and every exact score and inspection field", async () => {
  const mismatches: OrbRunSnapshot[] = [
    { ...run, workflow: null }, { ...run, pattern: { ...run.pattern, exact: false } },
    { ...run, run: { ...run.run, run_id: "run-other" } },
    ...["checkpoint_schema", "implementation_revision", "entry_node", "digest", "revision"].map(field => ({ ...run, workflow: { ...score, [field]: "mismatch" } })),
    { ...run, workflow: { ...score, nodes: [] } }, { ...run, workflow: { ...score, edges: [{ key: "x", source: "start", target: "start", relation: "permits" }] } }
  ];
  for (const mismatched of mismatches) expect(() => validateRun("run-a", mismatched, score)).toThrow("full pinned Run manifest");
  const binding = { source_id: "fixture", source_generation: "g1", profile_id: "p", profile_revision: "1", registrant_id: "r", executable: false, publication: "observed" as const };
  expect(() => validateRun("run-a", run, { ...score, binding })).toThrow("inspection binding");
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  vi.mocked(getOrbRun).mockResolvedValue({ ...run, workflow: { ...score, implementation_revision: "other" } });
  await workspace.loadSource(id, score); expect(getBridgeSnapshot).not.toHaveBeenCalled(); expect(workspace.active?.source).toBeNull();
});

it("uses only matching supplied Session agent turns and requires explicit ambiguity resolution", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  vi.mocked(getBridgeSnapshot).mockResolvedValue(session([ { ...turn, role: "user" }, { ...turn, run_id: "other", content: "Latest unrelated output" } ]));
  await workspace.loadSource(id, score); expect(workspace.active?.error).toContain("No supplied agent turn matches"); expect(workspace.active?.turns).toHaveLength(0);
  vi.mocked(getBridgeSnapshot).mockResolvedValue(session([turn], "wrong-session"));
  await workspace.loadSource(id, score); expect(workspace.active?.error).toContain("exact Session");
  vi.mocked(getBridgeSnapshot).mockResolvedValue(session([turn, { ...turn, content: "Second supplied output" }]));
  await workspace.loadSource(id, score); await workspace.freezeSource(id); expect(workspace.active?.source).toBeNull();
  workspace.selectTurn(id, 1); await workspace.freezeSource(id);
  expect(workspace.active?.source?.content).toBe("Second supplied output"); expect(workspace.active?.source?.limitations.join(" ")).toContain("Multiple supplied agent turns");
});

it("freezes exact bytes and SHA-256, preserves limitations in both exports, and creates immutable revisions", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenSource(workspace);
  expect(workspace.active?.source?.digest).toBe(await digest(turn.content));
  workspace.editJudgment(id, "criterion-1", { verdict: "PASS", rationale: "An exact match.", quotation: "altered quotation" }); workspace.finish(id);
  expect(workspace.active?.record).toBeNull(); expect(workspace.active?.error).toContain("occur exactly");
  workspace.editJudgment(id, "criterion-1", { quotation: "Exact output" }); workspace.finish(id);
  const completed = workspace.active!.record!, bytes = exportJson(completed);
  expect(Object.isFrozen(completed.judgments[0])).toBe(true);
  expect(JSON.parse(bytes).source.content).toBe(turn.content);
  for (const limitation of completed.source.limitations) expect(exportMarkdown(completed)).toContain(limitation);
  expect(exportMarkdown(completed)).toContain(completed.contract.digest);
  workspace.revise(id); const newId = workspace.activeId!;
  workspace.editJudgment(newId, "criterion-1", { verdict: "DISPUTED", rationale: "Another interpretation" });
  expect(exportJson(completed)).toBe(bytes); expect(workspace.active?.parentId).toBe(id); expect(workspace.active?.revision).toBe(2);
  expect(workspace.active?.contract?.digest).toBe(completed.contract.digest);
});

it("requires rationale and quotation or explicit limitation even for UNKNOWN", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenSource(workspace);
  workspace.finish(id); expect(workspace.active?.error).toContain("rationale");
  workspace.editJudgment(id, "criterion-1", { rationale: "Cannot establish this" }); workspace.finish(id); expect(workspace.active?.error).toContain("quotation or");
  workspace.editJudgment(id, "criterion-1", { limitation: "The output has no receipt for that claim." }); workspace.finish(id);
  expect(workspace.active?.record?.judgments[0]?.verdict).toBe("UNKNOWN");
});

it("fences edits, cancellation and late Run/Session completions and refusals", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  const lateRun = deferred<OrbRunSnapshot>(); vi.mocked(getOrbRun).mockReturnValueOnce(lateRun.promise);
  const loading = workspace.loadSource(id, score); workspace.editRun(id, "run-b"); lateRun.resolve(run); await loading;
  expect(getBridgeSnapshot).not.toHaveBeenCalled(); expect(workspace.active?.runId).toBe("run-b");
  workspace.editRun(id, "run-a"); const lateSession = deferred<BridgeSnapshot>(); vi.mocked(getBridgeSnapshot).mockReturnValueOnce(lateSession.promise);
  const reading = workspace.loadSource(id, score); await waitFor(() => expect(getBridgeSnapshot).toHaveBeenCalledOnce());
  workspace.cancelRead(id); lateSession.reject({ status: 403 }); await reading;
  expect(workspace.active?.error).toContain("interrupted"); expect(workspace.notice).not.toContain("Authorization");
  await workspace.loadSource(id, { ...score, revision: "2" }); expect(workspace.active?.error).toContain("another exact score");
});

it("cancels a pending source read on displayed-score replacement and ignores its completion", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  const late = deferred<BridgeSnapshot>(); vi.mocked(getBridgeSnapshot).mockReturnValueOnce(late.promise);
  const { component } = mount(workspace);
  await fireEvent.click(screen.getByRole("button", { name: "Load exact Run output" }));
  await waitFor(() => expect(getBridgeSnapshot).toHaveBeenCalledOnce());
  await component.rerender({ score: { ...score, revision: "2" } });
  await act(() => late.resolve(session()));
  expect(workspace.active?.turns).toHaveLength(0); expect(workspace.active?.source).toBeNull(); expect(workspace.active?.error).toContain("interrupted"); component.unmount();
});

it.each([401, 403])("clears all protected captures and completed records on a current %i and fences other callbacks", async status => {
  const workspace = createEvaluationWorkspace(), completedId = await frozenSource(workspace);
  workspace.editJudgment(completedId, "criterion-1", { rationale: "Unknown", limitation: "No evidence" }); workspace.finish(completedId);
  const pendingId = await frozenContract(workspace); workspace.editRun(pendingId, "run-a");
  const pending = deferred<BridgeSnapshot>(); vi.mocked(getBridgeSnapshot).mockReturnValueOnce(pending.promise);
  const late = workspace.loadSource(pendingId, score); await waitFor(() => expect(getBridgeSnapshot).toHaveBeenCalledTimes(2));
  const refusedId = await frozenContract(workspace); workspace.editRun(refusedId, "run-a"); vi.mocked(getOrbRun).mockRejectedValueOnce({ status });
  await workspace.loadSource(refusedId, score); pending.resolve(session()); await late;
  expect(workspace.entries.some(entry => entry.record || entry.source || entry.run || entry.turns.length)).toBe(false);
  expect(workspace.entries.some(entry => entry.id === completedId)).toBe(false); expect(workspace.notice).toContain("Authorization refused");
  vi.mocked(getOrbRun).mockResolvedValue(run); vi.mocked(getBridgeSnapshot).mockResolvedValue(session());
  await workspace.loadSource(refusedId, score); workspace.selectTurn(refusedId, 0); await workspace.freezeSource(refusedId);
  expect(workspace.active?.judgments).toHaveLength(1); workspace.finish(refusedId);
  expect(workspace.active?.record).toBeNull(); expect(workspace.active?.error).toContain("rationale");
});

it("bounds the active and completed document, refuses oversized fields/source without truncation, and discards explicitly", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace);
  workspace.editRun(id, "run-a"); vi.mocked(getBridgeSnapshot).mockResolvedValue(session([{ ...turn, content: "x".repeat(256_001) }]));
  await workspace.loadSource(id, score); expect(workspace.active?.turns).toHaveLength(0); expect(workspace.active?.error).toContain("exceeds");
  workspace.start(score); const next = workspace.activeId!; workspace.editContract(next, { goal: "x".repeat(4_001) }); expect(workspace.active?.goal).toBe(""); expect(workspace.notice).toContain("truncated");
  workspace.start(score); workspace.start(score); const before = canonical(workspace.entries); workspace.start(score); expect(canonical(workspace.entries)).toBe(before); expect(workspace.entries).toHaveLength(4);
  for (const entry of workspace.entries) workspace.discard(entry.id); expect(workspace.needsUnloadWarning).toBe(false);
});

it("settles a failed digest near the payload limit and permits retry without truncating source", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenContract(workspace); workspace.editRun(id, "run-a");
  const content = "x".repeat(230_000);
  vi.mocked(getBridgeSnapshot).mockResolvedValue(session([{ ...turn, content }]));
  await workspace.loadSource(id, score); workspace.selectTurn(id, 0);
  expect(workspace.active?.turns[0]?.content).toBe(content);
  const failure = vi.spyOn(crypto.subtle, "digest").mockRejectedValueOnce(new Error("x".repeat(30_000)));
  await workspace.freezeSource(id);
  expect(workspace.active?.loading).toBe(false); expect(workspace.active?.error).toContain("oversized error message");
  expect(workspace.active?.turns[0]?.content).toBe(content); expect(workspace.active?.source).toBeNull();
  failure.mockRestore(); await workspace.freezeSource(id);
  expect(workspace.active?.loading).toBe(false); expect(workspace.active?.source?.content).toBe(content);
});

it("settles rejected contract freezing at the document limit and retries after space is released", async () => {
  const workspace = createEvaluationWorkspace();
  const criteria = Array.from({ length: 8 }, (_, index) => ({ id: `criterion-${index}`, statement: "s".repeat(2_000), evidence: "e".repeat(2_000), missing: "m".repeat(2_000) }));
  for (let index = 0; index < 4; index++) {
    workspace.start(score);
    workspace.editContract(workspace.activeId!, { goal: "g".repeat(4_000), reviewer: "r".repeat(256), criteria });
  }
  const id = workspace.activeId!, original = canonical(workspace.active?.criteria);
  await workspace.freezeContract(id);
  expect(workspace.active?.loading).toBe(false);
  expect(workspace.active?.contract).toBeNull();
  expect(canonical(workspace.active?.criteria)).toBe(original);
  expect(workspace.active?.error).toContain("character limit");
  workspace.discard(workspace.entries.find(entry => entry.id !== id)!.id);
  await workspace.freezeContract(id);
  expect(workspace.active?.loading).toBe(false);
  expect(workspace.active?.contract?.criteria).toHaveLength(8);
});

it("preserves a shell-owned review through remount and keeps its exact score when the displayed score changes", async () => {
  const workspace = createEvaluationWorkspace(), id = await frozenSource(workspace);
  const first = mount(workspace); first.component.unmount(); const second = mount(workspace);
  expect(await screen.findByRole("region", { name: "Frozen output" })).toBeTruthy();
  await second.component.rerender({ score: { ...score, revision: "2" } });
  expect(screen.getByText(/belongs to another exact score/)).toBeTruthy(); expect(workspace.active?.source?.score.revision).toBe("1");
  await fireEvent.click(screen.getByRole("button", { name: "Discard review" }));
  expect(workspace.entries).toHaveLength(1); await fireEvent.click(screen.getByRole("button", { name: "Confirm discard" })); expect(workspace.entries).toHaveLength(0);
  expect(workspace.activeId).not.toBe(id); second.component.unmount();
});
