<script lang="ts">
  import { tick } from "svelte";
  import { FIELD_HISTORY_WINDOWS, fieldFrameAt, type FieldFrame } from "$lib/orb/field-history";

  let {
    frames, cursorId, onseeking, onlive, onpause, windowSeconds = 90, onwindowchange,
    connectionLabel = "Transport status unavailable"
  }: {
    frames: readonly FieldFrame[];
    cursorId: number | null;
    onseeking: (id: number) => void;
    onlive: () => void;
    onpause?: () => void;
    windowSeconds?: number;
    onwindowchange?: (seconds: number) => void;
    connectionLabel?: string;
  } = $props();
  let speed = $state(1);
  interface PlaybackSession { readonly expectedId: number; cancelled: boolean; readonly pending?: boolean }
  let playback = $state.raw<PlaybackSession | null>(null);
  interface DragBounds { readonly min: number; readonly max: number; cancelled: boolean }
  let dragBounds = $state.raw<DragBounds | null>(null);
  let dragValue = $state<number | null>(null);
  let first = $derived(frames[0]);
  let latest = $derived(frames.at(-1));
  let index = $derived(cursorId === null ? frames.length - 1 : frames.findIndex((frame) => frame.id === cursorId));
  let selected = $derived(index >= 0 ? frames[index] : undefined);
  let next = $derived(index >= 0 ? frames[index + 1] : frames[0]);
  let pinned = $derived(cursorId !== null && index < 0);
  let playing = $derived(playback !== null && !playback.cancelled && !playback.pending && playback.expectedId === cursorId && !!selected && !!next);
  let span = $derived(first && latest ? latest.observedAt - first.observedAt : 0);
  let dragging = $derived(!!first && !!dragBounds && !dragBounds.cancelled);
  let rangeStart = $derived(dragging ? dragBounds!.min : first?.observedAt ?? 0);
  let rangeEnd = $derived(dragging ? dragBounds!.max : latest?.observedAt ?? 0);
  let rangeMax = $derived(Math.max(0, rangeEnd - rangeStart));
  let rangeValue = $derived(Math.max(0, Math.min(rangeMax, (dragging ? dragValue ?? rangeStart : selected?.observedAt ?? rangeStart) - rangeStart)));
  let rows = $derived.by(() => {
    const runs = new Map<string, { id: string; name: string; marks: FieldFrame[] }>();
    for (const frame of frames) {
      for (const run of frame.runs) {
        const row = runs.get(run.run_id) ?? { id: run.run_id, name: run.workflow_name, marks: [] };
        row.name = run.workflow_name; runs.set(run.run_id, row);
      }
      for (const id of frame.changedRunIds) runs.get(id)?.marks.push(frame);
    }
    return [...runs.values()];
  });

  // This effect owns only an external timer. Input replacement cancels its pending
  // callback; user actions and timer callbacks own cursor/playback state changes.
  $effect(() => {
    const session = playback;
    const from = selected;
    const to = next;
    if (!session || session.cancelled || session.pending) return;
    if (cursorId !== session.expectedId || !from) { session.cancelled = true; return; }
    if (!to) return;
    const delay = Math.max(16, (to.observedAt - from.observedAt) / speed);
    const timer = window.setTimeout(() => {
      if (session.cancelled || playback !== session || cursorId !== from.id) return;
      const currentIndex = frames.findIndex((frame) => frame.id === from.id);
      if (currentIndex < 0 || frames[currentIndex + 1]?.id !== to.id) { playback = null; return; }
      onseeking(to.id);
      void tick().then(() => {
        if (playback !== session || cursorId !== to.id) return;
        playback = frames.at(-1)?.id === to.id ? null : { expectedId: to.id, cancelled: false };
      });
    }, delay);
    return () => window.clearTimeout(timer);
  });

  // A cleared authority scope invalidates only numeric gesture bounds. No Run or
  // lens snapshot is retained by the pointer interaction.
  $effect(() => { if (!frames.length && dragBounds) dragBounds.cancelled = true; });

  function beginDrag() {
    if (!first || !latest) return;
    dragBounds = { min: first.observedAt, max: latest.observedAt, cancelled: false };
    dragValue = selected?.observedAt ?? latest.observedAt;
    pause();
  }
  function endDrag() { dragBounds = null; dragValue = null; }
  function seek(id: number) { playback = null; onseeking(id); }
  function live() { playback = null; onlive(); }
  function pause() {
    playback = null;
    if (cursorId === null) {
      if (onpause) onpause();
      else if (latest) onseeking(latest.id);
    }
  }
  function play() {
    if (playing) { pause(); return; }
    if (!frames.length) return;
    const start = cursorId === null || !selected || !next ? first : selected;
    if (!start) return;
    const session: PlaybackSession = { expectedId: start.id, cancelled: false, pending: true };
    playback = session;
    onseeking(start.id);
    void tick().then(() => {
      if (playback !== session || cursorId !== start.id) return;
      playback = { expectedId: start.id, cancelled: false };
    });
  }
  function changeSpeed(value: number) {
    speed = value;
    if (playing && playback) playback = { expectedId: playback.expectedId, cancelled: false };
  }
  function seekTime(value: number) {
    const observedAt = rangeStart + value;
    if (dragging) dragValue = observedAt;
    const frame = fieldFrameAt(frames, observedAt);
    if (frame) seek(frame.id);
  }
  function position(time: number): number { return first && span > 0 ? (time - first.observedAt) / span * 100 : 50; }
  function clock(time: number): string { return new Date(time).toLocaleTimeString(undefined, { hour12: false }); }
  function duration(milliseconds: number): string { return milliseconds < 1000 ? `${Math.round(milliseconds)}ms` : `${(milliseconds / 1000).toFixed(1)}s`; }
  function shortId(id: string): string { return id.length <= 12 ? id : `${id.slice(0, 8)}…${id.slice(-4)}`; }
