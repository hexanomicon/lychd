<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { onMount } from "svelte";

  onMount(() => {
    void goto(resolve("/orb"), { replace: true });
  });
</script>

<svelte:head><title>LychD — The Altar</title></svelte:head>
<div class="shell-placeholder" aria-busy="true">
  <p role="status">Opening Orb…</p>
</div>
