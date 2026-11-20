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

<style>
  .shell-placeholder { max-width: 420px; margin: auto; padding: 40px 20px; color: var(--color-text-muted); text-align: center; }
  .shell-placeholder p { line-height: 1.65; }
</style>
