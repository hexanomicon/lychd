import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";
import processorSource from "./pcm-recorder.js?raw";

interface Processor {
  port: { onmessage: (event: { data: unknown }) => void };
  process(inputs: Float32Array[][], outputs: Float32Array[][]): boolean;
}

function worklet(rate = 48_000) {
  let Constructor!: new () => Processor;
  const messages: Array<{ type: string; samples?: Float32Array; offset?: number;
    totalFrames?: number; reason?: string }> = [];
  runInNewContext(processorSource, {
    sampleRate: rate,
    AudioWorkletProcessor: class {
      port = { onmessage: null, postMessage: (message: typeof messages[number]) => messages.push(message) };
    },
    registerProcessor: (name: string, value: typeof Constructor) => {
      expect(name).toBe("lychd-pcm-recorder"); Constructor = value;
    },
    Float32Array, Number, Math
  });
  return { processor: new Constructor(), messages };
}

describe("actual PCM worklet", () => {
  it("averages channels explicitly and writes only silence to connected output", () => {
    const { processor, messages } = worklet();
    const output = new Float32Array(3).fill(1);
    expect(processor.process([[new Float32Array([1, 0.5, -1]), new Float32Array([-1, 0.5, 1])]], [[output]]))
      .toBe(true);
    expect([...output]).toEqual([0, 0, 0]);
    processor.port.onmessage({ data: { type: "stop" } });
    expect([...messages[0]!.samples!]).toEqual([0, 0.5, 0]);
    expect(messages[0]!.offset).toBe(0);
    expect(messages[1]).toEqual({ type: "stopped", reason: "stop", totalFrames: 3 });
  });

  it("emits finite ordered chunks and stops at exact source-frame bound", () => {
    const { processor, messages } = worklet(44_100);
    const input = [[new Float32Array(128).fill(0.25)]];
    let calls = 0;
    while (processor.process(input, []) && calls++ < 11_000) { /* render quanta */ }
    expect(calls).toBeLessThan(11_000);
    let frames = 0;
    for (const message of messages.filter((item) => item.type === "chunk")) {
      expect(message.offset).toBe(frames);
      expect(message.samples!.length).toBeGreaterThan(0);
      expect(message.samples!.length).toBeLessThanOrEqual(2048);
      frames += message.samples!.length;
    }
    expect(frames).toBe(44_100 * 30);
    expect(messages.at(-1)).toEqual({ type: "stopped", reason: "limit", totalFrames: frames });
    const count = messages.length;
    processor.port.onmessage({ data: { type: "stop" } });
    expect(processor.process(input, [])).toBe(false); expect(messages.length).toBe(count);
  });

  it("cancel drops the unflushed samples and produces no completed utterance", () => {
    const { processor, messages } = worklet();
    processor.process([[new Float32Array(128).fill(1)]], []);
    processor.port.onmessage({ data: { type: "cancel" } });
    processor.port.onmessage({ data: { type: "stop" } });
    expect(processor.process([[new Float32Array(128)]], [])).toBe(false);
    expect(messages).toEqual([]);
  });

  it.each([[[new Float32Array([NaN])]], [[new Float32Array([Infinity])]],
    [[new Float32Array(2), new Float32Array(1)]], [Array.from({ length: 33 }, () => new Float32Array(1))]]
    .map((inputs) => ({ inputs })))
    ("rejects invalid render input", ({ inputs }) => {
      const { processor, messages } = worklet();
      expect(processor.process(inputs, [])).toBe(false);
      expect(messages).toEqual([{ type: "error" }]);
    });

  it.each([null, {}, { type: "unknown" }])("rejects invalid control messages", (data) => {
    const { processor, messages } = worklet();
    processor.port.onmessage({ data });
    expect(messages).toEqual([{ type: "error" }]);
  });
});
