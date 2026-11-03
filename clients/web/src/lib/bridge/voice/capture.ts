export const VOICE_SAMPLE_RATE = 16_000;
export const VOICE_LIMIT_MS = 30_000;
export const VOICE_MAX_FRAMES = 480_000;
export const VOICE_MAX_WAV_BYTES = 960_044;
export const VOICE_CHUNK_FRAMES = 2_048;

export type VoiceCaptureStatus =
  | "idle" | "requesting" | "recording" | "stopping" | "complete" | "cancelled" | "error";

export interface VoiceCaptureState {
  status: VoiceCaptureStatus;
  elapsedMs: number;
  limitMs: number;
  error?: string;
}

export interface VoiceRecording {
  blob: Blob;
  sampleRate: 16000;
  channels: 1;
  frames: number;
  durationMs: number;
}

/** Inject only browser mechanics; the format and resource limits are not configurable. */
export interface VoiceCapturePlatform {
  getUserMedia(): Promise<MediaStream>;
  createContext(): AudioContext;
  createWorklet(context: AudioContext): AudioWorkletNode;
  now(): number;
  setTimer(callback: () => void, delayMs: number): unknown;
  clearTimer(timer: unknown): void;
}

export interface VoiceCaptureOptions {
  platform?: VoiceCapturePlatform;
  /** Tests may override the default Vite-bundled module asset. */
  workletUrl?: string;
  onstate?: (state: Readonly<VoiceCaptureState>) => void;
  onlimit?: () => void;
}

/** Streaming area-average resampling: each destination sample integrates its source interval.
 * State spans chunks, so splitting an input does not change the encoded samples.
 * The incomplete final destination interval is dropped, never padded or extrapolated.
 */
export class CanonicalPcmCollector {
  readonly sampleRate: number;
  readonly maxSourceFrames: number;
  sourceFrames = 0;
  frames = 0;
  private readonly pcm = new Int16Array(VOICE_MAX_FRAMES);
  private weight = 0;
  private sum = 0;

  constructor(sampleRate: number) {
    if (!Number.isFinite(sampleRate) || sampleRate < 8_000 || sampleRate > 192_000) {
      throw new Error("Unsupported microphone sample rate.");
    }
    this.sampleRate = sampleRate;
    this.maxSourceFrames = Math.floor(sampleRate * VOICE_LIMIT_MS / 1000);
  }

  append(samples: Float32Array): void {
    if (samples.length < 1 || samples.length > VOICE_CHUNK_FRAMES ||
        this.sourceFrames + samples.length > this.maxSourceFrames) {
      throw new Error("Microphone frame limit exceeded.");
    }
    for (const sample of samples) {
      if (!Number.isFinite(sample)) throw new Error("Invalid microphone sample.");
    }
    for (const sample of samples) {
      let remaining = VOICE_SAMPLE_RATE;
      const value = Math.max(-1, Math.min(1, sample));
      while (remaining > 0) {
        const amount = Math.min(remaining, this.sampleRate - this.weight);
        this.sum += value * amount;
        this.weight += amount;
        remaining -= amount;
        if (this.weight >= this.sampleRate) {
          if (this.frames >= VOICE_MAX_FRAMES) throw new Error("Microphone frame limit exceeded.");
          const normalized = Math.max(-1, Math.min(1, this.sum / this.sampleRate));
          this.pcm[this.frames++] = Math.round(normalized * (normalized < 0 ? 32768 : 32767));
          this.sum = 0;
          this.weight = 0;
        }
      }
    }
    this.sourceFrames += samples.length;
  }

  encode(): ArrayBuffer {
    return encodePcmWav(this.pcm.subarray(0, this.frames));
  }

  clear(): void {
    this.pcm.fill(0);
    this.sourceFrames = this.frames = this.weight = this.sum = 0;
  }
}

/** Canonical RIFF/WAVE: PCM format 1, mono, 16 kHz, signed 16-bit little endian. */
export function encodePcmWav(samples: Int16Array): ArrayBuffer {
  if (samples.length < 1 || samples.length > VOICE_MAX_FRAMES) {
    throw new Error("No complete microphone audio, or audio exceeds the capture limit.");
  }
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const tag = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  tag(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true);
  tag(8, "WAVE"); tag(12, "fmt "); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, VOICE_SAMPLE_RATE, true); view.setUint32(28, VOICE_SAMPLE_RATE * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  tag(36, "data"); view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) view.setInt16(44 + i * 2, samples[i]!, true);
  return buffer;
}

