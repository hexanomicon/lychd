<script lang="ts">
  let { name, description }: { name: string; description: string } = $props();
</script>

<svelte:head><title>{name} — LychD</title></svelte:head>
<div class="shell-placeholder" data-state="unbuilt">
  <span class="glyph-big">◇</span>
  <span class="rune-head">{name}</span>
  <p>{description}</p>
</div>
