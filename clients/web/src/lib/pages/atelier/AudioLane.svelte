<script lang="ts">
  import { onDestroy } from "svelte";
  let { name }: { name: string } = $props();
  let url = $state(""),
    filename = $state(""),
    peaks = $state(""),
    error = $state("");
  let player = $state<HTMLAudioElement>();
  let version = 0;
  async function load(event: Event) {
    const input = event.currentTarget as HTMLInputElement,
      file = input.files?.[0];
    input.value = "";
    if (!file) return;
    const current = ++version;
    if (url) URL.revokeObjectURL(url);
    url = URL.createObjectURL(file);
    filename = file.name;
    peaks = "";
    error = "";
    if (file.size > 12_000_000 || typeof AudioContext === "undefined") return;
    let audio: AudioContext | undefined;
    try {
      audio = new AudioContext();
      const data = await audio.decodeAudioData(await file.arrayBuffer());
      if (current !== version) return;
      const samples = data.getChannelData(0);
      const points = [];
      for (let i = 0; i < 160; i++) {
        const begin = Math.floor((i * samples.length) / 160),
          end = Math.floor(((i + 1) * samples.length) / 160);
        let peak = 0;
        for (let j = begin; j < end; j += Math.max(1, Math.floor((end - begin) / 64)))
          peak = Math.max(peak, Math.abs(samples[j]!));
        points.push(`M${i} ${10 - peak * 9}v${Math.max(0.5, peak * 18)}`);
      }
      peaks = points.join(" ");
    } catch {
      /* The media element can still audition formats the decoder does not support. */
    } finally {
      if (audio) await audio.close();
    }
  }
  onDestroy(() => {
    version++;
    if (url) URL.revokeObjectURL(url);
  });
</script>

<div class="lane" data-track={name}>
  {#if url}
    <audio bind:this={player} src={url} onerror={() => (error = "Cannot play this file.")}></audio>
    <button
      title={filename}
      aria-label={`Audition ${name}: ${filename}`}
      onclick={() => {
        if (player?.paused) void player.play().catch(() => (error = "Cannot play this file."));
        else player?.pause();
      }}
    >
      {#if peaks}<svg viewBox="0 0 160 20" preserveAspectRatio="none" aria-hidden="true"
          ><path d={peaks} /></svg
        >{/if}
      <span>▷ {filename}</span></button
    >
  {/if}
  <label title={url ? "Replace " + name : "Add " + name}
    ><span>{url ? "↺" : "+ " + name}</span><input
      aria-label={`Choose ${name} audio`}
      type="file"
      accept="audio/*"
      onchange={load}
    /></label
  >
  {#if error}<small role="alert">{error}</small>{/if}
</div>

<style>
  .lane {
    display: flex;
    min-width: 0;
    min-height: 24px;
    align-items: stretch;
    gap: 0.25rem;
    border-block-end: 1px solid var(--color-engraving);
    color: #91bdbc;
  }
  .lane[data-track="Music"] {
    color: #b29ac5;
  }
  .lane[data-track="Effects"] {
    color: #bfa781;
  }
  label,
  button {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: transparent;
    border: 0;
    color: inherit;
    font: 11px var(--font-body);
    cursor: pointer;
  }
  label {
    min-width: 1.8rem;
    overflow: hidden;
    padding: 0.15rem 0.4rem;
  }
  label input {
    position: absolute;
    inset: 0;
    width: 100%;
    opacity: 0;
    cursor: pointer;
  }
  button {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    padding: 0 0.5rem;
    background: color-mix(in srgb, currentColor 13%, transparent);
    border-radius: 3px;
  }
  button span {
    position: relative;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0.55;
    stroke: currentColor;
    stroke-width: 0.65;
  }
  audio {
    display: none;
  }
  label:focus-within {
    outline: 2px solid var(--color-frost);
    outline-offset: -2px;
  }
</style>
