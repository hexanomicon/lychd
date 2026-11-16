import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, readCreationFeedback } from "$lib/api/client";
import CreationFeedback from "./CreationFeedback.svelte";
import {
  explicitlyNotAssessed, held, ids, newerReport, retainedReason, retainedReport,
  reviewRequired, unassessed, type FeedbackView
} from "./CreationFeedback.fixtures";

const deniedCalls = vi.hoisted(() => [] as string[]);
vi.mock("$lib/api/client", async (original) => {
  const actual = await original<typeof import("$lib/api/client")>();
  const denied = Object.fromEntries(Object.entries(actual)
    .filter(([name, value]) => name !== "ApiError" && typeof value === "function")
    .map(([name]) => [name, vi.fn(() => {
      deniedCalls.push(name);
      return Promise.reject(new Error("Only the feedback read is admitted by this component oracle."));
    })]));
  return { ...actual, ...denied, readCreationFeedback: vi.fn() };
});

const read = vi.mocked(readCreationFeedback);
const fetchGuard = vi.fn(() => Promise.reject(new Error("Direct network calls are outside this component contract.")));
function region() { return screen.getByRole("region", { name: "External feedback" }); }
function control(): HTMLButtonElement {
  const button = within(region()).getByRole("button", { name: /^(load|reload|retry) feedback$/i });
  expect(button).toBeInstanceOf(HTMLButtonElement);
  expect(button.tabIndex).toBeGreaterThanOrEqual(0);
  return button as HTMLButtonElement;
}
function value(label: string): string {
  const term = within(region()).getByText(label, { selector: "dt" });
  expect(term.nextElementSibling?.tagName).toBe("DD");
  return term.nextElementSibling?.textContent?.trim() ?? "";
}
async function load() { await fireEvent.click(control()); }
function signalAt(index = 0): AbortSignal {
  const signal = read.mock.calls[index]?.[1];
  expect(signal).toBeInstanceOf(AbortSignal);
  return signal as AbortSignal;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => { resolve = accept; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks(); read.mockReset(); deniedCalls.length = 0;
  read.mockResolvedValue(held()); vi.stubGlobal("fetch", fetchGuard);
});
afterEach(() => {
  cleanup();
  expect(deniedCalls, "The disclosure may only call readCreationFeedback").toEqual([]);
  expect(fetchGuard, "The API helper owns transport").not.toHaveBeenCalled();
  vi.unstubAllGlobals();
});

