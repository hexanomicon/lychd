<!--
  Speaker line above a conversation turn: an initials avatar and the speaker's name.
  User turns align to the end, matching their right-aligned bubble.
-->
<script lang="ts">
  let { role, name }: {
    /** Who spoke. */
    role: "agent" | "user";
    /** Visible speaker name. */
    name: string;
  } = $props();

  const initials = $derived(name.replace(/[^\p{L}\p{N}]/gu, "").slice(0, 2));
</script>

<div class="turn__meta turn-header" data-role={role}>
  {#if role === "agent"}<span class="turn-header__avatar" aria-hidden="true">{initials}</span>{/if}
  <span class="who">{name}</span>
</div>

<style>
  .turn-header { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.6rem; margin-bottom: 6px; color: var(--color-text-muted); font-size: var(--text-xs); }
  .turn-header[data-role="user"] { justify-content: flex-end; }
  .turn-header__avatar {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 50%;
    background: var(--color-status-active);
    color: var(--color-on-action);
    font: 600 var(--text-2xs)/1 var(--font-body);
  }
  .who { color: var(--color-text-body); font: 600 var(--text-sm)/1.5 var(--font-body); font-variant: normal; letter-spacing: 0; }
  .turn-header[data-role="user"] .who { color: var(--color-text-muted); font-size: var(--text-xs); font-weight: 500; }
</style>
