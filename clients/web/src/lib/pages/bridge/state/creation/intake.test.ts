import { describe, expect, it, vi } from "vitest";
import { ApiError } from "$lib/api/client";
import { emptyDraft, initialIntakeState, InvestigationIntake, prepareRequest, retainedReport,
  type CaseView, type IntakeState, type InvestigationDraft } from "./intake";

const a = "00000000-0000-4000-8000-000000000001";
const b = "00000000-0000-4000-8000-000000000002";
const run = "00000000-0000-4000-8000-000000000003";
function draft(): InvestigationDraft {
  return { ...emptyDraft(), repository: "public/example", baseRevision: "main", digest: "a".repeat(40),
    question: "What does this return?", publicMaterial: true,
    sources: [{ key: "source-a", name: "a.py", text: "return 1\n" }],
    criteria: [{ key: "criterion-a", id: "answer", predicate: "Cite the return value." }] };
}
function request(id = a) {
  const result = prepareRequest(draft(), id);
  if (!result.request) throw new Error("fixture invalid");
  return result.request;
}
function view(id = a): CaseView {
  return { case_id: id, request: request(id), status: "accepted", deadline: "2026-10-17T12:00:00+00:00",
    slot_encumbered: false, reason: null, admissions: [{ case_id: id, admission_id: id, run_id: run,
      principal: "MUST_NOT_PROJECT", authentication_generation: "MUST_NOT_PROJECT" }],
    attempts: [{ response: "MUST_NOT_PROJECT" }], profile: { endpoint: "MUST_NOT_PROJECT" },
    profile_digest: "a".repeat(64), request_digest: "b".repeat(64), candidate_digest: "c".repeat(64),
    candidate: { summary: "It returns 1.", findings: [{ criterion: "answer", claim: "One.", unknown: "",
      citations: [{ source: "a.py", first_line: 1, last_line: 1 }] }] },
    verdict: { disposition: "accepted", findings: [{ criterion: "answer", claim: "Supported.", unknown: "", citations: [] }], contradictions: [] } };
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done; }); return { promise, resolve }; }
function harness(api = { submit: vi.fn().mockResolvedValue(view()), read: vi.fn().mockResolvedValue(view()) }) {
  let state = initialIntakeState();
  const model = new InvestigationIntake(api, (next) => { state = next; });
  return { api, model, get state(): IntakeState { return state; } };
}

describe("literal investigation preparation", () => {
  it("preserves source bytes and field whitespace in a new plain request", () => {
    const value = draft(); value.sources[0]!.text = "  é\n"; value.question = "  Question? ";
    expect(prepareRequest(value, a).request).toMatchObject({ request_id: a, question: "  Question? ", sources: [{ name: "a.py", text: "  é\n" }] });
  });
  it.each([
    (d: InvestigationDraft) => { d.publicMaterial = false; },
    (d: InvestigationDraft) => { d.sources[0]!.text = "é".repeat(2049); },
    (d: InvestigationDraft) => { d.question = "é".repeat(257); },
    (d: InvestigationDraft) => { d.sources[0]!.name = "../private"; },
    (d: InvestigationDraft) => { d.sources[0]!.name = "a\\b"; },
    (d: InvestigationDraft) => { d.sources[0]!.name = "a:b"; },
    (d: InvestigationDraft) => { d.sources[0]!.name = "a\0b"; },
    (d: InvestigationDraft) => { d.sources.push({ ...d.sources[0]!, key: "another" }); },
    (d: InvestigationDraft) => { d.criteria.push({ ...d.criteria[0]!, key: "another" }); },
    (d: InvestigationDraft) => { d.sources = Array.from({ length: 9 }, (_, index) => ({ key: String(index), name: `${index}.py`, text: "a" })); },
    (d: InvestigationDraft) => { d.criteria[0]!.predicate = "é".repeat(97); },
    (d: InvestigationDraft) => { d.sources[0]!.text = "\ud800"; }
  ])("refuses invalid or over-byte input without creating an offering", (change) => {
    const value = draft(); change(value);
    const prepared = prepareRequest(value, a);
    expect(prepared.request).toBeNull(); expect(prepared.errors.length).toBeGreaterThan(0);
  });
});