describe("explicit protected Creation feedback disclosure", () => {
  it("starts not loaded, exposes a focusable native control, and bounds a pending read to one request", async () => {
    const pending = deferred<FeedbackView>(); read.mockReturnValueOnce(pending.promise);
    render(CreationFeedback, { caseId: ids.a });
    expect(region().textContent).toMatch(/not loaded/i);
    expect(read).not.toHaveBeenCalled();
    const button = control(); button.focus(); expect(document.activeElement).toBe(button);
    await act(() => { button.click(); button.click(); });
    expect(read).toHaveBeenCalledOnce(); expect(read.mock.calls[0]?.[0]).toBe(ids.a);
    expect(button.disabled).toBe(true); expect(signalAt().aborted).toBe(false);
    expect(Boolean(button.closest('[aria-busy="true"]')) || /loading|reading/i.test(region().textContent ?? "")).toBe(true);
    await act(() => pending.resolve(held()));
    expect(control().disabled).toBe(false);
  });

  it("shows three separate judgments, the current report and owner reason, and literal unassessed coverage", async () => {
    render(CreationFeedback, { caseId: ids.a }); await load();
    await screen.findByText(retainedReport);
    expect(value("Native verdict")).toBe("accepted");
    expect(value("External assessment")).toBe("partial");
    expect(value("Owner disposition")).toBe("hold");
    expect(value("Feedback status")).toBe("hold");
    expect(within(region()).getByText(retainedReason)).toBeTruthy();
    expect(region().textContent).toMatch(/answer\s*[:·–-]?\s*not[ _]assessed/i);
    expect(region().textContent).not.toMatch(/answer\s*[:·–-]?\s*(passed|verified|accepted)/i);
    expect(region().textContent).toMatch(/native.*(not|does not).*owner|separate judgments/i);
    expect(read).toHaveBeenCalledOnce();
  });

  it("reloads explicitly and leaves an earlier hold historical after a newer external rejection", async () => {
    read.mockResolvedValueOnce(held()).mockResolvedValueOnce(reviewRequired());
    render(CreationFeedback, { caseId: ids.a }); await load(); await screen.findByText(retainedReport);
    expect(read).toHaveBeenCalledOnce();
    expect(control().textContent).toMatch(/^reload feedback$/i); await load();
    await screen.findByText(newerReport);
    expect(value("Native verdict")).toBe("accepted");
    expect(value("External assessment")).toBe("rejected");
    expect(value("Feedback status")).toMatch(/^review[ _]required$/);
    expect(value("Owner disposition")).toBe("No current owner decision");
    expect(read.mock.calls.map(([id]) => id)).toEqual([ids.a, ids.a]);
  });

  it("separates a successful empty unassessed view from a reviewer disposition of not_assessed", async () => {
    read.mockResolvedValueOnce(unassessed()).mockResolvedValueOnce(explicitlyNotAssessed());
    render(CreationFeedback, { caseId: ids.a }); await load();
    await screen.findByText("No external assessment");
    expect(value("Feedback status")).toBe("unassessed");
    expect(value("External assessment")).toBe("No external assessment");
    expect(value("Owner disposition")).toBe("No current owner decision");
    expect(region().textContent).not.toMatch(/refused|unavailable/i);
    await load(); await screen.findByText("Reviewer explicitly did not assess semantics.");
    expect(value("External assessment")).toMatch(/^not[ _]assessed$/);
    expect(value("Feedback status")).toMatch(/^review[ _]required$/);
    expect(value("Owner disposition")).toBe("No current owner decision");
  });

  it.each([401, 403])("clears protected feedback on a %i refusal and never displays raw server detail", async (status) => {
    read.mockResolvedValueOnce(held()).mockRejectedValueOnce(new ApiError("PRIVATE_REFUSAL_DETAIL", status));
    render(CreationFeedback, { caseId: ids.a }); await load(); await screen.findByText(retainedReport);
    await load(); await screen.findByText(/refused/i);
    expect(region().textContent).toMatch(/No protected feedback is displayed/i);
    expect(region().textContent).not.toContain(retainedReport);
    expect(region().textContent).not.toContain(retainedReason);
    expect(region().textContent).not.toContain("PRIVATE_REFUSAL_DETAIL");
    expect(control().disabled).toBe(false);
  });

  it.each([404, 503, undefined])("labels an unavailable read (%s) without claiming a successful empty result", async (status) => {
    read.mockRejectedValue(new ApiError("PRIVATE_UNAVAILABLE_DETAIL", status));
    render(CreationFeedback, { caseId: ids.a }); await load();
    await screen.findByText(/unavailable/i);
    expect(region().textContent).not.toContain("PRIVATE_UNAVAILABLE_DETAIL");
    expect(region().textContent).not.toContain("No external assessment");
    expect(region().textContent).not.toMatch(/refused/i);
    expect(control().disabled).toBe(false);
  });

  it("aborts a selected-case read, performs no automatic B read, and fences late A after B has loaded", async () => {
    const old = deferred<FeedbackView>();
    read.mockReturnValueOnce(old.promise).mockResolvedValueOnce({ ...held(ids.b), assessments: [{
      ...held(ids.b).assessments[0]!, body: { ...held(ids.b).assessments[0]!.body, report: "Protected report for B" }
    }] });
    const view = render(CreationFeedback, { caseId: ids.a }); await load();
    const oldSignal = signalAt();
    await view.rerender({ caseId: ids.b });
    expect(oldSignal.aborted).toBe(true); expect(read).toHaveBeenCalledOnce();
    expect(region().textContent).toMatch(/not loaded/i);
    await load(); await screen.findByText("Protected report for B");
    await act(() => old.resolve(held()));
    expect(region().textContent).toContain("Protected report for B");
    expect(region().textContent).not.toContain(retainedReport);
    await view.rerender({ caseId: ids.a });
    expect(region().textContent).toMatch(/not loaded/i);
    expect(region().textContent).not.toContain("Protected report for B");
    expect(read.mock.calls.map(([id]) => id)).toEqual([ids.a, ids.b]);
  });

  it("aborts on destruction and cannot repopulate a remounted not-loaded disclosure", async () => {
    const old = deferred<FeedbackView>(); read.mockReturnValueOnce(old.promise);
    const view = render(CreationFeedback, { caseId: ids.a }); await load();
    const pendingSignal = signalAt(); view.unmount(); expect(pendingSignal.aborted).toBe(true);
    await act(() => old.resolve(held()));
    render(CreationFeedback, { caseId: ids.a });
    expect(region().textContent).toMatch(/not loaded/i);
    expect(region().textContent).not.toContain(retainedReport); expect(read).toHaveBeenCalledOnce();
  });

  it("keeps a valid other-case response outside the selected case disclosure", async () => {
    read.mockResolvedValue(held(ids.b));
    render(CreationFeedback, { caseId: ids.a }); await load();
    await act(() => Promise.resolve());
    expect(region().textContent).not.toContain(retainedReport);
    expect(region().textContent).not.toContain(retainedReason);
    expect(control().disabled).toBe(false);
  });

  it("renders server-valid hostile report and reason strings as escaped text", async () => {
    const view = held(); const report = '<img src=x onerror="window.stolen=true">';
    const reason = '<script>window.stolen=true</script>';
    view.assessments[0]!.body.report = report; view.decisions[0]!.body.reason = reason;
    read.mockResolvedValue(view); render(CreationFeedback, { caseId: ids.a }); await load();
    expect(await screen.findByText(report)).toBeTruthy(); expect(within(region()).getByText(reason)).toBeTruthy();
    expect(region().querySelector("img, script, iframe")).toBeNull();
  });

  it("omits unsafe dictionary fields and unknown enum strings without coercing objects or leaking raw records", async () => {
    const view = held();
    view.native_verdict = { disposition: { private: "PRIVATE_NESTED_NATIVE" } };
    view.assessments[0]!.body = {
      disposition: "INVENTED_EXTERNAL_DISPOSITION", report: { private: "PRIVATE_NESTED_REPORT" },
      reviewer_label: ["PRIVATE_NESTED_REVIEWER"], unexpected: "PRIVATE_RAW_ASSESSMENT"
    };
    view.decisions[0]!.body = { action: "APPROVE_WITHOUT_AUTHORITY", reason: ["PRIVATE_NESTED_REASON"],
      unexpected: "PRIVATE_RAW_DECISION" };
    view.assessments[0]!.attribution = { private: "PRIVATE_RAW_ATTRIBUTION" };
    read.mockResolvedValue(view); render(CreationFeedback, { caseId: ids.a }); await load();
    await act(() => Promise.resolve());
    expect(region().textContent).not.toMatch(/PRIVATE_|INVENTED_EXTERNAL_DISPOSITION|APPROVE_WITHOUT_AUTHORITY|\[object Object\]/);
    expect(control().disabled).toBe(false);
  });
});
