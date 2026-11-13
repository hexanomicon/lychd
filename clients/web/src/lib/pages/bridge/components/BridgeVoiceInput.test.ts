import { act, cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { DictationDiscovery, DictationResult } from "$lib/api/models";
import { ApiError } from "$lib/api/client";
import type { DictationDraft } from "$lib/pages/bridge/state/voice/dictation";
import type { VoiceCaptureOptions, VoiceRecording } from "$lib/pages/bridge/state/voice/capture";
import BridgeVoiceInput from "./BridgeVoiceInput.svelte";

const api = vi.hoisted(() => ({ discovery: vi.fn(), recover: vi.fn(), transcribe: vi.fn(), correct: vi.fn(), capture: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  ApiError: class extends Error { constructor(message: string, readonly status?: number) { super(message); } },
  getDictationDiscovery: api.discovery, getDictationAttempt: api.recover,
  transcribeDictation: api.transcribe, recordDictationCorrection: api.correct
}));
vi.mock("$lib/pages/bridge/state/voice/capture", () => ({ createVoiceCapture: api.capture, VOICE_MAX_WAV_BYTES: 960044 }));

const discovery: DictationDiscovery = {
  status: "available", reason: null, profile_digest: `sha256:${"a".repeat(64)}`, languages: ["en", "sk"],
  max_audio_bytes: 1048576, max_audio_seconds: 30, sample_rate_hz: 16000, channels: 1,
  sample_width_bytes: 2, raw_audio_retention_seconds: 300
};
let resolveCapture: (result: VoiceRecording | null) => void;
let captureOptions: VoiceCaptureOptions;
let dispose: ReturnType<typeof vi.fn>;

function transcript(attemptId: string, text = "add a thought"): DictationResult {
  return { attempt_id: attemptId, status: "transcribed", original_text: text, language: "en",
    source_digest: `sha256:${"b".repeat(64)}`, profile_digest: `sha256:${"a".repeat(64)}`, reason: null };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.discovery.mockResolvedValue(discovery);
  api.transcribe.mockImplementation(async (body: { attempt_id: string }) => transcript(body.attempt_id));
  api.correct.mockResolvedValue({});
  dispose = vi.fn();
  api.capture.mockImplementation((options: VoiceCaptureOptions) => {
    captureOptions = options;
    return {
      start: () => {
        options.onstate?.({ status: "recording", elapsedMs: 0, limitMs: 30000 });
        return new Promise<VoiceRecording | null>((resolve) => { resolveCapture = resolve; });
      },
      stop: vi.fn(), dispose, cancel: vi.fn()
    };
  });
  // Asynchronous encoding seam, no microphone, audio processing or provider effect.
  vi.stubGlobal("FileReader", class {
    result: string | null = null;
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    readAsDataURL() { queueMicrotask(() => { this.result = "data:audio/wav;base64,UklGRg=="; this.onload?.(); }); }
    abort() {}
  });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

async function setup(initial: Partial<DictationDraft> = {}) {
  let current: DictationDraft = {
    sessionId: "session", draftText: "", draftRevision: 0, contextEpoch: 0, targetEpoch: 0,
    mode: "chat", busy: false, composing: false, ...initial
  };
  const submit = vi.fn();
  const adopt = vi.fn((expected: DictationDraft, text: string) => {
    if (expected.draftRevision !== current.draftRevision || expected.draftText !== current.draftText) return null;
    current = { ...current, draftText: text, draftRevision: Number(current.draftRevision) + 1 };
    return current;
  });
  const props = { snapshot: current, target: null, onadopt: adopt, onsubmit: submit, readSnapshot: () => current };
  const mounted = render(BridgeVoiceInput, { props });
  await act(() => Promise.resolve());
  return {
    mounted, submit, adopt, read: () => current,
    change: async (patch: Partial<DictationDraft>) => {
      current = { ...current, ...patch };
      mounted.component.notifyChanged(current);
      await mounted.rerender({ ...props, snapshot: current });
    }
  };
}

async function record() { await fireEvent.click(screen.getByRole("button", { name: "Record voice" })); }
async function complete() {
  await act(async () => {
    captureOptions.onstate?.({ status: "complete", elapsedMs: 10, limitMs: 30000 });
    resolveCapture({ blob: new Blob([new Uint8Array(48)], { type: "audio/wav" }), channels: 1, sampleRate: 16000, frames: 2, durationMs: .125 });
    await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  });
}

it("discovers availability without prompting for microphone permission", async () => {
  await setup();
  expect(api.discovery).toHaveBeenCalledOnce();
  expect(api.capture).not.toHaveBeenCalled();
  expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false);
  expect(screen.getByText(/recognition quality unverified/)).toBeTruthy();
  expect((screen.getByLabelText("Language") as HTMLSelectElement).options.length).toBe(2);
});

it("keeps the microphone disabled when unconfigured", async () => {
  api.discovery.mockResolvedValue({ ...discovery, status: "unavailable", reason: "unconfigured", profile_digest: null, languages: [] });
  await setup(); await record();
  expect(api.capture).not.toHaveBeenCalled();
  expect(screen.getByText("Voice unavailable: unconfigured.")).toBeTruthy();
});

it("reports permission/setup denial and leaves the typed draft intact", async () => {
  const fixture = await setup({ draftText: "Keep this" }); await record();
  await act(async () => {
    captureOptions.onstate?.({ status: "error", elapsedMs: 0, limitMs: 30000, error: "Microphone permission denied." });
    resolveCapture(null);
  });
  expect(screen.getByRole("alert").textContent).toContain("permission denied");
  expect(fixture.read().draftText).toBe("Keep this");
  expect(api.transcribe).not.toHaveBeenCalled();
});

it("drops late complete audio after cancellation", async () => {
  await setup(); await record();
  await fireEvent.click(screen.getByRole("button", { name: "Cancel recording" }));
  await complete();
  expect(dispose).toHaveBeenCalled();
  expect(api.transcribe).not.toHaveBeenCalled();
});

it("adopts into the existing draft, then sends the operator-edited text once", async () => {
  const fixture = await setup({ draftText: "Existing" });
  await record(); await complete();
  expect(fixture.read().draftText).toBe("Existing add a thought");
  expect(screen.getByText("Transcript added to draft. Review and send.").closest("details")).toBeNull();
  expect(fixture.submit).not.toHaveBeenCalled();
  await fixture.change({ draftText: "Existing corrected thought", draftRevision: 2 });
  expect(fixture.mounted.component.handleSend()).toBe(true);
  expect(fixture.mounted.component.handleSend()).toBe(true);
  expect(fixture.submit).toHaveBeenCalledOnce();
  expect(fixture.submit.mock.calls[0]?.[0].draftText).toBe("Existing corrected thought");
  await fixture.change({ draftText: "Next ordinary typed message", draftRevision: 3 });
  expect(fixture.mounted.component.handleSend()).toBe(false);
});

it("keeps a transcript separate after typing during capture and inserts only on request", async () => {
  const fixture = await setup(); await record();
  await fixture.change({ draftText: "Typed while recording", draftRevision: 1 });
  await complete();
  expect(fixture.read().draftText).toBe("Typed while recording");
  const suggestion = screen.getByLabelText("Transcript suggestion");
  await fireEvent.input(suggestion, { target: { value: "reviewed words" } });
  await fireEvent.click(screen.getByRole("button", { name: "Insert into draft" }));
  expect(fixture.read().draftText).toBe("Typed while recording reviewed words");
  expect(fixture.submit).not.toHaveBeenCalled();
});

it("never adopts or sends an unknown transcription", async () => {
  api.transcribe.mockImplementation(async (body: { attempt_id: string }) => ({
    ...transcript(body.attempt_id), status: "unknown", original_text: null, reason: "outcome_unknown"
  } satisfies DictationResult));
  const fixture = await setup(); await record(); await complete();
  expect(fixture.adopt).not.toHaveBeenCalled();
  expect(fixture.submit).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain("outcome unknown");
});

it("cancels visible autosend on transient IME and does not rearm", async () => {
  const fixture = await setup();
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  await fireEvent.click(screen.getByLabelText("Automatically send after 2 seconds"));
  await record(); await complete();
  expect(screen.getByRole("button", { name: "Cancel automatic send" })).toBeTruthy();
  await fixture.change({ composing: true });
  await fixture.change({ composing: false });
  await act(() => vi.advanceTimersByTime(2000));
  expect(fixture.submit).not.toHaveBeenCalled();
});

it("cancels autosend through the visible button while preserving manual Send", async () => {
  const fixture = await setup();
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  await fireEvent.click(screen.getByLabelText("Automatically send after 2 seconds"));
  await record(); await complete();
  await fireEvent.click(screen.getByRole("button", { name: "Cancel automatic send" }));
  await act(() => vi.advanceTimersByTime(2000));
  expect(fixture.submit).not.toHaveBeenCalled();
  expect(fixture.mounted.component.handleSend()).toBe(true);
  expect(fixture.submit).toHaveBeenCalledOnce();
});

it("aborts transcription on context change and ignores late results", async () => {
  let resolve!: (result: DictationResult) => void;
  api.transcribe.mockImplementation(() => new Promise<DictationResult>((done) => { resolve = done; }));
  const fixture = await setup(); await record(); await complete();
  const call = api.transcribe.mock.calls[0]!;
  await fixture.change({ sessionId: "other", contextEpoch: 1 });
  expect((call[1] as AbortSignal).aborted).toBe(true);
  await act(async () => { resolve(transcript(call[0].attempt_id)); });
  expect(fixture.adopt).not.toHaveBeenCalled();
});

it("saves corrections only after explicit opt-in and visibly reports storage failure", async () => {
  api.correct.mockRejectedValue(new Error("private storage unavailable"));
  const fixture = await setup(); await record(); await complete();
  expect(api.correct).not.toHaveBeenCalled();
  await fireEvent.click(screen.getByLabelText("Remember corrections when sending"));
  await fixture.change({ draftText: "  corrected words  ", draftRevision: 2 });
  await act(async () => { fixture.mounted.component.handleSend(); });
  expect(api.correct).toHaveBeenCalledWith({ attempt_id: api.transcribe.mock.calls[0]?.[0].attempt_id, final_text: "corrected words" });
  expect(screen.getByText(/storage could not be confirmed/)).toBeTruthy();
  expect(screen.getByText(/storage could not be confirmed/).closest("details")).toBeNull();
});

it("keeps native labeled controls focusable and does not intercept Escape or Tab", async () => {
  await setup();
  const microphone = screen.getByRole("button", { name: "Record voice" });
  microphone.focus();
  expect(document.activeElement).toBe(microphone);
  const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
  microphone.dispatchEvent(tab);
  expect(tab.defaultPrevented).toBe(false);
  const escape = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
  microphone.dispatchEvent(escape);
  expect(escape.defaultPrevented).toBe(false);
  expect(microphone.querySelector("svg")?.getAttribute("width")).toBe("18");
});

it("fences an old discovery reply after context replacement", async () => {
  let first!: (result: DictationDiscovery) => void;
  api.discovery.mockImplementationOnce(() => new Promise<DictationDiscovery>((resolve) => { first = resolve; }));
  const fixture = await setup();
  await fixture.change({ sessionId: "new-session", contextEpoch: 1 });
  await act(async () => { first({ ...discovery, status: "unavailable", reason: "unconfigured", languages: [] }); });
  expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false);
  expect(screen.queryByText("Voice unavailable: unconfigured.")).toBeNull();
});

