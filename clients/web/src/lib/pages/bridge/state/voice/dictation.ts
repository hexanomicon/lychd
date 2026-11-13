import type { CommandTarget } from "../work-commands";
import type { DictationResult } from "$lib/api/models";

type TranscriptProjection = Pick<DictationResult, "attempt_id" | "status"> &
  Partial<Pick<DictationResult, "original_text" | "reason">>;

export type DraftEpoch = string | number | symbol;
export interface DictationDraft {
  readonly sessionId: string;
  readonly draftText: string;
  /** Must advance on every edit, including edit-away-and-back. */
  readonly draftRevision: DraftEpoch;
  readonly mode: "chat" | "work";
  /** Must advance on navigation/replacement, even when returning to the same identity. */
  readonly contextEpoch: DraftEpoch;
  readonly targetEpoch: DraftEpoch;
  readonly composing: boolean;
  /** Includes unresolved/uncertain prior Bridge sends, not only active requests. */
  readonly busy: boolean;
}
export interface DictationCapture {
  readonly attemptId: string;
  readonly target: CommandTarget | null;
  readonly draft: DictationDraft;
}
export interface DictationView {
  readonly phase: "idle" | "capturing" | "review" | "countdown" | "submitted" | "cancelled";
  readonly originalText: string;
  readonly finalText: string;
  readonly reason: string;
  readonly deadline: number | null;
  readonly autosend: boolean;
  readonly adopted: boolean;
}
export interface DictationClock {
  now(): number;
  setTimeout(callback: () => void, delay: number): unknown;
  clearTimeout(handle: unknown): void;
}
export interface DictationOptions {
  read(): DictationDraft;
  /** Synchronous compare-and-set: independently check ALL expected guards before writing. */
  adopt(expected: DictationDraft, nextText: string): DictationDraft | null;
  /** Existing Bridge send or registry.execute only; never Canvas Apply or a retry loop. */
  submit(draft: DictationDraft, intent: {
    attemptId: string; source: "manual" | "auto"; target: CommandTarget | null;
  }): void | Promise<unknown>;
  isTargetCurrent?(target: CommandTarget): boolean;
  onChange?(view: DictationView): void;
  clock?: DictationClock;
}

const browserClock: DictationClock = {
  now: () => Date.now(),
  setTimeout: (callback, delay) => globalThis.setTimeout(callback, delay),
  clearTimeout: (handle) => globalThis.clearTimeout(handle as ReturnType<typeof setTimeout>)
};

function sameContext(a: DictationDraft, b: DictationDraft): boolean {
  return a.sessionId === b.sessionId && a.mode === b.mode &&
    a.contextEpoch === b.contextEpoch && a.targetEpoch === b.targetEpoch;
}
function sameDraft(a: DictationDraft, b: DictationDraft): boolean {
  return sameContext(a, b) && a.draftRevision === b.draftRevision && a.draftText === b.draftText;
}
function append(draft: string, transcript: string): string {
  return draft + (draft && !/\s$/.test(draft) ? " " : "") + transcript;
}

