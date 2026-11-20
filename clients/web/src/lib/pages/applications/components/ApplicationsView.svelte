<script lang="ts">
  import { applications } from "$lib/navigation/applications";
  import { getApplicationPins } from "$lib/navigation/application-pins.svelte";
  import { resolvePath } from "$lib/navigation/paths";
  import AltarIcon from "$lib/shell/components/AltarIcon.svelte";
  import AppMotif from "./AppMotif.svelte";

  const pins = getApplicationPins();
  const areas = [...new Set(applications.map((app) => app.area))];
  let query = $state("");
  let area = $state("");
  const matches = $derived(
    applications.filter(
      (app) => (!area || app.area === area) && app.name.toLowerCase().includes(query.trim().toLowerCase()),
    ),
  );
</script>

<section class="catalogue" aria-labelledby="catalogue-title">
  <header>
    <h1 id="catalogue-title">Applications</h1>
  </header>
  <div class="filters">
    <label><span class="visually-hidden">Search</span><input type="search" placeholder="Find an app…" bind:value={query} /></label>
    <label
      ><span class="visually-hidden">Area</span><select bind:value={area}>
        <option value="">All areas</option>
        {#each areas as name (name)}<option value={name}>{name}</option>{/each}
      </select></label
    >
  </div>
  <div class="cards">
    {#each matches as app (app.id)}
      {@const pinned = pins.ids.includes(app.id)}
      <article data-app={app.id}>
        <div class="card-top">
          <AppMotif id={app.id} />
          <button
            type="button"
            aria-label={(pinned ? "Unpin " : "Pin ") + app.name}
            title={(pinned ? "Unpin " : "Pin ") + app.name}
            aria-pressed={pinned}
            onclick={() => pins.toggle(app.id)}
          >
            <AltarIcon name="pin" size={16} />
          </button>
        </div>
        <div class="body">
          <h2>{app.name}</h2>
          <p>{app.detail}</p>
          <a href={app.href.startsWith("/") ? resolvePath(app.href as `/${string}`) : app.href}>
            {app.action}<span aria-hidden="true">{app.href.startsWith("/") ? "→" : "↗"}</span>
          </a>
        </div>
      </article>
    {:else}
      <p role="status">No applications match this search.</p>
    {/each}
  </div>
</section>

<style>
  .catalogue { box-sizing:border-box; width:100%; max-width:96rem; align-self:flex-start; padding:clamp(1.3rem,3.2cqi,3rem); color:var(--color-bone); }
  h1,h2 { margin:0; color:var(--color-bone); font-family:var(--font-rune); font-weight:600; letter-spacing:-.035em; }
  h1 { font-size:clamp(1.9rem,3.2cqi,2.65rem); line-height:1.16; }
  .filters { display:flex; flex-wrap:wrap; gap:.65rem; margin:.95rem 0 1.25rem; }
  label { min-width:0; }
  label:first-child { flex:0 1 19rem; }
  label:last-child { flex:0 1 11rem; }
  input,select { box-sizing:border-box; width:100%; height:2.25rem; padding:0 .7rem; border:1px solid var(--color-engraving); border-radius:6px; background:var(--color-obsidian); color:var(--color-parchment); font:var(--text-sm)/1 var(--font-body); }
  .cards { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:clamp(.75rem,1.6cqi,1.4rem); }
  article { --motif:var(--color-accent); position:relative; display:flex; flex-direction:column; min-width:0; overflow:hidden; border:1px solid var(--color-engraving); border-radius:9px; background:linear-gradient(135deg,color-mix(in srgb,var(--motif) 4%,var(--color-obsidian)),var(--color-obsidian)); }
  article[data-app="atelier"] { --motif:var(--color-heat); }
  article[data-app="canvas"],article[data-app="language"] { --motif:var(--color-primary); }
  article[data-app="broadcast"] { --motif:var(--color-frost-deep); }
  article[data-app="riffmaw"] { --motif:color-mix(in srgb,var(--color-accent) 60%,var(--color-ember)); }
  .card-top { display:flex; align-items:center; min-height:clamp(5.8rem,8.6cqi,8.4rem); padding:.7rem 1.25rem .25rem; color:var(--motif); }
  .card-top button { position:absolute; inset:.6rem .65rem auto auto; display:grid; place-items:center; width:2rem; height:2rem; border:0; border-radius:5px; color:var(--color-ash); background:transparent; cursor:pointer; }
  .card-top button[aria-pressed="true"] { color:var(--color-heat); }
  .card-top button:hover { background:var(--color-obsidian-2); color:var(--color-bone); }
  .body { flex:1; display:flex; flex-direction:column; align-items:start; padding:.2rem clamp(.8rem,1.65cqi,1.55rem) 1rem; }
  h2 { font-size:clamp(1.35rem,2.2cqi,1.95rem); line-height:1.16; }
  p { margin:.35rem 0 .8rem; color:var(--color-parchment); font:var(--text-sm)/1.5 var(--font-body); }
  a { display:inline-flex; align-items:center; gap:.45rem; margin-top:auto; color:var(--color-primary); font:var(--text-sm)/1.5 var(--font-body); text-decoration:none; }
  a:hover { text-decoration:underline; }
  @container work-area (max-width:54rem) { .cards { grid-template-columns:repeat(2,minmax(0,1fr)); } }
  @container work-area (max-width:31rem) { .cards { grid-template-columns:minmax(0,1fr); } label:first-child { flex:1 1 100%; } }
</style>
