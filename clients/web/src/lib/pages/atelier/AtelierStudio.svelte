<script lang="ts">
  import { onDestroy } from "svelte";
  import {
    decodeBrief,
    recipes,
    sampleBrief,
    timecode,
    validateBrief,
    wireBytes,
    type Brief,
    type Recipe,
  } from "./brief";
  import plate from "./observatory-study.webp";

  const initial = sampleBrief();
  let recipe = $state<Recipe>(initial.recipe);
  let script = $state(initial.script);
  let duration = $state<number | undefined>(initial.duration_seconds);
  let windowed = $state(false);
  let opening = $state("");
  let closing = $state("");
  let notice = $state("");
  let fileError = $state("");
  let elapsed = $state(0);
  let playing = $state(false);
  let frame = 0;
  let request = 0;
  let mediaUrl = $state("");
  let mediaName = $state("");
  let mediaDuration = $state<number | undefined>(undefined);
  let mediaError = $state("");
  let sourceMode = $state(false);

  const length = $derived(Number.isInteger(duration) && duration! > 0 && duration! <= 180 ? duration! : 0);
  const lines = $derived(
    script
      .split(/\r\n|\n|\r/)
      .map((line) => line.trim())
      .filter(Boolean),
  );
  const cue = $derived(
    length && lines.length ? Math.min(lines.length - 1, Math.floor((elapsed * lines.length) / length)) : 0,
  );
  const checked = $derived.by(() => {
    try {
      return {
        value: validateBrief({
          recipe,
          script,
          duration_seconds: duration,
          ...(windowed ? { not_before: opening, latest_start_at: closing } : {}),
        }),
        error: "",
      };
    } catch (e) {
      return { value: null, error: e instanceof Error ? e.message : "Check the brief fields." };
    }
  });

  function pause() {
    cancelAnimationFrame(frame);
    playing = false;
  }
  function seek(to: number) {
    pause();
    elapsed = Math.min(Math.max(0, to), length);
  }
  function play() {
    if (playing) {
      pause();
      return;
    }
    if (!length || !lines.length) return;
    if (elapsed >= length) elapsed = 0;
    const start = performance.now() - elapsed * 1000;
    playing = true;
    function advance(now: number) {
      elapsed = Math.min(length, (now - start) / 1000);
      if (elapsed >= length) pause();
      else frame = requestAnimationFrame(advance);
    }
    frame = requestAnimationFrame(advance);
  }
  function edit() {
    request++;
    notice = "";
    fileError = "";
  }
  function apply(brief: Brief) {
    pause();
    recipe = brief.recipe;
    script = brief.script;
    duration = brief.duration_seconds;
    windowed = brief.not_before !== undefined;
    opening = brief.not_before ?? "";
    closing = brief.latest_start_at ?? "";
    sourceMode = false;
    elapsed = 0;
  }
  async function importFile(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    const version = ++request;
    fileError = "";
    notice = "";
    try {
      if (file.size > wireBytes) throw new Error("The file exceeds 8,192 UTF-8 bytes.");
      const bytes = await file.arrayBuffer();
      const brief = decodeBrief(new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes));
      if (version !== request) return;
      apply(brief);
      notice = "Brief imported into this page.";
    } catch (cause) {
      if (version === request)
        fileError = cause instanceof Error ? cause.message : "The brief could not be read.";
    }
  }
  function exportFile() {
    if (!checked.value) return;
    const blob = new Blob([JSON.stringify(checked.value)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "short-video-brief.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notice = "Brief prepared for download.";
  }
  function openVideo(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    pause();
    if (mediaUrl) URL.revokeObjectURL(mediaUrl);
    mediaUrl = URL.createObjectURL(file);
    mediaName = file.name;
    mediaDuration = undefined;
    mediaError = "";
    sourceMode = true;
  }
  function closeVideo() {
    sourceMode = false;
    if (mediaUrl) URL.revokeObjectURL(mediaUrl);
    mediaUrl = "";
    mediaName = "";
    mediaError = "";
    mediaDuration = undefined;
  }
  onDestroy(() => {
    request++;
    cancelAnimationFrame(frame);
    if (mediaUrl) URL.revokeObjectURL(mediaUrl);
  });
</script>

<svelte:head><title>Atelier · Short-video studio — LychD</title></svelte:head>
<section class="studio">
  <header class="studio-header">
    <div>
      <nav aria-label="Application location">
        <a href="/applications">Applications</a><span>/</span>Atelier
      </nav>
      <h1>Short-video studio</h1>
    </div>
    <div class="actions">
      <label class="file-button"
        >Import brief<input type="file" accept=".json,application/json" onchange={importFile} /></label
      >
      <button class="export" disabled={!checked.value} onclick={exportFile}
        ><b aria-hidden="true">↓</b> Export brief</button
      >
    </div>
  </header>

  {#if fileError}<p class="notice error" role="alert">{fileError}</p>{:else if notice}<p
      class="notice"
      role="status"
    >
      {notice}
    </p>{/if}
  <div class="studio-grid">
    <div class="editing-field">
      <section class="monitor" aria-label="Local preview">
        <header class="bar">
          <h2>Program monitor</h2>
          <span>{sourceMode ? "Local video" : "Timing study"}</span>
          <div class="monitor-tools">
            <label class="file-button"
              >{mediaUrl ? "Change video" : "Open video"}<input
                type="file"
                accept="video/*"
                onchange={openVideo}
              /></label
            >
          </div>
        </header>
        {#if sourceMode && mediaUrl}
          <div class="screen media">
            <!-- The local video's own tracks and native controls stay available. -->
            <!-- svelte-ignore a11y_media_has_caption -->
            <video
              src={mediaUrl}
              controls
              playsinline
              preload="metadata"
              bind:duration={mediaDuration}
              onerror={() => {
                mediaError = "This browser could not play the selected video.";
              }}
            ></video>
          </div>
          {#if mediaError}<p class="notice error" role="alert">{mediaError}</p>{/if}
          <div class="transport">
            <strong>{mediaName}</strong>
            {#if mediaDuration && Number.isFinite(mediaDuration)}<span
                >{mediaDuration.toFixed(2)} s · source</span
              >{/if}
            <button class="end" onclick={closeVideo}>Close video</button>
          </div>
        {:else}
          <div class="screen">
            <img
              src={plate}
              alt="Illustrative still of the observatory dome above a mountain ridge at sunset"
            />
            <span class="plate-label">Sample plate · Observatory at dusk</span>
            {#if lines[cue]}<p class="caption"><span>{lines[cue]}</span></p>{/if}
          </div>
          <div class="transport">
            <button
              class="play"
              aria-label={playing ? "Pause timing preview" : "Play timing preview"}
              disabled={!length || !lines.length}
              onclick={play}>{playing ? "Ⅱ" : "▶"}</button
            >
            <label class="scrub"
              ><input
                type="range"
                min="0"
                max={length || 1}
                step={1 / 30}
                aria-label="Script playhead"
                value={elapsed}
                disabled={!length}
                oninput={(event) => seek(+event.currentTarget.value)}
              /></label
            >
            <time>{timecode(elapsed)} <span>/ {timecode(length)}</span></time>
          </div>
        {/if}
      </section>

      <section class="timeline" aria-labelledby="timing-title">
        <header class="bar">
          <h2 id="timing-title">Script timing</h2>
          <span>{lines.length} {lines.length === 1 ? "cue" : "cues"}</span><small>30 fps study</small>
        </header>
        {#if length && lines.length}
          <div class="ruler">
            <span>00:00</span><span>{timecode(length / 2).slice(3, 8)}</span><span
              >{timecode(length).slice(3, 8)}</span
            >
          </div>
          <div class="tracks">
            <span class="track-label">Picture</span>
            <div class="picture-strip" style:--plate={`url("${plate}")`}><span>Observatory study</span></div>
            <span class="track-label">Script</span>
            <div class="cue-strip" style:--cue-count={lines.length}>
              {#each lines as line, index (`${index}-${line}`)}
                <button
                  aria-label={`Preview cue ${index + 1}`}
                  title={line}
                  aria-pressed={index === cue}
                  onclick={() => {
                    sourceMode = false;
                    seek((index * length) / lines.length);
                  }}>{index + 1}</button
                >
              {/each}
            </div>
          </div>
          <div class="current-cue">
            <span>Current cue</span>
            <p>{lines[cue]}</p>
            <time
              >{timecode((cue * length) / lines.length)} – {timecode(
                ((cue + 1) * length) / lines.length,
              )}</time
            >
          </div>
        {:else}<p class="empty">Enter a script and a duration to preview its timing.</p>{/if}
      </section>
    </div>

    <aside class="brief-panel" aria-labelledby="brief-title">
      <header class="bar">
        <h2 id="brief-title">Commission brief</h2>
        <span>Local draft</span>
      </header>
      <div class="brief-fields">
        <label
          >Recipe<select bind:value={recipe} onchange={edit}
            >{#each Object.entries(recipes) as [key, label] (key)}<option value={key}>{label}</option
              >{/each}</select
          ></label
        >
        <label
          >Script<textarea
            bind:value={script}
            rows="5"
            oninput={() => {
              edit();
              seek(0);
            }}></textarea></label
        >
        <div class="script-meta">
          <span>One cue per line</span><span>{Array.from(script).length.toLocaleString("en")} / 8,000</span>
        </div>
        <label class="duration"
          >Requested duration<span
            ><input
              type="number"
              min="1"
              max="180"
              step="1"
              bind:value={duration}
              oninput={() => {
                edit();
                seek(0);
              }}
            /><small>seconds</small></span
          ></label
        >
        <div class="window">
          <label class="check"
            ><input type="checkbox" bind:checked={windowed} onchange={edit} /> UTC start window</label
          >
          {#if windowed}
            <label
              >Earliest start<input
                type="text"
                bind:value={opening}
                placeholder="2026-11-19T18:00:00Z"
                oninput={edit}
              /></label
            >
            <label
              >Latest start (exclusive)<input
                type="text"
                bind:value={closing}
                placeholder="2026-11-19T20:30:00Z"
                oninput={edit}
              /></label
            >
          {/if}
        </div>
        {#if checked.error}<p class="error" role="status">{checked.error}</p>{/if}
      </div>
      <footer>
        <span aria-hidden="true">◇</span>
        <p>Export contains the recipe, script, duration and any UTC start window.</p>
      </footer>
    </aside>
  </div>
</section>

<style>
  .studio {
    max-width: 108rem;
    margin: 0 auto;
    color: var(--color-bone);
    font: 14px/1.5 var(--font-body);
  }
  .studio-header,
  .bar,
  .actions,
  .transport,
  .script-meta,
  .duration > span,
  .check,
  .brief-panel footer {
    display: flex;
    align-items: center;
  }
  .studio-header {
    justify-content: space-between;
    gap: 1rem;
    padding: clamp(1rem, 2vw, 1.75rem);
  }
  nav {
    display: flex;
    gap: 0.65rem;
    font: 11px/1.5 var(--font-glyph);
    color: var(--color-ash);
  }
  a {
    color: var(--color-accent);
    text-decoration: none;
  }
  h1 {
    margin: 0.28rem 0 0;
    font: 500 clamp(1.65rem, 2.8vw, 2.65rem)/1.12 var(--font-rune);
    letter-spacing: -0.025em;
  }
  h2,
  p {
    margin: 0;
  }
  h2 {
    font: 600 12px/1.3 var(--font-body);
  }
  .actions {
    gap: 7px;
  }
  button,
  input,
  textarea,
  select {
    font: inherit;
  }
  .file-button {
    position: relative;
    display: inline-block;
    overflow: hidden;
  }
  .file-button input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
  }
  .file-button:focus-within {
    outline: 2px solid var(--color-rune);
    outline-offset: 2px;
  }
  button,
  .file-button {
    color: var(--color-parchment);
    border: 1px solid var(--color-control-border);
    background: var(--color-obsidian);
    border-radius: 5px;
    padding: 0.42rem 0.72rem;
    cursor: pointer;
    font-size: 12px;
  }
  button:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-bone);
  }
  button:disabled {
    opacity: 0.48;
    cursor: default;
  }
  button.export {
    background: var(--color-accent);
    border-color: var(--color-accent);
    color: var(--color-void);
    font-weight: 650;
  }
  .export b {
    margin-right: 0.3rem;
  }
  .studio-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) clamp(230px, 23%, 315px);
    border-top: 1px solid var(--color-engraving);
  }
  .editing-field {
    min-width: 0;
    padding: clamp(0.65rem, 1.45vw, 1.35rem);
  }
  .monitor,
  .timeline {
    border: 1px solid var(--color-engraving);
    border-radius: 7px;
    overflow: hidden;
    background: var(--color-obsidian);
  }
  .bar {
    min-height: 39px;
    gap: 9px;
    padding: 5px 12px;
    border-bottom: 1px solid var(--color-engraving);
  }
  .bar > span,
  .bar small,
  .script-meta,
  .track-label,
  .current-cue > span,
  .duration small,
  .brief-panel footer {
    color: var(--color-ash);
    font: 10px/1.5 var(--font-glyph);
  }
  .monitor-tools,
  .bar small,
  .end {
    margin-left: auto;
  }
  .bar .file-button,
  .end {
    font-size: 11px;
    padding: 3px 7px;
  }
  .screen {
    position: relative;
    display: grid;
    place-items: center;
    aspect-ratio: 16/8;
    min-height: 120px;
    max-height: 54vh;
    background: #08090a;
  }
  .screen img,
  .screen video {
    display: block;
    height: 100%;
    width: 100%;
    min-height: 0;
    object-fit: contain;
  }
  .screen img {
    object-fit: cover;
  }
  .plate-label {
    position: absolute;
    left: 12px;
    top: 10px;
    padding: 3px 7px;
    color: white;
    background: #101016ae;
    border: 1px solid #ffffff30;
    border-radius: 3px;
    font: 10px/1.4 var(--font-glyph);
  }
  .caption {
    position: absolute;
    bottom: 8%;
    left: 6%;
    right: 6%;
    text-align: center;
    max-height: 56%;
    overflow: auto;
    font: 650 clamp(15px, 1.55vw, 25px)/1.38 var(--font-body);
    overflow-wrap: anywhere;
  }
  .caption span {
    color: #fff;
    background: #101015d9;
    padding: 2px 6px;
    box-decoration-break: clone;
  }
  .transport {
    gap: 0.65rem;
    padding: 7px 10px;
    background: var(--color-obsidian-2);
    overflow: hidden;
  }
  .transport strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
  }
  .transport > span {
    font-size: 11px;
    color: var(--color-ash);
  }
  .play {
    flex: none;
    padding: 0;
    width: 30px;
    height: 27px;
    font-size: 11px;
  }
  .scrub {
    flex: 1;
    display: flex;
    min-width: 24px;
  }
  .scrub input {
    width: 100%;
    accent-color: var(--color-accent);
  }
  time {
    font: 10px/1.45 var(--font-glyph);
    color: var(--color-parchment);
  }
  time span {
    color: var(--color-ash);
  }
  .timeline {
    margin-top: 12px;
  }
  .ruler {
    display: flex;
    justify-content: space-between;
    margin: 10px 11px 4px 61px;
    padding-bottom: 7px;
    background: repeating-linear-gradient(90deg, var(--color-control-border) 0 1px, transparent 1px 5%) left
      bottom/100% 4px no-repeat;
    font: 9px/1.3 var(--font-glyph);
    color: var(--color-ash);
  }
  .tracks {
    display: grid;
    align-items: center;
    grid-template-columns: 43px minmax(0, 1fr);
    gap: 5px 7px;
    padding: 0 11px 13px;
  }
  .picture-strip {
    height: 33px;
    display: flex;
    align-items: center;
    border: 1px solid var(--color-control-border);
    border-radius: 4px;
    overflow: hidden;
    background-image: linear-gradient(90deg, #1118, #1114), var(--plate);
    background-size:
      cover,
      72px 100%;
  }
  .picture-strip span {
    padding: 1px 5px;
    margin-left: 4px;
    border-radius: 2px;
    background: #0c0c12c9;
    color: #fff;
    font-size: 10px;
  }
  .cue-strip {
    height: 25px;
    display: grid;
    grid-template-columns: repeat(var(--cue-count), minmax(23px, 1fr));
    gap: 2px;
    overflow: auto hidden;
  }
  .cue-strip button {
    min-width: 0;
    padding: 0 4px;
    text-align: left;
    font: 10px var(--font-glyph);
    color: var(--color-parchment);
    background: color-mix(in srgb, var(--color-accent) 22%, var(--color-obsidian));
    border-color: var(--color-control-border);
    border-radius: 3px;
  }
  .cue-strip button[aria-pressed="true"] {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 41%, var(--color-obsidian));
  }
  .current-cue {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    align-items: baseline;
    gap: 3px 10px;
    padding: 10px 12px;
    border-top: 1px solid var(--color-engraving);
  }
  .current-cue p {
    font-size: 12px;
    overflow-wrap: anywhere;
  }
  .current-cue time {
    grid-column: 2;
    color: var(--color-ash);
  }
  .brief-panel {
    min-width: 0;
    align-self: start;
    border-left: 1px solid var(--color-engraving);
    border-bottom: 1px solid var(--color-engraving);
    background: var(--color-obsidian);
  }
  .brief-panel .bar {
    justify-content: space-between;
  }
  .brief-fields {
    padding: 16px 14px 12px;
    display: grid;
    gap: 13px;
  }
  .brief-fields label:not(.check) {
    display: grid;
    gap: 5px;
  }
  .brief-fields label {
    font-size: 12px;
    color: var(--color-parchment);
  }
  input:not([type="range"], [type="checkbox"]),
  select,
  textarea {
    min-width: 0;
    width: 100%;
    padding: 0.45rem 0.55rem;
    background: var(--color-void);
    color: var(--color-bone);
    border: 1px solid var(--color-control-border);
    border-radius: 5px;
    font: 12px/1.5 var(--font-body);
  }
  textarea {
    resize: vertical;
    min-height: 5rem;
  }
  .script-meta {
    justify-content: space-between;
    margin-top: -8px;
  }
  .duration > span,
  .check {
    gap: 8px;
  }
  .duration input {
    max-width: 75px;
  }
  .window {
    display: grid;
    gap: 10px;
    border-top: 1px solid var(--color-engraving);
    padding-top: 13px;
  }
  .check input {
    accent-color: var(--color-accent);
  }
  .brief-panel footer {
    align-items: flex-start;
    gap: 7px;
    margin: 0;
    padding: 12px 14px;
    border-top: 1px solid var(--color-engraving);
    font-family: var(--font-body);
    font-size: 11px;
  }
  .brief-panel footer > span {
    color: var(--color-accent);
  }
  .notice,
  .empty {
    padding: 8px 12px;
    color: var(--color-parchment);
    font-size: 12px;
  }
  .error {
    color: var(--color-heat);
    font-size: 12px;
  }
  @container (max-width:680px) {
    .studio-grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .brief-panel {
      border-left: 0;
    }
  }
  @media (max-width: 850px) {
    .studio-grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .brief-panel {
      border-left: 0;
    }
  }
  @media (max-width: 500px) {
    .studio-header {
      flex-wrap: wrap;
      gap: 0.6rem;
      padding: 0.85rem;
    }
    .screen {
      aspect-ratio: 16/9;
    }
    .transport time span {
      display: none;
    }
  }
</style>
