<script lang="ts">
  import { page } from "$app/state";
  import { afterNavigate, beforeNavigate, goto } from "$app/navigation";
  import { asset } from "$app/paths";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { onMount, setContext, tick, untrack, type Snippet } from "svelte";
  import BridgeDock from "./BridgeDock.svelte";
  import BridgeView from "./BridgeView.svelte";
  import AltarIcon from "./AltarIcon.svelte";
  import { altarNavigationContext, selectedBridgeHref, type AltarNavigation } from "$lib/navigation/instruments";

  import { createSeancesWorkspace, setSeancesWorkspace } from "$lib/seances/workspace.svelte";
  import { seanceHref } from "$lib/seances/material";
  import { navigationId } from "$lib/navigation/instruments";

  import { getAltarStatus } from "$lib/api/client";

  let { children, offline = false }: { children: Snippet; offline?: boolean } = $props();
  let connected = $state(false);
  const available = $derived(!offline || connected);
  let dockOpen = $state(true);
  let narrow = $state(false);
  const bridgeFocused = $derived(
    !!selectedBridgeHref(page.url.pathname, resolve("/bridge")) ||
    ((page.url.pathname === resolve("/bridge") || page.url.pathname === `${resolve("/bridge")}/`) &&
      !page.url.searchParams.has("notes") && !page.url.searchParams.has("investigation"))
  );
  const bridgeModal = $derived(narrow && dockOpen && !bridgeFocused);
  let resolvedBridgeSession = $state<string | null>(null);
  let bridgeView = $state<ReturnType<typeof BridgeView>>();
  function suspendBridgeVoice() { bridgeView?.suspendVoice(); }
  function readBridgeVisibility() {
    return available && (dockOpen || bridgeFocused) &&
      (typeof document === "undefined" || document.visibilityState !== "hidden");
  }
  let workHref = $state(untrack(() => bridgeFocused ? "/orb" : `${page.url.pathname}${page.url.search}`));
  const viewing = $derived.by(() => {
    const path = page.url.pathname;
    if (path.startsWith("/bridge")) return page.url.searchParams.has("notes") ? "Public notes" :
      page.url.searchParams.has("investigation") ? "Public source investigation" : "Conversation workspace";
    return ({ seances: "Séances", atlas: "Atlas", orb: "Orb", loom: "Loom", nexus: "Nexus", canvas: "Canvas", scavenger: "Scavenger market" } as Record<string, string>)[path.split("/")[1] ?? ""] ?? "Altar";
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
    return initialPath || ((page.url.pathname === resolve("/bridge") || page.url.pathname === `${resolve("/bridge")}/`) && !params.has("notes") && !params.has("investigation"))
      ? page.url.search : "";
  }));
  let pending = $state<number | null>(null);
  let omens = $state<Array<{ id: number; text: string; fault: boolean }>>([]);
  const navigation = $state<AltarNavigation>({ bridgePath: initialPath ?? "/bridge" });
  setContext(altarNavigationContext, navigation);
  const seances = setSeancesWorkspace(createSeancesWorkspace(async (id) => {
    if (navigationId(id) !== id) return;
    suspendBridgeVoice();
    bridgeView?.focusSessionComposer(id);
    navigation.bridgePath = `/bridge/${encodeURIComponent(id)}`;
    bridgeSession = id;
    bridgeSearch = "";
    dockOpen = true;
  }));
  function guardMaterialUnload(event: BeforeUnloadEvent) {
    if (!seances.needsUnloadWarning) return;
    event.preventDefault();
    event.returnValue = "";
  }

  const mainScroll = new Map<string, { top: number; left: number }>();
  let mainNavigation = 0;
  let navigatingFromBridge = false;
  beforeNavigate(({ from }) => {
    suspendBridgeVoice();
    navigatingFromBridge = bridgeFocused;
    if (!bridgeFocused) workHref = `${page.url.pathname}${page.url.search}`;
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
    if (navigatingFromBridge && !bridgeFocused) {
      if (!narrow) dockOpen = true;
      void tick().then(() => {
        if (version === mainNavigation) document.getElementById("altar-main")?.focus({ preventScroll: true });
      });
    }
    if (selectedSession) {
      navigation.bridgePath = selectedSession;
      bridgeSession = decodeURIComponent(selectedSession.slice("/bridge/".length));
      bridgeSearch = search;
    } else if (ordinaryRoot) {
      bridgeSession = undefined;
      bridgeSearch = search;
    } else if (type !== "enter" && narrow && dockOpen) {
      suspendBridgeVoice();
      dockOpen = false;
      void tick().then(() => document.getElementById("altar-main")?.focus({ preventScroll: true }));
    }
  });

  async function selectConversation(id: string, search: string) {
    const destination = `/bridge/${encodeURIComponent(id)}` as const;
    const params = page.url.searchParams;
    const legacy = page.url.pathname === resolve("/bridge") || page.url.pathname === `${resolve("/bridge")}/` || !!selectedBridgeHref(page.url.pathname, resolve("/bridge"));
    if (legacy && !params.has("notes") && !params.has("investigation")) {
      await goto(resolve(`${destination}${search}`), { reset: false });
    } else {
      navigation.bridgePath = destination;
      bridgeSession = id;
      bridgeSearch = search;
    }
  }
  function toggleBridge() {
    if (dockOpen) { if (!bridgeFocused) suspendBridgeVoice(); dockOpen = false; return; }
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
    { slug: "seances", label: "Séances" }, { slug: "atlas", label: "Atlas" },
    { slug: "canvas", label: "Canvas" }, { slug: "orb", label: "Orb" },
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
      suspendBridgeVoice();
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

<svelte:window onfocus={refreshAttention} onbeforeunload={guardMaterialUnload} />
<svelte:document onvisibilitychange={attentionVisibilityChanged} />

<a class="skip-link" href="#altar-main">Skip to instrument</a>
<header class="topbar" inert={bridgeModal} {@attach measureMasthead}>
  <details class="altar-about" {@attach manageAboutDisclosure}>
    <summary class="brand" aria-label="About Altar" title="Altar">
      <img class="mark" src={asset("altar-mark.svg")} width="44" height="44" alt="" />
    </summary>
    <div class="altar-about__panel">
      <h2>About the Altar</h2>
      <p class="altar-product">LychD · The Altar</p>
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
  <main id={bridgeFocused ? undefined : "altar-main"} tabindex="-1" hidden={bridgeFocused} inert={bridgeModal}>
    {@render children()}
  </main>
  <BridgeDock bind:open={dockOpen} bind:narrow focused={bridgeFocused} focusHref={resolve(resolvedBridgeSession ? seanceHref(resolvedBridgeSession) : "/seances")} focusLabel={resolvedBridgeSession ? "Open Séance" : "Browse séances"} {workHref} {available} {viewing} onconnect={connect} onexpand={toggleBridge} onsuspend={suspendBridgeVoice}>
    {#if available}<BridgeView bind:this={bridgeView} visible={dockOpen || bridgeFocused} isVisible={readBridgeVisibility} embedded={!bridgeFocused} sessionId={bridgeSession} search={bridgeSearch} onNavigate={selectConversation} onSessionResolved={(id) => { resolvedBridgeSession = id; }} />{/if}
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
  .topbar { height: auto; min-height: 4rem; padding: .5rem 1.25rem; gap: .75rem; flex: 0 0 auto; flex-wrap: wrap; background: var(--color-obsidian); border: 0; border-bottom: 1px solid var(--color-engraving); border-image: none; box-shadow: none; backdrop-filter: none; position: relative; z-index: 40; }
  .brand { justify-content: center; width: 3rem; min-height: 3rem; padding: .125rem; }
  .brand:hover { background: var(--color-tertiary); }
  .altar-product { margin-top: .35rem; color: var(--color-parchment); font-size: var(--text-sm); }
  nav.instruments { height: auto; align-self: center; gap: .25rem; margin-left: .5rem; }
  nav.instruments a { gap: .6rem; padding: .65rem .85rem; letter-spacing: 0; text-transform: none; color: var(--color-ash); min-height: 2.75rem; border: 1px solid transparent; border-radius: var(--radius-rune); }
  nav.instruments a :global(svg), .application-menu :global(svg) { color: currentColor; flex: 0 0 auto; }
  nav.instruments a:hover { color: var(--color-bone); background: var(--color-obsidian-2); }
  nav.instruments a[aria-current="page"] { color: var(--color-accent); text-shadow: none; border-color: color-mix(in srgb,var(--color-accent) 25%,var(--color-engraving)); background: color-mix(in srgb,var(--color-accent) 10%,var(--color-obsidian)); }
  .topbar .spacer { flex: 1 1 0; }
  .sigil { border-radius: var(--radius-rune); padding: .55rem .7rem; box-shadow: none; animation: none; border-color: transparent; }
  .sigil-identity { display: none; }
  .offline-status { color: var(--color-ash); font-size: var(--text-xs); }
  .application-menu { position: relative; flex-shrink: 0; align-self: center; }
  .application-menu > summary { display: flex; align-items: center; gap: .5rem; list-style: none; min-height: 2.75rem; padding: .5rem .65rem; border-radius:var(--radius-rune); color: var(--color-ash); cursor: pointer; font-size: var(--text-xs); }
  .application-menu > summary:hover { color:var(--color-bone); background:var(--color-obsidian-2); }
  .application-menu > summary::-webkit-details-marker { display: none; }
  .application-menu nav { position: absolute; inset-block-start: 100%; inset-inline-start: -.5rem; z-index: 50; min-width: 14rem; padding: .35rem; background: var(--color-tertiary); border: 1px solid var(--color-tertiary-edge); border-radius: var(--radius-glyph); }
  .application-menu a { display: flex; align-items: center; gap: .75rem; min-height: 2.75rem; padding: .65rem; font-size: var(--text-sm); text-decoration: none; color: var(--color-bone); }
  .application-menu a:hover, .application-menu a[aria-current="page"] { background: color-mix(in srgb, var(--color-rune) 10%, var(--color-tertiary)); }
  .altar-workbench { position: relative; display: flex; flex: 0 0 auto; min-width: 0; min-height: 0; overflow: hidden; background: var(--color-void); }
  #altar-main { flex: 1 1 0; min-width: 0; min-height: 0; overflow: auto; background: var(--color-void); container-type: inline-size; container-name: work-area; }
  #altar-main::before, #altar-main::after { display: none; }
  main[hidden] { display: none; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 75rem) { .topbar { gap: .65rem; padding-inline: .75rem; } nav.instruments a { padding-inline: .5rem; gap: .4rem; } .offline-status { display: none; } }
  @media (max-width: 56rem) { .topbar { display: grid; grid-template-columns: 3rem minmax(0, 1fr) auto; gap: .25rem .5rem; padding: .25rem .5rem .5rem; } .altar-about { grid-column: 1; grid-row: 1; } nav.instruments { grid-column: 1 / -1; grid-row: 2; width: 100%; margin: 0; justify-content: center; } nav.instruments a { min-height: 2.75rem; flex: 1; justify-content: center; } .topbar .spacer { display: none; } .application-menu { grid-column: 2; grid-row: 1; margin: 0; } .application-menu > summary { min-height: 2.75rem; gap: .4rem; font-size: var(--text-xs); } .application-menu nav { inset-inline-start: 0; inset-inline-end: auto; } .sigil { grid-column: 3; grid-row: 1; margin: 0; max-width: 100%; font-size: var(--text-xs); line-height: 1.3; white-space: normal; } }
  @media (max-width: 36rem) { nav.instruments { gap: 0; } nav.instruments a { flex-direction: column; gap: .2rem; padding: .4rem .2rem; font-size: var(--text-xs); } }
</style>
