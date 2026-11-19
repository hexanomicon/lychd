<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { afterNavigate } from "$app/navigation";
  import { getRailContent } from "$lib/shell/state/rail-content";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import AudioLane from "./AudioLane.svelte";
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";
  import { frameAt, captionTrack } from "./cut";
  import {
    decodeBrief,
    sampleBrief,
    timecode,
    validateBrief,
    wireBytes,
    type Brief,
  } from "./brief";
  import { recipes, type Recipe } from "$lib/compositions/video";
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
  let elapsed = $state(5.4);
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
  const rail = getRailContent();
  let mode = $state<"Storyboard" | "Cut" | "Review">("Cut");
  let panel = $state<"caption" | "brief">("caption");
  let panelOpen = $state(true),
    panelWidth = $state(290);
  let font = $state("System sans"),
    weight = $state("600"),
    size = $state(52),
    place = $state("Bottom centre");
  let focusCuts = $state<number[] | null>(null);
  const totalFrames = $derived(length * 30);
  const bounds = $derived(
    focusCuts?.length === lines.length + 1 && focusCuts.at(-1) === totalFrames
      ? focusCuts
      : Array.from({ length: lines.length + 1 }, (_, i) =>
          Math.round((i * totalFrames) / Math.max(1, lines.length)),
        ),
  );
  const cue = $derived(
    Math.min(
      Math.max(0, lines.length - 1),
      Math.max(
        0,
        bounds.findLastIndex((f) => f <= Math.floor(elapsed * 30 + 0.00001)),
      ),
    ),
  );
  const title = $derived(
    mediaName ||
      (script === initial.script ? "Observatory at dusk" : lines[0]?.slice(0, 55) || "Untitled cut"),
  );
  const shotName = (index: number) =>
    script === initial.script
      ? (["Ridge", "Dome", "Night sky"][index] ?? "Shot " + (index + 1))
      : "Shot " + (index + 1);
  let previousRecipeUrl: string | null = null;
  afterNavigate(({ to }) => {
    const chosen = to?.url.searchParams.get("recipe");
    if (chosen && chosen !== previousRecipeUrl && Object.hasOwn(recipes, chosen)) recipe = chosen as Recipe;
    previousRecipeUrl = chosen ?? null;
  });
  onMount(() => {
    if (rail) rail.section = shotBin;
    return () => {
      if (rail?.section === shotBin) rail.section = undefined;
    };
  });
  function selectCue(index: number) {
    sourceMode = false;
    mode = "Cut";
    panel = "caption";
    seek((bounds[index] ?? 0) / 30);
  }
  function changeLine(text: string) {
    if (!text.trim()) return;
    script = lines.map((line, i) => (i === cue ? text.replace(/[\r\n]+/g, " ").trim() : line)).join("\n");
    edit();
  }
  function trim(at: number, input: HTMLInputElement) {
    const frame = frameAt(input.value),
      selectedCue = cue;
    if (
      frame === null ||
      at <= 0 ||
      at >= bounds.length - 1 ||
      frame <= bounds[at - 1]! ||
      frame >= bounds[at + 1]!
    ) {
      input.value = timecode(bounds[at]! / 30);
      fileError = "Place the cut between the previous and next frame boundaries.";
      return;
    }
    focusCuts = bounds.map((value, index) => (index === at ? frame : value));
    seek(Math.max(bounds[selectedCue]! / 30, Math.min(elapsed, (bounds[selectedCue + 1]! - 1) / 30)));
    edit();
  }
  function split() {
    const frame = Math.round(elapsed * 30),
      index = cue;
    if (frame <= bounds[index]! || frame >= bounds[index + 1]!) return;
    const next = bounds.toSpliced(index + 1, 0, frame);
    script = lines.toSpliced(index + 1, 0, lines[index]!).join("\n");
    focusCuts = next;
    edit();
  }
  function exportCaptions() {
    if (!length || !lines.length || totalFrames < lines.length) return;
    const url = URL.createObjectURL(new Blob([captionTrack(lines, bounds)], { type: "text/vtt" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "atelier-captions.vtt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
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
    focusCuts = null;
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
{#snippet shotBin()}
  <section class="shot-bin" aria-label="Shot bin">
    <h2>Shot bin <small>{lines.length} shots</small></h2>
    {#each lines as line, i (i)}<button
        type="button"
        aria-pressed={cue === i}
        title={line}
        onclick={() => selectCue(i)}
      >
        <img src={plate} alt="" style:object-position={i % 2 ? "85% center" : "15% center"} />
        <span
          ><strong>{shotName(i)}</strong><small
            >{timecode(bounds[i]! / 30).slice(3, 8)} – {timecode(bounds[i + 1]! / 30).slice(3, 8)}</small
          ></span
        >
      </button>{/each}
  </section>
{/snippet}
<section class="studio" style:--panel-width={panelWidth + "px"} class:panel-folded={!panelOpen}>
  <header class="studio-header">
    <div>
      <nav aria-label="Application location">
        <a href="/applications"><AltarIcon name="atelier" size={14} /> Atelier</a><span>/</span>Video master
      </nav>
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
      <div class="cut-title">
        <div>
          <h1>{title}</h1>
          <p>{recipes[recipe]} · {length} s · 30 fps</p>
        </div>
        <div class="modes" aria-label="Editing view">
          {#each ["Storyboard", "Cut", "Review"] as item (item)}<button
              aria-pressed={mode === item}
              onclick={() => (mode = item as typeof mode)}>{item}</button
            >{/each}
        </div>
      </div>
      {#if mode === "Storyboard"}<section class="board" aria-label="Storyboard">
          {#each lines as line, i (i)}<button onclick={() => selectCue(i)}
              ><img src={plate} alt="" /><small>{shotName(i)} · {timecode(bounds[i]! / 30)}</small><strong
                >{line}</strong
              ></button
            >{/each}
        </section>
      {:else if mode === "Review"}<section class="review">
          <h2>Cut review</h2>
          <dl>
            <dt>Picture source</dt>
            <dd>{mediaName || "Illustrative observatory plate"}</dd>
            <dt>Captions</dt>
            <dd>{lines.length} cues · {length} s</dd>
            <dt>Master</dt>
            <dd>{mediaUrl ? "Local video selected" : "Timing study"}</dd>
          </dl>
          <button disabled={!length || !lines.length || totalFrames < lines.length} onclick={exportCaptions}
            >Export captions (.vtt)</button
          > <a href={`/loom?composition=${recipe}`}>Open workflow in Loom ↗</a>
        </section>
      {:else}
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

              {#if lines[cue]}<p
                  class="caption"
                  class:top={place === "Top centre"}
                  style:font-family={font === "Serif"
                    ? "Georgia,serif"
                    : font === "Monospace"
                      ? "monospace"
                      : "var(--font-body)"}
                  style:font-weight={weight}
                  style:font-size={size / 2 + "px"}
                >
                  <span>{lines[cue]}</span>
                </p>{/if}
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
            <h2 id="timing-title">Timeline</h2>
            <button
              type="button"
              disabled={Math.round(elapsed * 30) <= bounds[cue]! ||
                Math.round(elapsed * 30) >= bounds[cue + 1]!}
              onclick={split}>Split</button
            >
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
              <div class="picture-strip" style:--plate={`url("${plate}")`}>
                {#each lines as _, i (i)}<button
                    aria-label={`Inspect shot ${i + 1}`}
                    style:flex={bounds[i + 1]! - bounds[i]!}
                    aria-pressed={cue === i}
                    onclick={() => selectCue(i)}><span>{shotName(i)}</span></button
                  >{/each}
              </div>
              <span class="track-label">Captions</span>
              <div
                class="cue-strip"
                style:grid-template-columns={lines
                  .map((_, i) => `minmax(0,${bounds[i + 1]! - bounds[i]!}fr)`)
                  .join(" ")}
              >
                {#each lines as line, index (`${index}-${line}`)}
                  <button
                    aria-label={`Preview cue ${index + 1}`}
                    title={line}
                    aria-pressed={index === cue}
                    onclick={() => {
                      sourceMode = false;
                      selectCue(index);
                    }}>{line}</button
                  >
                {/each}
              </div>
            </div>
            <div class="audio-tracks">
              {#each ["Voice", "Music", "Effects"] as track (track)}<span class="track-label">{track}</span
                ><AudioLane name={track} />{/each}
            </div>
            <div class="current-cue">
              <span>Current cue</span>
              <p>{lines[cue]}</p>
              <time>{timecode(bounds[cue]! / 30)} – {timecode(bounds[cue + 1]! / 30)}</time>
            </div>
          {:else}<p class="empty">Enter a script and a duration to preview its timing.</p>{/if}
        </section>
      {/if}
    </div>

    <aside class="brief-panel" aria-label="Atelier inspector">
      {#if panelOpen}<PaneGrip
          bind:width={panelWidth}
          name="Atelier inspector width"
          min={225}
          max={510}
        />{/if}
      <button
        class="seam"
        aria-label={panelOpen ? "Collapse Atelier inspector" : "Expand Atelier inspector"}
        onclick={() => (panelOpen = !panelOpen)}>{panelOpen ? "›" : "‹"}</button
      >
      {#if panelOpen}
        <div class="inspect-tabs">
          <button
            aria-label="Caption inspector"
            title="Caption cue"
            aria-pressed={panel === "caption"}
            onclick={() => (panel = "caption")}><AltarIcon name="loom" size={16} /></button
          >
          <button
            aria-label="Commission brief"
            title="Commission brief"
            aria-pressed={panel === "brief"}
            onclick={() => (panel = "brief")}><AltarIcon name="files" size={16} /></button
          ><a href={`/loom?composition=${recipe}`}>Workflow ↗</a>
        </div>
        {#if panel === "caption"}<section class="caption-inspector">
            <h2>Caption cue</h2>
            <p>Cue {lines.length ? cue + 1 : 0} of {lines.length}</p>
            {#if lines.length && length}
              <fieldset>
                <legend>Text</legend><label
                  ><span class="sr-only">Caption text</span><textarea
                    rows="2"
                    value={lines[cue]}
                    onchange={(e) => changeLine(e.currentTarget.value)}></textarea></label
                >
              </fieldset>
              <fieldset>
                <legend>Timing</legend>
                <div class="split-fields">
                  <label
                    >In<input
                      value={timecode(bounds[cue]! / 30)}
                      disabled={cue === 0}
                      onchange={(e) => trim(cue, e.currentTarget)}
                    /></label
                  ><label
                    >Out<input
                      value={timecode(bounds[cue + 1]! / 30)}
                      disabled={cue === lines.length - 1}
                      onchange={(e) => trim(cue + 1, e.currentTarget)}
                    /></label
                  >
                </div>
              </fieldset>
              <fieldset>
                <legend>Typography</legend><label
                  >Font family<select bind:value={font}
                    ><option>System sans</option><option>Serif</option><option>Monospace</option></select
                  ></label
                >
                <div class="split-fields">
                  <label
                    >Weight<select bind:value={weight}
                      ><option value="400">Regular</option><option value="600">Semibold</option><option
                        value="700">Bold</option
                      ></select
                    ></label
                  ><label
                    >Size<select bind:value={size}
                      >{#each [36, 44, 52, 64] as px (px)}<option value={px}>{px} px</option>{/each}</select
                    ></label
                  >
                </div>
              </fieldset>
              <fieldset>
                <legend>Placement</legend><select aria-label="Caption placement" bind:value={place}
                  ><option>Bottom centre</option><option>Top centre</option></select
                >
              </fieldset>
              <button type="button" disabled={totalFrames < lines.length} onclick={exportCaptions}
                >Export captions (.vtt)</button
              >
            {:else}<p>Add script lines and a duration in the commission brief.</p>{/if}
          </section>{:else}
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
              <span>One cue per line</span><span
                >{Array.from(script).length.toLocaleString("en")} / 8,000</span
              >
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
        {/if}{/if}
    </aside>
  </div>
</section>

<style>
  .studio {
    width: 100%;
    min-width: 0;
    margin: 0;
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
    grid-template-columns: minmax(0, 1fr) min(var(--panel-width), 38%);
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

  .studio {
    min-height: 100%;
    background: var(--color-void);
  }
  .studio-header {
    height: 46px;
    padding: 0.3rem 1.1rem;
    background: #19161f;
  }
  .studio-header nav a,
  .inspect-tabs {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .cut-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.65rem;
    margin-bottom: 0.9rem;
  }
  .cut-title h1 {
    font-size: clamp(1.5rem, 2.3vw, 2rem);
  }
  .cut-title p,
  .caption-inspector > p {
    color: var(--color-ash);
    font-size: 12px;
    margin: 0.3rem 0;
  }
  .modes,
  .inspect-tabs {
    display: flex;
    gap: 2px;
  }
  .modes {
    border: 1px solid var(--color-engraving);
    border-radius: 5px;
    padding: 2px;
  }
  .modes button,
  .inspect-tabs button {
    border: 0;
    background: transparent;
  }
  button[aria-pressed="true"],
  .inspect-tabs button[aria-pressed="true"] {
    background: #41344e;
    color: #f4eafa;
  }
  .editing-field {
    padding: clamp(0.65rem, 1.4vw, 1.4rem);
  }
  .brief-panel {
    position: relative;
    align-self: stretch;
    background: #1c1921;
    min-height: calc(100dvh - 47px);
  }
  .studio.panel-folded .studio-grid {
    grid-template-columns: minmax(0, 1fr) 0;
  }
  .seam {
    position: absolute;
    z-index: 6;
    right: 100%;
    top: 48%;
    padding: 0.1rem 0.2rem;
    min-width: 0.85rem;
    color: var(--color-ash);
    background: var(--color-obsidian);
  }
  .inspect-tabs {
    border-bottom: 1px solid var(--color-engraving);
    padding: 0.4rem 0.8rem;
  }
  .inspect-tabs a {
    font-size: 11px;
    margin-left: auto;
  }
  .caption-inspector {
    padding: 1rem;
  }
  .caption-inspector > h2,
  .timeline h2,
  .review h2 {
    font: 500 1.6rem/1.2 var(--font-rune);
  }
  .caption-inspector fieldset {
    border: 0;
    border-block-start: 1px solid var(--color-engraving);
    margin: 0.9rem 0;
    padding: 0.8rem 0 0.15rem;
  }
  .caption-inspector legend {
    font: 600 12px var(--font-body);
    padding-right: 0.6rem;
  }
  .caption-inspector label,
  .split-fields label {
    display: grid;
    gap: 0.3rem;
    font-size: 11px;
    color: var(--color-ash);
  }
  .split-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    margin: 0.4rem 0;
  }
  .caption.top {
    inset-block: 10% auto;
  }
  .audio-tracks {
    display: grid;
    grid-template-columns: 43px minmax(0, 1fr);
    align-items: center;
    gap: 3px 7px;
    padding: 0 11px 8px;
  }
  .tracks {
    padding-bottom: 4px;
  }
  .screen img {
    object-fit: contain;
  }
  .picture-strip button {
    height: 100%;
    min-width: 0;
    overflow: hidden;
    text-align: start;
    border: 0;
    border-inline-end: 2px solid #100f16;
    border-radius: 0;
    background:
      linear-gradient(0deg, #17131bbd, transparent),
      var(--plate) center/cover;
  }
  .picture-strip button[aria-pressed="true"] {
    outline: 1px solid var(--color-frost);
    outline-offset: -1px;
  }
  .picture-strip span {
    margin: 0;
    padding: 0;
    background: transparent;
  }
  .cue-strip button {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .shot-bin {
    padding: 0.75rem 0.2rem;
    border-top: 1px solid var(--color-engraving);
    margin-top: 1rem;
    overflow: auto;
    min-height: 0;
  }
  .shot-bin h2 {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin: 0 0.2rem 0.4rem;
    font: 600 12px var(--font-body);
  }
  .shot-bin small {
    color: var(--color-ash);
    font: 10px var(--font-glyph);
  }
  .shot-bin button {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 0.45rem;
    text-align: left;
    padding: 0.35rem;
    border: 0;
    background: transparent;
  }
  .shot-bin button[aria-pressed="true"] {
    background: #38303e;
  }
  .shot-bin img {
    width: 33px;
    height: 27px;
    object-fit: cover;
    border-radius: 3px;
  }
  .shot-bin button span {
    min-width: 0;
    display: grid;
  }
  .shot-bin button strong {
    font-size: 11px;
  }
  .board {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.6rem;
  }
  .board button {
    display: grid;
    text-align: left;
    gap: 0.3rem;
    padding: 0.45rem;
  }
  .board img {
    width: 100%;
    aspect-ratio: 16/9;
    object-fit: cover;
  }
  .board small {
    color: var(--color-ash);
  }
  .review {
    padding: 1rem;
    border: 1px solid var(--color-engraving);
    border-radius: 5px;
  }
  .review dt {
    color: var(--color-ash);
  }
  .review dl {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.4rem 1rem;
  }
  .review dd {
    margin: 0;
  }
  .review a {
    font-size: 12px;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  @container work-area (max-width:720px) {
    .studio-grid {
      display: flex;
      flex-direction: column;
    }
    .brief-panel {
      min-height: 0;
    }
    .seam {
      position: static;
    }
    .cut-title {
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .studio-header {
      height: auto;
    }
  }
</style>
