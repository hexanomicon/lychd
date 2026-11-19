<script lang="ts">
  import type { NexusCovenRow, NexusSnapshot } from "$lib/api/models";

  let { snapshot }: { snapshot: NexusSnapshot } = $props();
  let groupBy = $state<"owner" | "groups" | "family" | "connector">("owner");
  let search = $state("");
  let selected = $state("");
  let markers = $state<Record<string, string>>({});
  const marks = [{ icon: "◇", label: "Diamond" }, { icon: "○", label: "Circle" }, { icon: "△", label: "Triangle" }, { icon: "□", label: "Square" }, { icon: "✧", label: "Star" }];
  const entries = $derived([
    ...snapshot.board.covens.flatMap(([, rows]) => rows.map(row => ({ row, kind: "Soulstone" }))),
    ...snapshot.board.portals.map(row => ({ row, kind: "Portal" }))
  ]);
  const groups = $derived.by(() => {
    const result = new Map<string, NexusCovenRow[]>();
    const query = search.trim().toLowerCase();
    for (const { row } of entries) {
      if (![row.animator_name, row.capability_key, row.connector, row.runtime, ...(row.groups ?? [])].some(value => value?.toLowerCase().includes(query))) continue;
      const labels = groupBy === "owner" ? [row.animator_name] : groupBy === "groups" ? (row.groups?.length ? row.groups : ["No declared group"]) : [row[groupBy] || "Unreported"];
      for (const label of labels) result.set(label, [...(result.get(label) ?? []), row]);
    }
    return [...result].sort(([left], [right]) => left.localeCompare(right));
  });
  const item = $derived(entries.find(({ row }) => row.capability_key === selected));
</script>

<div class="filters">
  <label>Find a capability<input type="search" bind:value={search} placeholder="Animator, model, connector…" /></label>
  <label>Group by<select bind:value={groupBy}><option value="owner">Animator</option><option value="groups">Coven membership</option><option value="family">Capability family</option><option value="connector">Connector</option></select></label>
</div>
<div class="inventory">
  <section aria-label="Capability inventory">
    {#each groups as [label, rows] (label)}
      <h3>{label}</h3>
      {#each rows as row (row.capability_key)}
        <button type="button" aria-pressed={selected === row.capability_key} onclick={() => { selected = row.capability_key; }}><span aria-hidden="true">{markers[row.animator_name] || "◇"}</span><strong>{row.model_id}</strong><small>{row.family} · {row.state}</small></button>
      {/each}
    {:else}<p>{entries.length ? "No capabilities match this search." : "No capability observations in this snapshot."}</p>{/each}
  </section>
  {#if item}
    <section class="detail" aria-label="Selected inventory capability">
      <h3>{item.row.animator_name}</h3>
      <dl>
        <dt>Embodiment</dt><dd>{item.kind}</dd><dt>Capability</dt><dd>{item.row.capability_key}</dd>
        <dt>Groups</dt><dd>{item.row.groups?.join(", ") || "None declared"}</dd>
        <dt>Runtime</dt><dd>{item.row.runtime}</dd><dt>Connector</dt><dd>{item.row.connector ?? "Unreported"}</dd>
        <dt>Extension</dt><dd>{item.row.registrant_id ?? "Unattributed"}</dd>
        <dt>Tool support</dt><dd>{item.row.supports_tools == null ? "Unreported" : item.row.supports_tools ? "Declared" : "Disabled"}</dd>
      </dl>
      <label>Animator icon for this view<select value={markers[item.row.animator_name] || "◇"} onchange={(event) => { if (item) markers[item.row.animator_name] = event.currentTarget.value; }}>{#each marks as mark (mark.label)}<option value={mark.icon}>{mark.icon} {mark.label}</option>{/each}</select></label>
    </section>
  {:else if selected}<p role="status">The selected capability is absent from this snapshot.</p>{/if}
</div>

<style>
  .filters, .inventory { display: flex; gap: 1rem; flex-wrap: wrap; align-items: end; }
  .filters { padding-bottom: 1rem; border-bottom: 1px solid var(--color-engraving); }
  label { display: grid; gap: .4rem; font-size: var(--text-sm); }
  input, select { min-height: 2.45rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); padding: .35rem .6rem; background: var(--color-obsidian-2); color: var(--color-bone); }
  .inventory { align-items: start; } .inventory > section { min-width: min(100%, 14rem); flex: 1; }
  h3 { margin: 1rem 0 .5rem; color: var(--color-bone); font-size: var(--text-base); }
  button { display: grid; align-items: center; grid-template-columns: 1.4rem minmax(0, 1fr) auto; gap: .5rem; width: 100%; min-height: 2.65rem; text-align: left; overflow-wrap: anywhere; border: 0; border-bottom: 1px solid var(--color-engraving); background: transparent; color: var(--color-parchment); cursor: pointer; }
  button[aria-pressed="true"] { background: var(--color-obsidian-2); color: var(--color-rune); } button span { color: var(--color-rune); }
  small { font-size: var(--text-xs); color: var(--color-ash); }
  dl { display: grid; grid-template-columns: auto minmax(0,1fr); gap: .55rem 1rem; font-size: var(--text-sm); }
  dd { margin: 0; overflow-wrap: anywhere; } dt { color: var(--color-ash); }
  .detail { padding: 0 .8rem 1rem; border-left: 1px solid var(--color-engraving); }
</style>
