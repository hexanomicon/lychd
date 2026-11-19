<script lang="ts">
  import { afterNavigate } from "$app/navigation";
  import { onMount, tick, type Snippet } from "svelte";
  import { applications } from "$lib/navigation/applications";
  import { getApplicationPins } from "$lib/navigation/application-pins.svelte";
  import { resolvePath } from "$lib/navigation/paths";
  import AltarIcon from "./AltarIcon.svelte";
  import AppearancePreferences from "./AppearancePreferences.svelte";

  let {
    instruments,
    pathname,
    available,
    pending,
    suspended,
    brand,
    section,
  }: {
    instruments: readonly {
      slug: string;
      label: string;
      href: string;
      current: "page" | "location" | undefined;
    }[];
    pathname: string;
    available: boolean;
    pending: number | null;
    suspended: boolean;
    brand: Snippet;
    section?: Snippet;
  } = $props();
  const pins = getApplicationPins();
  let compact = $state(false);
  let preferred = $state<boolean | null>(null);
  const folded = $derived(preferred ?? (compact || pathname.replace(/\/$/, "") === resolvePath("/orb")));
  let quick = $state(false);
  let quickButton: HTMLButtonElement;
  let popup = $state<HTMLElement>();
  let quickOwner: HTMLElement | null = null;
  const railKey = "lychd.altar.nav-folded.v1";
  const appHref = (path: string) => (path.startsWith("/") ? resolvePath(path as `/${string}`) : path);
  onMount(() => {
    const small = window.matchMedia?.("(max-width: 68rem)");
    try {
      const saved = localStorage.getItem(railKey);
      if (saved === "true" || saved === "false") preferred = saved === "true";
    } catch {}
    const update = () => {
      compact = small?.matches ?? false;
    };
    update();
    small?.addEventListener?.("change", update);
    return () => small?.removeEventListener?.("change", update);
  });
  function fold() {
    preferred = !folded;
    try {
      localStorage.setItem(railKey, String(preferred));
    } catch {}
  }
  async function toggle(owner: HTMLElement) {
    if (quick) {
      close(true);
      return;
    }
    quickOwner = owner;
    quick = true;
    await tick();
    popup?.querySelector<HTMLElement>("a")?.focus();
  }
  function close(restore = false) {
    quick = false;
    if (restore) quickOwner?.focus();
  }
  function outside(e: PointerEvent) {
    if (quick && e.target instanceof Element && !popup?.contains(e.target) && !e.target.closest(".app-split"))
      close();
  }
  afterNavigate(() => close());
</script>

<svelte:window
  onpointerdown={outside}
  onkeydown={(e) => {
    if (quick && e.key === "Escape") {
      e.preventDefault();
      close(true);
    }
  }}
