<script lang="ts">
  import type { Scene, CanvasNode, CanvasEdge } from "$lib/canvas/types";
  let { scene, selected = [] }: { scene: Scene; selected?: string[] } = $props();
  const uid = $props.id();
  const marker = `${uid}-arrow`;
  let nodes = $derived(new Map(scene.nodes.map((node) => [node.id, node])));

  function endpoint(node: CanvasNode, other: CanvasNode) {
    const dx = other.x + other.width / 2 - node.x - node.width / 2;
    const dy = other.y + other.height / 2 - node.y - node.height / 2;
    const scale = 1 / Math.max(Math.abs(dx) / (node.width / 2), Math.abs(dy) / (node.height / 2), 1);
    return { x: node.x + node.width / 2 + dx * scale, y: node.y + node.height / 2 + dy * scale };
  }
  function edgePath(edge: CanvasEdge) {
    const source = nodes.get(edge.source), target = nodes.get(edge.target);
    if (!source || !target) return "";
    if (source.id === target.id) return `M ${source.x + source.width * .3} ${source.y} C ${source.x - 35} ${source.y - 80}, ${source.x + source.width + 35} ${source.y - 80}, ${source.x + source.width * .7} ${source.y}`;
    const a = endpoint(source, target), b = endpoint(target, source);
    return `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
  }
  function lines(node: CanvasNode) {
    const length = Math.max(3, Math.floor((node.width - 36) / 8));
    const words = node.label.split(/\s+/);
    const result: string[] = [];
    let line = "";
    for (const word of words) {
      if (line && `${line} ${word}`.length > length) { result.push(line); line = ""; }
      for (let offset = 0; offset < word.length; offset += length) {
        const part = word.slice(offset, offset + length);
        if (offset) { result.push(line); line = part; }
        else line = line ? `${line} ${part}` : part;
      }
    }
    if (line) result.push(line);
    const count = Math.max(1, Math.floor((node.height - (artSize(node) ? artSize(node) + 50 : 34)) / 20));
    return result.length > count ? [...result.slice(0, count - 1), `${result[count - 1]?.slice(0, Math.max(1, length - 1))}…`] : result;
  }
  function artSize(node: CanvasNode) { return node.artwork ? Math.max(0, Math.min(46, node.width - 24, node.height - 62)) : 0; }
</script>

<defs>
  <marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="var(--color-rune-dim, #447b91)" stroke-width="1.5" /></marker>
</defs>
{#each scene.edges as edge (edge.id)}
  {@const source = nodes.get(edge.source)}
  {@const target = nodes.get(edge.target)}
  {#if source && target}
    <g data-object-id={edge.id}>
      <path d={edgePath(edge)} fill="none" stroke={selected.includes(edge.id) ? "var(--color-rune, #8be7ff)" : "var(--color-rune-dim, #447b91)"} stroke-width={selected.includes(edge.id) ? 3 : 2} marker-end={`url(#${marker})`} />
      <path d={edgePath(edge)} fill="none" stroke="transparent" stroke-width="16" />
      {#if edge.label}<text x={(source.x + source.width / 2 + target.x + target.width / 2) / 2} y={(source.y + source.height / 2 + target.y + target.height / 2) / 2 - 10} text-anchor="middle" fill="var(--color-parchment, #b8b4c8)" font-family="system-ui, sans-serif" font-size="12">{edge.label}</text>{/if}
    </g>
  {/if}
{/each}
{#each scene.strokes.filter((stroke) => !stroke.archived) as stroke (stroke.id)}
  <g data-object-id={stroke.id}>
    {#if selected.includes(stroke.id)}<polyline points={stroke.points.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="var(--color-rune, #8be7ff)" stroke-width={stroke.width + 7} stroke-opacity=".35" stroke-linecap="round" stroke-linejoin="round" />{/if}
    <polyline points={stroke.points.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke={stroke.color} stroke-width={stroke.width} stroke-linecap="round" stroke-linejoin="round" />
    <polyline points={stroke.points.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="transparent" stroke-width={Math.max(14, stroke.width + 6)} stroke-linecap="round" />
  </g>
{/each}
{#each scene.nodes as node (node.id)}
  <g data-object-id={node.id}>
    <rect x={node.x} y={node.y} width={node.width} height={node.height} rx={node.kind === "person" ? Math.min(node.width, node.height) / 2 : node.kind === "note" ? 2 : 4} fill="var(--color-obsidian, #111416)" stroke={selected.includes(node.id) ? "var(--color-rune, #8be7ff)" : "var(--color-ash, #9aa6ae)"} stroke-width={selected.includes(node.id) ? 2.5 : 1} />
    {#if node.kind === "database"}<path d={`M ${node.x} ${node.y + 15} Q ${node.x + node.width / 2} ${node.y + 40} ${node.x + node.width} ${node.y + 15}`} fill="none" stroke="var(--color-rune-dim, #447b91)" />{/if}
    {#if node.height >= 64 && node.width >= 110 && (!node.artwork || node.height >= 130)}<text x={node.x + 14} y={node.y + 20} fill="var(--color-ash, #8a8699)" font-family="system-ui, sans-serif" font-size="10" letter-spacing="1.2">{node.kind.toUpperCase()}{node.pinned ? " · PINNED" : ""}</text>{/if}
    {#if node.artwork && artSize(node)}<image href={node.artwork.png_data_url} x={node.x + node.width / 2 - artSize(node) / 2} y={node.y + (node.height >= 130 ? 28 : 10)} width={artSize(node)} height={artSize(node)} preserveAspectRatio="xMidYMid meet"><title>{node.artwork.alt}</title></image>{/if}
    <text x={node.x + node.width / 2} y={node.y + (artSize(node) ? node.height - 15 : node.height / 2 + 7) - (lines(node).length - 1) * 10} text-anchor="middle" fill="var(--color-bone, #d9d7e4)" font-family="system-ui, sans-serif" font-size="15" font-weight="550">
      {#each lines(node) as line, index (`${node.id}-${index}`)}<tspan x={node.x + node.width / 2} dy={index ? 20 : 0}>{line}</tspan>{/each}
    </text>
    <title>{node.label}{node.pinned ? " (pinned for arrangement)" : ""}</title>
  </g>
{/each}
