<script lang="ts">
  import { Handle, NodeToolbar, Position, type Node, type NodeProps } from "@xyflow/svelte";
  import { onDestroy } from "svelte";
  import type { GraphNode } from "$lib/graph/model";
  type OrbData = { semantic: GraphNode; select: (id: string, opener: HTMLElement, pointer?: boolean) => void };
  let { data, selected, dragging }: NodeProps<Node<OrbData>> = $props();
  let preview = $state(false);
  let closeTimer: ReturnType<typeof setTimeout> | undefined;
  const previewId = $props.id();
  let folded = $derived(data.semantic.kind === "run" ? data.semantic.members !== undefined : !!data.semantic.members?.length);
  let glyph = $derived.by(() => {
    switch (data.semantic.kind) {
      case "run": return "◉";
      case "tool": return "⌘";
      case "dispatch": return "↗";
      case "delegate": return "↗";
      case "peer": return "⊙";
      case "animator": return data.semantic.label.slice(0, 1).toUpperCase();
      case "gate": return "◇";
      case "terminal": return "■";
      case "gap": case "unknown": return "?";
      case "event": return "·";
      case "occurrence": return "↻";
      default: return data.semantic.label.slice(0, 1).toUpperCase();
    }
  });
  function showPreview() { clearTimeout(closeTimer); preview = true; }
  function hidePreview() { clearTimeout(closeTimer); closeTimer = setTimeout(() => preview = false, 120); }
  function dismiss(event: KeyboardEvent) { if (event.key === "Escape") { clearTimeout(closeTimer); preview = false; } }
  onDestroy(() => clearTimeout(closeTimer));
</script>

