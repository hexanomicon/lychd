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
    <path opacity=".45" d="M12 42h136M22 39v6m25-6v6m25-6v6m25-6v6m25-6v6" />
    <path d="m16 34 23-9 18 5 21-14 18 5 22-10" />
    <circle cx="118" cy="11" r="3" fill="currentColor" />
  {:else if id === "atelier"}
    <rect x="16" y="9" width="126" height="38" rx="3" />
    <path opacity=".45" d="M16 16h126M16 40h126m-96-24v24m32-24v24m32-24v24" />
    <path d="m60 20 12 8-12 8z" fill="currentColor" />
    <path d="M26 12h6m24 0h6m24 0h6m24 0h6m-96 31h6m24 0h6m24 0h6m24 0h6" />
  {:else if id === "canvas"}
    <path d="M47 28h16q5 0 5-5v-4q0-5 5-5h12m-17 9v12q0 5 5 5h29" />
    <rect x="17" y="19" width="30" height="18" rx="3" /><rect x="85" y="5" width="32" height="18" rx="3" />
    <rect x="102" y="32" width="38" height="17" rx="3" /><path
      opacity=".45"
      d="M23 25h13m55-14h16m-1 27h24"
    />
  {:else if id === "broadcast"}
    <path
      d="M80 27v20m-9 0h18m-21-33a18 18 0 0 0 0 25m24-25a18 18 0 0 1 0 25m-30-32a28 28 0 0 0 0 39m36-39a28 28 0 0 1 0 39"
    />
    <circle cx="80" cy="24" r="4" fill="currentColor" /><path opacity=".45" d="M16 26h26m76 0h26" />
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
    width: 9rem;
    max-width: 58%;
    height: 3.15rem;
  }
</style>
