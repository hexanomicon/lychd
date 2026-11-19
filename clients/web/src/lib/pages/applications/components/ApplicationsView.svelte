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
    <p>Open a tool or pin it to your Altar.</p>
  </header>
  <div class="filters">
    <label>Search<input type="search" placeholder="Find an application" bind:value={query} /></label>
    <label
      >Area<select bind:value={area}>
        <option value="">All areas</option>
        {#each areas as name (name)}<option value={name}>{name}</option>{/each}
      </select></label
    >
  </div>
  <div class="cards">
    {#each matches as app (app.id)}
      {@const pinned = pins.ids.includes(app.id)}
      <article>
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
  .catalogue {
    box-sizing: border-box;
    width: 100%;
    max-width: 76rem;
    margin: 0 auto;
    padding: clamp(1.25rem, 4cqi, 4rem);
    color: var(--color-bone);
  }
  h1,
  h2 {
    margin: 0;
    font-family: var(--font-rune);
    font-weight: 500;
    letter-spacing: -0.035em;
  }
  h1 {
    font-size: clamp(2.5rem, 5cqi, 4rem);
    line-height: 1.1;
  }
  p {
    color: var(--color-parchment);
    font-size: var(--text-sm);
    line-height: 1.55;
  }
  header p {
    margin: 0.65rem 0 0;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
    margin: 2rem 0 1.25rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--color-engraving);
  }
  label {
    display: grid;
    min-width: 0;
    gap: 0.4rem;
    color: var(--color-parchment);
    font-size: var(--text-xs);
  }
  label:first-child {
    flex: 1 1 15rem;
  }
  label:last-child {
    flex: 0 1 17rem;
  }
  input,
  select {
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    height: 2.65rem;
    padding: 0 0.8rem;
    border: 1px solid var(--color-control-border);
    border-radius: 6px;
    background: var(--color-obsidian);
    color: var(--color-bone);
    font: var(--text-sm)/1.4 var(--font-body);
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
  }
  article {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--color-engraving);
    border-radius: 8px;
    background: var(--color-obsidian);
  }
  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    color: var(--color-accent);
    border-bottom: 1px solid var(--color-engraving);
    background-color: var(--color-obsidian-2);
    background-image: radial-gradient(
      color-mix(in srgb, var(--color-accent) 16%, transparent) 0.7px,
      transparent 0.8px
    );
    background-size: 9px 9px;
  }
  button {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border: 1px solid var(--color-control-border);
    border-radius: 6px;
    color: var(--color-parchment);
    background: var(--color-obsidian);
    cursor: pointer;
  }
  button[aria-pressed="true"] {
    color: var(--color-void);
    border-color: var(--color-accent);
    background: var(--color-accent);
  }
  .body {
    display: flex;
    flex: 1;
    flex-direction: column;
    align-items: start;
    padding: 1.15rem 1.25rem;
  }
  h2 {
    font-size: 1.65rem;
    line-height: 1.15;
  }
  .body p {
    margin: 0.45rem 0 1.1rem;
  }
  a {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    margin-top: auto;
    color: var(--color-accent);
    font-size: var(--text-sm);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  a span {
    font: 1rem var(--font-body);
  }
  @container work-area (max-width: 58rem) {
    .cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @container work-area (max-width: 35rem) {
    .cards {
      grid-template-columns: 1fr;
    }
    label:last-child {
      flex-grow: 1;
    }
  }
</style>