it("disposes capture when unmounted and ignores audio that completes later", async () => {
  const fixture = await setup(); await record();
  fixture.mounted.unmount(); await complete();
  expect(dispose).toHaveBeenCalled();
  expect(api.transcribe).not.toHaveBeenCalled();
});

it("rechecks failed discovery without capturing or transcribing", async () => {
  api.discovery.mockRejectedValueOnce(new Error("unavailable"));
  await setup();
  await fireEvent.click(screen.getByRole("button", { name: "Check voice again" }));
  expect(api.discovery).toHaveBeenCalledTimes(2);
  expect((screen.getByRole("button", { name: "Record voice" }) as HTMLButtonElement).disabled).toBe(false);
  expect(api.capture).not.toHaveBeenCalled();
  expect(api.transcribe).not.toHaveBeenCalled();
});

function unknownTranscription() {
  api.transcribe.mockImplementation(async (body: { attempt_id: string }) => ({
    ...transcript(body.attempt_id), status: "unknown", original_text: null, reason: "outcome_unknown"
  } satisfies DictationResult));
}

it("recovers the exact unknown attempt with GET and sends only after manual review", async () => {
  unknownTranscription();
  api.recover.mockImplementation(async (id: string) => transcript(id, "recovered words"));
  const fixture = await setup(); await record(); await complete();
  const attempt = api.transcribe.mock.calls[0]![0].attempt_id;
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(api.recover).toHaveBeenCalledWith(attempt, expect.any(AbortSignal));
  expect(api.transcribe).toHaveBeenCalledOnce();
  expect(fixture.read().draftText).toBe("recovered words");
  expect(fixture.submit).not.toHaveBeenCalled();
  expect(fixture.mounted.component.handleSend()).toBe(true);
  expect(fixture.submit).toHaveBeenCalledOnce();
});

