<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { onMount } from "svelte";

  onMount(() => {
    void goto(resolve("/bridge"), { replaceState: true });
  });
</script>

<svelte:head><title>LychD — The Altar</title></svelte:head>
<div class="shell-placeholder" aria-busy="true">
  <span class="glyph-big">⬡</span>
  <span class="rune-head">Opening the Bridge</span>
</div>
