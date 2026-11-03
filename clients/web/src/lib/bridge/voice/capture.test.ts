import { describe, expect, it, vi } from "vitest";
import {
  CanonicalPcmCollector, createVoiceCapture, encodePcmWav, VOICE_MAX_FRAMES,
  VOICE_MAX_WAV_BYTES, type VoiceCapturePlatform
} from "./capture";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

async function microtasks() {
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

function fixture(rate = 48_000) {
  const permission = deferred<MediaStream>();
  const module = deferred<void>();
  const resume = deferred<void>();
  const track = new EventTarget() as EventTarget & { stop: ReturnType<typeof vi.fn> };
  track.stop = vi.fn();
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] } as unknown as MediaStream;
  const source = { connect: vi.fn(), disconnect: vi.fn() };
  const port = {
    onmessage: null as ((event: MessageEvent<unknown>) => void) | null,
    onmessageerror: null as (() => void) | null,
    postMessage: vi.fn(), close: vi.fn()
  };
  const node = { port, connect: vi.fn(), disconnect: vi.fn(), onprocessorerror: null as (() => void) | null };
  const context = {
    sampleRate: rate, destination: {}, audioWorklet: { addModule: vi.fn(() => module.promise) },
    createMediaStreamSource: vi.fn(() => source), resume: vi.fn(() => resume.promise),
    close: vi.fn(() => Promise.resolve())
  };
  let now = 0;
  let timerId = 0;
  const timers = new Map<number, { callback: () => void; at: number }>();
  const platform: VoiceCapturePlatform = {
    getUserMedia: vi.fn(() => permission.promise),
    createContext: () => context as unknown as AudioContext,
    createWorklet: () => node as unknown as AudioWorkletNode,
    now: () => now,
    setTimer: (callback, delay) => { timers.set(++timerId, { callback, at: now + delay }); return timerId; },
    clearTimer: (id) => { timers.delete(id as number); }
  };
  const message = (data: unknown) => port.onmessage?.({ data } as MessageEvent<unknown>);
  const ready = async () => {
    permission.resolve(stream); module.resolve(); resume.resolve(); await microtasks();
  };
  const advance = (ms: number) => {
    const until = now + ms;
    for (;;) {
      const next = [...timers].filter(([, timer]) => timer.at <= until)
        .sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      now = next[1].at; timers.delete(next[0]); next[1].callback();
    }
    now = until;
  };
  return { platform, permission, module, resume, stream, track, source, node, context,
    timers, message, ready, advance };
}

