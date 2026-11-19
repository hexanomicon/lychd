<script lang="ts">
  import type { NexusSnapshot } from "$lib/api/models";
  import { findOperation, type Operation, type OperationId } from "../state/operations";

  let { snapshot, onselect }: { snapshot: NexusSnapshot; onselect: (operation: Operation) => void } = $props();

  type Row = { id: OperationId; title: string; detail: string; value: string };
  const capabilities = $derived(snapshot.board.covens.reduce((sum, [, items]) => sum + items.length, snapshot.board.portals.length));
  const groups = $derived<{title: string; rows: Row[]}[]>([
    { title: "Operations", rows: [
      { id: "board", title: "Capabilities", detail: "Animator readiness, Portals and runtime observations.", value: String(capabilities) },
      { id: "transitions", title: "Transitions", detail: "Request tickets and observed lifecycle changes.", value: String(snapshot.transitions.length) },
      { id: "installation", title: "Installation", detail: "Worker capacity, active configuration and extensions.", value: snapshot.configuration?.database_profile ?? "Unavailable" }
    ]},
    { title: "Scrolls and peers", rows: [
      { id: "skills", title: "Advertised skills", detail: "Review a local Scroll for explicit public disclosure.", value: "No Agent Card" },
      { id: "offers", title: "Connected offers", detail: "Review an exact peer offer against a local receiver.", value: "No feed" },
      { id: "checkpoints", title: "Human checkpoints", detail: "Inspect declared consent gates in a Scroll revision.", value: "By Scroll" }
    ]},
    { title: "People and access", rows: [
      { id: "colleagues", title: "Colleagues", detail: "Paired operators and reported availability.", value: "Unreported" },
      { id: "principals", title: "Users", detail: "Identity and Sigil for the authenticated operator.", value: snapshot.operator?.subject ?? "Unavailable" },
      { id: "access", title: "Access policy", detail: "Scoped requests and time-limited elevation.", value: "Review" }
    ]}
  ]);
</script>

<p class="deck">Readiness, requests and access on this vessel.</p>
<div class="snapshot-grid">
  <div class="directory">
    <div class="capture"><span>▤ &nbsp; Snapshot captured</span><time datetime={snapshot.snapshot_at}>{new Date(snapshot.snapshot_at).toLocaleString()}</time></div>
    {#each groups as group (group.title)}
      <section><h2>{group.title}</h2>
        {#each group.rows as row (row.id)}
          <button class="record" onclick={() => onselect(findOperation(row.id))}>
            <span class="mark" aria-hidden="true">{findOperation(row.id).mark}</span>
            <span class="copy"><strong>{row.title}</strong><small>{row.detail}</small></span><span class="value">{row.value}</span><span aria-hidden="true">›</span>
          </button>
        {/each}
      </section>
    {/each}
  </div>
  <aside aria-label="Instance snapshot"><p class="eyebrow">Instance snapshot</p><h2>At this snapshot</h2>
    <h3>Runtime</h3><dl><dt>Admission</dt><dd>{snapshot.containment_reason ? "Contained" : "Open"}</dd><dt>Observed</dt><dd>{new Date(snapshot.snapshot_at).toLocaleTimeString()}</dd></dl>
    <h3>Local operator</h3><p>{snapshot.operator?.subject ?? "Unavailable"}</p>{#if snapshot.operator}<code>{snapshot.operator.sigil}</code>{/if}
    <h3>Latest request</h3>{#if snapshot.transitions[0]}<button class="request" onclick={() => onselect(findOperation("transitions"))}>{snapshot.transitions[0].target_capability_key} ›</button>{:else}<p>No retained transition requests.</p>{/if}
  </aside>
</div>

<style>
  .deck { color:var(--color-parchment); margin:0 0 1.7rem; line-height:1.5; }
  .snapshot-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(11rem,22%); gap:clamp(1rem,3vw,2.5rem); }
  .directory,.copy { min-width:0; }
  .capture { padding:.7rem .9rem; display:flex; flex-wrap:wrap; justify-content:space-between; gap:.5rem; border:1px solid var(--color-engraving); border-radius:.5rem; background:var(--color-obsidian); font-size:var(--text-sm); }
  time,.value,.eyebrow,code { font: .74rem/1.45 var(--font-glyph); color:var(--color-ash); }
  section { margin:1.35rem 0; } h2 { margin:0; color:var(--color-bone); font:500 1.28rem/1.3 Georgia,serif; letter-spacing:-.02em; }
  section h2 { display:flex; align-items:center; gap:.75rem; margin-bottom:.2rem; }
  section h2::after { content:""; height:1px; flex:1; background:var(--color-engraving); }
  .record { display:flex; align-items:center; gap:.8rem; padding:.75rem .15rem; text-align:left; width:100%; background:transparent; border:0; border-bottom:1px solid var(--color-engraving); color:var(--color-parchment); cursor:pointer; }
  .record:hover,.request:hover { background:var(--color-obsidian); } .copy strong,.copy small { display:block; }
  .copy strong { font-size:var(--text-sm); font-weight:550; color:var(--color-bone); } .copy small { font-size:.8rem; color:var(--color-ash); margin-top:.17rem; }
  .mark { width:2rem; height:2rem; flex:none; display:grid; place-items:center; background:color-mix(in srgb,var(--color-rune) 12%,var(--color-obsidian)); color:var(--color-rune); border-radius:.5rem; }
  section:first-of-type .mark { background:color-mix(in srgb,var(--color-frost) 12%,var(--color-obsidian)); color:var(--color-frost); }
  .value { margin-left:auto; text-align:right; overflow-wrap:anywhere; }
  aside { align-self:start; padding:1rem; border-inline-start:1px solid var(--color-engraving); background:var(--color-obsidian); }
  aside h3,.eyebrow { text-transform:uppercase; letter-spacing:.08em; font: 550 .71rem/1.4 var(--font-glyph); color:var(--color-ash); }
  aside h3 { padding-top:1rem; border-top:1px solid var(--color-engraving); margin:1rem 0 .45rem; }
  aside p { margin:.3rem 0; } aside dl { display:grid; grid-template-columns:auto 1fr; gap:.4rem; } aside dd { margin:0; text-align:right; }
  aside :is(p,dl,.request) { font-size:var(--text-sm); } .request { border:0; padding:.3rem 0; color:var(--color-rune); background:transparent; cursor:pointer; }
  button:focus-visible { outline:2px solid var(--color-rune); outline-offset:2px; }
  @container work-area (max-width:66rem) { .snapshot-grid { grid-template-columns:minmax(0,1fr); } aside { border-inline-start:0; border-top:1px solid var(--color-engraving); } }
  @media(max-width:540px) { .value { max-width:6rem; } }
</style>
