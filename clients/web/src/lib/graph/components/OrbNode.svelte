<script lang="ts">
  import { Handle, NodeToolbar, Position, type Node, type NodeProps } from "@xyflow/svelte";
  import { onDestroy } from "svelte";
  import type { GraphNode } from "$lib/graph/model";

  type OrbData = { semantic: GraphNode; select: (id: string, opener: HTMLElement, pointer?: boolean) => void };
  let { data, selected, dragging }: NodeProps<Node<OrbData>> = $props();
  let preview = $state(false);
  let closeTimer: ReturnType<typeof setTimeout> | undefined;
  const previewId = $props.id();
  let item = $derived(data.semantic);
  let folded = $derived(item.kind === "run" ? item.members !== undefined : !!item.members?.length);
  let station = $derived(["step", "agent", "delegate", "node"].includes(item.kind));
  let runId = $derived((item.group ?? item.id).replace(/^run:/, "").slice(0, 8));
  let attention = $derived(item.attention === "cursor" ? "Playback cursor" : item.attention === "received" ? "New observation" : "Latest record");
  const symbols: Record<string, string> = {
    step: "M6 7h12v10H6z M3 12h3m12 0h3",
    agent: "M5 9h14v10H5z M12 4v5 M8 13h1m6 0h1 M9 16h6",
    delegate: "M5 17v-3q0-3 4-3h6 M5 7v7 M12 8l4 3-4 3 M17 5h3v3 M17 16h3v3",
    dispatch: "M5 4v5q0 3 4 3h9 M5 20v-4q0-4 4-4 M15 8l4 4-4 4",
    gate: "M12 3l8 3v5c0 4-3 7-8 10-5-3-8-6-8-10V6z M8 12l3 3 5-6",
    animator: "M5 7h14v10H5z M9 3v4m6-4v4m-6 10v4m6-4v4M2 10h3m14 0h3M2 14h3m14 0h3",
    tool: "M14 5a5 5 0 0 0-6 6l-5 5 3 3 5-5a5 5 0 0 0 6-6l-3 3-2-2 3-3",
    "Reach operation": "M8 5H4v15h15v-4 M11 4h9v9 M19 5l-9 9",
    peer: "M14 12a4 4 0 1 0-8 0a4 4 0 1 0 8 0 M17 6a7 7 0 0 1 0 12",
    terminal: "M6 6h12v12H6z",
    gap: "M8 8c0-5 9-5 9 0 0 3-5 4-5 7m0 3v1",
    event: "M5 5h14v14H5z M8 9h8m-8 4h5",
    occurrence: "M5 11a7 7 0 1 1 1 6 M5 5v6h6",
    status: "M3 13h4l3-7 4 12 3-6h4",
    done: "m4 12 5 5L20 6"
  };
  function showPreview() { clearTimeout(closeTimer); preview = true; }
  function hidePreview() { clearTimeout(closeTimer); closeTimer = setTimeout(() => preview = false, 120); }
  function dismiss(event: KeyboardEvent) { if (event.key === "Escape") { clearTimeout(closeTimer); preview = false; } }
  onDestroy(() => clearTimeout(closeTimer));
</script>

