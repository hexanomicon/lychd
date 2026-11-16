import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ArchiveRunRecall } from "$lib/api/models";

vi.mock("$lib/api/client", async (original) => ({
  ...await original<typeof import("$lib/api/client")>(), getArchiveRunRecall: vi.fn()
}));
import { ApiError, getArchiveRunRecall } from "$lib/api/client";
import ArchiveRecallPanel from "./ArchiveRecallPanel.svelte";

const runId = "00000000-0000-4000-8000-000000000001";
const recorded: ArchiveRunRecall = {
  run_id: runId, capture: "matching_retained_request", status: "recorded",
  receipt: {
    schema_version: 1, run_id: runId, receipt_id: "receipt-a", request_id: "request-a",
    namespace_id: "namespace-a", subject: { identity: "protected-subject" }, purpose: "answer",
    profile: "local-public-notes@1", policy_revision: "1", retrieval_policy: "postgres-simple-lexical@1",
    created_at: "2026-10-18T01:00:00Z", max_results: 5, char_budget: 8000, min_score: 0,
    omitted_for_budget: 2, query_digest: "query-digest", request_digest: "request-digest", receipt_digest: "receipt-digest",
    selected: [{ source_key: "<img src=x onerror=alert(1)>", source_revision: "rev-7",
      source_digest: "source-digest", score: 0.125, projected_chars: 234, projection_digest: "projection-digest",
      reference: { record_id: "record-a", lifecycle_version: 3, revision_digest: "revision-digest" } },
    { source_key: "second-source", source_revision: "rev-2", source_digest: "second-digest", score: 0.1,
      projected_chars: 100, projection_digest: "second-projection", reference: { record_id: "record-b", lifecycle_version: 1, revision_digest: "second-revision" } }]
  }
};
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function read() { await fireEvent.click(screen.getByRole("button", { name: "Read Archive selection" })); }
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getArchiveRunRecall).mockResolvedValue(recorded); });
afterEach(cleanup);

