import { act, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeNavigate } from "$app/navigation";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, readCreationFeedback, readCreationInvestigation, submitCreationInvestigation } from "$lib/api/client";
import type { CaseView, InvestigationRequest } from "$lib/creation/intake";
import CreationInvestigation from "./CreationInvestigation.svelte";

const navigationHooks = vi.hoisted(() => ({ after: [] as Array<() => void> }));
vi.mock("$app/navigation", () => ({ beforeNavigate: vi.fn(), afterNavigate: (callback: () => void) => {
  navigationHooks.after.push(callback); callback();
} }));
vi.mock("$lib/api/client", async (original) => {
  const actual = await original<typeof import("$lib/api/client")>();
  return { ...actual, readCreationFeedback: vi.fn(), readCreationInvestigation: vi.fn(), submitCreationInvestigation: vi.fn() };
});
const a = "00000000-0000-4000-8000-000000000001";
const b = "00000000-0000-4000-8000-000000000002";
const run = "00000000-0000-4000-8000-000000000003";
const read = vi.mocked(readCreationInvestigation);
const feedbackRead = vi.mocked(readCreationFeedback);
const post = vi.mocked(submitCreationInvestigation);
function view(id = a): CaseView {
  return { case_id: id, status: "accepted", deadline: "2026-10-17T12:00:00+00:00", slot_encumbered: false, reason: null,
    request_digest: "a".repeat(64), profile_digest: "b".repeat(64), candidate_digest: "c".repeat(64), profile: {}, attempts: [],
    request: { request_id: id, public_material: true, repository: "public/example", base_revision: "main", tree_or_patch_digest: "a".repeat(40),
      question: "Question?", non_goals: [], omissions: [], sources: [{ name: "a.py", text: "return 1\n" }], criteria: [{ id: "answer", predicate: "Cite it." }] },
    admissions: [{ case_id: id, admission_id: id, run_id: run }],
    candidate: { summary: `Candidate ${id}`, findings: [{ criterion: "answer", claim: "One.", unknown: "", citations: [{ source: "a.py", first_line: 1, last_line: 1 }] }] },
    verdict: { disposition: "accepted", findings: [{ criterion: "answer", claim: "Supported.", unknown: "", citations: [] }], contradictions: [] } };
}
async function fill() {
  for (const [label, value] of [["Repository", "public/example"], ["Base revision", "main"], ["Tree or patch digest", "a".repeat(40)],
    [/^Question/, "Question?"], ["Source name", "a.py"], ["Source text", "return 1\n"], ["Criterion ID", "answer"], [/^Criterion predicate/, "Cite it."]] as const) {
    await fireEvent.input(screen.getByLabelText(label), { target: { value } });
  }
  await fireEvent.click(screen.getByRole("checkbox", { name: "I confirm every supplied item is public material." }));
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done; }); return { promise, resolve }; }
function guardNavigation(target: string, source: string, type: "link" | "popstate" = "link", willUnload = false) {
  const guard = vi.mocked(beforeNavigate).mock.calls.at(-1)?.[0];
  if (!guard) throw new Error("The investigation has no navigation guard.");
  const cancel = vi.fn();
  guard({ from: { url: new URL(source) }, to: { url: new URL(target) }, type, willUnload, cancel } as never);
  return cancel;
}
beforeEach(() => {
  navigationHooks.after = []; vi.mocked(beforeNavigate).mockClear();
  read.mockReset(); feedbackRead.mockReset(); post.mockReset(); vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => { vi.restoreAllMocks(); });

describe("Bridge Creation investigation focus", () => {
  it("submits one explicit immutable request and links its retained report to the exact Run", async () => {
    post.mockImplementation(async (request: InvestigationRequest) => ({ ...view(request.request_id), request }));
    const onSelect = vi.fn(); render(CreationInvestigation, { caseId: null, onSelect });
    await fill(); await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByText("Retained investigation");
    expect(post).toHaveBeenCalledOnce(); expect(onSelect).toHaveBeenCalledWith(post.mock.calls[0]![0].request_id);
    expect(screen.getByRole("link", { name: `Look into the Orb · ${run}` }).getAttribute("href")).toBe(`/orb/${run}`);
    expect(screen.getByRole("region", { name: "External feedback" }).textContent).toMatch(/not loaded/i);
    expect(screen.getByRole("button", { name: "Load feedback" })).toBeTruthy();
    expect(feedbackRead).not.toHaveBeenCalled();
    expect(screen.getByText(/A native accepted verdict is not final owner acceptance/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /cancel|continue|assessment|decision/i })).toBeNull();
  });
  it("keeps a failed403 admission ambiguous, checks explicitly and never retries POST on404", async () => {
    post.mockRejectedValue(new ApiError("PRIVATE ENDPOINT", 403)); read.mockRejectedValue(new ApiError("missing", 404));
    render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    expect(post).toHaveBeenCalledOnce(); expect(read).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    await screen.findByText(/No protected report is displayed/);
    expect(post).toHaveBeenCalledOnce(); expect(screen.getByRole("button", { name: "Replay identical request" })).toBeTruthy();
    expect(document.body.textContent).not.toContain("PRIVATE ENDPOINT");
  });
  it("reload selection contains only a UUID and cannot recover replay; only Check reads", async () => {
    read.mockResolvedValue(view()); render(CreationInvestigation, { caseId: a, onSelect: vi.fn() });
    expect(read).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Replay identical request" })).toBeNull();
    expect(screen.getByText(/original request body is unavailable/)).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" })); await screen.findByText("Retained investigation");
    expect(read.mock.calls[0]?.[0]).toBe(a); expect(post).not.toHaveBeenCalled();
  });
  it("announces local validation and byte errors with focus without posting", async () => {
    render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.input(screen.getByLabelText("Source text"), { target: { value: "é".repeat(2049) } });
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByText(/All source text together must fit 4096/);
    expect(post).not.toHaveBeenCalled(); expect(document.activeElement?.textContent).toBe("Check the request");
    expect(screen.getByLabelText("Source text")).toHaveProperty("value", "é".repeat(2049));
  });
  it("clears old protected text when a selected-case read is refused", async () => {
    read.mockResolvedValueOnce(view()).mockRejectedValueOnce(new ApiError("PRIVATE", 401));
    render(CreationInvestigation, { caseId: a, onSelect: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" })); await screen.findByText(`Candidate ${a}`);
    await fireEvent.click(screen.getByRole("button", { name: "Refresh retained case" })); await screen.findByText(/No protected report is displayed/);
    expect(screen.queryByText(`Candidate ${a}`)).toBeNull(); expect(screen.queryByText("Retained literal sources")).toBeNull();
  });
  it("fences a late report after another case is selected", async () => {
    const old = deferred<CaseView>(); read.mockImplementationOnce(() => old.promise).mockResolvedValueOnce(view(b));
    const rendered = render(CreationInvestigation, { caseId: a, onSelect: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    await rendered.rerender({ caseId: b, onSelect: vi.fn() });
    await act(() => { navigationHooks.after.at(-1)?.(); });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" })); await screen.findByText(`Candidate ${b}`);
    old.resolve(view(a)); await waitFor(() => expect(screen.queryByText(`Candidate ${a}`)).toBeNull());
    expect(screen.getByText(`Candidate ${b}`)).toBeTruthy();
  });
  it("invalidates a pending read when navigation changes even without another Check", async () => {
    const old = deferred<CaseView>(); read.mockImplementationOnce(() => old.promise);
    const rendered = render(CreationInvestigation, { caseId: a, onSelect: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    await rendered.rerender({ caseId: b, onSelect: vi.fn() });
    await act(() => { navigationHooks.after.at(-1)?.(); });
    old.resolve(view(a)); await act(() => Promise.resolve());
    expect(screen.queryByText(`Candidate ${a}`)).toBeNull();
    await rendered.rerender({ caseId: a, onSelect: vi.fn() });
    await act(() => { navigationHooks.after.at(-1)?.(); });
    expect(screen.queryByText(`Candidate ${a}`)).toBeNull(); expect(read).toHaveBeenCalledOnce();
  });
  it("renders retained source and report as escaped text without operational payloads", async () => {
    const hostile = view(); hostile.candidate!.summary = "<img src=x onerror=alert(1)>";
    hostile.request.sources = [{ name: "a.py", text: "<script>window.stolen=true</script>" }];
    hostile.attempts = [{ input: "PRIVATE_ROLE_PACKET", response: "PRIVATE_PROVIDER_RESPONSE" }];
    read.mockResolvedValue(hostile); render(CreationInvestigation, { caseId: a, onSelect: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" })); await screen.findByText("<img src=x onerror=alert(1)>");
    expect(document.body.querySelector("img, script")).toBeNull();
    expect(screen.getByText("<script>window.stolen=true</script>")).toBeTruthy();
    expect(document.body.textContent).not.toContain("PRIVATE_ROLE_PACKET"); expect(document.body.textContent).not.toContain("PRIVATE_PROVIDER_RESPONSE");
  });

  it("allows same-component A to B to A selection without a loss prompt or automatic requests", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    const oldRead = deferred<CaseView>(); read.mockImplementationOnce(() => oldRead.promise);
    const rendered = render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const original = JSON.stringify(post.mock.calls[0]![0]); const id = post.mock.calls[0]![0].request_id;
    const from = "http://localhost/bridge?investigation=" + id;
    vi.mocked(window.confirm).mockReturnValue(false);
    expect(guardNavigation("http://localhost/bridge?investigation=" + b, from)).not.toHaveBeenCalled();
    expect(window.confirm).not.toHaveBeenCalled(); expect(post).toHaveBeenCalledOnce(); expect(read).not.toHaveBeenCalled();
    await rendered.rerender({ caseId: b, onSelect: vi.fn() }); await act(() => { navigationHooks.after.at(-1)?.(); });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    expect(read).toHaveBeenCalledOnce();
    expect(guardNavigation(from, "http://localhost/bridge?investigation=" + b, "popstate")).not.toHaveBeenCalled();
    await rendered.rerender({ caseId: id, onSelect: vi.fn() }); await act(() => { navigationHooks.after.at(-1)?.(); });
    oldRead.resolve(view(b)); await act(() => Promise.resolve());
    expect(screen.queryByText("Candidate " + b)).toBeNull();
    expect(window.confirm).not.toHaveBeenCalled(); expect(post).toHaveBeenCalledOnce(); expect(read).toHaveBeenCalledOnce();
    expect(guardNavigation("http://localhost/bridge?investigation=new", from)).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole("button", { name: "Replay identical request" }));
    await screen.findByText(/Admission unconfirmed\. Check this exact case/);
    expect(post).toHaveBeenCalledTimes(2); expect(JSON.stringify(post.mock.calls[1]![0])).toBe(original);
  });
  it("guards duplicate and invalid focus and ordinary Bridge departure before transient work is lost", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const id = post.mock.calls[0]![0].request_id; const from = "http://localhost/bridge?investigation=" + id;
    vi.mocked(window.confirm).mockReturnValue(false);
    const targets = [
      from + "&investigation=" + b, from + "&investigation=" + id, "http://localhost/bridge?investigation=invalid",
      "http://localhost/bridge?investigation=", "http://localhost/bridge", "http://localhost/bridge/session?investigation=" + id,
      "http://localhost/orb/" + run, "http://different.example/bridge?investigation=" + id
    ];
    for (const target of targets) expect(guardNavigation(target, from)).toHaveBeenCalledOnce();
    expect(window.confirm).toHaveBeenCalledTimes(targets.length);
    expect(post).toHaveBeenCalledOnce(); expect(read).not.toHaveBeenCalled();
    vi.mocked(window.confirm).mockReturnValue(true);
    expect(guardNavigation("http://localhost/bridge", from)).not.toHaveBeenCalled();
  });
  it("retains native document unload protection even for a valid investigation destination", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const id = post.mock.calls[0]![0].request_id;
    guardNavigation("http://localhost/bridge?investigation=" + b, "http://localhost/bridge?investigation=" + id, "link", true);
    expect(window.confirm).not.toHaveBeenCalled();
    const leaving = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(true); expect(post).toHaveBeenCalledOnce(); expect(read).not.toHaveBeenCalled();
  });
  it("keeps the draft and identical replay body when the inline discard review is declined", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    const onSelect = vi.fn(); const rendered = render(CreationInvestigation, { caseId: null, onSelect }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const id = post.mock.calls[0]![0].request_id; const original = JSON.stringify(post.mock.calls[0]![0]);
    const opener = screen.getByRole("button", { name: "Start different request" }); await fireEvent.click(opener);
    const review = await screen.findByRole("heading", { name: "Start a different request?" });
    expect(document.activeElement).toBe(review);
    expect(screen.getByText(/does not cancel or resolve/)).toBeTruthy();
    expect(post).toHaveBeenCalledOnce(); expect(read).not.toHaveBeenCalled(); expect(onSelect).toHaveBeenCalledOnce();
    await fireEvent.click(screen.getByRole("button", { name: "Keep current request" }));
    expect(screen.queryByRole("heading", { name: "Start a different request?" })).toBeNull();
    expect(document.activeElement).toBe(opener); expect(window.confirm).not.toHaveBeenCalled();
    await rendered.rerender({ caseId: null, onSelect }); await act(() => { navigationHooks.after.at(-1)?.(); });
    expect(screen.getByLabelText("Repository")).toHaveProperty("value", "public/example");
    expect(screen.getByLabelText("Source text")).toHaveProperty("value", "return 1\n");
    await rendered.rerender({ caseId: id, onSelect }); await act(() => { navigationHooks.after.at(-1)?.(); });
    await fireEvent.click(screen.getByRole("button", { name: "Replay identical request" }));
    await screen.findByText(/Admission unconfirmed\. Check this exact case/);
    expect(post).toHaveBeenCalledTimes(2); expect(JSON.stringify(post.mock.calls[1]![0])).toBe(original);
  });
  it("discards only on explicit confirmation and rejects a busy or stale discard review", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    const oldRead = deferred<CaseView>(); read.mockImplementationOnce(() => oldRead.promise);
    const onSelect = vi.fn(); const rendered = render(CreationInvestigation, { caseId: null, onSelect }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const id = post.mock.calls[0]![0].request_id;
    await fireEvent.click(screen.getByRole("button", { name: "Start different request" }));
    await screen.findByRole("heading", { name: "Start a different request?" });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    const discard = screen.getByRole("button", { name: "Discard draft and replay body" });
    expect(discard).toHaveProperty("disabled", true); await fireEvent.click(discard);
    expect(onSelect).toHaveBeenCalledOnce(); expect(post).toHaveBeenCalledOnce();
    await rendered.rerender({ caseId: b, onSelect }); await act(() => { navigationHooks.after.at(-1)?.(); });
    expect(screen.queryByRole("heading", { name: "Start a different request?" })).toBeNull();
    oldRead.resolve(view(id)); await act(() => Promise.resolve());
    await rendered.rerender({ caseId: id, onSelect }); await act(() => { navigationHooks.after.at(-1)?.(); });
    expect(screen.getByRole("button", { name: "Replay identical request" })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Start different request" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Discard draft and replay body" }));
    const heading = screen.getByRole("heading", { name: "Creation investigation", level: 1 });
    await waitFor(() => expect(document.activeElement).toBe(heading));
    expect(onSelect).toHaveBeenLastCalledWith(null); expect(post).toHaveBeenCalledOnce(); expect(read).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("Repository")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Source text")).toHaveProperty("value", "");
    expect(screen.getByRole("link", { name: id })).toBeTruthy();
    await rendered.rerender({ caseId: id, onSelect }); await act(() => { navigationHooks.after.at(-1)?.(); });
    expect(screen.queryByRole("button", { name: "Replay identical request" })).toBeNull();
    expect(post).toHaveBeenCalledOnce(); expect(window.confirm).not.toHaveBeenCalled();
  });
  it("loses the original body on real component destruction and requires an explicit Check after remount", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    const rendered = render(CreationInvestigation, { caseId: null, onSelect: vi.fn() }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const id = post.mock.calls[0]![0].request_id; rendered.unmount();
    read.mockResolvedValue(view(id)); render(CreationInvestigation, { caseId: id, onSelect: vi.fn() });
    expect(screen.queryByRole("button", { name: "Replay identical request" })).toBeNull();
    expect(read).not.toHaveBeenCalled(); expect(post).toHaveBeenCalledOnce();
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    await screen.findByText("Retained investigation"); expect(read).toHaveBeenCalledOnce(); expect(post).toHaveBeenCalledOnce();
  });
  it("keeps a pending Check and replay body while Keep returns focus to the intake heading", async () => {
    post.mockRejectedValue(new ApiError("unconfirmed", 403));
    let rejectRead!: (reason: unknown) => void;
    read.mockImplementationOnce(() => new Promise<CaseView>((_resolve, reject) => { rejectRead = reject; }));
    const onSelect = vi.fn(); render(CreationInvestigation, { caseId: null, onSelect }); await fill();
    await fireEvent.submit(screen.getByRole("form", { name: "Public-source investigation" }));
    await screen.findByRole("heading", { name: "Admission unconfirmed" });
    const original = JSON.stringify(post.mock.calls[0]![0]);
    const opener = screen.getByRole("button", { name: "Start different request" }); await fireEvent.click(opener);
    await screen.findByRole("heading", { name: "Start a different request?" });
    await fireEvent.click(screen.getByRole("button", { name: "Check this case" }));
    const signal = read.mock.calls[0]![1] as AbortSignal;
    expect(opener).toHaveProperty("disabled", true);
    const keep = screen.getByRole("button", { name: "Keep current request" }); keep.focus();
    expect(document.activeElement).toBe(keep); await fireEvent.click(keep);
    const heading = screen.getByRole("heading", { name: "Creation investigation", level: 1 });
    await waitFor(() => expect(document.activeElement).toBe(heading));
    expect(screen.queryByRole("heading", { name: "Start a different request?" })).toBeNull();
    expect(screen.getByRole("button", { name: "Checking…" })).toHaveProperty("disabled", true);
    expect(signal.aborted).toBe(false); expect(read).toHaveBeenCalledOnce(); expect(post).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledOnce();
    await act(() => { rejectRead(new ApiError("missing", 404)); });
    await screen.findByText(/No protected report is displayed/);
    await fireEvent.click(screen.getByRole("button", { name: "Replay identical request" }));
    await screen.findByText(/Admission unconfirmed\. Check this exact case/);
    expect(post).toHaveBeenCalledTimes(2); expect(JSON.stringify(post.mock.calls[1]![0])).toBe(original);
    expect(window.confirm).not.toHaveBeenCalled();
  });
});
