<script lang="ts">
  import { page } from "$app/state";
  import { afterNavigate, beforeNavigate, goto } from "$app/navigation";
  import { asset, resolve } from "$app/paths";
  import { onMount, setContext, tick, untrack, type Snippet } from "svelte";
  import BridgeDock from "./BridgeDock.svelte";
  import BridgeView from "./BridgeView.svelte";
  import AltarIcon from "./AltarIcon.svelte";
  import { altarNavigationContext, selectedBridgeHref, type AltarNavigation } from "$lib/navigation/instruments";

  import { getAltarStatus } from "$lib/api/client";

  let { children, offline = false }: { children: Snippet; offline?: boolean } = $props();
  let connected = $state(false);
  const available = $derived(!offline || connected);
  let dockOpen = $state(true);
  let narrow = $state(false);
  const viewing = $derived.by(() => {
    const path = page.url.pathname;
    if (path.startsWith("/bridge")) return page.url.searchParams.has("notes") ? "Public notes" :
      page.url.searchParams.has("investigation") ? "Public source investigation" : "Conversation workspace";
    return ({ atlas: "Atlas", orb: "Orb", loom: "Loom", nexus: "Nexus", canvas: "Canvas", scavenger: "Scavenger market" } as Record<string, string>)[path.split("/")[1] ?? ""] ?? "Altar";
  });
  let mastheadHeight = $state(56);
  function measureMasthead(element: HTMLElement) {
    const measure = () => { mastheadHeight = Math.ceil(element.getBoundingClientRect().height) || 56; };
    measure();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }
  const initialPath = untrack(() => selectedBridgeHref(page.url.pathname, resolve("/bridge")));
  let bridgeSession = $state<string | undefined>(initialPath ? decodeURIComponent(initialPath.slice("/bridge/".length)) : undefined);
  let bridgeSearch = $state(untrack(() => {
    const params = page.url.searchParams;
    return initialPath || (page.url.pathname === resolve("/bridge") && !params.has("notes") && !params.has("investigation"))
      ? page.url.search : "";
  }));
  let pending = $state<number | null>(null);
  let omens = $state<Array<{ id: number; text: string; fault: boolean }>>([]);
  const navigation = $state<AltarNavigation>({ bridgePath: initialPath ?? "/bridge" });
  setContext(altarNavigationContext, navigation);

  const mainScroll = new Map<string, { top: number; left: number }>();
  let mainNavigation = 0;
  beforeNavigate(({ from }) => {
    const main = document.getElementById("altar-main");
    if (!from || !main) return;
    mainScroll.delete(from.url.href);
    mainScroll.set(from.url.href, { top: main.scrollTop, left: main.scrollLeft });
    if (mainScroll.size > 64) mainScroll.delete(mainScroll.keys().next().value!);
  });

  // SvelteKit's navigation lifecycle supplies explicit URL focus. Layout changes
  // and work-route queries never become ordinary Bridge conversation inputs.
  afterNavigate(({ type, to }) => {
    const version = ++mainNavigation;
    if (to && !to.url.hash && (type === "link" || type === "popstate")) {
      const position = type === "popstate" ? mainScroll.get(to.url.href) : undefined;
      void tick().then(() => {
        const main = document.getElementById("altar-main");
        if (!main || version !== mainNavigation) return;
        main.scrollTop = position?.top ?? 0;
        main.scrollLeft = position?.left ?? 0;
      });
    }
    const pathname = page.url.pathname;
    const search = page.url.search;
    const selectedSession = selectedBridgeHref(pathname, resolve("/bridge"));
    const root = pathname === resolve("/bridge") || pathname === `${resolve("/bridge")}/`;
    const params = new URLSearchParams(search);
    const ordinaryRoot = root && !params.has("notes") && !params.has("investigation");
    if (selectedSession) {
      navigation.bridgePath = selectedSession;
      bridgeSession = decodeURIComponent(selectedSession.slice("/bridge/".length));
      bridgeSearch = search;
      dockOpen = true;
    } else if (ordinaryRoot) {
      bridgeSession = undefined;
      bridgeSearch = search;
      dockOpen = true;
    } else if (type !== "enter" && narrow && dockOpen) {
      dockOpen = false;
      void tick().then(() => document.getElementById("altar-main")?.focus({ preventScroll: true }));
    }
  });

  async function selectConversation(id: string, search: string) {
    const destination = `/bridge/${encodeURIComponent(id)}` as const;
    const params = page.url.searchParams;
    const legacy = page.url.pathname === resolve("/bridge") || !!selectedBridgeHref(page.url.pathname, resolve("/bridge"));
    if (legacy && !params.has("notes") && !params.has("investigation")) {
      await goto(resolve(`${destination}${search}`), { keepFocus: true, noScroll: true });
    } else {
      navigation.bridgePath = destination;
      bridgeSession = id;
      bridgeSearch = search;
    }
  }
  function toggleBridge() {
    if (dockOpen) { dockOpen = false; return; }
    const remembered = navigation.bridgePath;
    bridgeSession = remembered === "/bridge" ? undefined : decodeURIComponent(remembered.slice("/bridge/".length));
    bridgeSearch = "";
    dockOpen = true;
  }
  function connect() { connected = true; refreshAttention(); }

  let nextOmen = 0;
  let attentionVersion = 0;
  let attentionInFlight = false;
  let attentionQueued = false;
  let attentionTimer: number | undefined;
  let attentionFault = "";
  let mounted = false;

  function manageAboutDisclosure(node: HTMLDetailsElement) {
    let pinned = false;
    const application = node.classList.contains("application-menu");
    function dismissOutside(event: MouseEvent) {
      if (node.open && !event.composedPath().includes(node)) { node.open = false; pinned = false; }
    }

    function dismissOnEscape(event: KeyboardEvent) {
      if (event.key !== "Escape" || event.defaultPrevented || !node.open) return;
      node.open = false;
      pinned = false;
      node.querySelector("summary")?.focus();
      event.preventDefault();
    }

    function openOnHover() { if (application) node.open = true; }
    function closeAfterLeave() { if (application && !pinned && !node.contains(document.activeElement)) node.open = false; }
    function openOnFocus(event: FocusEvent) {
      if (application && !(event.relatedTarget instanceof Node && node.contains(event.relatedTarget))) node.open = true;
    }
    function closeAfterFocus(event: FocusEvent) {
      if (application && !(event.relatedTarget instanceof Node && node.contains(event.relatedTarget))) { node.open = false; pinned = false; }
    }
    function clickDisclosure(event: MouseEvent) {
      if (!application || !(event.target instanceof Element) || !event.target.closest("summary")) return;
      event.preventDefault();
      pinned = !pinned;
      node.open = pinned;
    }
    node.addEventListener("pointerenter", openOnHover);
    node.addEventListener("pointerleave", closeAfterLeave);
    node.addEventListener("focusin", openOnFocus);
    node.addEventListener("focusout", closeAfterFocus);
    node.addEventListener("click", clickDisclosure);
    window.addEventListener("click", dismissOutside);
    window.addEventListener("keydown", dismissOnEscape);
    return () => {
      node.removeEventListener("click", clickDisclosure);
      node.removeEventListener("pointerenter", openOnHover);
      node.removeEventListener("pointerleave", closeAfterLeave);
      node.removeEventListener("focusin", openOnFocus);
      node.removeEventListener("focusout", closeAfterFocus);
      window.removeEventListener("click", dismissOutside);
      window.removeEventListener("keydown", dismissOnEscape);
    };
  }

  const instruments = [
    { slug: "atlas", label: "Atlas" }, { slug: "orb", label: "Orb" },
    { slug: "loom", label: "Loom" }, { slug: "nexus", label: "Nexus" }
  ] as const;

  function attention(_event: Event) {
    // Instrument events are invalidation hints; only the shell status endpoint
    // owns the cross-session count.
    void refreshAttention();
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

  function clearAttentionTimer() {
    if (attentionTimer !== undefined) window.clearTimeout(attentionTimer);
    attentionTimer = undefined;
  }

  function refreshAttention() {
    if (!mounted || !available || document.visibilityState !== "visible") return;
    clearAttentionTimer();
    pending = null;
    const version = ++attentionVersion;
    if (attentionInFlight) {
      attentionQueued = true;
      return;
    }
    attentionInFlight = true;
    void readAttention(version);
  }

  async function readAttention(version: number) {
    try {
      const next = (await getAltarStatus()).pending_consents;
      if (mounted && version === attentionVersion) {
        pending = next;
        attentionFault = "";
      }
    } catch (error) {
      if (!mounted || version !== attentionVersion) return;
      pending = null;
      const message = error instanceof Error ? error.message : "The Altar cannot be reached.";
      if (message !== attentionFault) raiseOmen(message);
      attentionFault = message;
    } finally {
      attentionInFlight = false;
      if (mounted && available && document.visibilityState === "visible") {
        if (attentionQueued) {
          attentionQueued = false;
          refreshAttention();
        } else attentionTimer = window.setTimeout(refreshAttention, 5000);
      }
    }
  }

  function attentionVisibilityChanged() {
    if (document.visibilityState === "visible") refreshAttention();
    else {
      attentionVersion++;
      attentionQueued = false;
      pending = null;
      clearAttentionTimer();
    }
  }

  onMount(() => {
    mounted = true;
    void refreshAttention();
    window.addEventListener("altar:attention", attention);
    window.addEventListener("altar:omen", receiveOmen);
    return () => {
      mounted = false;
      attentionVersion++;
      attentionQueued = false;
      clearAttentionTimer();
      window.removeEventListener("altar:attention", attention);
      window.removeEventListener("altar:omen", receiveOmen);
    };
  });
</script>

<svelte:window onfocus={refreshAttention} />
<svelte:document onvisibilitychange={attentionVisibilityChanged} />

<a class="skip-link" href="#altar-main">Skip to instrument</a>
<header class="topbar" inert={narrow && dockOpen} {@attach measureMasthead}>
  <details class="altar-about" {@attach manageAboutDisclosure}>
    <summary class="brand" aria-label="About LychD — The Altar">
      <img class="mark" src={asset("/favicon.svg")} width="32" height="32" alt="" />
      <span class="brand-wordmark">
        <span class="name rune-head">LychD</span>
        <span class="sub">The Altar <span class="about-caret" aria-hidden="true">⌄</span></span>
      </span>
    </summary>
    <div class="altar-about__panel">
      <h2>About the Altar</h2>
      <p class="altar-about__version" title={__LYCHD_ALTAR_VERSION__}>
        Altar {__LYCHD_ALTAR_VERSION__.slice(0, 12)}
      </p>
      <div class="altar-about__links">
        <a href={__LYCHD_SOURCE_URL__} rel="noreferrer">{__LYCHD_SOURCE_LABEL__}</a>
      </div>
    </div>
  </details>

  <nav class="instruments" aria-label="Instruments">
    {#each instruments as instrument (instrument.slug)}
      <a
        href={resolve(`/${instrument.slug}`)}
        aria-current={page.url.pathname.startsWith(`/${instrument.slug}`) ? "page" : undefined}
      >
        <AltarIcon name={instrument.slug} /><span>{instrument.label}</span>
      </a>
    {/each}
  </nav>

  <details class="application-menu" {@attach manageAboutDisclosure}>
    <summary><AltarIcon name="applications" /><span>Applications</span><span aria-hidden="true">⌄</span></summary>
    <nav aria-label="Applications">
      <a href={resolve("/canvas")} aria-current={page.url.pathname === "/canvas" ? "page" : undefined}><AltarIcon name="canvas" />Canvas</a>
      <a href={resolve("/scavenger")} aria-current={page.url.pathname === "/scavenger" ? "page" : undefined}><AltarIcon name="scavenger" />Scavenger market</a>
    </nav>
  </details>

  <div class="spacer"></div>
  {#if available}
  <a
    class="sigil"
    data-state={pending === null ? "unknown" : pending > 0 ? "lit" : "dormant"}
    href={resolve("/bridge?attention=pending")}
  >
    ⬡ {pending === null ? "Consent status unknown" : pending > 0 ? `${pending} awaiting` : "Consent clear"}
  </a>
  {:else}<span class="offline-status">Offline · consent unavailable</span>{/if}
  <span class="sigil-identity" title="Fixed local authority context; not authentication">
    Local Sigil · <b>Magus</b>
  </span>
</header>

<div class="altar-workbench" style:height={`calc(100dvh - ${mastheadHeight}px)`}>
  <main id="altar-main" tabindex="-1" inert={narrow && dockOpen}>
    {@render children()}
  </main>
  <BridgeDock bind:open={dockOpen} bind:narrow forceOpen={!!selectedBridgeHref(page.url.pathname, resolve("/bridge")) || (page.url.pathname === resolve("/bridge") && !page.url.searchParams.has("notes") && !page.url.searchParams.has("investigation"))} {available} {viewing} onconnect={connect} onexpand={toggleBridge}>
    {#if available}<BridgeView embedded sessionId={bridgeSession} search={bridgeSearch} onNavigate={selectConversation} />{/if}
  </BridgeDock>
</div>

<div class="omen-stack" role="status" aria-live="polite">
  {#each omens as omen (omen.id)}
    <div class="omen" data-state={omen.fault ? "fault" : "info"}>
      <span>{omen.text}</span>
      <button class="dismiss" type="button" onclick={() => dismiss(omen.id)} aria-label="Dismiss">✕</button>
    </div>
  {/each}
</div>

<style>
  .topbar { height: auto; min-height: 3.5rem; padding: 0 1.25rem; gap: 1.25rem; flex: 0 0 auto; flex-wrap: wrap; background: var(--color-obsidian); border: 0; border-bottom: 1px solid var(--color-engraving); border-image: none; box-shadow: none; backdrop-filter: none; position: relative; z-index: 40; }
  .brand { gap: .6rem; padding: .5rem 0; }
  .brand .name { font: 650 var(--text-lg)/1.2 var(--font-body); letter-spacing: .06em; }
  .brand .sub { font-size: .65rem; }
  nav.instruments { height: auto; align-self: stretch; gap: .25rem; margin-left: auto; }
  nav.instruments a { gap: .6rem; padding: .5rem .7rem; letter-spacing: 0; text-transform: none; color: var(--color-parchment); min-height: 3.5rem; }
  nav.instruments a :global(svg), .application-menu :global(svg) { color: var(--color-rune); flex: 0 0 auto; }
  nav.instruments a[aria-current="page"] { color: var(--color-bone); text-shadow: none; background: var(--color-obsidian-2); }
  .topbar .spacer { flex: 1 1 0; }
  .sigil { border-radius: var(--radius-glyph); padding: .45rem .6rem; box-shadow: none; animation: none; }
  .sigil-identity { display: none; }
  .offline-status { color: var(--color-ash); font-size: var(--text-xs); }
  .application-menu { position: relative; flex-shrink: 0; align-self: stretch; }
  .application-menu > summary { display: flex; align-items: center; gap: .65rem; list-style: none; min-height: 3.5rem; padding: .5rem .25rem; color: var(--color-bone); cursor: pointer; font-size: var(--text-sm); }
  .application-menu > summary::-webkit-details-marker { display: none; }
  .application-menu nav { position: absolute; inset-block-start: 100%; inset-inline-start: -.5rem; z-index: 50; min-width: 14rem; padding: .35rem; background: var(--color-obsidian); border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); }
  .application-menu a { display: flex; align-items: center; gap: .75rem; min-height: 2.75rem; padding: .65rem; font-size: var(--text-sm); text-decoration: none; color: var(--color-bone); }
  .application-menu a:hover, .application-menu a[aria-current="page"] { background: var(--color-grimoire); }
  .altar-workbench { position: relative; display: flex; flex: 0 0 auto; min-width: 0; min-height: 0; overflow: hidden; background: var(--color-void); }
  #altar-main { flex: 1 1 0; min-width: 0; min-height: 0; overflow: auto; background: var(--color-void); }
  #altar-main::before, #altar-main::after { display: none; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 75rem) { .topbar { gap: .65rem; padding-inline: .75rem; } nav.instruments a { padding-inline: .5rem; gap: .4rem; } .offline-status { display: none; } }
  @media (max-width: 56rem) { .topbar { gap: .4rem .8rem; } .brand-wordmark .sub { display: none; } nav.instruments { order: 3; flex: 1 0 100%; justify-content: center; } nav.instruments a { min-height: 2.75rem; flex: 1; justify-content: center; } .topbar .spacer { display: none; } .application-menu { margin-left: auto; } .application-menu > summary { min-height: 3rem; } .application-menu nav { inset-inline-start: auto; inset-inline-end: 0; } .sigil { font-size: .65rem; } }
  @media (max-width: 30rem) { .brand .mark { width: 1.5rem; height: 1.5rem; } .brand .name { font-size: var(--text-sm); } .sigil { order: 4; margin: 0 auto .4rem; } .application-menu > summary { gap: .35rem; font-size: var(--text-xs); } }
</style>
