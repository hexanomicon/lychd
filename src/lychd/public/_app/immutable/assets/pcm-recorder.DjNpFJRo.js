/* Local capture only. The output is always silence; this processor never plays the input. */
class LychdPcmRecorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.chunk = new Float32Array(2048);
    this.used = 0;
    this.totalFrames = 0;
    this.maxFrames = Math.floor(sampleRate * 30);
    this.done = false;
    this.port.onmessage = (event) => {
      const message = event.data;
      if (!message || typeof message !== "object" ||
          (message.type !== "stop" && message.type !== "cancel")) {
        this.abort();
      } else if (message.type === "cancel") {
        this.done = true;
        this.chunk.fill(0);
        this.used = 0;
      } else {
        this.finish("stop");
      }
    };
  }

  flush() {
    if (!this.used) return;
    const samples = this.chunk.slice(0, this.used);
    this.port.postMessage({ type: "chunk", offset: this.totalFrames - this.used, samples }, [samples.buffer]);
    this.chunk.fill(0);
    this.used = 0;
  }

  finish(reason) {
    if (this.done) return;
    this.done = true;
    this.flush();
    this.port.postMessage({ type: "stopped", reason, totalFrames: this.totalFrames });
  }

  abort() {
    this.done = true;
    this.chunk.fill(0);
    this.used = 0;
    this.port.postMessage({ type: "error" });
    return false;
  }

  process(inputs, outputs) {
    for (const output of outputs) for (const channel of output) channel.fill(0);
    if (this.done) return false;
    const channels = inputs[0];
    if (!channels?.length) return true;
    if (channels.length > 32) return this.abort();
    const frames = channels[0].length;
    if (frames < 1 || frames > 2048 || channels.some((channel) => channel.length !== frames)) {
      return this.abort();
    }
    for (let frame = 0; frame < frames; frame++) {
      let mono = 0;
      for (const channel of channels) {
        const sample = channel[frame];
        if (!Number.isFinite(sample)) return this.abort();
        mono += Math.max(-1, Math.min(1, sample)) / channels.length;
      }
      this.chunk[this.used++] = mono;
      this.totalFrames++;
      if (this.used === this.chunk.length) this.flush();
      if (this.totalFrames === this.maxFrames) {
        this.finish("limit");
        return false;
      }
    }
    return true;
  }
}

registerProcessor("lychd-pcm-recorder", LychdPcmRecorder);
