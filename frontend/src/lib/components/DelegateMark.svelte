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
