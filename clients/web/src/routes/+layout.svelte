<script lang="ts">
  import "../app.css";
  import AltarShell from "$lib/components/AltarShell.svelte";

  let { children } = $props();
</script>

<AltarShell>
  {@render children()}
</AltarShell>
