import { webcrypto } from "node:crypto";
import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { ArchiveBridgeDefault, NoteRecord } from "$lib/api/models";
const hooks = vi.hoisted(() => ({ after: [] as (() => void)[], before: [] as ((event: unknown) => void)[] }));
vi.mock("$app/navigation", () => ({ afterNavigate: (fn: () => void) => { hooks.after.push(fn); }, beforeNavigate: (fn: (event: unknown) => void) => { hooks.before.push(fn); } }));
vi.mock("$lib/api/client", () => ({ ApiError: class ApiError extends Error { constructor(message: string, public status?: number) { super(message); } }, getArchiveProfile: vi.fn(), getArchiveBridgeDefault: vi.fn(), listArchiveNotes: vi.fn(), getArchiveNote: vi.fn(), admitArchiveNote: vi.fn(), promoteArchiveNote: vi.fn(), revokeArchiveNote: vi.fn(), discoverArchiveGeneration: vi.fn(), registerArchiveGeneration: vi.fn(), deriveArchiveNote: vi.fn(), inspectArchiveDerivation: vi.fn(), getBridgeSnapshot: vi.fn() }));
import * as api from "$lib/api/client";
import PublicNotes from "./PublicNotes.svelte";
const namespace = "00000000-0000-4000-8000-000000000001", id = "00000000-0000-4000-8000-000000000002";
const record: NoteRecord = { namespace_id: namespace, reference: { record_id: id, revision_digest: "a".repeat(64), lifecycle_version: 1 }, source_key: "<script>key</script>", source_revision: "r1", source_digest: "b".repeat(64), producer: "p", observed_at: "2026-10-19T00:00:00Z", created_at: "2026-10-19T00:00:00Z", lifecycle: "candidate" };
beforeEach(() => { vi.clearAllMocks(); hooks.after = []; hooks.before = []; vi.stubGlobal("crypto", webcrypto);
  vi.mocked(api.discoverArchiveGeneration).mockResolvedValue({ generation_id: "00000000-0000-4000-8000-000000000004", manifest_digest: "c".repeat(64) });
  vi.mocked(api.getArchiveProfile).mockResolvedValue({ profile: "local-public-notes@1", namespace_id: namespace, owner_subject: { identity: "owner" }, policy_revision: "policy" });
  vi.mocked(api.getArchiveBridgeDefault).mockResolvedValue({ current_default: { pattern_id: "bridge_chat", pattern_revision: "3", guidance: "ignored" }, requests_profile: true });
  vi.mocked(api.listArchiveNotes).mockResolvedValue({ records: [record], next_cursor: null }); vi.mocked(api.getArchiveNote).mockResolvedValue(record);
});
afterEach(() => { vi.unstubAllGlobals(); });
it.each([true, false, null] as const)("shows the current default %s separately and makes zero BridgeSnapshot calls", async (matches) => {
  const defaults: ArchiveBridgeDefault = { current_default: matches === null ? null : { pattern_id: "bridge_chat", pattern_revision: "3", guidance: null }, requests_profile: matches };
  vi.mocked(api.getArchiveBridgeDefault).mockResolvedValue(defaults);
  const view = render(PublicNotes, { selection: "manage", onSelect: vi.fn() });
  await screen.findByText(matches === null ? "Current default unavailable." : matches ? "Current default requests this profile." : "Current default does not request this profile.");
  expect(screen.queryByText("ignored")).toBeNull(); expect(api.getBridgeSnapshot).not.toHaveBeenCalled(); expect(api.admitArchiveNote).not.toHaveBeenCalled(); view.unmount();
});
it("deep-link loads exact metadata, escapes identities, stages correction without text and reviews exact revocation", async () => {
  const onSelect = vi.fn(); const view = render(PublicNotes, { selection: id, onSelect });
  await screen.findByRole("button", { name: "Review revoke" }); expect(document.querySelector("script")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Review revoke" }));
  expect(screen.getByRole("heading", { name: "Revoke this exact revision?" })).toBe(document.activeElement);
  expect(screen.getByText(/Controlled source text is cleared/)).toBeTruthy(); expect(api.revokeArchiveNote).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Keep revision" }));
  await fireEvent.click(screen.getByRole("button", { name: "Stage correction" })); expect(onSelect).toHaveBeenCalledWith("new");
  await view.rerender({ selection: "new", onSelect }); await act(() => { hooks.after.forEach((fn) => fn()); });
  expect((screen.getByLabelText(/^Complete replacement text/) as HTMLTextAreaElement).value).toBe("");
  expect((screen.getByLabelText("Source revision") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Source key") as HTMLInputElement).value).toBe(record.source_key);
  expect((screen.getByLabelText("Source key") as HTMLInputElement).readOnly).toBe(true);
  expect(api.admitArchiveNote).not.toHaveBeenCalled(); expect(api.promoteArchiveNote).not.toHaveBeenCalled(); view.unmount();
});
it("validates and focuses errors, freezes exact intake before one explicit POST, then promotes separately", async () => {
  vi.mocked(api.admitArchiveNote).mockImplementation(async (body) => ({ ...record, source_key: body.source_key, source_revision: body.source_revision, source_digest: body.source_digest, producer: body.producer, observed_at: body.observed_at }));
  const view = render(PublicNotes, { selection: "new", onSelect: vi.fn() }); await screen.findByRole("heading", { name: "Configured profile" });
  await fireEvent.submit(screen.getByRole("form", { name: "Public note intake" })); expect(screen.getByRole("heading", { name: "Check public intake" })).toBe(document.activeElement);
  for (const [label, value] of [["Source key", "key"], ["Source revision", "r1"], ["Producer", "p"], ["Observation time with timezone", "2026-10-19T00:00:00Z"], ["Complete replacement text", " exact é\n "]]) await fireEvent.input(screen.getByLabelText(new RegExp(`^${label!}`)), { target: { value } });
  await fireEvent.click(screen.getByLabelText("I confirm this is public material.")); await fireEvent.submit(screen.getByRole("form", { name: "Public note intake" }));
  await screen.findByRole("heading", { name: "Frozen public intake" }); expect(api.admitArchiveNote).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Submit candidate once" })); await screen.findByRole("button", { name: "Promote this candidate" });
  expect(api.admitArchiveNote).toHaveBeenCalledTimes(1); expect(api.promoteArchiveNote).not.toHaveBeenCalled();
  expect(vi.mocked(api.admitArchiveNote).mock.calls[0]![0].text).toBe(" exact é\n "); view.unmount();
});
it("default read failure is distinct and refusal clears protected metadata and controls", async () => {
  vi.mocked(api.getArchiveBridgeDefault).mockRejectedValue(new Error("sensitive")); const view = render(PublicNotes, { selection: id, onSelect: vi.fn() });
  await screen.findByText(/Current-default read failed/); await screen.findByRole("button", { name: "Review revoke" });
  vi.mocked(api.getArchiveNote).mockRejectedValue(new api.ApiError("sensitive", 403)); await fireEvent.click(screen.getByRole("button", { name: "Check exact record" }));
  await screen.findByText(/Public-note configuration is unavailable/); expect(screen.queryByRole("button", { name: "Review revoke" })).toBeNull(); expect(screen.queryByText("sensitive")).toBeNull();
  expect(api.admitArchiveNote).not.toHaveBeenCalled(); view.unmount();
});

it("requires separate promotion and exact revoke confirmation, with no POST from refresh", async () => {
  vi.mocked(api.promoteArchiveNote).mockResolvedValue({ ...record, lifecycle: "promoted", reference: { ...record.reference, lifecycle_version: 2 } });
  vi.mocked(api.revokeArchiveNote).mockResolvedValue({ ...record, lifecycle: "revoked", reference: { ...record.reference, lifecycle_version: 3 } });
  const view = render(PublicNotes, { selection: id, onSelect: vi.fn() });
  await screen.findByRole("button", { name: "Promote this candidate" });
  await fireEvent.click(screen.getByRole("button", { name: "Check exact record" }));
  await screen.findByRole("button", { name: "Promote this candidate" }); expect(api.promoteArchiveNote).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Promote this candidate" }));
  await screen.findByText(/Promoted: lifecycle-eligible/);
  expect(api.promoteArchiveNote).toHaveBeenCalledExactlyOnceWith(id, { expected_version: 1 });
  await fireEvent.click(screen.getByRole("button", { name: "Review revoke" })); expect(api.revokeArchiveNote).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Confirm exact revoke" }));
  await screen.findByText(/Revoked tombstone:/);
  expect(api.revokeArchiveNote).toHaveBeenCalledExactlyOnceWith(id, { expected_version: 2 }); expect(api.admitArchiveNote).not.toHaveBeenCalled(); view.unmount();
});

it("does not steal an intake input focus when initial secondary reads finish late", async () => {
  let finish!: (value: { records: NoteRecord[] }) => void;
  vi.mocked(api.listArchiveNotes).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const view = render(PublicNotes, { selection: "new", onSelect: vi.fn() });
  const producer = await screen.findByLabelText("Producer"); producer.focus();
  await fireEvent.input(producer, { target: { value: "Still composing" } });
  await act(() => { finish({ records: [] }); });
  expect(document.activeElement).toBe(producer); expect((producer as HTMLInputElement).value).toBe("Still composing"); view.unmount();
});

it.each([{ modes: ["manage"] }, { modes: ["manage", "new"] }])("a late intake cannot steal the newer mode focus %j or change its filter/detail/route", async ({ modes }) => {
  let finish!: (value: NoteRecord) => void;
  vi.mocked(api.admitArchiveNote).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const onSelect = vi.fn(); const view = render(PublicNotes, { selection: "new", onSelect });
  await screen.findByRole("heading", { name: "Configured profile" });
  for (const [label, value] of [["Source key", "key"], ["Source revision", "r1"], ["Producer", "p"], ["Observation time with timezone", "2026-10-19T00:00:00Z"], ["Complete replacement text", "exact public text"]])
    await fireEvent.input(screen.getByLabelText(new RegExp(`^${label!}`)), { target: { value } });
  await fireEvent.click(screen.getByLabelText("I confirm this is public material."));
  await fireEvent.submit(screen.getByRole("form", { name: "Public note intake" }));
  await screen.findByRole("button", { name: "Submit candidate once" });
  await fireEvent.click(screen.getByRole("button", { name: "Submit candidate once" }));
  vi.mocked(api.listArchiveNotes).mockResolvedValue({ records: [] });
  await view.rerender({ selection: "manage", onSelect }); await act(() => { hooks.after.forEach((fn) => fn()); });
  const filter = screen.getByLabelText("Exact source-key filter (optional)");
  await fireEvent.input(filter, { target: { value: "newer-filter" } }); await fireEvent.submit(filter.closest("form")!);
  for (const mode of modes.slice(1)) {
    await view.rerender({ selection: mode, onSelect }); await act(() => { hooks.after.forEach((fn) => fn()); });
  }
  const current = modes.at(-1) === "manage" ? screen.getByLabelText("Exact source-key filter (optional)") : screen.getByRole("link", { name: "New public note" });
  current.focus(); const reads = vi.mocked(api.listArchiveNotes).mock.calls.length;
  const sent = vi.mocked(api.admitArchiveNote).mock.calls[0]![0];
  await act(() => { finish({ ...record, source_key: sent.source_key, source_revision: sent.source_revision, source_digest: sent.source_digest, producer: sent.producer, observed_at: sent.observed_at }); });
  expect(onSelect).not.toHaveBeenCalled(); expect(screen.queryByRole("heading", { name: "Exact note metadata" })).toBeNull();
  expect(document.activeElement).toBe(current); expect(api.admitArchiveNote).toHaveBeenCalledTimes(1); expect(api.listArchiveNotes).toHaveBeenCalledTimes(reads);
  expect(screen.queryByText(id)).toBeNull();
  await view.rerender({ selection: "manage", onSelect }); await act(() => { hooks.after.forEach((fn) => fn()); });
  expect((screen.getByLabelText("Exact source-key filter (optional)") as HTMLInputElement).value).toBe("newer-filter");
  expect(screen.getByText("newer-filter", { selector: "code" })).toBeTruthy(); expect(api.admitArchiveNote).toHaveBeenCalledTimes(1);
  view.unmount();
});

it("promotion starts no preparation POST; a reviewed preparation serializes revoke/correction and never hydrates note metadata", async () => {
  const promoted = { ...record, lifecycle: "promoted" as const, reference: { ...record.reference, lifecycle_version: 2 } };
  vi.mocked(api.promoteArchiveNote).mockResolvedValue(promoted);
  let finish!: (value: import("$lib/api/models").ArchiveDerivationStatus) => void;
  vi.mocked(api.deriveArchiveNote).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const view = render(PublicNotes, { selection: id, onSelect: vi.fn() });
  await screen.findByRole("button", { name: "Promote this candidate" });
  await fireEvent.click(screen.getByRole("button", { name: "Promote this candidate" })); await screen.findByText(/Promoted: lifecycle-eligible/);
  expect(api.registerArchiveGeneration).not.toHaveBeenCalled(); expect(api.deriveArchiveNote).not.toHaveBeenCalled(); expect(api.inspectArchiveDerivation).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Review preparation" }));
  expect(screen.getByRole("heading", { name: "Review exact preparation" })).toBe(document.activeElement);
  expect(api.deriveArchiveNote).not.toHaveBeenCalled(); await fireEvent.click(screen.getByRole("button", { name: "Prepare this promoted revision" }));
  expect((screen.getByRole("button", { name: "Review revoke" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: "Stage correction" }) as HTMLButtonElement).disabled).toBe(true);
  const sent = vi.mocked(api.deriveArchiveNote).mock.calls[0]![0]; expect(sent).toEqual({ generation: { generation_id: "00000000-0000-4000-8000-000000000004", manifest_digest: "c".repeat(64) }, source: promoted.reference });
  await act(() => { finish({ derivation_id: id, namespace_id: namespace, generation: sent.generation, source: sent.source, source_digest: promoted.source_digest,
    row_version: 2, attempt_version: 1, state: "complete", observed_at: record.created_at, expires_at: null, completed_at: record.created_at, failure_code: null, invalidated_reason: null, vector_digest: "d".repeat(64), receipt_digest: null }); });
  expect(screen.getByText("complete", { selector: "strong" })).toBeTruthy(); expect(screen.getByText(/Promoted: lifecycle-eligible/)).toBeTruthy();
  expect((screen.getByRole("button", { name: "Review revoke" }) as HTMLButtonElement).disabled).toBe(false); expect(api.revokeArchiveNote).not.toHaveBeenCalled(); view.unmount();
});
it.each([401, 403])("a current preparation %s clears protected parent management too", async (status) => {
  vi.mocked(api.getArchiveNote).mockResolvedValue({ ...record, lifecycle: "promoted" });
  vi.mocked(api.inspectArchiveDerivation).mockRejectedValue(new api.ApiError("sensitive", status));
  const view = render(PublicNotes, { selection: id, onSelect: vi.fn() }); await screen.findByText("Configured generation");
  await screen.findByRole("button", { name: "Review revoke" }); await fireEvent.click(screen.getByRole("button", { name: "Check preparation" }));
  await screen.findByText(/Public-note configuration is unavailable/);
  expect(screen.queryByRole("heading", { name: "Semantic preparation" })).toBeNull(); expect(screen.queryByRole("button", { name: "Review revoke" })).toBeNull();
  expect(screen.queryByText(record.source_key)).toBeNull(); expect(screen.queryByText("sensitive")).toBeNull(); view.unmount();
});
it("late initial secondary metadata cannot steal a preparation review heading focus", async () => {
  let finish!: (value: { records: NoteRecord[] }) => void;
  vi.mocked(api.listArchiveNotes).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  vi.mocked(api.getArchiveNote).mockResolvedValue({ ...record, lifecycle: "promoted" });
  const view = render(PublicNotes, { selection: id, onSelect: vi.fn() }); await screen.findByText("Configured generation");
  await fireEvent.click(screen.getByRole("button", { name: "Review preparation" }));
  const heading = screen.getByRole("heading", { name: "Review exact preparation" }); expect(document.activeElement).toBe(heading);
  await act(() => { finish({ records: [record] }); }); expect(document.activeElement).toBe(heading); expect(api.deriveArchiveNote).not.toHaveBeenCalled(); view.unmount();
});

it.each([401, 403])("current preparation %s refusal after same-note metadata refresh clears the whole management focus", async (status) => {
  const promoted = { ...record, lifecycle: "promoted" as const };
  vi.mocked(api.getArchiveNote).mockResolvedValue(promoted);
  let reject!: (error: unknown) => void;
  vi.mocked(api.inspectArchiveDerivation).mockReturnValue(new Promise((_resolve, no) => { reject = no; }));
  const view = render(PublicNotes, { selection: id, onSelect: vi.fn() }); await screen.findByText("Configured generation");
  await fireEvent.click(screen.getByRole("button", { name: "Check preparation" }));
  await fireEvent.click(screen.getByRole("button", { name: "Check exact record" }));
  await screen.findByText(/Promoted: lifecycle-eligible/);
  await act(() => { reject(new api.ApiError("sensitive", status)); });
  expect(screen.queryByRole("heading", { name: "Semantic preparation" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Review revoke" })).toBeNull();
  expect(screen.getByText(/Public-note configuration is unavailable/)).toBeTruthy();
  view.unmount();
});