it("keeps a recovered transcript separate after the operator edits the draft", async () => {
  unknownTranscription();
  api.recover.mockImplementation(async (id: string) => transcript(id, "recovered words"));
  const fixture = await setup(); await record(); await complete();
  await fixture.change({ draftText: "my newer draft", draftRevision: 1 });
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(fixture.read().draftText).toBe("my newer draft");
  expect((screen.getByLabelText("Transcript suggestion") as HTMLTextAreaElement).value).toBe("recovered words");
  expect(api.transcribe).toHaveBeenCalledOnce();
});

it("keeps earlier-context recovery separate without acquiring its new draft", async () => {
  unknownTranscription();
  api.recover.mockImplementation(async (id: string) => transcript(id, "earlier words"));
  const fixture = await setup(); await record(); await complete();
  await fixture.change({ sessionId: "new-session", contextEpoch: 1, draftText: "new context" });
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(fixture.adopt).not.toHaveBeenCalled();
  expect(fixture.read().draftText).toBe("new context");
  expect((screen.getByLabelText("Recovered transcript from earlier context") as HTMLTextAreaElement).value).toBe("earlier words");
});

it("distinguishes missing retained attempts from an unknown transcription without guessing deletion", async () => {
  unknownTranscription();
  api.recover.mockRejectedValue(new ApiError("Unavailable", 404));
  const fixture = await setup(); await record(); await complete();
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(screen.getByText(/may have expired or been deleted/)).toBeTruthy();
  expect(fixture.adopt).not.toHaveBeenCalled();
  expect(api.transcribe).toHaveBeenCalledOnce();
});

it("reports an attempt that is still unknown and permits another GET only", async () => {
  unknownTranscription();
  api.recover.mockImplementation(async (id: string) => ({
    ...transcript(id), status: "unknown", original_text: null, reason: "outcome_unknown"
  } satisfies DictationResult));
  await setup(); await record(); await complete();
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(screen.getByText(/outcome is still unknown/)).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Check transcription outcome" }));
  expect(api.recover).toHaveBeenCalledTimes(2);
  expect(api.transcribe).toHaveBeenCalledOnce();
});