describe("explicit exact-Run Archive selection", () => {
  it("does not read on mount and shows ordered safe metadata with truthful capture and bounds", async () => {
    const view = render(ArchiveRecallPanel, { runId });
    expect(getArchiveRunRecall).not.toHaveBeenCalled();
    expect(screen.getByText(/Not read\./)).toBeTruthy();
    await read();
    expect(getArchiveRunRecall).toHaveBeenCalledWith(runId, expect.any(AbortSignal));
    await screen.findByText("Recorded selection");
    expect(screen.getByText(/caller can preseed/)).toBeTruthy();
    expect(screen.getByText(/consumption and provider transmission are unproved/)).toBeTruthy();
    expect(screen.getByText(/not complete corpus, Context or token accounting/)).toBeTruthy();
    expect(screen.getByText(/no current source eligibility/)).toBeTruthy();
    expect(screen.getByText("2 within this bounded selection")).toBeTruthy();
    expect(screen.getByText("Selected-note character bound (char_budget)")).toBeTruthy();
    const list = screen.getByRole("list", { name: "Selected source revisions in receipt order" });
    expect(within(list).getAllByRole("heading").map((item) => item.textContent)).toEqual(["<img src=x onerror=alert(1)>", "second-source"]);
    expect(view.container.querySelector("img")).toBeNull();
    for (const text of ["rev-7", "record-a", "0.125", "234", "revision-digest", "protected-subject"]) expect(screen.getByText(text)).toBeTruthy();
    expect(screen.getByText("Receipt identity and policy").closest("details")?.open).toBe(false);
    const times = [...view.container.querySelectorAll("time")];
    expect(times).toHaveLength(2);
    expect(times[0]!.dateTime).not.toBe(times[1]!.dateTime);
    expect(times[1]!.dateTime).toBe(recorded.receipt!.created_at);
  });

  it("distinguishes a recorded empty selection from missing or unsupported capture", async () => {
    vi.mocked(getArchiveRunRecall).mockResolvedValue({ ...recorded, receipt: { ...recorded.receipt!, selected: [], omitted_for_budget: 0 } });
    render(ArchiveRecallPanel, { runId }); await read();
    await screen.findByText(/Successful empty selection: zero notes/);
    expect(screen.getByText("Recorded selection")).toBeTruthy();
    expect(screen.getByText("0 within this bounded selection")).toBeTruthy();
  });

  it.each(["not_recorded", "not_applicable"] as const)("shows %s without inventing a receipt", async (status) => {
    vi.mocked(getArchiveRunRecall).mockResolvedValue({ ...recorded, status, receipt: null });
    render(ArchiveRecallPanel, { runId }); await read();
    await screen.findByText(status === "not_recorded" ? /Not recorded: no matching retained request/ : /Not applicable: this Run's pinned Pattern/);
    expect(screen.queryByText("Retained receipt created at")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each([
    [new ApiError("secret arbitrary error", 403), "Denied:"],
    [new ApiError("secret arbitrary error", 404), "Unavailable: Archive is unconfigured"],
    [new ApiError("secret arbitrary error", 409), "Refused:"],
    [new ApiError("secret arbitrary error", 500), "Failed:"],
    [new TypeError("secret arbitrary error"), "Failed:"]
  ])("clears protected metadata on a fresh failed read (%s)", async (failure, label) => {
    render(ArchiveRecallPanel, { runId }); await read(); await screen.findByText("protected-subject");
    const pending = deferred<ArchiveRunRecall>();
    vi.mocked(getArchiveRunRecall).mockReturnValueOnce(pending.promise);
    await fireEvent.click(screen.getByRole("button", { name: "Refresh Archive selection" }));
    expect(screen.queryByText("protected-subject")).toBeNull();
    await act(() => pending.reject(failure));
    expect((await screen.findByRole("alert")).textContent).toContain(label);
    expect(screen.queryByText(/secret arbitrary error/)).toBeNull();
    expect(screen.queryByText("record-a")).toBeNull();
    vi.mocked(getArchiveRunRecall).mockResolvedValueOnce(recorded);
    await fireEvent.click(screen.getByRole("button", { name: "Retry Archive selection" }));
    await screen.findByText("protected-subject");
  });

  it.each([
    { ...recorded, run_id: "other-run" },
    { ...recorded, receipt: null },
    { ...recorded, status: "not_recorded", receipt: recorded.receipt },
    { ...recorded, status: "not_applicable", receipt: recorded.receipt },
    { ...recorded, receipt: { ...recorded.receipt!, run_id: "other-run" } },
    { ...recorded, capture: "invented" },
    { ...recorded, receipt: { ...recorded.receipt!, selected: [recorded.receipt!.selected[0]!, recorded.receipt!.selected[0]!] } }
  ])("rejects a wrong Run or inconsistent receipt before display", async (response) => {
    vi.mocked(getArchiveRunRecall).mockResolvedValue(response as ArchiveRunRecall);
    render(ArchiveRecallPanel, { runId }); await read();
    expect((await screen.findByRole("alert")).textContent).toContain("Invalid response:");
    expect(screen.queryByText("protected-subject")).toBeNull();
  });

  it.each(["resolve", "reject"] as const)("aborts teardown and fences late %s", async (settle) => {
    const pending = deferred<ArchiveRunRecall>(); vi.mocked(getArchiveRunRecall).mockReturnValueOnce(pending.promise);
    const view = render(ArchiveRecallPanel, { runId }); await read();
    const signal = vi.mocked(getArchiveRunRecall).mock.calls[0]![1]!;
    view.unmount(); expect(signal.aborted).toBe(true);
    await act(() => settle === "resolve" ? pending.resolve(recorded) : pending.reject(new Error("late")));
    expect(screen.queryByText("protected-subject")).toBeNull();
  });
});
