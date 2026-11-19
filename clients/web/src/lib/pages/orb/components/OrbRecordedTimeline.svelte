<script lang="ts">
  import type { recordedTimeline } from "../state/recorded-timeline";
  import { durationLabel } from "../state/orb-evidence";
  let { data, cursor, onseek, onlive, onrecord, onhistory }: {
    data: ReturnType<typeof recordedTimeline>;
    cursor: number | null;
    onseek: (time: number) => void;
    onlive: () => void;
    onrecord: (run: string, event: string, opener: HTMLElement) => void;
    onhistory: () => void;
  } = $props();
  let open = $state(true);
  let playing = $state(false);
  const uid = $props.id();
  const first = $derived(data.times[0] ?? 0);
  const last = $derived(data.times.at(-1) ?? first);
  const current = $derived(cursor ?? last);
  const previous = $derived(data.times.findLast(t => t < current));
  const next = $derived(data.times.find(t => t > current));
  const position = (t: number) => last > first ? Math.min(100, Math.max(0, (t-first)/(last-first)*100)) : 0;
  const clock = (t: number) => {
    const elapsed = Math.max(0, Math.round(t-first));
    if (last > first && last-first < 1000) return elapsed + "ms";
    const sec = Math.floor(elapsed/1000);
    return `${Math.floor(sec/60).toString().padStart(2,"0")}:${(sec%60).toString().padStart(2,"0")}`;
  };
  function seek(time: number) { playing = false; onseek(time); }
  function play() {
    if (playing) { playing = false; return; }
    if (next === undefined) onseek(first);
    playing = true;
  }
  $effect(() => {
    if (!playing || cursor === null || next === undefined) return;
    const target = next;
    const timer = window.setTimeout(() => {
      if (target === data.times.at(-1)) playing = false;
      onseek(target);
    }, Math.min(2147483647, Math.max(16,target-current)));
    return () => window.clearTimeout(timer);
  });
</script>

