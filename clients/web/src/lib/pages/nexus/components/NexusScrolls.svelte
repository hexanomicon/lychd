<script lang="ts">
  import { onMount } from "svelte";
  import { getLoomCatalogue, getLoomPatternRevision } from "$lib/api/client";
  import { sameInspectionBinding } from "$lib/api/inspection";
  import type { LoomSummary } from "$lib/api/models";
  import { resolvePath } from "$lib/navigation/paths";

  let { mode }: { mode: "skills" | "offers" | "checkpoints" } = $props();
  let catalogue = $state.raw<LoomSummary[]>([]);
  let catalogueState = $state<"loading" | "available" | "error">("loading");
  let selected = $state("");
  let skill = $state("");
  let schema = $state("");
  let audience = $state("");
  let peer = $state("");
  let offer = $state("");
  let requestPolicy = $state("refuse");

  let readGeneration = 0;
  async function reload() {
    const generation = ++readGeneration;
    catalogueState = "loading";
    try {
      const entries = (await getLoomCatalogue()).filter(item => item.publication === "published" && item.binding?.executable !== false);
      if (generation !== readGeneration) return;
      catalogue = entries;
      selected = entries.some(row => row.detail_path === selected) ? selected : (entries.find(row => row.default) ?? entries[0])?.detail_path ?? "";
      catalogueState = "available";
    } catch {
      if (generation === readGeneration) { catalogue = []; selected = ""; catalogueState = "error"; }
    }
  }
  onMount(() => { void reload(); return () => { readGeneration += 1; }; });
  const entry = $derived(catalogue.find(row => row.detail_path === selected));
  async function contract(row: LoomSummary) {
    const value = await getLoomPatternRevision(row.pattern_id, row.revision, row.binding ?? undefined);
    if (row.digest !== value.digest || row.pattern_id !== value.pattern_id || row.revision !== value.revision || (row.binding && !sameInspectionBinding(row.binding, value.binding))) throw new Error("The selected revision has changed.");
    return value;
  }
  const definition = $derived(mode === "checkpoints" && entry ? contract(entry) : null);
  const target = $derived(entry ? {pattern_id: entry.pattern_id, revision: entry.revision, digest: entry.digest} : null);
  const proposal = $derived.by(() => {
    if (!target) return null;
    if (mode === "skills" && skill.trim() && schema.trim() && audience.trim()) return {
      kind: "local-disclosure-review", local_target: target, proposed_public_fields: {skill:skill.trim(), task_schema:schema.trim(), audience:audience.trim()}
    };
    if (mode === "offers" && peer.trim() && schema.trim() && offer.trim()) return {
      kind: "receiver-binding-review", local_target: target, remote_identity:peer.trim(), offered_contract:offer.trim(), task_schema:schema.trim(), receiver_policy:requestPolicy
    };
    return null;
  });
  const json = $derived(proposal ? JSON.stringify(proposal, null, 2) : "");
</script>