<Handle type="target" position={Position.Top} id="in" isConnectable={false} style="top:2px;left:50%" />
<Handle type="source" position={Position.Bottom} id="out" isConnectable={false} style={`top:${station ? 59 : item.kind === 'run' ? 38 : 34}px;bottom:auto;left:50%`} />
<Handle type="target" position={Position.Right} id="loop-in" isConnectable={false} style="left:63%;top:12px" />
<Handle type="source" position={Position.Right} id="loop-out" isConnectable={false} style="left:63%;top:25px" />
<div class="node-anchor">
  <button type="button" class={["orb-node orb-drag-handle nopan", { chosen: selected, folded, dragging, station }]}
    data-kind={item.kind} data-state={item.state} data-attention={item.attention}
    aria-label={`${folded ? "Expand" : "Inspect"} ${item.label} · ${item.kind}${item.attention ? ` · ${attention}` : ""}${item.annotation ? ` · ${item.annotation}` : ""}`}
    aria-pressed={selected} aria-describedby={preview && !dragging ? previewId : undefined}
    onpointerenter={showPreview} onpointerleave={hidePreview} onfocus={showPreview} onblur={hidePreview} onkeydown={dismiss}
    onclick={(event) => data.select(item.id, event.currentTarget, event.detail !== 0)}>
    {#if item.kind === "run"}
      <span class="run-dot" aria-hidden="true"></span>
      <span class="run-id">{runId}</span>
      <strong class="orb-name">{item.label}</strong>
      <span class="run-count">{item.count == null ? item.state ?? "Run" : `${item.count} record${item.count === 1 ? "" : "s"}`}</span>
      <svg class="run-focus" aria-hidden="true" viewBox="0 0 18 18"><path d="m9 2 7 7-7 7-7-7z"/><circle cx="9" cy="9" r="2"/></svg>
    {:else}
      <span class="orb-mark" aria-hidden="true">
        {#if item.icon}<img src={item.icon} alt="" width="20" height="20" />
        {:else}<svg viewBox="0 0 24 24"><path d={symbols[item.kind] ?? "M12 4l7 4v8l-7 4-7-4V8z"}/></svg>{/if}
      </span>
      <span class="orb-name">{item.label}</span>
      {#if folded}<span class="fold" aria-hidden="true">+</span>{/if}
      {#if item.attention}<span class="attention-dot" title={attention} aria-hidden="true"></span>{/if}
      {#if item.annotation}<span class="annotation">{item.annotation}</span>{/if}
    {/if}
  </button>
</div>
<NodeToolbar isVisible={preview && !dragging} position={Position.Top} offset={10}
  onpointerenter={showPreview} onpointerleave={hidePreview}>
  <div class="orb-preview" id={previewId} role="tooltip">
    <strong>{item.label}</strong>
    <span>{item.kind}{item.state ? ` · last recorded: ${item.state}` : ""}</span>
    <span>{item.detail}</span>
    {#if item.attention}<span class="attention">{attention}</span>{/if}
    <code>{item.id}</code>
    <small>Drag to arrange locally · {folded ? "Click to expand" : "Click to inspect"}</small>
  </div>
</NodeToolbar>

<style>
  .node-anchor { display:flex; justify-content:center; width:100%; height:100%; align-items:flex-start; pointer-events:none; }
  .orb-node { --ink:var(--color-parchment); --stroke:color-mix(in srgb,var(--color-accent) 43%,var(--color-engraving));
    display:inline-flex; position:relative; align-items:center; gap:7px; max-width:100%; min-height:32px; padding:5px 11px;
    border:1px solid var(--stroke); border-radius:7px; background:color-mix(in srgb,var(--color-accent) 9%,var(--color-obsidian));
    color:var(--ink); font:500 12px/1.16 var(--font-body); cursor:grab; pointer-events:auto; touch-action:none; }
  .orb-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .orb-mark { display:grid; place-items:center; flex:none; width:16px; height:16px; }
  .orb-node svg { display:block; width:100%; height:100%; fill:none; stroke:currentColor; stroke-width:1.55; stroke-linecap:round; stroke-linejoin:round; }
  .orb-mark img { display:block; max-width:100%; max-height:100%; filter:invert(1); }
  .orb-node[data-kind="run"] { --ink:var(--color-bone); width:100%; padding:4px 3px 12px; min-height:37px; gap:9px;
    border:0; border-bottom:1px solid var(--stroke); border-radius:0; background:transparent; text-align:left; }
  .run-dot { flex:none; width:7px; height:7px; border-radius:50%; background:var(--color-accent); box-shadow:0 0 0 3px color-mix(in srgb,var(--color-accent) 13%,transparent); }
  .run-id,.run-count { font:11px var(--font-glyph); color:var(--color-accent); white-space:nowrap; }
  .run-count { color:var(--color-ash); margin-left:auto; }
  .orb-node .run-focus { flex:none; width:13px; height:13px; color:var(--color-ash); }
  .orb-node[data-kind="run"] .orb-name { font:560 15px/1.3 var(--font-body); }
  .orb-node.station { --ink:#bdd6ff; display:flex; flex-direction:column; justify-content:center; width:39px; height:39px; min-height:39px; padding:0;
    border-color:#708bb0; border-radius:50%; background:radial-gradient(ellipse at 32% 20%,#4b678d,#324b70 53%,#243149);
    box-shadow:0 0 0 4px #6487bf12,0 3px 8px #0003; }
  .station .orb-mark { width:21px; height:21px; }
  .station .orb-name { position:absolute; top:calc(100% + 3px); left:50%; transform:translateX(-50%); max-width:160px; padding:1px 4px 2px; border-radius:3px;
    background:var(--color-obsidian); color:#d8e8ff; font:600 12px/1.15 var(--font-body); }
  .orb-node[data-kind="animator"] { --ink:var(--color-accent); border-radius:20px; }
  .orb-node[data-kind="gate"] { --ink:#e1b8d4; --stroke:#785568; background:#30242f; }
  .orb-node[data-kind="dispatch"] { --ink:#d8bee8; }
  .orb-node[data-kind="tool"], .orb-node[data-kind="Reach operation"], .orb-node[data-kind="call attempt"] { --ink:#b4d8d2; --stroke:#4c6d69; background:#202c2c; }
  .orb-node[data-kind="occurrence"],.orb-node[data-kind="unknown"],.orb-node[data-kind="gap"] { border-style:dashed; }
  .orb-node[data-kind="event"] { --ink:var(--color-ash); font:11px/1.2 var(--font-glyph); }
  .orb-node[data-state="failed"],.orb-node[data-state="error"] { --stroke:var(--color-ember); }
  .station[data-state="failed"],.station[data-state="error"] { border-color:var(--color-ember); }
  .fold { font:11px/1 var(--font-glyph); color:var(--color-accent); }
  .station .fold { position:absolute; right:-6px; bottom:0; display:grid; place-items:center; width:14px; height:14px; background:var(--color-obsidian);
    border:1px solid var(--color-control-border); border-radius:50%; }
  .attention-dot { width:5px; height:5px; flex:none; border-radius:50%; background:var(--color-primary); }
  .station .attention-dot { position:absolute; top:0; right:0; }
  .annotation { position:absolute; left:50%; top:calc(100% + 2px); transform:translateX(-50%); font:10px var(--font-glyph); color:var(--color-frost); white-space:nowrap; background:var(--color-void); }
  .station .annotation { top:calc(100% + 18px); }
  .orb-node:hover,.orb-node.chosen,.orb-node:focus-visible { outline:1.5px solid var(--ink); outline-offset:3px; }
  .orb-node.dragging { cursor:grabbing; }
  .orb-node[data-attention="received"] { animation:received 1.2s ease-out 1; }
  @keyframes received { from { outline:2px solid var(--color-primary); outline-offset:9px; } to { outline-color:transparent; outline-offset:2px; } }
  .orb-preview { max-width:min(310px,75vw); padding:12px 14px; display:flex; flex-direction:column; gap:6px; border:1px solid var(--color-engraving);
    border-radius:8px; background:var(--color-obsidian); color:var(--color-bone); box-shadow:0 6px 30px #0006; font:12px/1.4 var(--font-body); overflow-wrap:anywhere; }
  .orb-preview span { color:var(--color-parchment); }
  .orb-preview code,.orb-preview small { color:var(--color-ash); font-size:10px; }
  .orb-preview .attention { color:var(--color-primary); }
  @media(prefers-reduced-motion:reduce) { .orb-node[data-attention="received"] { animation:none; } }
</style>
