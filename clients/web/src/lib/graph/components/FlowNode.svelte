<script lang="ts">
  import { Handle, NodeToolbar, Position, type Node, type NodeProps } from "@xyflow/svelte";
  import { onDestroy } from "svelte";
  import type { GraphNode } from "$lib/graph/model";
  type FlowData = { semantic: GraphNode; select: (id: string, opener: HTMLElement) => void };
  let { data, selected, type }: NodeProps<Node<FlowData>> = $props();
  let loom = $derived(type === "loom");
  const glyphs: Record<string,string> = { gate:"◇", router:"⑂", agent:"✦", object:"⬡", subflow:"▧", ledger:"▤", terminal:"■", delegate:"⑂", pattern:"▧", peer:"◎" };
  let preview = $state(false);
  let closeTimer: ReturnType<typeof setTimeout> | undefined;
  const previewId = $props.id();
  function showPreview() { clearTimeout(closeTimer); preview = true; }
  function hidePreview() { clearTimeout(closeTimer); closeTimer = setTimeout(() => preview = false, 180); }
  function dismiss(event: KeyboardEvent) { if (event.key === "Escape") { clearTimeout(closeTimer); preview = false; } }
  onDestroy(() => clearTimeout(closeTimer));
</script>

<Handle type="target" position={loom ? Position.Top : Position.Left} id="in" isConnectable={false} />
<Handle type="source" position={loom ? Position.Bottom : Position.Right} id="out" isConnectable={false} />
<Handle type="target" position={Position.Top} id="loop-in" isConnectable={false} style="left:30%" />
<Handle type="source" position={Position.Top} id="loop-out" isConnectable={false} style="left:70%" />
{#if loom}
  <Handle type="source" position={Position.Right} id="right-out" isConnectable={false} />
  <Handle type="target" position={Position.Right} id="right-in" isConnectable={false} />
  <Handle type="source" position={Position.Left} id="left-out" isConnectable={false} />
  <Handle type="target" position={Position.Left} id="left-in" isConnectable={false} />
{/if}
<button type="button" class={["flow-card nodrag nopan", { chosen: selected, loom }]}
  data-kind={data.semantic.kind} data-state={data.semantic.state}
  data-attention={data.semantic.attention} style={`--node-accent:var(--color-${data.semantic.accent ?? "rune"})`}
  aria-label={`${data.semantic.members ? "Expand" : "Inspect"} ${data.semantic.label}`} aria-pressed={selected}
  aria-describedby={preview ? previewId : undefined}
  onpointerenter={showPreview} onpointerleave={hidePreview} onfocus={showPreview} onblur={hidePreview} onkeydown={dismiss}
  onclick={(event) => data.select(data.semantic.id, event.currentTarget)}>
  <span class="node-kind"><span aria-hidden="true">{glyphs[data.semantic.kind] ?? "▣"}</span>{data.semantic.kind}{#if data.semantic.entry}<span class="entry">Entry</span>{/if}</span>
  <strong>{data.semantic.label}</strong>
  {#if data.semantic.attention}<span class="attention-label">{data.semantic.attention === "cursor" ? "At playback cursor" : "Latest record"}</span>{/if}
  {#if data.semantic.state || data.semantic.count != null}<span class="node-observation">{#if data.semantic.state}<span>{data.semantic.state}</span>{/if}{#if data.semantic.count != null}<span>{data.semantic.count} {data.semantic.kind === "pattern" ? "stations" : "loaded"}</span>{/if}</span>{/if}
</button>
<NodeToolbar isVisible={preview} position={Position.Top} offset={12}
  onpointerenter={showPreview} onpointerleave={hidePreview}>
  <div class="node-preview" id={previewId} role="tooltip">
    <strong>{data.semantic.label}</strong><span>{data.semantic.kind} · {data.semantic.detail}</span>
    <code>{data.semantic.id}</code>
  </div>
</NodeToolbar>

<style>
  .flow-card.loom { --station-ink:#c5bbd2; width:180px; min-height:56px; height:56px; gap:3px; padding:7px 12px;
    border:1px solid color-mix(in srgb,var(--station-ink) 34%,var(--color-engraving)); border-radius:7px;
    background:color-mix(in srgb,var(--station-ink) 9%, var(--color-void)); }
  .flow-card.loom[data-kind="object"],.flow-card.loom[data-kind="ledger"] { --station-ink:#94cdcf; }
  .flow-card.loom[data-kind="router"],.flow-card.loom[data-kind="gate"] { --station-ink:#e4bc7e; }
  .flow-card.loom[data-kind="agent"],.flow-card.loom[data-kind="step"] { --station-ink:#acbfdc; }
  .flow-card.loom .node-kind { color:var(--station-ink); font:10px var(--font-glyph); gap:5px; line-height:12px; }
  .flow-card.loom .node-kind > span:first-child { color:var(--station-ink); font-size:12px; }
  .flow-card.loom strong { font:600 13px/1.15 var(--font-body); display:-webkit-box; line-clamp:2; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .flow-card.loom .node-observation { display:none; }
  .flow-card.loom.chosen { outline:1px solid var(--station-ink); outline-offset:3px; }

  .flow-card { width:240px; min-height:142px; display:flex; flex-direction:column; gap:10px; padding:17px 18px; text-align:left; border:1px solid var(--color-engraving); border-top:2px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-obsidian); color:var(--color-bone); box-shadow:none; cursor:pointer; }
  .flow-card:hover { background:var(--color-obsidian-2); border-color:var(--color-rune-dim); }
  .flow-card.chosen, .flow-card:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  .node-kind { display:flex; gap:8px; align-items:center; font-size:11px; text-transform:uppercase; letter-spacing:.09em; color:var(--color-parchment); }
  .node-kind > span:first-child { color:var(--color-rune); font-size:16px; }
  .entry { margin-left:auto; font-size:10px; }
  strong { font-size:15px; line-height:1.4; overflow-wrap:anywhere; }
  .node-observation { display:flex; flex-wrap:wrap; gap:7px; font-size:11px; color:var(--color-frost); }
  .node-observation span { border:1px solid var(--color-engraving); border-radius:4px; padding:2px 6px; }
  .flow-card[data-kind="run"] { border-top-color:var(--color-primary); }
  .flow-card[data-state="failed"], .flow-card[data-state="error"] { border-top-color:var(--color-ember); }
  .flow-card[data-state="running"], .flow-card[data-state="entered"] { border-top-color:var(--color-lich); }
  .flow-card[data-kind="gate"] { border-top-color:var(--color-heat); }
  .flow-card:not(.loom)[data-kind="agent"] { width:142px; height:142px; margin-inline:49px; border-radius:50%; text-align:center; align-items:center; justify-content:center; }
  .flow-card[data-attention] { border-color:var(--node-accent); box-shadow:0 0 0 1px var(--node-accent); }
  .attention-label { color:var(--node-accent); font-size:11px; }
  .node-preview { width: min(290px,70vw); padding:14px 16px; display:flex; flex-direction:column; gap:8px; border:1px solid var(--color-rune-dim); border-radius:var(--radius-panel); background:var(--color-obsidian); color:var(--color-bone); box-shadow:0 8px 24px color-mix(in srgb,var(--color-void) 75%,transparent); font:12px/1.5 var(--font-body); overflow-wrap:anywhere; }
  .node-preview span,.node-preview code { color:var(--color-parchment); }
</style>