<Handle type="target" position={Position.Left} id="in" isConnectable={false} style="top:24px;left:43px" />
<Handle type="source" position={Position.Right} id="out" isConnectable={false} style="top:24px;right:43px" />
<Handle type="target" position={Position.Top} id="loop-in" isConnectable={false} style="left:55px;top:3px" />
<Handle type="source" position={Position.Top} id="loop-out" isConnectable={false} style="left:73px;top:3px" />
<button type="button" class={["orb-node orb-drag-handle nopan", { chosen: selected, folded, dragging }]}
  data-kind={data.semantic.kind} data-state={data.semantic.state} data-attention={data.semantic.attention}
  style:--node-accent={`var(--color-${data.semantic.accent ?? "rune"})`}
  aria-label={`${folded ? "Expand" : "Inspect"} ${data.semantic.label} · ${data.semantic.kind}${data.semantic.attention ? ` · ${data.semantic.attention === "cursor" ? "At playback cursor" : "Latest record"}` : ""}`}
  aria-pressed={selected} aria-describedby={preview && !dragging ? previewId : undefined}
  onpointerenter={showPreview} onpointerleave={hidePreview} onfocus={showPreview} onblur={hidePreview} onkeydown={dismiss}
  onclick={(event) => data.select(data.semantic.id, event.currentTarget, event.detail !== 0)}>
  <span class="orb-mark" aria-hidden="true"><span>{glyph}</span>{#if folded}<i>+</i>{/if}</span>
  <span class="orb-name">{data.semantic.label}</span>
  {#if data.semantic.attention}<span class="orb-caption attention">{data.semantic.attention === "cursor" ? "Playback cursor" : "Latest record"}</span>
  {:else if folded}<span class="orb-caption">{data.semantic.kind === "run" ? "Run" : data.semantic.kind}{#if data.semantic.count != null} · {data.semantic.count} loaded{/if}</span>
  {:else}<span class="orb-caption">{data.semantic.kind}{#if data.semantic.entry} · entry{/if}</span>{/if}
</button>
<NodeToolbar isVisible={preview && !dragging} position={Position.Top} offset={14}
  onpointerenter={showPreview} onpointerleave={hidePreview}>
  <div class="orb-preview" id={previewId} role="tooltip">
    <strong>{data.semantic.label}</strong>
    <span>{data.semantic.kind}{data.semantic.state ? ` · last recorded: ${data.semantic.state}` : ""}</span>
    <span>{data.semantic.detail}</span>
    {#if data.semantic.attention}<span class="attention">{data.semantic.attention === "cursor" ? "At playback cursor" : "Latest loaded record"}</span>{/if}
    <code>{data.semantic.id}</code>
    <small>Drag to arrange locally · {folded ? "Click to expand" : "Click to inspect"}</small>
  </div>
</NodeToolbar>

<style>
  .orb-node { width:128px; height:84px; display:flex; flex-direction:column; align-items:center; gap:5px; position:relative; padding:3px 0 0; border:0; background:transparent; color:var(--color-parchment); cursor:grab; text-align:center; touch-action:none; transform:scale(var(--orb-ui-scale,1)); transform-origin:64px 24px; pointer-events:none; }
  .orb-mark { pointer-events:auto; width:40px; height:40px; flex:none; display:grid; place-items:center; position:relative; border:1px solid color-mix(in srgb,var(--node-accent) 38%,var(--color-engraving)); border-radius:50%; background:color-mix(in srgb,var(--node-accent) 5%,var(--color-obsidian)); color:var(--color-ash); font:13px var(--font-glyph); transition:background-color 120ms,border-color 120ms,box-shadow 120ms; }
  .orb-mark > span { position:relative; z-index:1; }
  .orb-name { max-width:128px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font:12px/1.25 var(--font-body); visibility:var(--orb-name-visibility,visible); }
  .orb-caption { max-width:128px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--color-ash); font:9px/1.2 var(--font-body); letter-spacing:.045em; visibility:var(--orb-caption-visibility,visible); }
  .orb-node[data-kind="run"] .orb-name,.orb-node[data-kind="animator"] .orb-name,
  .orb-node:hover .orb-name,.orb-node:focus-visible .orb-name,.orb-node[data-attention] .orb-name { visibility:visible; }
  .orb-node[data-kind="run"] .orb-caption,.orb-node[data-kind="animator"] .orb-caption,.orb-caption.attention { visibility:visible; }
  .orb-node[data-kind="run"] .orb-mark { width:48px; height:48px; margin-top:-4px; margin-bottom:-4px; background:color-mix(in srgb,var(--color-primary) 7%,var(--color-obsidian)); box-shadow:0 0 0 9px color-mix(in srgb,var(--color-primary) 3%,transparent); color:var(--color-primary); }
  .orb-node.folded[data-kind="run"] .orb-mark::before { content:""; position:absolute; inset:5px; border:1px dashed color-mix(in srgb,var(--color-primary) 25%,transparent); border-radius:50%; }
  .orb-node[data-kind="tool"] .orb-mark { width:44px; height:30px; margin:5px 0; border-radius:5px; border-color:var(--color-tertiary-edge); color:var(--color-parchment); background:var(--color-tertiary); }
  .orb-node[data-kind="delegate"] .orb-mark { border-style:double; border-width:3px; }
  .orb-node[data-kind="peer"] .orb-mark { box-shadow:inset 0 0 0 4px var(--color-obsidian),inset 0 0 0 5px var(--color-engraving); }
  .orb-node[data-kind="terminal"] .orb-mark { border-radius:4px; }
  .orb-node[data-kind="dispatch"] .orb-mark { border-radius:11px 3px 11px 3px; border-color:var(--color-tertiary-edge); background:color-mix(in srgb,var(--color-tertiary) 70%,var(--color-obsidian)); }
  .orb-node[data-kind="gate"] .orb-mark,.orb-node[data-kind="animator"] .orb-mark { width:32px; height:32px; margin:4px; border-radius:7px; transform:rotate(45deg); border-color:var(--color-tertiary-edge); }
  .orb-node[data-kind="gate"] .orb-mark > span,.orb-node[data-kind="animator"] .orb-mark > span { transform:rotate(-45deg); }
  .orb-node[data-kind="gap"] .orb-mark,.orb-node[data-kind="unknown"] .orb-mark { border-style:dashed; background:transparent; }
  .orb-node[data-kind="event"] .orb-mark { width:28px; height:28px; margin:6px; border-radius:4px; }
  .orb-node[data-kind="occurrence"] .orb-mark { width:32px; height:32px; margin:4px; border-style:dotted; }
  .orb-mark i { position:absolute; right:-4px; bottom:-3px; width:14px; height:14px; display:grid; place-items:center; border:1px solid var(--color-engraving); border-radius:50%; background:var(--color-obsidian); color:var(--color-parchment); font:10px var(--font-body); font-style:normal; }
  .orb-node:hover .orb-mark { border-color:var(--node-accent); color:var(--color-bone); background:color-mix(in srgb,var(--node-accent) 12%,var(--color-obsidian)); }
  .orb-node.chosen .orb-mark,.orb-node:focus-visible .orb-mark { outline:2px solid var(--color-primary); outline-offset:4px; }
  .orb-node:focus-visible { outline:none; }
  .orb-node[data-attention] .orb-mark { border-color:var(--node-accent); color:var(--color-bone); background:color-mix(in srgb,var(--node-accent) 22%,var(--color-obsidian)); box-shadow:0 0 18px 4px color-mix(in srgb,var(--node-accent) 22%,transparent),0 0 0 5px color-mix(in srgb,var(--node-accent) 6%,transparent); }
  .orb-node[data-state="failed"] .orb-mark,.orb-node[data-state="error"] .orb-mark { border-color:var(--color-ember); }
  .attention { color:var(--color-primary); }
  .orb-node.dragging { cursor:grabbing; }
  .orb-preview { max-width:min(310px,75vw); padding:13px 15px; display:flex; flex-direction:column; gap:6px; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-obsidian); color:var(--color-bone); box-shadow:0 6px 30px var(--color-void); font:12px/1.4 var(--font-body); overflow-wrap:anywhere; }
  .orb-preview span,.orb-preview code { color:var(--color-parchment); }
  .orb-preview code,.orb-preview small { font-size:10px; color:var(--color-ash); }
  .orb-preview .attention { color:var(--color-primary); }
  @media(prefers-reduced-motion:reduce) { .orb-mark { transition:none; } }
</style>