/>
<header class="rail" class:folded inert={suspended} aria-label="Altar navigation">
  <div class="brand-line">{@render brand()}</div>
  <nav class="instrument-links" aria-label="Instruments">
    {#each instruments as item (item.slug)}<a
        href={item.href}
        aria-label={item.label}
        title={item.label}
        aria-current={item.current}
        ><AltarIcon name={item.slug} size={19} /><span class="caption">{item.label}</span></a
      >{/each}
  </nav>
  <div class="apps">
    <h2 class="caption">Pinned apps</h2>
    {#each applications.filter((app) => pins.ids.includes(app.id)) as app (app.id)}
      <a
        href={appHref(app.href)}
        title={app.name}
        aria-label={app.name}
        aria-current={pathname === appHref(app.href) ? "page" : undefined}
        ><AltarIcon name={app.id} size={18} /><span class="caption">{app.name}</span></a
      >
    {/each}
  </div>
  <div class="app-split">
    <a
      href={resolvePath("/applications")}
      aria-current={pathname === resolvePath("/applications") ? "page" : undefined}
      aria-label="Applications"
      title="Applications"
      oncontextmenu={(e) => {
        e.preventDefault();
        void toggle(e.currentTarget);
      }}><AltarIcon name="applications" size={18} /><span class="caption">Applications</span></a
    >
    <button
      bind:this={quickButton}
      type="button"
      aria-label="Quick applications list"
      aria-expanded={quick}
      title="Quick applications list"
      onclick={() => void toggle(quickButton)}
      oncontextmenu={(e) => {
        e.preventDefault();
        void toggle(quickButton);
      }}>›</button
    >
  </div>
  {#if quick}
    <nav bind:this={popup} class="quick" aria-label="Quick applications list">
      {#each applications.filter((app) => !pins.ids.includes(app.id)) as app (app.id)}
        <a href={appHref(app.href)} onclick={() => close()}><AltarIcon name={app.id} size={16} />{app.name}</a
        >
      {/each}
      <a class="all" href={resolvePath("/applications")} onclick={() => close()}
        >All applications <span aria-hidden="true">↗</span></a
      >
    </nav>
  {/if}
  {#if section && !folded}{@render section()}{/if}
  <footer>
    {#if available}<a
        class="attention"
        href={resolvePath("/bridge?attention=pending")}
        title={pending === null
          ? "Consent status unknown"
          : pending > 0
            ? `${pending} awaiting`
            : "Consent clear"}
        ><span class="status" data-state={pending === null ? "unknown" : pending > 0 ? "awaiting" : "clear"}
        ></span><span class="caption"
          >{pending === null
            ? "Consent status unknown"
            : pending > 0
              ? `${pending} awaiting`
              : "Consent clear"}</span
        ><span class="sr">Consent</span></a
      >{:else}<span class="offline">Offline<span class="caption"> · consent unavailable</span></span>{/if}
    <AppearancePreferences />
    <button
      class="fold"
      type="button"
      aria-label={folded ? "Expand navigation" : "Collapse navigation"}
      title={folded ? "Expand navigation" : "Collapse navigation"}
      aria-expanded={!folded}
      onclick={fold}><AltarIcon name="panel" size={16} /><span class="caption">Collapse</span></button
    >
  </footer>
</header>

<style>
  .rail {
    --nav-size: 10.45rem;
    position: relative;
    z-index: 40;
    display: flex;
    flex: none;
    flex-direction: column;
    width: var(--nav-size);
    min-height: 0;
    padding: 0.65rem 0.5rem 0.5rem;
    background: var(--color-obsidian);
    border-right: 1px solid var(--color-engraving);
    font: var(--text-sm)/1.45 var(--font-body);
    color: var(--color-parchment);
  }
  .rail.folded {
    --nav-size: 3.25rem;
  }
  .brand-line {
    padding: 0 0.3rem 0.7rem;
  }
  .instrument-links,
  .apps {
    display: grid;
    gap: 0.18rem;
  }
  .rail a,
  .fold,
  .app-split button {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    min-width: 0;
    min-height: 2.45rem;
    padding: 0.4rem 0.63rem;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: inherit;
    text-decoration: none;
    font: inherit;
    letter-spacing: normal;
    text-transform: none;
    text-align: left;
    cursor: pointer;
  }
  .rail a:hover,
  .rail button:hover {
    background: var(--color-obsidian-2);
    color: var(--color-bone);
  }
  .rail a[aria-current] {
    box-shadow: inset 2px 0 var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 19%, var(--color-obsidian));
    color: var(--color-bone);
  }
  .apps {
    border-block: 1px solid var(--color-engraving);
    margin: 0.9rem 0 0.45rem;
    padding: 0.8rem 0;
  }
  .apps h2 {
    color: var(--color-ash);
    font: 600 var(--text-xs)/1.4 var(--font-body);
    padding: 0 0.65rem 0.25rem;
    margin: 0;
  }
  .app-split {
    display: flex;
    align-items: stretch;
  }
  .app-split a {
    flex: 1;
  }
  .app-split button {
    padding: 0.15rem 0.4rem;
    justify-content: center;
    font-size: 1.15rem;
    min-width: 1.25rem;
  }
  footer {
    display: grid;
    gap: 0.15rem;
    margin-top: auto;
    padding-top: 0.8rem;
  }
  .rail a.attention,
  .offline {
    font-size: 0.72rem;
    color: var(--color-ash);
    line-height: 1.3;
  }
  .status {
    background: var(--color-ash);
    border-radius: 50%;
    width: 0.45rem;
    height: 0.45rem;
    flex: none;
  }
  .status[data-state="awaiting"] {
    background: var(--color-heat);
  }
  .status[data-state="clear"] {
    background: var(--color-lich);
  }
  .fold {
    font-size: 0.78rem;
    color: var(--color-ash);
  }
  .sr {
    position: absolute;
    clip-path: inset(50%);
    width: 1px;
    height: 1px;
    overflow: hidden;
  }
  .quick {
    position: absolute;
    z-index: 65;
    left: calc(100% + 3px);
    top: min(43%, 22rem);
    width: min(14rem, 65vw);
    max-height: 44dvh;
    overflow: auto;
    border: 1px solid var(--color-control-border);
    border-radius: 8px;
    background: var(--color-obsidian-2);
    padding: 0.35rem;
    box-shadow: 0 0.65rem 2rem #0006;
  }
  .quick a {
    white-space: normal;
  }
  .quick a.all {
    justify-content: space-between;
    border-top: 1px solid var(--color-engraving);
    border-radius: 0;
  }
  .folded .caption {
    display: none;
  }
  .folded .brand-line {
    padding-left: 0;
  }
  .folded {
    padding-inline: 0.23rem;
  }
  .folded .instrument-links a,
  .folded .apps a,
  .folded footer > a,
  .folded footer > button {
    justify-content: center;
  }
  .folded .app-split a {
    justify-content: center;
    padding: 0.1rem;
  }
  .folded .app-split button {
    padding: 0.05rem;
    min-width: 0.85rem;
  }
  .folded .apps {
    padding-block: 0.45rem;
  }
  .rail :global(.appearance-panel) {
    position: fixed;
    inset: auto auto 0.75rem calc(var(--nav-size) + 0.45rem);
    width: min(20rem, calc(100vw - var(--nav-size) - 1.3rem));
  }
  .rail :global(.appearance summary) {
    border: 0;
    min-height: 2.3rem;
    padding: 0.5rem 0.65rem;
  }
  .folded :global(.appearance summary) {
    font-size: 0;
    text-align: center;
  }
  .folded :global(.appearance summary::after) {
    content: "⚙";
    font-size: 1.1rem;
  }
  @media (max-height: 610px) {
    .rail {
      overflow-y: auto;
    }
    .quick {
      position: fixed;
      left: var(--nav-size);
      top: 30%;
    }
    .apps {
      margin: 0.35rem 0;
      padding-block: 0.25rem;
    }
    .rail a,
    .fold,
    .app-split button {
      min-height: 2rem;
    }
  }
</style>