function browserPlatform(): VoiceCapturePlatform {
  return {
    getUserMedia: () => {
      if (!globalThis.navigator?.mediaDevices?.getUserMedia) {
        return Promise.reject(new Error("Microphone capture requires a supported secure browser."));
      }
      return navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    },
    createContext: () => new AudioContext(),
    createWorklet: (context) => new AudioWorkletNode(context, "lychd-pcm-recorder", {
      numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1],
      channelCountMode: "max", channelInterpretation: "discrete"
    }),
    now: () => performance.now(),
    setTimer: (callback, delay) => globalThis.setTimeout(callback, delay),
    clearTimer: (timer) => globalThis.clearTimeout(timer as ReturnType<typeof setTimeout>)
  };
}

interface Attempt {
  result: Promise<VoiceRecording | null>;
  resolve: (recording: VoiceRecording | null) => void;
  settled: boolean;
  stopping: boolean;
  startedAt?: number;
  stream?: MediaStream;
  context?: AudioContext;
  source?: MediaStreamAudioSourceNode;
  node?: AudioWorkletNode;
  collector?: CanonicalPcmCollector;
  timer?: unknown;
  limitTimer?: unknown;
  flushTimer?: unknown;
  trackHandlers: Array<() => void>;
}

/** No speech service, persistence, playback, upload, or object URL is created here.
 * start() settles once: a complete WAV, or null after cancellation/failure.
 * Always call dispose() when the owning view is destroyed or loses its capture authority.
 */
