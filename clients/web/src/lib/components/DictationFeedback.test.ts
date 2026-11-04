import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { DictationCorrection, DictationAttemptSummary, DictationResult, DictationLexiconRule, DictationSuggestion } from "$lib/api/models";
import DictationFeedback from "./DictationFeedback.svelte";

const api = vi.hoisted(() => ({ history: vi.fn(), corrections: vi.fn(), inspect: vi.fn(), deleteAttempt: vi.fn(), lexicon: vi.fn(), approve: vi.fn(), deleteRule: vi.fn(), suggest: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  listDictationAttempts: api.history, listDictationCorrections: api.corrections,
  getDictationAttempt: api.inspect, deleteDictationAttempt: api.deleteAttempt,
  listDictationLexicon: api.lexicon, approveDictationLexicon: api.approve,
  deleteDictationLexicon: api.deleteRule, getDictationSuggestions: api.suggest
}));

const rule: DictationLexiconRule = {
  id: "rule-one", language: "en", heard: "light", replacement: "LychD",
  created_at: "2026-11-03T10:00:00Z", expires_at: "2026-11-10T10:00:00Z"
};
const correction: DictationCorrection = {
  attempt_id: "attempt-one", language: "en", original_text: "light", final_text: "LychD",
  source_digest: `sha256:${"a".repeat(64)}`, profile_digest: `sha256:${"b".repeat(64)}`,
  created_at: "2026-11-03T10:00:00Z", expires_at: "2026-11-10T10:00:00Z"
};
const attempt: DictationAttemptSummary = {
  attempt_id: "attempt-one", status: "transcribed", language: "en", has_correction: true,
  created_at: correction.created_at, expires_at: correction.expires_at,
  audio_expires_at: "2026-11-03T10:05:00Z", audio_available: false
};
const outcome: DictationResult = {
  attempt_id: "attempt-one", status: "transcribed", language: "en", original_text: "light",
  source_digest: correction.source_digest, profile_digest: correction.profile_digest, reason: null
};
const suggestion: DictationSuggestion = {
  attempt_id: "attempt-one", language: "en", original_text: "light", suggested_text: "LychD",
  applied_rule_ids: [rule.id], rules: [rule]
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-03T12:00:00Z"));
  vi.resetAllMocks();
  api.history.mockResolvedValue([attempt]);
  api.corrections.mockResolvedValue([correction]);
  api.inspect.mockResolvedValue(outcome);
  api.lexicon.mockResolvedValue([rule]);
  api.suggest.mockResolvedValue(suggestion);
  api.approve.mockResolvedValue(rule);
  api.deleteAttempt.mockResolvedValue({ attempt_id: correction.attempt_id, deleted: true });
  api.deleteRule.mockResolvedValue({ rule_id: rule.id, deleted: true });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

function setup() {
  const applySuggestion = vi.fn(() => true);
  const props = { attemptId: "attempt-one", originalText: "light", finalText: "light", language: "en", savedRevision: 0, applySuggestion, active: true };
  return { ...render(DictationFeedback, props), props, applySuggestion };
}

async function disclosure(name: string, open = true) {
  const summary = screen.getByText(name, { selector: "summary" });
  const details = summary.parentElement as HTMLDetailsElement;
  details.open = open;
  await fireEvent(details, new Event("toggle"));
  await act(() => Promise.resolve());
  return summary;
}

async function fillApproval() {
  await fireEvent.input(screen.getByLabelText("Rule language"), { target: { value: "en" } });
  await fireEvent.input(screen.getByLabelText("Heard phrase"), { target: { value: "light" } });
  await fireEvent.input(screen.getByLabelText("Replacement phrase"), { target: { value: "LychD" } });
}

it("makes no request or mutation until a disclosure is opened", async () => {
  setup();
  await act(() => Promise.resolve());
  expect(api.history).not.toHaveBeenCalled();
  expect(api.corrections).not.toHaveBeenCalled();
  expect(api.inspect).not.toHaveBeenCalled();
  expect(api.lexicon).not.toHaveBeenCalled();
  expect(api.suggest).not.toHaveBeenCalled();
  expect(api.approve).not.toHaveBeenCalled();
  expect(screen.queryByRole("list")).toBeNull();
});

it("keeps failed history distinct from empty history and retries only on request", async () => {
  api.history.mockRejectedValueOnce(new Error("private diagnostic"));
  api.history.mockResolvedValueOnce([]);
  setup();
  await disclosure("Voice history");
  expect(screen.getByRole("alert").textContent).toContain("Could not load");
  expect(screen.queryByText("No retained voice attempts.")).toBeNull();
  expect(screen.queryByText("private diagnostic")).toBeNull();
  expect(api.history).toHaveBeenCalledOnce();
  await fireEvent.click(screen.getByRole("button", { name: "Retry history" }));
  expect(await screen.findByText("No retained voice attempts.")).toBeTruthy();
});

it("shows retained original/final text and expiry without an expanded wall of text", async () => {
  setup();
  await disclosure("Voice history");
  const pair = screen.getByText("Original and final text", { selector: "summary" }).parentElement as HTMLDetailsElement;
  expect(pair.open).toBe(false);
  expect(within(pair).getByText("light").textContent).toBe("light");
  expect(within(pair).getByText("LychD").textContent).toBe("LychD");
  expect(document.querySelector("time")?.dateTime).toBe(correction.expires_at);
});

it("pages all 1,000 retained attempts without truncation and bounds vocabulary to 128", async () => {
  api.history.mockResolvedValue(Array.from({ length: 1000 }, (_, index) => ({ ...attempt, has_correction: false, attempt_id: `attempt-${index}` })));
  api.corrections.mockResolvedValue([]);
  api.lexicon.mockResolvedValue(Array.from({ length: 135 }, (_, index) => ({ ...rule, id: `rule-${index}` })));
  setup();
  await disclosure("Voice history");
  await disclosure("Approved vocabulary");
  expect(within(screen.getByRole("list", { name: "Retained voice attempts" })).getAllByRole("listitem")).toHaveLength(25);
  expect(screen.getByText("Showing 25 of 1000 retained attempts.")).toBeTruthy();
  const showMore = screen.getByRole("button", { name: "Show more attempts" });
  for (let page = 1; page < 40; page += 1) {
    await fireEvent.click(showMore);
  }
  expect(screen.getByRole("button", { name: "Delete retained attempt attempt-999" })).toBeTruthy();
  expect(screen.getByText("Showing 1000 of 1000 retained attempts.")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Show more attempts" })).toBeNull();
  expect(within(screen.getByRole("list", { name: "Approved vocabulary rules" })).getAllByRole("listitem")).toHaveLength(128);
}, 20000);

it("aborts a closed history request and ignores its late response", async () => {
  const pending = deferred<DictationAttemptSummary[]>();
  api.history.mockReturnValueOnce(pending.promise);
  api.history.mockResolvedValueOnce([]);
  setup();
  await disclosure("Voice history");
  const signal = api.history.mock.calls[0]?.[0] as AbortSignal;
  await disclosure("Voice history", false);
  expect(signal.aborted).toBe(true);
  await disclosure("Voice history");
  await act(async () => { pending.resolve([attempt]); });
  expect(screen.getByText("No retained voice attempts.")).toBeTruthy();
  expect(screen.queryByText("Original and final text")).toBeNull();
});

it("refreshes saved corrections only while history is open", async () => {
  const mounted = setup();
  await mounted.rerender({ ...mounted.props, savedRevision: 1 });
  expect(api.history).not.toHaveBeenCalled();
  await disclosure("Voice history");
  expect(api.history).toHaveBeenCalledOnce();
  await mounted.rerender({ ...mounted.props, savedRevision: 2 });
  expect(api.history).toHaveBeenCalledTimes(2);
});

it("disables only an affected delete and restores focus to its disclosure", async () => {
  const pending = deferred<{ attempt_id: string; deleted: true }>();
  api.history.mockResolvedValueOnce([attempt, { ...attempt, attempt_id: "attempt-two" }]);
  api.history.mockResolvedValueOnce([{ ...attempt, attempt_id: "attempt-two" }]);
  api.deleteAttempt.mockReturnValueOnce(pending.promise);
  setup();
  const summary = await disclosure("Voice history");
  const button = screen.getByRole("button", { name: "Delete retained attempt attempt-one" }) as HTMLButtonElement;
  button.focus();
  await fireEvent.click(button);
  expect(button.disabled).toBe(true);
  expect((screen.getByRole("button", { name: "Delete retained attempt attempt-two" }) as HTMLButtonElement).disabled).toBe(false);
  await act(async () => { pending.resolve({ attempt_id: "attempt-one", deleted: true }); });
  expect(document.activeElement).toBe(summary);
  expect(screen.queryByRole("button", { name: "Delete retained attempt attempt-one" })).toBeNull();
});

it("does not steal draft focus when a deferred deletion completes", async () => {
  const pending = deferred<{ attempt_id: string; deleted: true }>();
  api.deleteAttempt.mockReturnValueOnce(pending.promise);
  api.history.mockResolvedValueOnce([attempt]).mockResolvedValueOnce([]);
  setup();
  await disclosure("Voice history");
  const button = screen.getByRole("button", { name: "Delete retained attempt attempt-one" });
  button.focus();
  await fireEvent.click(button);
  const draft = document.createElement("textarea");
  draft.setAttribute("aria-label", "Bridge draft");
  document.body.append(draft);
  try {
    draft.focus();
    draft.value = "Keep typing here";
    await act(async () => { pending.resolve({ attempt_id: "attempt-one", deleted: true }); });
    expect(document.activeElement).toBe(draft);
    expect(draft.value).toBe("Keep typing here");
    expect(screen.queryByRole("button", { name: "Delete retained attempt attempt-one" })).toBeNull();
  } finally {
    draft.remove();
  }
});

it("requires a history read after uncertain deletion instead of automatic retry", async () => {
  api.deleteAttempt.mockRejectedValue(new Error("connection lost"));
  setup();
  await disclosure("Voice history");
  const button = screen.getByRole("button", { name: "Delete retained attempt attempt-one" }) as HTMLButtonElement;
  await fireEvent.click(button);
  expect(button.disabled).toBe(true);
  expect(api.deleteAttempt).toHaveBeenCalledOnce();
  expect(screen.getByText(/Deletion could not be confirmed/)).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Refresh history" }));
  expect((await screen.findByRole("button", { name: "Delete retained attempt attempt-one" }) as HTMLButtonElement).disabled).toBe(false);
  expect(api.deleteAttempt).toHaveBeenCalledOnce();
});

it("restores focus when disabling the deletion control leaves only body focused", async () => {
  const pending = deferred<{ attempt_id: string; deleted: true }>();
  api.deleteAttempt.mockReturnValueOnce(pending.promise);
  api.history.mockResolvedValueOnce([attempt]).mockResolvedValueOnce([]);
  setup();
  const summary = await disclosure("Voice history");
  const button = screen.getByRole("button", { name: "Delete retained attempt attempt-one" });
  button.focus();
  await fireEvent.click(button);
  document.body.tabIndex = -1;
  try {
    document.body.focus();
    expect(document.activeElement).toBe(document.body);
    await act(async () => { pending.resolve({ attempt_id: "attempt-one", deleted: true }); });
    expect(document.activeElement).toBe(summary);
  } finally {
    document.body.removeAttribute("tabindex");
  }
});

it("does not reclaim body focus after the operator deliberately moved outside the row", async () => {
  const pending = deferred<{ attempt_id: string; deleted: true }>();
  api.deleteAttempt.mockReturnValueOnce(pending.promise);
  api.history.mockResolvedValueOnce([attempt]).mockResolvedValueOnce([]);
  setup();
  await disclosure("Voice history");
  const button = screen.getByRole("button", { name: "Delete retained attempt attempt-one" });
  button.focus();
  await fireEvent.click(button);
  const draft = document.createElement("textarea");
  document.body.append(draft);
  try {
    draft.focus();
    draft.blur();
    expect(document.activeElement).toBe(document.body);
    await act(async () => { pending.resolve({ attempt_id: "attempt-one", deleted: true }); });
    expect(document.activeElement).toBe(document.body);
  } finally {
    draft.remove();
  }
});

it("defaults only the language and requires explicit phrases and approval", async () => {
  setup();
  await disclosure("Approved vocabulary");
  expect((screen.getByLabelText("Heard phrase") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Rule language") as HTMLInputElement).value).toBe("en");
  await fillApproval();
  expect((screen.getByRole("button", { name: "Approve rule" }) as HTMLButtonElement).disabled).toBe(true);
  expect(api.approve).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByLabelText("I approve this language and phrase replacement"));
  await fireEvent.click(screen.getByRole("button", { name: "Approve rule" }));
  expect(api.approve).toHaveBeenCalledExactlyOnceWith({ language: "en", heard: "light", replacement: "LychD", approved: true });
});

it("follows transcript language only until the vocabulary form is edited", async () => {
  const mounted = setup();
  await disclosure("Approved vocabulary");
  expect((screen.getByLabelText("Rule language") as HTMLInputElement).value).toBe("en");
  await mounted.rerender({ ...mounted.props, language: "sk" });
  expect((screen.getByLabelText("Rule language") as HTMLInputElement).value).toBe("sk");
  await fireEvent.input(screen.getByLabelText("Heard phrase"), { target: { value: "heard phrase" } });
  await mounted.rerender({ ...mounted.props, language: "en-us" });
  expect((screen.getByLabelText("Rule language") as HTMLInputElement).value).toBe("sk");
  expect((screen.getByLabelText("Heard phrase") as HTMLInputElement).value).toBe("heard phrase");
});

it("aborts reads while outer options are inactive and resumes only open disclosures", async () => {
  const pending = deferred<DictationAttemptSummary[]>();
  api.history.mockReturnValueOnce(pending.promise).mockResolvedValueOnce([]);
  const mounted = setup();
  await disclosure("Voice history");
  const signal = api.history.mock.calls[0]?.[0] as AbortSignal;
  await mounted.rerender({ ...mounted.props, active: false });
  expect(signal.aborted).toBe(true);
  await mounted.rerender({ ...mounted.props, active: false, savedRevision: 1 });
  await act(async () => { pending.resolve([attempt]); });
  expect(api.history).toHaveBeenCalledOnce();
  expect(api.lexicon).not.toHaveBeenCalled();
  expect(api.suggest).not.toHaveBeenCalled();
  await mounted.rerender({ ...mounted.props, active: true, savedRevision: 1 });
  expect(await screen.findByText("No retained voice attempts.")).toBeTruthy();
  expect(api.history).toHaveBeenCalledTimes(2);
  expect(api.lexicon).not.toHaveBeenCalled();
  expect(api.suggest).not.toHaveBeenCalled();
});

it("preserves a frozen approval through outer close and ignores hidden completion", async () => {
  const pending = deferred<DictationLexiconRule>();
  api.approve.mockReturnValueOnce(pending.promise);
  api.lexicon.mockResolvedValue([]);
  const mounted = setup();
  await disclosure("Approved vocabulary");
  await fillApproval();
  await fireEvent.click(screen.getByLabelText("I approve this language and phrase replacement"));
  await fireEvent.click(screen.getByRole("button", { name: "Approve rule" }));
  await mounted.rerender({ ...mounted.props, active: false, language: "sk" });
  await act(async () => { pending.resolve(rule); });
  expect(api.approve).toHaveBeenCalledOnce();
  expect(api.lexicon).toHaveBeenCalledOnce();
  await mounted.rerender({ ...mounted.props, active: true, language: "sk" });
  expect(await screen.findByText(/previous approval remains unconfirmed/)).toBeTruthy();
  expect((screen.getByLabelText("Rule language") as HTMLInputElement).value).toBe("en");
  expect((screen.getByLabelText("Heard phrase") as HTMLInputElement).value).toBe("light");
  expect((screen.getByLabelText("Replacement phrase") as HTMLInputElement).value).toBe("LychD");
  expect(screen.getByLabelText("Heard phrase").closest("fieldset")?.disabled).toBe(true);
  expect(api.approve).toHaveBeenCalledOnce();
  expect(api.lexicon).toHaveBeenCalledTimes(2);
});

it("freezes an unconfirmed approval and reconciles it by reading without reposting", async () => {
  api.lexicon.mockResolvedValueOnce([]).mockResolvedValueOnce([rule]);
  api.approve.mockRejectedValue(new Error("lost response"));
  setup();
  await disclosure("Approved vocabulary");
  await fillApproval();
  await fireEvent.click(screen.getByLabelText("I approve this language and phrase replacement"));
  await fireEvent.click(screen.getByRole("button", { name: "Approve rule" }));
  expect(screen.getByText(/submitted form is held unchanged/)).toBeTruthy();
  expect(screen.getByLabelText("Heard phrase").closest("fieldset")?.disabled).toBe(true);
  expect((screen.getByLabelText("Heard phrase") as HTMLInputElement).value).toBe("light");
  await fireEvent.click(screen.getByRole("button", { name: "Check saved approval" }));
  expect(await screen.findByText("Approval confirmed in retained vocabulary.")).toBeTruthy();
  expect(api.approve).toHaveBeenCalledOnce();
});

it("distinguishes failed vocabulary reads and removes rules only on explicit click", async () => {
  api.lexicon.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([rule]).mockResolvedValueOnce([]);
  setup();
  await disclosure("Approved vocabulary");
  expect(screen.queryByText("No approved vocabulary rules.")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry vocabulary" }));
  const remove = await screen.findByRole("button", { name: "Remove vocabulary rule light (en)" });
  expect(api.deleteRule).not.toHaveBeenCalled();
  await fireEvent.click(remove);
  expect(api.deleteRule).toHaveBeenCalledExactlyOnceWith("rule-one");
  expect(await screen.findByText("No approved vocabulary rules.")).toBeTruthy();
});

it("applies a visible suggestion only on click and reports callback refusal", async () => {
  const mounted = setup();
  mounted.applySuggestion.mockReturnValue(false);
  await disclosure("Vocabulary suggestion");
  expect(api.suggest).toHaveBeenCalledWith({ attempt_id: "attempt-one" }, expect.any(AbortSignal));
  expect(screen.getByRole("list", { name: "Applied vocabulary rules" }).textContent).toContain("light");
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Use suggestion" }));
  expect(mounted.applySuggestion).toHaveBeenCalledExactlyOnceWith("LychD");
  expect(screen.getByText(/Suggestion not applied/)).toBeTruthy();
});

it("refuses a suggestion after the draft changes while it is loading", async () => {
  const pending = deferred<DictationSuggestion>();
  api.suggest.mockReturnValueOnce(pending.promise);
  const mounted = setup();
  await disclosure("Vocabulary suggestion");
  await mounted.rerender({ ...mounted.props, finalText: "my manual edit" });
  expect(api.suggest).toHaveBeenCalledOnce();
  await act(async () => { pending.resolve(suggestion); });
  await fireEvent.click(screen.getByRole("button", { name: "Use suggestion" }));
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
  expect(screen.getByText(/Suggestion not applied/)).toBeTruthy();
});

it("drops an old attempt suggestion after replacement and aborts on unmount", async () => {
  const first = deferred<DictationSuggestion>();
  const second = deferred<DictationSuggestion>();
  api.suggest.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
  const mounted = setup();
  await disclosure("Vocabulary suggestion");
  await mounted.rerender({ ...mounted.props, attemptId: "attempt-two" });
  expect((api.suggest.mock.calls[0]?.[1] as AbortSignal).aborted).toBe(true);
  await act(async () => { first.resolve(suggestion); });
  expect(screen.queryByRole("button", { name: "Use suggestion" })).toBeNull();
  mounted.unmount();
  expect((api.suggest.mock.calls[1]?.[1] as AbortSignal).aborted).toBe(true);
  await act(async () => { second.resolve({ ...suggestion, attempt_id: "attempt-two" }); });
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
});

it("fences a pending read on document hiding without writing browser storage", async () => {
  const pending = deferred<DictationAttemptSummary[]>();
  api.history.mockReturnValueOnce(pending.promise);
  const storage = vi.spyOn(Storage.prototype, "setItem");
  setup();
  await disclosure("Voice history");
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  await fireEvent(document, new Event("visibilitychange"));
  expect((api.history.mock.calls[0]?.[0] as AbortSignal).aborted).toBe(true);
  await act(async () => { pending.resolve([attempt]); });
  expect(screen.queryByText("Original and final text")).toBeNull();
  expect(storage).not.toHaveBeenCalled();
});

it("inspects and deletes a successful attempt without a saved correction", async () => {
  api.history.mockResolvedValueOnce([{ ...attempt, has_correction: false }]).mockResolvedValueOnce([]);
  api.corrections.mockResolvedValue([]);
  const mounted = setup();
  await disclosure("Voice history");
  expect(screen.getByText("No saved correction.")).toBeTruthy();
  expect(screen.getByText(/Audio no longer available/)).toBeTruthy();
  expect(api.inspect).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Inspect retained attempt attempt-one" }));
  const original = await screen.findByLabelText("Original transcript for this attempt") as HTMLTextAreaElement;
  expect(original.readOnly).toBe(true);
  expect(original.value).toBe("light");
  expect(api.inspect).toHaveBeenCalledExactlyOnceWith("attempt-one", expect.any(AbortSignal));
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
  expect(api.approve).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Delete retained attempt attempt-one" }));
  expect(api.deleteAttempt).toHaveBeenCalledExactlyOnceWith("attempt-one");
  expect(await screen.findByText("No retained voice attempts.")).toBeTruthy();
});

it("checks an unknown outcome without retranscription and allows deleting its metadata", async () => {
  api.history.mockResolvedValueOnce([{ ...attempt, status: "unknown", has_correction: false }]).mockResolvedValueOnce([]);
  api.corrections.mockResolvedValue([]);
  api.inspect.mockResolvedValue({ ...outcome, status: "unknown", original_text: null, reason: "outcome_unknown" } satisfies DictationResult);
  const mounted = setup();
  await disclosure("Voice history");
  const check = screen.getByRole("button", { name: "Inspect retained attempt attempt-one" });
  expect(check.textContent).toBe("Check outcome");
  await fireEvent.click(check);
  expect(await screen.findByText("Outcome remains unknown. This check does not restart transcription.")).toBeTruthy();
  expect(screen.queryByLabelText("Original transcript for this attempt")).toBeNull();
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
  expect(api.approve).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByRole("button", { name: "Delete retained attempt attempt-one" }));
  expect(api.deleteAttempt).toHaveBeenCalledExactlyOnceWith("attempt-one");
  expect(await screen.findByText("No retained voice attempts.")).toBeTruthy();
});

it("keeps attempt deletion accessible when the independent corrections read fails", async () => {
  api.corrections.mockRejectedValue(new Error("private storage diagnostic"));
  api.history.mockResolvedValueOnce([attempt]).mockResolvedValueOnce([]);
  setup();
  await disclosure("Voice history");
  expect(screen.getByRole("alert").textContent).toContain("Saved corrections could not be loaded completely");
  expect(screen.getByText("Saved correction is not available in this history read.")).toBeTruthy();
  expect(screen.queryByText("private storage diagnostic")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Delete retained attempt attempt-one" }));
  expect(api.deleteAttempt).toHaveBeenCalledExactlyOnceWith("attempt-one");
});

it("reports an over-limit catalogue instead of silently hiding inaccessible attempts", async () => {
  api.history.mockResolvedValue(Array.from({ length: 1001 }, (_, index) => ({ ...attempt, attempt_id: `attempt-${index}` })));
  setup();
  await disclosure("Voice history");
  expect(screen.getByRole("alert").textContent).toContain("exceeded the supported 1,000-attempt limit");
  expect(screen.queryByRole("list", { name: "Retained voice attempts" })).toBeNull();
  expect(screen.getByRole("button", { name: "Retry history" })).toBeTruthy();
});

it("aborts a hidden inspection, drops its late transcript and requires another explicit read", async () => {
  const pending = deferred<DictationResult>();
  api.inspect.mockReturnValueOnce(pending.promise);
  const mounted = setup();
  await disclosure("Voice history");
  await fireEvent.click(screen.getByRole("button", { name: "Inspect retained attempt attempt-one" }));
  const signal = api.inspect.mock.calls[0]?.[1] as AbortSignal;
  await mounted.rerender({ ...mounted.props, active: false });
  expect(signal.aborted).toBe(true);
  await act(async () => { pending.resolve(outcome); });
  await mounted.rerender({ ...mounted.props, active: true });
  expect(screen.queryByLabelText("Original transcript for this attempt")).toBeNull();
  expect(api.inspect).toHaveBeenCalledOnce();
  expect(mounted.applySuggestion).not.toHaveBeenCalled();
});

it("distinguishes inspection failure and permits an explicit GET retry", async () => {
  api.inspect.mockRejectedValueOnce(new Error("private error")).mockResolvedValueOnce(outcome);
  setup();
  await disclosure("Voice history");
  const inspect = screen.getByRole("button", { name: "Inspect retained attempt attempt-one" });
  await fireEvent.click(inspect);
  expect(screen.getByRole("alert").textContent).toContain("Could not inspect this attempt");
  expect(screen.queryByLabelText("Original transcript for this attempt")).toBeNull();
  expect(api.inspect).toHaveBeenCalledOnce();
  await fireEvent.click(inspect);
  expect(await screen.findByLabelText("Original transcript for this attempt")).toBeTruthy();
  expect(api.inspect).toHaveBeenCalledTimes(2);
});