/** Ephemeral UI authority only. No transport, retry, storage or instrument mutation. */
export function createDictationCoordinator(options: DictationOptions) {
  const clock = options.clock ?? browserClock;
  let alive = true;
  let active: DictationCapture | null = null;
  let expected: DictationDraft | null = null;
  let received = false;
  let consumed = false;
  let suppressed = true;
  let adopting = false;
  let timer: unknown;
  let timerGeneration = 0;
  let view: DictationView = Object.freeze({
    phase: "idle", originalText: "", finalText: "", reason: "", deadline: null,
    autosend: false, adopted: false
  });

  function publish(patch: Partial<DictationView>) {
    view = Object.freeze({ ...view, ...patch });
    if (alive) options.onChange?.(view);
  }
  function stopTimer() {
    ++timerGeneration;
    if (timer !== undefined) clock.clearTimeout(timer);
    timer = undefined;
  }
  function suppress(reason: string) {
    suppressed = true;
    stopTimer();
    publish({ deadline: null, reason, ...(view.phase === "countdown" ? { phase: "review" } : {}) });
  }
  function targetCurrent(token: DictationCapture): boolean {
    return token.draft.mode === "chat" ||
      (token.target !== null && options.isTargetCurrent?.(token.target) === true);
  }
  function usable(token: DictationCapture, snapshot: DictationDraft): boolean {
    return alive && active === token && !consumed && !!snapshot.sessionId.trim() && !snapshot.busy && !snapshot.composing &&
      sameContext(token.draft, snapshot) && targetCurrent(token);
  }
  function send(source: "manual" | "auto"): boolean {
    const token = active;
    const current = options.read();
    if (!token || !expected || !view.adopted || !usable(token, current) ||
        (source === "auto" && !sameDraft(expected, current)) || !current.draftText.trim() ||
        (source === "auto" && (!view.autosend || suppressed))) {
      if (alive) suppress("Send cancelled: the draft or context is no longer ready.");
      return false;
    }
    // Claim before notification/callback: reentrant clicks and queued timers cannot send again.
    consumed = true;
    stopTimer();
    publish({ phase: "submitted", deadline: null, reason: "" });
    if (!alive || active !== token) return false;
    try {
      Promise.resolve(options.submit(current, {
        attemptId: token.attemptId, source, target: token.target
      })).catch(() => {
        if (alive && active === token) publish({ reason: "Send outcome requires review in Bridge. No automatic retry." });
      });
    } catch {
      if (alive && active === token) publish({ reason: "Send outcome requires review in Bridge. No automatic retry." });
    }
    return true;
  }
  function schedule() {
    const deadline = clock.now() + 2000;
    const generation = ++timerGeneration;
    const tick = () => {
      if (!alive || generation !== timerGeneration) return;
      const remaining = deadline - clock.now();
      if (remaining > 0) { timer = clock.setTimeout(tick, remaining); return; }
      send("auto");
    };
    timer = clock.setTimeout(tick, 2000);
    publish({ phase: "countdown", deadline, reason: "Sending in 2 seconds. Cancel to keep editing." });
  }
  function adopt(token: DictationCapture, base: DictationDraft): boolean {
    if (!usable(token, base) || !view.finalText.trim()) return false;
    const nextText = append(base.draftText, view.finalText);
    let result: DictationDraft | null = null;
    adopting = true;
    try { result = options.adopt(base, nextText); }
    catch { /* Keep the transcript reviewable; never retry an uncertain owner write. */ }
    finally { adopting = false; }
    const current = options.read();
    if (!result || !usable(token, current) || !sameContext(base, result) ||
        result.draftText !== nextText || result.draftRevision === base.draftRevision ||
        !sameDraft(result, current)) return false;
    expected = Object.freeze({ ...result });
    publish({ adopted: true, reason: "" });
    return true;
  }

  return {
    get view(): DictationView { return view; },
    beginCapture(attemptId: string, target: CommandTarget | null = null): DictationCapture {
      if (!alive) throw new Error("Dictation coordinator is destroyed");
      stopTimer();
      const draft = Object.freeze({ ...options.read() });
      const token = Object.freeze({ attemptId, target, draft });
      active = token; expected = draft; received = false; consumed = false;
      suppressed = !view.autosend || draft.busy || draft.composing;
      publish({ phase: "capturing", originalText: "", finalText: "", reason: "", deadline: null, adopted: false });
      return token;
    },
    /** Pass a generated API result directly; projection types derive from that contract. */
    receive(token: DictationCapture, result: TranscriptProjection): boolean {
      if (!alive || active !== token || received || result.attempt_id !== token.attemptId) return false;
      received = true;
      const text = result.status === "transcribed" ? result.original_text ?? "" : "";
      publish({ phase: "review", originalText: text, finalText: text,
        reason: result.status === "transcribed" ? "" : result.reason ?? result.status });
      if (!alive || active !== token) return true;
      if (!text.trim()) { suppress(result.status === "transcribed" ? "No speech was transcribed." : view.reason); return true; }
      const current = options.read();
      if (!sameDraft(token.draft, current) || !adopt(token, current)) {
        suppress("Draft or context changed. Transcript kept separately for review.");
        return true;
      }
      if (!suppressed && view.autosend && active === token && !consumed) schedule();
      return true;
    },
    /** Call synchronously on edits, IME start, busy changes and route/context changes. */
    notifyChanged() {
      if (!alive || !active || adopting || consumed) return;
      const current = options.read();
      if (!expected || !sameDraft(expected, current) || !usable(active, current)) {
        suppress("Automatic send cancelled by a draft or context change.");
      }
    },
    setAutosend(enabled: boolean) {
      if (!alive) return;
      publish({ autosend: enabled });
      if (!enabled) suppress("Automatic send is off.");
      // Enabling never arms an existing capture or restarts a cancelled countdown.
    },
    setFinalText(text: string) {
      if (!alive || !active || consumed) return false;
      if (view.adopted) {
        suppress("Edit adopted text in the Bridge draft; send it manually.");
        return false;
      }
      suppress("Transcript edited. Insert and send manually.");
      publish({ finalText: text });
      return true;
    },
    /** Explicit insertion may rebase onto a changed draft, but never a changed context. */
    insert(): boolean {
      if (!alive || !active || !received || consumed || view.adopted) return false;
      suppress("Inserted transcripts are sent manually.");
      return adopt(active, Object.freeze({ ...options.read() }));
    },
    sendManual(): boolean { return send("manual"); },
    cancelAutosend() { if (alive) suppress("Automatic send cancelled. Draft preserved."); },
    cancel() {
      if (!alive) return;
      active = null; expected = null; consumed = true; suppressed = true;
      stopTimer(); publish({ phase: "cancelled", deadline: null, reason: "Dictation cancelled. Draft preserved." });
    },
    destroy() {
      alive = false; active = null; expected = null; consumed = true; stopTimer();
    }
  };
}

/** Fresh UUIDv7 only for dictation attempts. Existing Bridge request UUID4s are unchanged. */
export function newDictationAttemptId(
  now = Date.now(), random: (bytes: Uint8Array<ArrayBuffer>) => void = (bytes) => { globalThis.crypto.getRandomValues(bytes); }
): string {
  if (!Number.isSafeInteger(now) || now < 0 || now > 0xffffffffffff) throw new RangeError("Invalid UUIDv7 timestamp");
  const bytes = new Uint8Array(16);
  random(bytes);
  let timestamp = now;
  for (let i = 5; i >= 0; --i) { bytes[i] = timestamp % 256; timestamp = Math.floor(timestamp / 256); }
  bytes[6] = (bytes[6]! & 0x0f) | 0x70;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
