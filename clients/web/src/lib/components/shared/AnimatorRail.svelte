<script lang="ts">
  import type { OrbRunSnapshot } from "$lib/api/models";
  import { animatorObservations } from "$lib/orb/playback";
  let { evidence, cursor = null, onselect }: {
    evidence: OrbRunSnapshot["evidence"];
    cursor?: number | null;
    onselect: (seq: number) => void;
  } = $props();
  let observations = $derived(animatorObservations(evidence, cursor));
</script>

<aside class="animator-rail" aria-label="Recorded Animators">
  <h3>Animators</h3><p>Recorded grants {cursor === null ? "in this lens" : `through #${cursor}`}</p>
  <ul>
    {#each observations as observation (observation.name)}
      <li>
        <button type="button" class={["animator", { lit: observation.atCursor }]}
          style={`--animator-accent:var(--color-${observation.accent})`}
          onclick={() => onselect(observation.record.seq)}>
          <span class="sigil" aria-hidden="true">◇</span>
          <span><strong>{observation.name}</strong><small>{observation.record.model_id ?? observation.record.capability_family ?? "Model not supplied"}</small>
            <small>{observation.atCursor ? "Grant at cursor" : "Grant recorded"} · #{observation.record.seq}</small></span>
        </button>
      </li>
    {:else}<li class="empty">No Animator identity is supplied before this cursor.</li>{/each}
  </ul>
  <p class="boundary">A grant shows selection. Call duration and historical availability are not supplied.</p>
</aside>

<style>
  .animator-rail { padding:1rem; border:1px solid var(--color-engraving); border-radius:var(--radius-panel); background:var(--color-obsidian); min-width:0; }
  h3 { font:500 1rem/1.4 var(--font-body); margin:0 0 .4rem; color:var(--color-bone); }
  p,.empty { color:var(--color-parchment); font-size:var(--text-xs); line-height:1.6; }
  ul { padding:0; list-style:none; margin:1rem 0; display:grid; gap:.7rem; }
  .animator { width:100%; display:flex; gap:.6rem; align-items:center; text-align:left; padding:.7rem; min-height:44px; background:var(--color-obsidian-2); border:1px solid var(--color-engraving); border-inline-start:3px solid var(--animator-accent); border-radius:var(--radius-rune); cursor:pointer; color:var(--color-bone); }
  .sigil { color:var(--animator-accent); font-size:1.8rem; }
  strong,small { display:block; overflow-wrap:anywhere; }
  strong { font:500 var(--text-sm)/1.4 var(--font-body); }
  small { color:var(--color-parchment); font-size:var(--text-xs); line-height:1.6; }
  .lit { border-color:var(--animator-accent); box-shadow:inset 0 -2px var(--animator-accent); }
  button:hover { background:var(--color-obsidian); }
  button:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  .boundary { border-top:1px solid var(--color-engraving); padding-top:.8rem; }
</style>