{#if mode === "skills"}
  <p class="intro">Public skills describe the tasks this vessel accepts. Select an exact local Scroll to prepare its disclosure.</p>
  <div class="boundary"><strong>Outgoing advertisements</strong><span>0 published here</span><small>This build serves no public Agent Card. Only the explicitly reviewed skill, task schema and audience belong in a disclosure.</small></div>
{:else if mode === "offers"}
  <p class="intro">Compare a peer’s public offer with the local Scroll that would receive that task.</p>
  <div class="boundary"><strong>Connected offers</strong><span>Inventory unavailable</span><small>Intercom has no connected-offer feed in this build. Enrollment, task-schema compatibility and receiver admission each need their own evidence.</small></div>
{:else}
  <p class="intro">Inspect where a registered revision can pause for a human and which routes follow the decision.</p>
{/if}

{#if catalogueState === "loading"}<p role="status">Reading registered Scrolls…</p>
{:else if catalogueState === "error"}<p role="alert">The local Scroll catalogue is unavailable. <button onclick={() => void reload()}>Retry</button></p>
{:else if !entry}<p>No registered Scroll revisions are available in this catalogue.</p>
{:else}
  <div class="pick"><label>Local Scroll revision<select bind:value={selected}>{#each catalogue as row (row.detail_path)}<option value={row.detail_path}>{row.title} · {row.pattern_id}@{row.revision}</option>{/each}</select></label><span>{catalogue.length} registered {catalogue.length === 1 ? "revision" : "revisions"}</span></div>
  <section class="selected"><div class="heading"><div><code>{entry.pattern_id}@{entry.revision}</code><h2>{entry.title}</h2></div><a href={entry.detail_path}>View in Loom ↗</a></div>
    <p>{entry.description}</p><dl><dt>Entry station</dt><dd>{entry.entry_node}</dd><dt>Local routing</dt><dd>{entry.default ? "Default route" : entry.active ? "Active route" : "Retained revision"}</dd></dl>
    {#if mode === "checkpoints" && definition}
      {#await definition}<p role="status">Reading checkpoint declarations…</p>
      {:then scroll}
        {@const gates = scroll.nodes.filter(node => node.kind === "gate")}
        <h3>Declared checkpoints <span>{gates.length}</span></h3>
        {#each gates as gate (gate.key)}
          <div class="gate"><strong>{gate.label}</strong><code>{gate.key}</code>
          {#each scroll.edges.filter(edge => edge.source === gate.key) as edge (edge.key)}<small>{edge.relation} → {scroll.nodes.find(node => node.key === edge.target)?.label ?? edge.target}</small>{/each}</div>
        {:else}<p>This revision declares no human checkpoint.</p>{/each}
        <a href={resolvePath("/bridge?attention=pending")}>Review pending Run decisions in Bridge →</a>
      {:catch}<p role="alert">The exact revision could not be verified. <button onclick={() => void reload()}>Refresh catalogue</button></p>{/await}
    {/if}
  </section>
  {#if mode !== "checkpoints"}
    <h3>{mode === "skills" ? "Prepare a disclosure" : "Review an offered contract"}</h3>
    {#if mode === "skills"}<label>Public skill or material<input bind:value={skill} maxlength="240" /></label>
    {:else}<div class="pair"><label>Remote workload identity<input bind:value={peer} maxlength="180" /></label><label>Offer identity and revision<input bind:value={offer} maxlength="180" /></label></div>{/if}
    <div class="pair"><label>Task schema and version<input bind:value={schema} maxlength="180" /></label>
      {#if mode === "skills"}<label>Intended audience<input bind:value={audience} maxlength="180" /></label>
      {:else}<label>Unknown Spell policy<select bind:value={requestPolicy}><option value="refuse">Refuse</option><option value="request-teaching">Request teaching</option><option value="trusted-exact-contract">Trusted exact contract</option></select></label>{/if}
    </div>
    {#if proposal}<details><summary>Review local proposal</summary><pre>{json}</pre></details><a href={'data:application/json;charset=utf-8,' + encodeURIComponent(json)} download={'nexus-' + mode + '-proposal.json'}>Export proposal</a>{/if}
  {/if}
{/if}

<style>
  .intro,p { color:var(--color-parchment); line-height:1.5; max-width:66ch; margin:.3rem 0 1rem; }
  .boundary,.selected { border:1px solid var(--color-engraving); border-radius:.55rem; padding:1rem; background:var(--color-obsidian); margin:.75rem 0 1rem; }
  .boundary { display:flex; flex-wrap:wrap; gap:.4rem .75rem; align-items:center; }
  .boundary small { display:block; flex-basis:100%; color:var(--color-parchment); }
  .boundary span,h3 span { color:var(--color-rune); font-size:.78rem; } .boundary span { margin-left:auto; }
  h2,h3 { color:var(--color-bone); font:500 1.3rem/1.3 Georgia,serif; margin:.3rem 0 .65rem; }
  .heading,.pick,.pair { display:flex; flex-wrap:wrap; align-items:center; gap:.7rem 1rem; }
  .heading,.pick { justify-content:space-between; } .pick { align-items:end; } .pick span,code,dt { color:var(--color-ash); font:.77rem/1.5 var(--font-glyph); }
  .pair label { flex:1 1 12rem; } label { display:grid; gap:.3rem; min-width:0; margin:.6rem 0; color:var(--color-parchment); font-size:var(--text-sm); }
  input,select,button { background:var(--color-obsidian); color:var(--color-bone); border:1px solid var(--color-control-border); border-radius:.35rem; font:inherit; padding:.5rem .6rem; }
  select { max-width:100%; } .pick label { flex:1; } dl { display:grid; grid-template-columns:max-content 1fr; gap:.4rem .85rem; } dd { margin:0; overflow-wrap:anywhere; }
  a { color:var(--color-rune); } details,pre { margin:.8rem 0; } pre { white-space:pre-wrap; overflow-wrap:anywhere; }
  .gate { padding:.65rem 0; border-block-start:1px solid var(--color-engraving); } .gate strong,.gate code,.gate small { display:block; }
  :is(a,button,input,select,summary):focus-visible { outline:2px solid var(--color-rune); outline-offset:2px; }
</style>