describe("exact immutable submission and protected reads", () => {
  it("never retries an ambiguous POST; explicit replay preserves UUID and bytes after draft edits", async () => {
    const h = harness(); h.api.submit.mockRejectedValue(new TypeError("private endpoint credential body"));
    const original = request(); const body = JSON.stringify(original);
    await h.model.submit(original);
    original.question = "changed draft";
    h.model.select(b); h.model.select(a);
    h.api.read.mockRejectedValue(new ApiError("not found", 404));
    await h.model.check();
    expect(h.api.submit).toHaveBeenCalledOnce();
    expect(h.state.unconfirmedIds).toEqual([a]); expect(h.state.canReplay).toBe(true);
    expect(h.state.message).not.toContain("credential");
    await h.model.replay();
    expect(h.api.submit).toHaveBeenCalledTimes(2);
    expect(h.api.submit.mock.calls.map(([sent]) => JSON.stringify(sent))).toEqual([body, body]);
  });
  it.each([400, 401, 403, 404, 409, 500, 503])("keeps failed POST %s unconfirmed, including after possible commit", async (status) => {
    const h = harness(); h.api.submit.mockRejectedValue(new ApiError("PRIVATE", status, "unsafe PRIVATE"));
    await h.model.submit(request());
    expect(h.state.phase).toBe("unconfirmed"); expect(h.state.unconfirmedIds).toEqual([a]);
    expect(h.state.canReplay).toBe(true); expect(h.state.report).toBeNull(); expect(h.state.message).not.toContain("PRIVATE");
  });
  it("allows only explicit read after reload; UUID cannot recover the original body", async () => {
    const h = harness(); h.model.select(a);
    expect(h.api.read).not.toHaveBeenCalled(); await h.model.replay(); expect(h.api.submit).not.toHaveBeenCalled();
    h.api.read.mockRejectedValue(new ApiError("missing", 404)); await h.model.check();
    expect(h.state.phase).toBe("unavailable"); expect(h.state.canReplay).toBe(false);
    expect(h.state.message).toContain("does not resolve");
  });
  it("fences late selected-case responses and aborts the old read", async () => {
    const first = deferred<CaseView>(); const h = harness();
    h.api.read.mockImplementationOnce(() => first.promise).mockResolvedValueOnce(view(b));
    h.model.select(a); const pending = h.model.check();
    const signal = h.api.read.mock.calls[0]?.[1] as AbortSignal | undefined;
    h.model.select(b); await h.model.check(); first.resolve(view(a)); await pending;
    expect(signal?.aborted).toBe(true); expect(h.state.caseId).toBe(b); expect(h.state.report?.case_id).toBe(b);
  });
  it.each([401, 403])("clears the protected retained report on read refusal %s", async (status) => {
    const h = harness(); h.model.select(a); await h.model.check(); expect(h.state.report).not.toBeNull();
    h.api.read.mockRejectedValue(new ApiError("PRIVATE", status)); await h.model.check();
    expect(h.state.report).toBeNull(); expect(h.state.message).not.toContain("PRIVATE");
  });
  it("does not disclose or settle a mismatched successful POST response", async () => {
    const h = harness(); h.api.submit.mockResolvedValue(view(b)); await h.model.submit(request());
    expect(h.state.phase).toBe("unconfirmed"); expect(h.state.report).toBeNull(); expect(h.state.unconfirmedIds).toEqual([a]);
  });
  it("explicit different request discards replay body while keeping earlier uncertainty visible", async () => {
    const h = harness(); h.api.submit.mockRejectedValue(new TypeError("lost")); await h.model.submit(request());
    h.model.startDifferent(); expect(h.state.unconfirmedIds).toEqual([a]); expect(h.state.caseId).toBeNull();
    h.model.select(a); await h.model.replay(); expect(h.api.submit).toHaveBeenCalledOnce(); expect(h.state.canReplay).toBe(false);
  });
  it("drops private operational fields and refuses malformed or foreign retained report structure", () => {
    const safe = retainedReport(view(), a);
    expect(JSON.stringify(safe)).not.toContain("MUST_NOT_PROJECT");
    expect(() => retainedReport(view(b), a)).toThrow();
    const foreign = view(); foreign.admissions[0]!.case_id = b; expect(() => retainedReport(foreign, a)).toThrow();
    const malformed = view(); malformed.candidate = { summary: "private", findings: [] }; expect(() => retainedReport(malformed, a)).toThrow();
    const duplicate = view(); duplicate.candidate = { summary: "two", findings: [{ criterion: "answer", claim: "A", unknown: "", citations: [] }, { criterion: "answer", claim: "B", unknown: "", citations: [] }] };
    expect(() => retainedReport(duplicate, a)).toThrow();
  });
});