</script>

<svelte:window onpointerup={endDrag} onpointercancel={endDrag} />

<section class="orb-timeline" aria-label="Tab observation history">
  <div class="timeline-heading">
    <div class="title"><strong>Tab history</strong><span>observed updates · cleared on reload</span></div>
    <div class="transport"><span>Current transport:</span> {connectionLabel}</div>
    <details class="coverage-help"><summary>Coverage</summary><p>Captures contain served projections received in this browser tab. Marks show changed Run metadata, evidence or declared scores at local receipt time. They do not establish producer order, execution duration or a complete trace. Pausing freezes the field while incoming updates continue. Retention is bounded to 300 captures and the selected window from the latest capture; widening it cannot restore discarded captures.</p></details>
  </div>
  <div class="timeline-controls">
    <div role="group" aria-label="Tab history playback" class="playback-controls">
      <button type="button" class={["live", { active: cursorId === null }]} aria-pressed={cursorId === null} onclick={live}>LIVE</button>
      <button type="button" aria-label="Previous capture" disabled={frames.length < 2 || index <= 0} onclick={() => { const previous = frames[index - 1]; if (previous) seek(previous.id); }}>←</button>
      <button type="button" aria-label={playing ? "Pause playback" : "Play captured updates"} aria-pressed={playing} disabled={frames.length < 2} onclick={play}>{playing ? "Ⅱ Pause" : "▶ Play"}</button>
      <button type="button" aria-label="Pause live field" disabled={cursorId !== null || !latest} onclick={pause}>Ⅱ</button>
      <button type="button" aria-label="Next capture" disabled={!next} onclick={() => { if (next) seek(next.id); }}>→</button>
      <label class="speed"><span class="visually-hidden">Playback speed</span><select aria-label="Playback speed" value={speed} onchange={(event) => changeSpeed(Number(event.currentTarget.value))}><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option></select></label>
    </div>
    <p class="cursor" role="status">{pinned ? "Pinned capture outside window" : cursorId === null ? "Following latest capture" : `Capture ${cursorId} · ${selected ? clock(selected.observedAt) : "unavailable"}`}</p>
    <label class="window">Retain <select aria-label="Tab history retention window" value={windowSeconds} disabled={!onwindowchange} onchange={(event) => { playback = null; onwindowchange?.(Number(event.currentTarget.value)); }}>{#each FIELD_HISTORY_WINDOWS as seconds (seconds)}<option value={seconds}>{seconds < 60 ? `${seconds}s` : `${seconds / 60}m`}</option>{/each}</select></label>
  </div>
  <div class="seek-line">
    <span>{first ? clock(first.observedAt) : "No captures"}</span>
    <input type="range" aria-label="Seek tab observation time" aria-valuetext={pinned ? "Pinned capture outside retained window" : selected ? `Capture ${selected.id}, observed ${clock(selected.observedAt)}` : "No captures"} min={0} max={rangeMax} step={1} value={rangeValue} disabled={frames.length < 2} onpointerdown={beginDrag} onblur={endDrag} oninput={(event) => seekTime(Number(event.currentTarget.value))} />
    <span>{latest ? clock(latest.observedAt) : "—"}</span>
    <span class="available">{frames.length} capture{frames.length === 1 ? "" : "s"} · {duration(span)} available</span>
  </div>
  <div class="run-tracks" aria-label="Observed Run updates">
    {#each rows as row (row.id)}
      <div class="run-track">
        <span class="run-label" title={`${row.name} · ${row.id}`}>{row.name} <code>{shortId(row.id)}</code></span>
        <div class="marks" role="group" aria-label={`${row.name} · ${row.id} observed updates`}>
          {#each row.marks as frame (frame.id)}
            <button type="button" class={["mark", { selected: cursorId === frame.id }]} style:left={`${position(frame.observedAt)}%`} aria-label={`${row.name} · ${shortId(row.id)} · capture ${frame.id} · observed ${clock(frame.observedAt)}`} title={`Capture ${frame.id} · observed ${clock(frame.observedAt)}`} onclick={() => seek(frame.id)}></button>
          {/each}
        </div>
      </div>
    {/each}
  </div>
</section>

<style>
  .orb-timeline { position:relative; flex:none; min-width:0; padding:.55rem .8rem .45rem; border-block-start:1px solid var(--color-engraving); background:var(--color-void); color:var(--color-parchment); font:var(--text-xs)/1.4 var(--font-body); }
  .timeline-heading,.timeline-controls,.seek-line { display:flex; align-items:center; gap:.6rem; min-width:0; }
  .timeline-heading { margin-block-end:.35rem; }
  .title { display:flex; align-items:baseline; gap:.6rem; flex:1; min-width:0; }
  .title strong { color:var(--color-bone); font-weight:500; white-space:nowrap; }
  .title span,.transport { color:var(--color-ash); }
  .transport { font-size:var(--text-2xs); }
  .timeline-controls { flex-wrap:wrap; }
  .playback-controls { display:flex; align-items:center; gap:.2rem; }
  button,select { font:inherit; color:var(--color-parchment); border:1px solid var(--color-engraving); border-radius:var(--radius-glyph); background:var(--color-void); }
  button { min-height:30px; padding:.2rem .5rem; cursor:pointer; }
  button:hover:not(:disabled),select:hover:not(:disabled) { color:var(--color-rune); border-color:var(--color-rune-dim); }
  button:disabled,select:disabled { opacity:.45; cursor:default; }
  button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible { outline:2px solid var(--color-rune); outline-offset:2px; }
  .live { letter-spacing:.1em; font-weight:600; }
  .live.active { color:var(--color-rune); border-color:var(--color-rune-dim); }
  select { padding:.25rem; min-height:30px; }
  .cursor { margin:0; flex:1; color:var(--color-ash); font-size:var(--text-2xs); }
  .window { display:flex; align-items:center; gap:.35rem; color:var(--color-ash); }
  .seek-line { margin-block:.3rem .2rem; font-family:var(--font-glyph); font-size:var(--text-2xs); }
  input[type="range"] { flex:1; min-width:50px; height:20px; margin:0; accent-color:var(--color-rune); cursor:pointer; }
  .available { color:var(--color-ash); min-width:11rem; text-align:end; }
  .run-tracks { min-height:32px; max-height:68px; overflow-y:auto; scrollbar-width:thin; }
  .run-track { display:grid; grid-template-columns:minmax(9rem, 18%) 1fr; align-items:center; min-height:22px; gap:.6rem; }
  .run-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:var(--text-2xs); }
  code { color:var(--color-ash); font:inherit; font-family:var(--font-glyph); margin-inline-start:.3rem; }
  .marks { position:relative; height:20px; margin-inline:7px; border-block-end:1px solid var(--color-engraving); }
  .mark { position:absolute; transform:translateX(-50%); top:3px; width:9px; min-height:13px; padding:0; border-color:var(--color-tertiary-edge); border-radius:1px; background:var(--color-tertiary); }
  .mark.selected { background:var(--color-rune); border-color:var(--color-rune); }
  .mark:hover { width:13px; }
  .coverage-help summary { cursor:pointer; color:var(--color-rune); font-size:var(--text-2xs); }
  .coverage-help p { position:absolute; bottom:calc(100% - 2rem); right:.8rem; z-index:5; width:min(35rem, calc(100% - 1.6rem)); margin:0; padding:.75rem; border:1px solid var(--color-engraving); background:var(--color-obsidian); color:var(--color-parchment); line-height:1.6; box-shadow:0 0 0 1px var(--color-void); }
  .visually-hidden { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; }
  @media (max-width:800px) { .transport { display:none; } .title { flex-wrap:wrap; gap:.15rem .5rem; } .available { min-width:0; font-family:var(--font-body); } .seek-line>span:first-child,.seek-line>span:nth-of-type(2) { display:none; } }
  @media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none; transition:none; scroll-behavior:auto; } }
</style>
