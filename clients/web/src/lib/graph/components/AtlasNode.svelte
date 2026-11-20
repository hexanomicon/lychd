<script lang="ts">
  import { Handle, Position, type NodeProps } from "@xyflow/svelte";
  import type { RenderNode } from "$lib/graph/components/flow-drafts";
  import { atlasGlyph } from "$lib/atlas/glyph";
  let { data, selected }: NodeProps<RenderNode> = $props();
</script>

<Handle type="target" position={Position.Left} id="in" isConnectable={false} />
<Handle type="source" position={Position.Right} id="out" isConnectable={false} />
<button
  type="button"
  class={["atlas-node nodrag nopan", { chosen: selected }]}
  data-kind={data.semantic.kind}
  aria-pressed={selected}
  aria-label={`Inspect ${data.semantic.kind} · ${data.semantic.label}`}
  onclick={(event) => data.select(data.semantic.id, event.currentTarget)}
>
  <span class="node-type"
    ><span aria-hidden="true">{atlasGlyph(data.semantic.kind)}</span><span class="visually-hidden">{data.semantic.kind}</span></span
  >
  <strong>{data.semantic.label}</strong>
</button>

<style>
  .atlas-node {
    --tint: var(--color-accent);
    width: 172px;
    height:60px;
    padding:7px 10px;
    display: flex;
    flex-direction:row; align-items:center;
    justify-content:flex-start;
    gap: 6px;
    text-align: left;
    border: 1px solid color-mix(in srgb, var(--tint) 56%, var(--color-engraving));
    background: linear-gradient(
      125deg,
      color-mix(in srgb, var(--tint) 9%, var(--color-obsidian)),
      var(--color-obsidian)
    );
    border-radius: 8px;
    color: var(--color-bone);
    cursor: pointer;
  }
  .atlas-node[data-kind="source turn"],
  .atlas-node[data-kind="reference"] {
    --tint: var(--color-rune);
  }
  .atlas-node[data-kind="working material"],
  .atlas-node[data-kind="run"],
  .atlas-node[data-kind="assessment"] {
    --tint: var(--color-heat);
  }
  .atlas-node[data-kind="public note"],
  .atlas-node[data-kind="recall"] {
    --tint: var(--color-lich);
  }
  .atlas-node:hover,
  .atlas-node:focus-visible,
  .chosen {
    border-color: var(--tint);
    outline: 2px solid color-mix(in srgb, var(--tint) 48%, transparent);
    outline-offset: 3px;
  }
  .node-type {
    display: flex;
    gap: 8px;
    align-items: center;
    font: 600 10px/1.2 var(--font-glyph);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--tint);
  }
  .node-type span {
    font-size: 17px;
  }
  strong {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
    font:600 15px/1.25 var(--font-rune);
  }
</style>
