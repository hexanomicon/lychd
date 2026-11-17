<!--
  Labelled list of onward links from an inspector ("Open score in Loom ↗").
  Entries without an `href` are omitted, so callers can pass unvalidated targets as null.
-->
<script module lang="ts">
  export interface InspectorLink {
    href: string | null | undefined;
    label: string;
  }
</script>

<script lang="ts">
  let { label, links }: {
    /** Accessible navigation name. */
    label: string;
    /** Onward targets; null hrefs are skipped. */
    links: readonly InspectorLink[];
  } = $props();

  const available = $derived(links.filter((link): link is { href: string; label: string } => !!link.href));
</script>

{#if available.length}
  <nav class="inspector-links" aria-label={label}>
    {#each available as link (link.href)}
      <a href={link.href}>{link.label}<span aria-hidden="true">↗</span></a>
    {/each}
  </nav>
{/if}

<style>
  .inspector-links { display: flex; flex-direction: column; }
  a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 2.75rem;
    color: var(--color-bone);
    font-size: var(--text-sm);
    text-decoration: none;
  }
  a:hover { color: var(--color-rune); }
  a span { color: var(--color-ash); }
  a:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