describe("canonical microphone WAV", () => {
  it("writes exact signed little-endian PCM and canonical headers", () => {
    const bytes = encodePcmWav(new Int16Array([-32768, -1, 0, 32767]));
    const view = new DataView(bytes);
    expect(new TextDecoder().decode(bytes.slice(0, 4))).toBe("RIFF");
    expect(new TextDecoder().decode(bytes.slice(8, 16))).toBe("WAVEfmt ");
    expect(new TextDecoder().decode(bytes.slice(36, 40))).toBe("data");
    expect([view.getUint32(4, true), view.getUint32(16, true), view.getUint16(20, true),
      view.getUint16(22, true), view.getUint32(24, true), view.getUint32(28, true),
      view.getUint16(32, true), view.getUint16(34, true), view.getUint32(40, true)])
      .toEqual([44, 16, 1, 1, 16000, 32000, 2, 16, 8]);
    expect([...new Uint8Array(bytes.slice(44))]).toEqual([0, 128, 255, 255, 0, 0, 255, 127]);
  });

  it.each([8_000, 16_000, 44_100, 48_000, 96_000, 192_000])
    ("resamples actual %i Hz without changing duration or chunk-dependent output", (rate) => {
      const a = new CanonicalPcmCollector(rate);
      const b = new CanonicalPcmCollector(rate);
      const samples = Float32Array.from({ length: rate / 10 }, (_, index) => Math.sin(index / 31));
      for (let i = 0; i < samples.length; i += 2048) a.append(samples.subarray(i, i + 2048));
      for (let i = 0; i < samples.length; i += 73) b.append(samples.subarray(i, i + 73));
      expect(a.frames).toBe(1600);
      expect(a.encode()).toEqual(b.encode());
    });

  it("averages source intervals and clamps signed full scale", () => {
    const collector = new CanonicalPcmCollector(48_000);
    collector.append(new Float32Array([1, 0, -1, 2, 2, 2, -2, -2, -2]));
    const view = new DataView(collector.encode());
    expect([view.getInt16(44, true), view.getInt16(46, true), view.getInt16(48, true)])
      .toEqual([0, 32767, -32768]);
  });

  it("enforces exact 30-second / 960044-byte maximum and clears cancelled audio", () => {
    const collector = new CanonicalPcmCollector(16_000);
    for (let i = 0; i < VOICE_MAX_FRAMES; i += 2048) {
      collector.append(new Float32Array(Math.min(2048, VOICE_MAX_FRAMES - i)));
    }
    expect(collector.frames).toBe(VOICE_MAX_FRAMES);
    expect(collector.encode().byteLength).toBe(VOICE_MAX_WAV_BYTES);
    expect(() => collector.append(new Float32Array([0]))).toThrow();
    collector.clear();
    expect(collector.frames).toBe(0);
    expect(() => collector.encode()).toThrow();
  });

  it("rejects invalid rates, non-finite samples, oversize chunks, empty and oversize output", () => {
    for (const rate of [0, 7999, 192001, NaN, Infinity]) {
      expect(() => new CanonicalPcmCollector(rate)).toThrow();
    }
    const collector = new CanonicalPcmCollector(48_000);
    for (const samples of [new Float32Array(), new Float32Array(2049), new Float32Array([NaN]),
      new Float32Array([Infinity]), new Float32Array([-Infinity])]) {
      expect(() => collector.append(samples)).toThrow();
    }
    expect(collector.sourceFrames).toBe(0);
    expect(() => encodePcmWav(new Int16Array())).toThrow();
    expect(() => encodePcmWav(new Int16Array(VOICE_MAX_FRAMES + 1))).toThrow();
  });
});

