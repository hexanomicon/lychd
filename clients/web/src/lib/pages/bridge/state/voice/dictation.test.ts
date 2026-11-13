import { describe, expect, it, vi } from "vitest";
import { createDictationCoordinator, newDictationAttemptId, type DictationDraft } from "./dictation";
import type { CommandTarget } from "$lib/shell/state/work-commands";

function fixture() {
  let state: DictationDraft = {
    sessionId: "bridge-a", draftText: "Existing draft", draftRevision: 0,
    mode: "chat", contextEpoch: 0, targetEpoch: 0, composing: false, busy: false
  };
  let now = 1000;
  let nextTimer = 0;
  const timers = new Map<number, () => void>();
  // Retain cancelled callbacks to simulate a callback already queued by the event loop.
  const allTimers: Array<() => void> = [];
  const submit = vi.fn();
  const targetCurrent = vi.fn(() => true);
  const adopt = vi.fn((expected: DictationDraft, nextText: string) => {
    if (JSON.stringify(state) !== JSON.stringify(expected)) return null;
    state = { ...state, draftText: nextText, draftRevision: Number(state.draftRevision) + 1 };
    return state;
  });
  const coordinator = createDictationCoordinator({
    read: () => state, adopt, submit, isTargetCurrent: targetCurrent,
    clock: {
      now: () => now,
      setTimeout(callback) { const key = ++nextTimer; timers.set(key, callback); allTimers.push(callback); return key; },
      clearTimeout(handle) { timers.delete(handle as number); }
    }
  });
  return {
    coordinator, submit, adopt, targetCurrent, allTimers,
    get state() { return state; },
    change(patch: Partial<DictationDraft>, notify = true) {
      state = { ...state, ...patch };
      if (notify) coordinator.notifyChanged();
    },
    tick(ms = 2000) { now += ms; for (const callback of [...timers.values()]) callback(); },
    ready(auto = true, target: CommandTarget | null = null) {
      coordinator.setAutosend(auto);
      const token = coordinator.beginCapture("attempt-a", target);
      coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "new words" });
      return token;
    }
  };
}

