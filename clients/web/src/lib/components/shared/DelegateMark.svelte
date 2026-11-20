<script lang="ts">
  let { label }: { label?: string } = $props();
</script>

<span
  class="delegate-mark"
  role={label ? "img" : undefined}
  aria-label={label}
  aria-hidden={label ? undefined : "true"}
  title={label}
>⬢</span>

<style>
  .delegate-mark { display: inline-grid; place-items: center; width: 1.1em; color: var(--color-interactive); font-family: var(--font-glyph); }
</style>