describe("microphone ownership and races", () => {
  it("captures real platform input and waits for final worklet acknowledgement before resolving", async () => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); const completed = vi.fn(); void result.then(completed);
    await f.ready();
    expect(capture.state.status).toBe("recording");
    expect(f.context.audioWorklet.addModule).toHaveBeenCalledWith(expect.stringContaining("pcm-recorder.js"));
    expect(f.source.connect).toHaveBeenCalledWith(f.node);
    f.message({ type: "chunk", offset: 0, samples: new Float32Array([1, 1, 1]) });
    expect(capture.stop()).toBe(result);
    expect(f.track.stop).toHaveBeenCalledTimes(1);
    expect(f.source.disconnect).toHaveBeenCalledTimes(1);
    await microtasks(); expect(completed).not.toHaveBeenCalled();
    f.message({ type: "stopped", reason: "stop", totalFrames: 3 });
    const recording = await result;
    expect(recording?.frames).toBe(1); expect(recording?.blob.size).toBe(46);
    expect(recording?.blob.type).toBe("audio/wav");
    expect(f.context.close).toHaveBeenCalledTimes(1);
    expect(f.node.disconnect).toHaveBeenCalledTimes(1);
    expect(f.node.port.close).toHaveBeenCalledTimes(1);
    expect(f.timers.size).toBe(0);
  });

  it("cancels an unresolved permission request and stops every late stream track", async () => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); capture.cancel();
    expect(await result).toBeNull();
    expect(capture.state.status).toBe("cancelled");
    f.permission.resolve(f.stream); await microtasks();
    expect(f.track.stop).toHaveBeenCalledTimes(1);
    expect(f.context.audioWorklet.addModule).not.toHaveBeenCalled();
  });

  it.each(["module", "resume"] as const)("disposes while %s is pending without connecting late", async (stage) => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); f.permission.resolve(f.stream); await microtasks();
    if (stage === "resume") { f.module.resolve(); await microtasks(); }
    capture.dispose(); expect(await result).toBeNull();
    f.module.resolve(); f.resume.resolve(); await microtasks();
    expect(f.track.stop).toHaveBeenCalledTimes(1);
    expect(f.context.close).toHaveBeenCalledTimes(1);
    expect(f.source.connect).not.toHaveBeenCalled();
    expect(await capture.start()).toBeNull();
    expect(f.timers.size).toBe(0);
  });

  it("cancel discards accumulated PCM, ignores late messages and prevents completion", async () => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); await f.ready();
    const late = f.node.port.onmessage!;
    f.message({ type: "chunk", offset: 0, samples: new Float32Array(192) });
    capture.stop(); capture.cancel();
    late({ data: { type: "stopped", reason: "stop", totalFrames: 192 } } as MessageEvent<unknown>);
    expect(await result).toBeNull(); expect(capture.state.status).toBe("cancelled");
    expect(f.context.close).toHaveBeenCalledTimes(1); expect(f.timers.size).toBe(0);
  });

  it.each([
    null, { type: "chunk", offset: 1, samples: new Float32Array([0]) },
    { type: "chunk", offset: 0, samples: [0] },
    { type: "chunk", offset: 0, samples: new Float32Array([NaN]) },
    { type: "stopped", reason: "limit", totalFrames: 0 },
    { type: "stopped", reason: "stop", totalFrames: 0 }, { type: "error" }
  ])("invalid worklet message releases resources and cannot produce audio: %j", async (message) => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); await f.ready(); f.message(message);
    expect(await result).toBeNull(); expect(capture.state.status).toBe("error");
    expect(f.track.stop).toHaveBeenCalledTimes(1); expect(f.context.close).toHaveBeenCalledTimes(1);
  });

  it("enforces wall-clock bound independently from worklet messages and bounds flush wait", async () => {
    const f = fixture(); const onlimit = vi.fn();
    const capture = createVoiceCapture({ platform: f.platform, onlimit });
    const result = capture.start(); await f.ready();
    f.advance(30_000);
    expect(capture.state.status).toBe("stopping"); expect(onlimit).toHaveBeenCalledTimes(1);
    expect(f.track.stop).toHaveBeenCalledTimes(1);
    f.advance(1000); expect(await result).toBeNull(); expect(capture.state.status).toBe("error");
    expect(f.context.close).toHaveBeenCalledTimes(1); expect(f.timers.size).toBe(0);
  });

  it("automatically completes at the finite worklet frame limit", async () => {
    const f = fixture(16_000); const onlimit = vi.fn();
    const capture = createVoiceCapture({ platform: f.platform, onlimit });
    const result = capture.start(); await f.ready();
    for (let offset = 0; offset < VOICE_MAX_FRAMES; offset += 2048) {
      f.message({ type: "chunk", offset, samples: new Float32Array(Math.min(2048, VOICE_MAX_FRAMES - offset)) });
    }
    f.message({ type: "stopped", reason: "limit", totalFrames: VOICE_MAX_FRAMES });
    expect((await result)?.blob.size).toBe(VOICE_MAX_WAV_BYTES);
    expect(onlimit).toHaveBeenCalledTimes(1); expect(capture.state.status).toBe("complete");
    expect(f.track.stop).toHaveBeenCalledTimes(1);
  });

  it("bounds hung setup and releases the stream even if module loading never completes", async () => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start(); f.permission.resolve(f.stream); await microtasks();
    f.advance(30_000); expect(await result).toBeNull();
    expect(f.track.stop).toHaveBeenCalledTimes(1); expect(f.context.close).toHaveBeenCalledTimes(1);
  });

  it.each(["track", "processor", "message", "permission"])("releases resources on %s failure", async (failure) => {
    const f = fixture(); const capture = createVoiceCapture({ platform: f.platform });
    const result = capture.start();
    if (failure === "permission") f.permission.reject(new Error("Denied"));
    else {
      await f.ready();
      if (failure === "track") f.track.dispatchEvent(new Event("ended"));
      if (failure === "processor") f.node.onprocessorerror?.();
      if (failure === "message") f.node.port.onmessageerror?.();
    }
    expect(await result).toBeNull(); expect(capture.state.status).toBe("error");
    if (failure !== "permission") expect(f.context.close).toHaveBeenCalledTimes(1);
  });

  it("deduplicates starts and stops and contains throwing UI observers", async () => {
    const f = fixture();
    const capture = createVoiceCapture({ platform: f.platform, onstate: () => { throw new Error("UI"); } });
    const result = capture.start(); expect(capture.start()).toBe(result); await f.ready();
    expect(capture.stop()).toBe(result); expect(capture.stop()).toBe(result); capture.cancel();
    expect(await result).toBeNull(); expect(f.track.stop).toHaveBeenCalledTimes(1);
  });
});