describe("dictation adoption and cancellable autosend", () => {
  it("defaults off, appends without changing existing draft text, and preserves original text", () => {
    const f = fixture();
    const token = f.coordinator.beginCapture("attempt-a");
    f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "new words" });
    expect(f.state.draftText).toBe("Existing draft new words");
    expect(f.coordinator.view).toMatchObject({ autosend: false, originalText: "new words", adopted: true, deadline: null });
    f.tick();
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.coordinator.sendManual()).toBe(true);
    expect(f.submit).toHaveBeenCalledTimes(1);
  });

  it("provides a full visible two seconds and claims manual/timer delivery once", () => {
    const f = fixture(); f.ready();
    expect(f.coordinator.view).toMatchObject({ phase: "countdown", deadline: 3000 });
    f.tick(1999);
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.coordinator.sendManual()).toBe(true);
    f.tick(1); f.allTimers.forEach((callback) => callback());
    expect(f.coordinator.sendManual()).toBe(false);
    expect(f.submit).toHaveBeenCalledTimes(1);
    expect(f.submit.mock.calls[0]?.[1].source).toBe("manual");
  });

  it("also claims once when timer wins before the manual click", () => {
    const f = fixture(); f.ready(); f.tick();
    expect(f.coordinator.sendManual()).toBe(false);
    expect(f.submit).toHaveBeenCalledTimes(1);
    expect(f.submit.mock.calls[0]?.[1].source).toBe("auto");
  });

  it("allows explicit manual send of an edited adopted draft after cancelling autosend", () => {
    const f = fixture(); f.ready();
    f.change({ draftText: "Operator corrected this", draftRevision: 2 });
    expect(f.coordinator.sendManual()).toBe(true);
    f.tick();
    expect(f.submit).toHaveBeenCalledTimes(1);
    expect(f.submit.mock.calls[0]?.[0].draftText).toBe("Operator corrected this");
  });

  it("Cancel autosend keeps the draft available for a single manual send", () => {
    const f = fixture(); f.ready(); f.coordinator.cancelAutosend(); f.tick();
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.state.draftText).toBe("Existing draft new words");
    expect(f.coordinator.sendManual()).toBe(true);
    expect(f.coordinator.sendManual()).toBe(false);
  });

  it.each([
    { draftText: "edited", draftRevision: 2 },
    { sessionId: "bridge-b" }, { contextEpoch: 1 }, { targetEpoch: 1 },
    { composing: true }, { busy: true }, { mode: "work" as const }
  ])("cancels a countdown when guard changes: %j", (patch) => {
    const f = fixture(); f.ready(); f.change(patch); f.tick();
    f.allTimers.forEach((callback) => callback());
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.coordinator.view.deadline).toBeNull();
  });

  it("rechecks guards at timer execution even when a notification was missed", () => {
    const f = fixture(); f.ready(); f.change({ busy: true }, false); f.tick();
    expect(f.submit).not.toHaveBeenCalled();
  });

  it("edit-away-and-back and composition end cannot rearm a cancelled countdown", () => {
    const f = fixture(); f.ready();
    f.change({ composing: true }); f.change({ composing: false });
    f.change({ draftText: "changed", draftRevision: 2 });
    f.change({ draftText: "Existing draft new words", draftRevision: 3 });
    f.tick(); expect(f.submit).not.toHaveBeenCalled();
  });

  it("keeps stale output separate and allows explicit insertion onto the same context", () => {
    const f = fixture(); f.coordinator.setAutosend(true);
    const token = f.coordinator.beginCapture("attempt-a");
    f.change({ draftText: "Operator edit", draftRevision: 1 });
    f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "dictated" });
    expect(f.state.draftText).toBe("Operator edit");
    expect(f.coordinator.view).toMatchObject({ originalText: "dictated", finalText: "dictated", adopted: false });
    f.coordinator.setFinalText("corrected");
    expect(f.coordinator.insert()).toBe(true);
    expect(f.coordinator.insert()).toBe(false);
    expect(f.state.draftText).toBe("Operator edit corrected");
    expect(f.coordinator.view.originalText).toBe("dictated");
    f.tick(); expect(f.submit).not.toHaveBeenCalled();
    expect(f.coordinator.sendManual()).toBe(true);
  });

  it.each([{ sessionId: "bridge-b" }, { contextEpoch: 1 }, { targetEpoch: 1 }])
    ("does not insert a stale suggestion into a replacement context: %j", (patch) => {
      const f = fixture(); const token = f.coordinator.beginCapture("attempt-a");
      f.change(patch);
      f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "dictated" });
      expect(f.coordinator.insert()).toBe(false);
      expect(f.adopt).not.toHaveBeenCalled();
      expect(f.state.draftText).toBe("Existing draft");
    });

  it("requires owner compare-and-set approval", () => {
    const f = fixture(); f.adopt.mockReturnValue(null); f.ready(); f.tick();
    expect(f.coordinator.view.adopted).toBe(false);
    expect(f.coordinator.sendManual()).toBe(false);
    expect(f.submit).not.toHaveBeenCalled();
  });

  it.each(["unknown", "refused", "unavailable", "transcribed"] as const)("never adopts empty or %s responses", (status) => {
    const f = fixture(); f.coordinator.setAutosend(true);
    const token = f.coordinator.beginCapture("attempt-a");
    f.coordinator.receive(token, { attempt_id: "attempt-a", status, original_text: "" });
    f.tick(); expect(f.adopt).not.toHaveBeenCalled(); expect(f.submit).not.toHaveBeenCalled();
  });

  it("never rearms after toggling off/on, and enabling mid-capture does not authorize autosend", () => {
    const f = fixture(); f.ready(); f.coordinator.setAutosend(false); f.coordinator.setAutosend(true); f.tick();
    expect(f.submit).not.toHaveBeenCalled();
    const g = fixture(); const token = g.coordinator.beginCapture("attempt-a");
    g.coordinator.setAutosend(true);
    g.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "words" });
    g.tick(); expect(g.submit).not.toHaveBeenCalled();
  });

  it("busy or IME during capture suppresses autosend even after becoming ready", () => {
    for (const patch of [{ busy: true }, { composing: true }]) {
      const f = fixture(); f.coordinator.setAutosend(true); const token = f.coordinator.beginCapture("attempt-a");
      f.change(patch); f.change({ busy: false, composing: false });
      f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "words" });
      f.tick(); expect(f.submit).not.toHaveBeenCalled();
    }
  });

  it("new capture fences reversed responses and repeated delivery", () => {
    const f = fixture(); f.coordinator.setAutosend(true);
    const first = f.coordinator.beginCapture("attempt-a");
    const second = f.coordinator.beginCapture("attempt-b");
    expect(f.coordinator.receive(second, { attempt_id: "attempt-b", status: "transcribed", original_text: "second" })).toBe(true);
    expect(f.coordinator.receive(first, { attempt_id: "attempt-a", status: "transcribed", original_text: "first" })).toBe(false);
    expect(f.coordinator.receive(second, { attempt_id: "attempt-b", status: "transcribed", original_text: "duplicate" })).toBe(false);
    expect(f.state.draftText).toBe("Existing draft second");
    f.tick(); expect(f.submit).toHaveBeenCalledTimes(1);
  });

  it("starting another capture invalidates an already queued old autosend", () => {
    const f = fixture(); f.ready();
    const oldTimer = f.allTimers[0]!;
    f.coordinator.beginCapture("attempt-b");
    f.tick(); oldTimer();
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.state.draftText).toBe("Existing draft new words");
  });

  it("rejects a copied token and mismatched result ID without consuming the real result", () => {
    const f = fixture(); const token = f.coordinator.beginCapture("attempt-a");
    expect(f.coordinator.receive({ ...token }, { attempt_id: "attempt-a", status: "transcribed", original_text: "copied" })).toBe(false);
    expect(f.coordinator.receive(token, { attempt_id: "attempt-b", status: "transcribed", original_text: "foreign" })).toBe(false);
    expect(f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "right" })).toBe(true);
    expect(f.state.draftText).toBe("Existing draft right");
  });

  it.each(["cancel", "destroy"] as const)("%s fences pending responses and queued timers", (action) => {
    const f = fixture(); const token = f.ready(); f.coordinator[action]();
    f.tick(); f.allTimers.forEach((callback) => callback());
    expect(f.coordinator.receive(token, { attempt_id: "attempt-a", status: "transcribed", original_text: "late" })).toBe(false);
    expect(f.submit).not.toHaveBeenCalled();
    expect(f.state.draftText).toBe("Existing draft new words");
  });

  it("retains the exact work capture and never invokes a Canvas acceptance hook", () => {
    const f = fixture(); f.change({ mode: "work" });
    const target = Object.freeze({ instrument: "canvas", id: "board-a", label: "Canvas",
      mountGeneration: Symbol(), revisionKey: "1", commands: [] }) satisfies CommandTarget;
    f.ready(true, target); f.tick();
    expect(f.submit).toHaveBeenCalledTimes(1);
    expect(f.submit.mock.calls[0]?.[1].target).toBe(target);
    const g = fixture(); g.change({ mode: "work" }); g.ready(true, target);
    g.targetCurrent.mockReturnValue(false); g.tick(); expect(g.submit).not.toHaveBeenCalled();
  });

  it("does not retry a rejected submit", async () => {
    const f = fixture(); f.submit.mockRejectedValue(new Error("unknown")); f.ready(); f.tick();
    await Promise.resolve();
    expect(f.coordinator.view.reason).toContain("No automatic retry");
    f.tick(); expect(f.coordinator.sendManual()).toBe(false); expect(f.submit).toHaveBeenCalledTimes(1);
  });
});

describe("dictation UUIDv7", () => {
  it("encodes exact millisecond time with v7/variant bits and injected entropy", () => {
    const now = 1793700000123;
    const id = newDictationAttemptId(now, (bytes) => bytes.fill(0xff));
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7fff-bfff-ffffffffffff$/);
    expect(Number.parseInt(id.replaceAll("-", "").slice(0, 12), 16)).toBe(now);
  });
  it.each([-1, Number.NaN, 1.5, 0x1000000000000])("rejects invalid timestamp %s", (now) => {
    expect(() => newDictationAttemptId(now)).toThrow(RangeError);
  });
});
