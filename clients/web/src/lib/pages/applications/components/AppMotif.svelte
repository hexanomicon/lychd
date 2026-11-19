<script lang="ts">
  import type { ApplicationId } from "$lib/navigation/applications";
  let { id }: { id: ApplicationId } = $props();
</script>

<svg
  aria-hidden="true"
  viewBox="0 0 160 56"
  fill="none"
  stroke="currentColor"
  stroke-width="1.35"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  {#if id === "scavenger"}
    <rect x="15" y="5" width="76" height="45" rx="5"/>
    <path d="M16 15h74m-66-5h2m4 0h2m4 0h2" opacity=".7"/>
    <path d="M23 22h5v5h-5zm0 11h5v5h-5zm12-9h24m-24 12h18" opacity=".75"/>
    <circle cx="84" cy="35" r="11" fill="var(--color-obsidian)"/><path d="m92 43 12 10m-10-12 12 10"/>
  {:else if id === "atelier"}
    <path d="m43 42 9-20L80 6l6 5-15 27-22 8z M51 39l19-19m-18 2 19 16"/>
    <circle cx="69" cy="20" r="2.6"/><path d="m43 37-23 8m48-10 21 9" opacity=".7"/>
    <rect x="14" y="42" width="8" height="8" rx="1"/><rect x="88" y="42" width="8" height="8" rx="1"/>
  {:else if id === "canvas"}
    <rect x="13" y="8" width="69" height="37" rx="4"/><path d="M36 50h25m-17-5v5m8-5v5"/>
    <path d="M22 16h22v11H22zm29 8h21v11H51zM44 21h4q4 0 4 4m-8 6h-7"/>
    <rect x="66" y="28" width="31" height="18" rx="2.5" fill="var(--color-obsidian)"/><path d="M74 50h18m-9-4v4"/>
  {:else if id === "broadcast"}
    <rect x="13" y="14" width="115" height="34" rx="3"/>
    <path d="M19 10v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4m10-4v4" opacity=".65"/>
    <path fill="currentColor" opacity=".5" d="M19 20h25v9H19zm30 0h28v9H49zm31 13h29v8H80zM37 33h39v8H37z"/>
    <path d="M69 9v39m-2-40h4l-2 4z"/>
  {:else if id === "riffmaw"}
    <path opacity=".45" d="M8 28h144" />
    <path
      stroke-width="2.5"
      d="M18 25v6m7-11v16m7-21v26m7-20v14m7-25v36m7-31v26m7-21v16m7-10v4m7-12v20m7-31v42m7-35v28m7-20v12m7-17v22m7-30v38m7-34v30m7-24v18m7-14v10m7-7v4"
    />
  {:else}
    <rect x="14" y="7" width="92" height="10" rx="2" /><rect x="52" y="23" width="88" height="10" rx="2" />
    <path
      opacity=".65"
      d="M21 12h37m5 0h23m-27 16h27m5 0h29M13 45h132m-119-3v6m23-6v6m23-6v6m23-6v6m23-6v6"
    />
  {/if}
</svg>

<style>
  svg {
    display: block;
    width: clamp(10rem, 14cqi, 15rem);
    max-width: 85%;
    height:auto;
  }
</style>
