<script lang="ts">
  import { page } from "$app/state";
  import { onMount } from "svelte";

  import { getAltarStatus } from "$lib/api/client";

  let { children } = $props();
  let pending = $state(0);
  let omens = $state<Array<{ id: number; text: string; fault: boolean }>>([]);
  let nextOmen = 0;

  const instruments = [
    { slug: "bridge", label: "Bridge", plain: "Talk" },
    { slug: "orb", label: "Orb", plain: "Evidence" },
    { slug: "nexus", label: "Nexus", plain: "Capabilities" },
    { slug: "loom", label: "Loom", plain: "Patterns" }
  ] as const;

  function attention(event: Event) {
    const value = (event as CustomEvent<number>).detail;
    if (Number.isInteger(value)) pending = value;
    else void refreshAttention();
  }

  function receiveOmen(event: Event) {
    const detail = (event as CustomEvent<{ text: string; fault?: boolean }>).detail;
    raiseOmen(detail.text, detail.fault ?? true);
  }

  function raiseOmen(text: string, fault = true) {
    const id = ++nextOmen;
    omens.push({ id, text, fault });
    if (!fault) window.setTimeout(() => dismiss(id), 6000);
  }

  function dismiss(id: number) {
    omens = omens.filter((omen) => omen.id !== id);
  }

  async function refreshAttention() {
    try {
      pending = (await getAltarStatus()).pending_consents;
    } catch (error) {
      raiseOmen(error instanceof Error ? error.message : "The Altar cannot be reached.");
    }
  }

  onMount(() => {
    void refreshAttention();
    window.addEventListener("altar:attention", attention);
    window.addEventListener("altar:omen", receiveOmen);
    return () => {
      window.removeEventListener("altar:attention", attention);
      window.removeEventListener("altar:omen", receiveOmen);
    };
  });
</script>

<a class="skip-link" href="#altar-main">Skip to instrument</a>
<header class="topbar">
  <div class="brand">
    <span class="mark" aria-hidden="true">⬡</span>
    <span class="name rune-head">LychD</span>
    <span class="sub">The Altar</span>
  </div>

  <nav class="instruments" aria-label="Instruments">
    {#each instruments as instrument (instrument.slug)}
      <a
        href="/{instrument.slug}"
        aria-current={page.url.pathname.startsWith(`/${instrument.slug}`) ? "page" : undefined}
      >
        <span>{instrument.label}</span>
        <small>{instrument.plain}</small>
      </a>
    {/each}
  </nav>

  <div class="spacer"></div>
  <a class="sigil" data-state={pending > 0 ? "lit" : "dormant"} href="/bridge">
    ⬡ {pending > 0 ? `${pending} awaiting` : "Consent clear"}
  </a>
  <span class="sigil-identity" title="Fixed local authority context; not authentication">
    Local Sigil · <b>Magus</b>
  </span>
</header>

<main id="altar-main">
  {@render children()}
</main>

<footer class="legal-links">
  <span>Altar {__LYCHD_ALTAR_VERSION__.slice(0, 12)}</span>
  <a href={__LYCHD_SOURCE_URL__} rel="noreferrer">{__LYCHD_SOURCE_LABEL__}</a>
  <a href="/THIRD_PARTY_NOTICES.txt">Third-party notices</a>
</footer>

<div class="omen-stack" role="status" aria-live="polite">
  {#each omens as omen (omen.id)}
    <div class="omen" data-state={omen.fault ? "fault" : "info"}>
      <span>{omen.text}</span>
      <button class="dismiss" type="button" onclick={() => dismiss(omen.id)} aria-label="Dismiss">✕</button>
    </div>
  {/each}
</div>