<section class="recorded-timeline" aria-label="Recorded Run timeline">
  <header>
    <button class="fold" type="button" aria-expanded={open} aria-controls={uid} onclick={()=>open=!open}><span aria-hidden="true">☷</span> Timeline <span aria-hidden="true">{open ? "⌄" : "›"}</span></button>
    <span class="legend"><i></i> Task <b>◆</b> Record</span>
    <button class="history" type="button" onclick={onhistory} title="Open the history of captures received in this tab">Tab history</button>
    <div class="transport" role="group" aria-label="Recorded time playback">
      <button aria-label="Previous recorded time" title="Previous recorded time" disabled={previous === undefined} onclick={()=>previous !== undefined && seek(previous)}>‹</button>
      <button aria-label={playing ? "Pause recorded playback" : "Play recorded timeline"} title={playing ? "Pause" : "Play"} aria-pressed={playing} disabled={data.times.length < 2} onclick={play}>{playing ? "Ⅱ" : "▷"}</button>
      <button aria-label="Next recorded time" title="Next recorded time" disabled={next === undefined} onclick={()=>next !== undefined && seek(next)}>›</button>
      <output aria-label="Elapsed recorded time">{clock(current)}</output>
      <button class="live" aria-pressed={cursor === null} onclick={()=>{playing=false;onlive();}}>Live</button>
    </div>
  </header>
  {#if open}
    <div id={uid} class="lanes">
      <div class="row ruler">
        <span>Elapsed</span>
        <div class="axis">
          <div class="ticks" aria-hidden="true">{#each [0,.25,.5,.75,1] as fraction (fraction)}<span>{clock(first+(last-first)*fraction)}</span>{/each}</div>
          <input type="range" aria-label="Seek recorded time" aria-valuetext={clock(current)} min={0} max={last-first} step="1" value={current-first} disabled={data.times.length < 2} oninput={e=>seek(first+Number(e.currentTarget.value))}/>
        </div>
      </div>
      {#each data.rows as row (row.run.run_id)}
        <div class="row">
          <span class="run" title={row.run.run_id}>{row.run.workflow_name}</span>
          <div class="lane" role="group" aria-label={`${row.run.workflow_name} recorded events`} style:min-height={`${row.lanes*1.4}rem`}>
            {#each row.spans as span (span.record.event_id)}
              <button class="span" title={`${span.label} · ${durationLabel(span.to-span.from)}`} aria-label={`${span.label} · ${durationLabel(span.to-span.from)}`} style:left={position(span.from)+"%"} style:width={(position(span.to)-position(span.from))+"%"} style:top={span.lane*1.4+"rem"} onclick={e=>{seek(span.to);onrecord(row.run.run_id,span.record.event_id,e.currentTarget);}}>{span.label} <small>{durationLabel(span.to-span.from)}</small></button>
            {/each}
            {#each row.marks as mark (mark.record.event_id)}
              <button class="mark" title={mark.record.summary} aria-label={mark.record.summary} style:left={position(mark.at)+"%"} onclick={e=>{seek(mark.at);onrecord(row.run.run_id,mark.record.event_id,e.currentTarget);}}>◆</button>
            {/each}
            <i class="playhead" style:left={position(current)+"%"} aria-hidden="true"></i>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .recorded-timeline { flex:none; min-width:0; border-top:1px solid var(--color-engraving); background:var(--color-obsidian); color:var(--color-parchment); font:.76rem/1.4 var(--font-body); }
  header,.transport,.legend,.fold { display:flex; align-items:center; }
  header { min-height:2.7rem; padding:.25rem 1rem; gap:1rem; }
  button { border:1px solid transparent; border-radius:4px; background:transparent; color:inherit; padding:.22rem .44rem; font:inherit; cursor:pointer; }
  button:hover,button:focus-visible { color:var(--color-bone); background:var(--color-obsidian-2); }
  button:focus-visible,input:focus-visible { outline:2px solid var(--color-rune); outline-offset:1px; }
  button:disabled { opacity:.35; cursor:default; }
  .fold { gap:.45rem; font-weight:600; color:var(--color-bone); }
  .legend { gap:.35rem; color:var(--color-ash); font:.64rem var(--font-glyph); }
  .legend i { width:.65rem; height:.35rem; border-radius:2px; background:var(--color-accent); }
  .legend b { margin-left:.3rem; font-size:.58rem; }
  .history { margin-right:auto; color:var(--color-ash); font-size:.7rem; }
  .transport { gap:.2rem; white-space:nowrap; }
  output,.ticks,.ruler>span { color:var(--color-ash); font:.68rem var(--font-glyph); }
  output { padding:0 .4rem; }
  .transport>button { min-width:1.65rem; }
  .live { border-color:var(--color-engraving); }
  .live[aria-pressed="true"] { color:var(--color-lich); background:color-mix(in srgb,var(--color-lich) 9%,transparent); }
  .live::before { content:""; display:inline-block; width:.35em; height:.35em; margin-right:.4em; border-radius:50%; background:currentColor; vertical-align:middle; }
  .lanes { max-height:8.5rem; overflow-y:auto; padding:0 1.2rem .6rem; scrollbar-width:thin; }
  .row { display:grid; grid-template-columns:clamp(5rem,14%,12rem) minmax(0,1fr); gap:.75rem; align-items:start; padding:.2rem 0; }
  .ruler { align-items:center; }
  .ruler>span { text-transform:uppercase; letter-spacing:.07em; }
  .run { padding-inline-start:.45rem; border-inline-start:2px solid var(--color-accent); text-overflow:ellipsis; white-space:nowrap; overflow:hidden; }
  .row:nth-child(2n+1) .run { border-inline-start-color:var(--color-primary); }
  .axis { min-width:0; }
  .ticks { display:flex; justify-content:space-between; gap:.2rem; font-size:.6rem; }
  input { display:block; width:100%; height:.68rem; margin:0; accent-color:var(--color-accent); cursor:pointer; }
  .lane { position:relative; margin-inline:.35rem; background:repeating-linear-gradient(to right,var(--color-engraving) 0 1px,transparent 1px 25%); }
  .lane button { position:absolute; white-space:nowrap; z-index:1; }
  .span { min-width:4px; overflow:hidden; text-overflow:ellipsis; height:1.2rem; text-align:left; padding:0 .25rem; background:color-mix(in srgb,var(--color-accent) 17%,var(--color-obsidian)); border-inline-start:2px solid var(--color-accent); font:.66rem/1 var(--font-body); }
  .span small { color:var(--color-ash); }
  .mark { bottom:0; transform:translateX(-50%); padding:0 .1rem; color:var(--color-accent); font:.7rem/1.4rem var(--font-glyph); }
  .playhead { position:absolute; inset-block:0; width:1px; background:var(--color-ash); pointer-events:none; }
  @container work-area (max-width:42rem) { header { padding:.25rem .45rem; gap:.2rem; flex-wrap:wrap; } .legend { display:none; } .lanes{padding-inline:.55rem;} .row{gap:.35rem;} }
</style>