export function createVoiceCapture(options: VoiceCaptureOptions = {}) {
  const platform = options.platform ?? browserPlatform();
  let current: Attempt | undefined;
  let disposed = false;
  let state: VoiceCaptureState = { status: "idle", elapsedMs: 0, limitMs: VOICE_LIMIT_MS };
  const publish = (status: VoiceCaptureStatus, elapsedMs = state.elapsedMs, error?: string) => {
    state = { status, elapsedMs, limitMs: VOICE_LIMIT_MS, ...(error ? { error } : {}) };
    // UI observer failures must never strand a microphone or interrupt cleanup.
    try { options.onstate?.({ ...state }); } catch { /* observer owns its error */ }
  };
  const active = (a: Attempt) => current === a && !a.settled;
  const stopTracks = (a: Attempt) => {
    for (const remove of a.trackHandlers.splice(0)) remove();
    for (const track of a.stream?.getTracks() ?? []) {
      try { track.stop(); } catch { /* continue releasing remaining tracks */ }
    }
    a.stream = undefined;
    try { a.source?.disconnect(); } catch { /* disconnected already */ }
    a.source = undefined;
  };
  const release = (a: Attempt) => {
    for (const timer of [a.timer, a.limitTimer, a.flushTimer]) {
      if (timer !== undefined) platform.clearTimer(timer);
    }
    stopTracks(a);
    if (a.node) {
      a.node.port.onmessage = null;
      a.node.port.onmessageerror = null;
      a.node.onprocessorerror = null;
      try { a.node.port.postMessage({ type: "cancel" }); } catch { /* port failed */ }
      try { a.node.port.close(); } catch { /* port failed */ }
      try { a.node.disconnect(); } catch { /* disconnected already */ }
      a.node = undefined;
    }
    if (a.context) {
      const context = a.context;
      a.context = undefined;
      try { void context.close().catch(() => {}); } catch { /* already closed */ }
    }
    a.collector?.clear();
    a.collector = undefined;
  };
  const settle = (a: Attempt, status: VoiceCaptureStatus, result: VoiceRecording | null, error?: string) => {
    if (!active(a)) return;
    a.settled = true;
    release(a);
    publish(status, result?.durationMs ?? state.elapsedMs, error);
    a.resolve(result);
  };
  const fail = (a: Attempt, message: string) => settle(a, "error", null, message);
  const limit = (a: Attempt) => {
    if (!active(a) || a.stopping) return;
    try { options.onlimit?.(); } catch { /* observer owns its error */ }
    if (active(a)) void stop();
  };
  const elapsed = (a: Attempt) => Math.min(VOICE_LIMIT_MS,
    Math.max(0, platform.now() - (a.startedAt ?? platform.now())));
  const tick = (a: Attempt) => {
    if (!active(a) || a.stopping) return;
    publish("recording", elapsed(a));
    if (active(a) && !a.stopping) a.timer = platform.setTimer(() => tick(a), 100);
  };
  const receive = (a: Attempt, data: unknown) => {
    if (!active(a)) return;
    if (typeof data !== "object" || data === null || !a.collector) {
      fail(a, "Invalid microphone recorder message."); return;
    }
    const message = data as Record<string, unknown>;
    if (message.type === "chunk" && message.samples instanceof Float32Array &&
        message.offset === a.collector.sourceFrames) {
      try { a.collector.append(message.samples); }
      catch { fail(a, "Invalid microphone audio or capture limit exceeded."); }
      return;
    }
    if (message.type === "stopped" && message.totalFrames === a.collector.sourceFrames &&
        (message.reason === "stop" || message.reason === "limit")) {
      if (message.reason === "stop" && !a.stopping) {
        fail(a, "Unexpected microphone stop."); return;
      }
      if (message.reason === "limit" && a.collector.sourceFrames !== a.collector.maxSourceFrames) {
        fail(a, "Invalid microphone limit message."); return;
      }
      if (message.reason === "limit" && !a.stopping) {
        try { options.onlimit?.(); } catch { /* observer owns its error */ }
      }
      try {
        const frames = a.collector.frames;
        const blob = new Blob([a.collector.encode()], { type: "audio/wav" });
        settle(a, "complete", { blob, frames, durationMs: frames / VOICE_SAMPLE_RATE * 1000,
          sampleRate: VOICE_SAMPLE_RATE, channels: 1 });
      } catch { fail(a, "No complete microphone audio was captured."); }
      return;
    }
    fail(a, "Invalid microphone recorder message.");
  };
  const acquire = async (a: Attempt) => {
    try {
      if (!active(a)) return;
      const stream = await platform.getUserMedia();
      if (!active(a)) {
        for (const track of stream.getTracks()) track.stop();
        return;
      }
      a.stream = stream;
      if (stream.getAudioTracks().length === 0) throw new Error("No microphone track.");
      for (const track of stream.getTracks()) {
        if (track.readyState === "ended") throw new Error("Microphone track already ended.");
        const ended = () => fail(a, "Microphone disconnected before capture completed.");
        track.addEventListener("ended", ended);
        a.trackHandlers.push(() => track.removeEventListener("ended", ended));
      }
      a.context = platform.createContext();
      a.collector = new CanonicalPcmCollector(a.context.sampleRate);
      // Start the bound while loading the module too: a hung setup cannot retain the mic.
      a.limitTimer = platform.setTimer(() => {
        if (a.startedAt === undefined) fail(a, "Microphone setup timed out.");
        else limit(a);
      }, VOICE_LIMIT_MS);
      await a.context.audioWorklet.addModule(options.workletUrl ?? new URL("./pcm-recorder.js?no-inline", import.meta.url).href);
      if (!active(a)) return;
      a.node = platform.createWorklet(a.context);
      a.node.port.onmessage = (event: MessageEvent<unknown>) => receive(a, event.data);
      a.node.port.onmessageerror = () => fail(a, "Microphone recorder message failed.");
      a.node.onprocessorerror = () => fail(a, "Microphone recorder failed.");
      a.source = a.context.createMediaStreamSource(stream);
      // The processor writes only zeroes to this output; microphone audio is never played.
      a.node.connect(a.context.destination);
      await a.context.resume();
      if (!active(a)) return;
      platform.clearTimer(a.limitTimer);
      a.startedAt = platform.now();
      a.limitTimer = platform.setTimer(() => limit(a), VOICE_LIMIT_MS);
      a.source.connect(a.node);
      publish("recording", 0);
      tick(a);
    } catch {
      fail(a, "Microphone access or recorder setup failed. Check browser permission and device availability.");
    }
  };
  const start = (): Promise<VoiceRecording | null> => {
    if (disposed) return Promise.resolve(null);
    if (current && !current.settled) return current.result;
    let resolve!: Attempt["resolve"];
    const result = new Promise<VoiceRecording | null>((done) => { resolve = done; });
    const a: Attempt = { result, resolve, settled: false, stopping: false, trackHandlers: [] };
    current = a;
    publish("requesting", 0);
    void acquire(a);
    return result;
  };
  function stop(): Promise<VoiceRecording | null> {
    const a = current;
    if (!a) return Promise.resolve(null);
    if (!active(a) || a.stopping) return a.result;
    if (a.startedAt === undefined || !a.node) {
      settle(a, "cancelled", null);
      return a.result;
    }
    a.stopping = true;
    publish("stopping", elapsed(a));
    if (!active(a)) return a.result;
    stopTracks(a);
    a.flushTimer = platform.setTimer(() => fail(a, "Microphone recorder did not finish."), 1000);
    try { a.node.port.postMessage({ type: "stop" }); }
    catch { fail(a, "Microphone recorder did not finish."); }
    return a.result;
  }
  const cancel = () => {
    if (current && active(current)) settle(current, "cancelled", null);
  };
  return {
    start, stop, cancel,
    dispose: () => { disposed = true; cancel(); current = undefined; },
    get state(): Readonly<VoiceCaptureState> { return { ...state }; }
  };
}
