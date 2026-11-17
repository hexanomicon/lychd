<script lang="ts">
  import { page } from "$app/state";
  import { afterNavigate, beforeNavigate, goto } from "$app/navigation";
  import { asset } from "$app/paths";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { onMount, setContext, tick, untrack, type Snippet } from "svelte";
  import BridgeDock from "$lib/pages/bridge/components/BridgeDock.svelte";
  import BridgeView from "$lib/pages/bridge/components/BridgeView.svelte";
  import AltarIcon from "./AltarIcon.svelte";
  import ConversationList from "$lib/components/conversation/ConversationList.svelte";
  import { dismissibleDetails } from "$lib/components/shared/dismissible";
  import { altarNavigationContext, bridgeHistoryContext, selectedBridgeHref, type AltarNavigation, type BridgeHistory, type BridgeHistoryHost } from "$lib/navigation/instruments";

  import { createSeancesWorkspace, setSeancesWorkspace } from "$lib/pages/seances/state/workspace.svelte";
  import { seanceHref } from "$lib/pages/seances/state/material";
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
  const viewing = $derived.by(() => {
    const path = page.url.pathname;
    if (path.startsWith("/bridge")) return page.url.searchParams.has("notes") ? "Public notes" :
      page.url.searchParams.has("investigation") ? "Public source investigation" : "Conversation workspace";
    return ({ seances: "Séances", atlas: "Atlas", orb: "Orb", loom: "Loom", nexus: "Nexus", canvas: "Canvas", scavenger: "Scavenger market" } as Record<string, string>)[path.split("/")[1] ?? ""] ?? "Altar";
  });
  // Navigation sidebar. Wide screens remember the expanded/collapsed (icon rail) choice;
  // narrow screens (`narrow`, shared with the Bridge dock) start as a rail and expand as a
  // temporary overlay that closes on navigation, Escape, or outside click.
  const sidebarStorageKey = "lychd.altar-sidebar.v1";
  let sidebarCollapsed = $state(false);
  let narrowSidebarOpen = $state(false);
  const sidebarExpanded = $derived(narrow ? narrowSidebarOpen : !sidebarCollapsed);
  function readSidebarPreference() {
    try {
      const saved = JSON.parse(localStorage.getItem(sidebarStorageKey) ?? "null") as { collapsed?: unknown } | null;
      if (typeof saved?.collapsed === "boolean") sidebarCollapsed = saved.collapsed;
    } catch { /* Optional layout preference. */ }
  }
  function toggleSidebar() {
    if (narrow) { narrowSidebarOpen = !narrowSidebarOpen; return; }
    sidebarCollapsed = !sidebarCollapsed;
    try { localStorage.setItem(sidebarStorageKey, JSON.stringify({ collapsed: sidebarCollapsed })); }
    catch { /* Optional layout preference. */ }
  }
  function closeNarrowSidebar() { narrowSidebarOpen = false; }
  function closeNarrowSidebarOnEscape(event: KeyboardEvent) {
    // Open disclosures (About, Applications) claim Escape first via preventDefault.
    if (event.key !== "Escape" || event.defaultPrevented || !narrow || !narrowSidebarOpen) return;
    narrowSidebarOpen = false;
    document.getElementById("altar-sidebar-toggle")?.focus();
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
  // BridgeView registers its conversation history here so the sidebar can list it.
  let bridgeHistory = $state.raw<BridgeHistory | null>(null);
  setContext<BridgeHistoryHost>(bridgeHistoryContext, {
    register(history) {
      bridgeHistory = history;
      return () => { if (bridgeHistory === history) bridgeHistory = null; };
    }
  });
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
    closeNarrowSidebar();
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

  const instruments = [
    { slug: "bridge", label: "Bridge", hint: "Talk", related: "/seances" },
    { slug: "atlas", label: "Atlas", hint: "Projects", related: "/canvas" },
    { slug: "loom", label: "Loom", hint: "Scores" },
    { slug: "nexus", label: "Nexus", hint: "Iron" },
    { slug: "orb", label: "Orb", hint: "Runs" }
  ] as const;

  function instrumentCurrent(instrument: typeof instruments[number], href: string) {
    const pathname = page.url.pathname;
    if (pathname === href || pathname === `${href}/`) return "page";
    const roots = [resolve(`/${instrument.slug}`)];
    if ("related" in instrument) roots.push(resolve(instrument.related));
    return roots.some(root => pathname === root || pathname.startsWith(`${root}/`)) ? "location" : undefined;
  }

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
    readSidebarPreference();
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

<svelte:window onfocus={refreshAttention} onbeforeunload={guardMaterialUnload} onkeydown={closeNarrowSidebarOnEscape} />
<svelte:document onvisibilitychange={attentionVisibilityChanged} />

<a class="skip-link" href="#altar-main">Skip to instrument</a>
<div class="altar-frame">
<aside class="altar-sidebar" aria-label="Altar" data-expanded={sidebarExpanded} data-overlay={narrow && narrowSidebarOpen} inert={bridgeModal}>
 <div class="sidebar-inner">
  <div class="sidebar-head">
  <details class="altar-about" {@attach dismissibleDetails}>
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
  <span class="wordmark label" aria-hidden="true">LychD <span>Altar</span></span>
  <a class="sidebar-icon" href={resolve("/seances")} aria-label="Search séances" title="Search séances"><AltarIcon name="search" size={20} /></a>
  <button id="altar-sidebar-toggle" class="sidebar-icon" type="button" aria-expanded={sidebarExpanded} aria-controls="altar-sidebar-nav" aria-label={sidebarExpanded ? "Collapse navigation" : "Expand navigation"} title={sidebarExpanded ? "Collapse navigation" : "Expand navigation"} onclick={toggleSidebar}>
    <AltarIcon name="sidebar" size={20} />
  </button>
  </div>

  {#if bridgeHistory}
    <button class="new-seance" data-new-seance type="button" disabled={bridgeHistory.creating} aria-busy={bridgeHistory.creating} title="New Séance" onclick={() => { bridgeHistory?.create(); closeNarrowSidebar(); }}>
      <AltarIcon name="compose" size={18} /><span class="label">{bridgeHistory.creating ? "Opening…" : "New Séance"}</span>
    </button>
  {/if}

  <nav id="altar-sidebar-nav" class="instruments" aria-label="Instruments">
    {#each instruments as instrument (instrument.slug)}
      {@const href = resolve(instrument.slug === "bridge" ? navigation.bridgePath : `/${instrument.slug}`)}
      <a {href} aria-current={instrumentCurrent(instrument, href)} title={instrument.label}>
        <AltarIcon name={instrument.slug} /><span class="label">{instrument.label}</span><span class="label hint" aria-hidden="true">{instrument.hint}</span>
      </a>
    {/each}
    <details class="application-menu">
      <summary title="Applications"><AltarIcon name="applications" /><span class="label">Applications</span><span class="caret" aria-hidden="true"><AltarIcon name="chevron" size={16} /></span></summary>
      <nav aria-label="Applications">
        <a href={resolve("/scavenger")} aria-current={page.url.pathname === resolve("/scavenger") ? "page" : undefined}><AltarIcon name="scavenger" /><span class="label">Scavenger market</span></a>
      </nav>
    </details>
  </nav>

  {#if bridgeHistory && sidebarExpanded}
    <div class="sidebar-history">
      <ConversationList history={bridgeHistory} variant="sidebar" onselect={closeNarrowSidebar} />
    </div>
  {/if}

  <div class="sidebar-foot">
  {#if available}
  {@const consentText = pending === null ? "Consent status unknown" : pending > 0 ? `${pending} awaiting consent` : "Consent clear"}
  <a
    class="sigil"
    data-state={pending === null ? "unknown" : pending > 0 ? "lit" : "dormant"}
    href={resolve("/bridge?attention=pending")}
    title={consentText}
  >
    <span aria-hidden="true">⬡</span> <span class="label">{consentText}</span>
    {#if pending}<span class="sigil-count" aria-hidden="true">{pending}</span>{/if}
  </a>
  {:else}<span class="offline-status" title="Offline · consent unavailable"><span aria-hidden="true">⊘</span> <span class="label">Offline · consent unavailable</span></span>{/if}
  <div class="sigil-identity" title="Fixed local authority context; not authentication">
    <span class="avatar" aria-hidden="true">M</span>
    <span class="label"><b>Magus</b><small>Local Sigil · {page.url.hostname}</small></span>
  </div>
  </div>
 </div>
</aside>
{#if narrow && narrowSidebarOpen}
  <!-- Click-away layer for the narrow-screen overlay; Escape and the toggle are the keyboard paths. -->
  <button class="sidebar-scrim" type="button" tabindex="-1" aria-label="Close navigation" onclick={closeNarrowSidebar}></button>
{/if}

<div class="altar-workbench">
  <main id={bridgeFocused ? undefined : "altar-main"} tabindex="-1" hidden={bridgeFocused} inert={bridgeModal}>
    {@render children()}
  </main>
  <BridgeDock bind:open={dockOpen} bind:narrow focused={bridgeFocused} focusHref={resolve(resolvedBridgeSession ? seanceHref(resolvedBridgeSession) : "/seances")} focusLabel={resolvedBridgeSession ? "Open Séance" : "Browse séances"} {available} {viewing} onconnect={connect} onexpand={toggleBridge} onsuspend={suspendBridgeVoice}>
    {#if available}<BridgeView bind:this={bridgeView} visible={dockOpen || bridgeFocused} isVisible={readBridgeVisibility} embedded={!bridgeFocused} sessionId={bridgeSession} search={bridgeSearch} onNavigate={selectConversation} onSessionResolved={(id) => { resolvedBridgeSession = id; }} />{/if}
  </BridgeDock>
</div>
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
  .altar-frame { position: relative; display: flex; height: 100dvh; min-height: 0; }
  .altar-sidebar { --sidebar-expanded: 17rem; --sidebar-rail: 3.75rem; position: relative; z-index: 40; flex: 0 0 var(--sidebar-expanded); min-width: 0; transition: flex-basis var(--duration-drift, 160ms) ease; }
  .altar-sidebar[data-expanded="false"] { flex-basis: var(--sidebar-rail); }
  .sidebar-inner { display: flex; flex-direction: column; gap: .5rem; width: 100%; height: 100%; padding: .75rem .625rem; background: var(--color-obsidian); border-inline-end: 1px solid var(--color-engraving); }
  /* Visually hidden but still announced, so links keep their names in the rail. */
  .altar-sidebar[data-expanded="false"] .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .sidebar-head { display: flex; align-items: center; gap: .25rem; }
  .altar-sidebar[data-expanded="false"] .sidebar-head { flex-direction: column; }
  .wordmark { flex: 1 1 auto; min-width: 0; margin-inline-start: .25rem; color: var(--color-bone); font: 600 var(--text-base)/1.4 var(--font-body); white-space: nowrap; }
  .wordmark span { color: var(--color-ash); font-weight: 400; }
  .sidebar-icon { display: grid; place-items: center; flex: 0 0 auto; width: 2.5rem; height: 2.5rem; padding: 0; border: 0; border-radius: var(--radius-rune); background: transparent; color: var(--color-ash); cursor: pointer; }
  .sidebar-icon:hover { color: var(--color-bone); background: var(--color-obsidian-2); }
  .new-seance { display: flex; align-items: center; gap: .75rem; min-height: 2.75rem; padding: .55rem .7rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); background: var(--color-obsidian-2); color: var(--color-bone); font: inherit; font-size: var(--text-sm); cursor: pointer; }
  .new-seance:hover:not(:disabled) { border-color: var(--color-rune); }
  .altar-sidebar[data-expanded="false"] .new-seance { justify-content: center; padding-inline: 0; }
  .sidebar-history { flex: 1 1 auto; min-height: 0; margin-inline: -.625rem; padding: .5rem .625rem; overflow-y: auto; border-top: 1px solid var(--color-engraving); }
  .sidebar-foot { display: flex; flex-direction: column; gap: .5rem; margin-top: auto; padding-top: .5rem; border-top: 1px solid var(--color-engraving); }
  /* Narrow screens: the rail stays in flow and the expanded panel floats over the work area. */
  .altar-sidebar[data-overlay="true"] { flex-basis: var(--sidebar-rail); }
  .altar-sidebar[data-overlay="true"] .sidebar-inner { position: absolute; inset-block: 0; inset-inline-start: 0; width: var(--sidebar-expanded); box-shadow: 0 0 2rem color-mix(in srgb, var(--color-void) 70%, transparent); }
  .sidebar-scrim { position: absolute; inset: 0; z-index: 39; padding: 0; border: 0; background: color-mix(in srgb, var(--color-void) 55%, transparent); cursor: default; }
  .brand { justify-content: center; width: 3rem; min-height: 3rem; padding: .125rem; }
  .brand:hover { background: var(--color-tertiary); }
  .altar-product { margin-top: .35rem; color: var(--color-parchment); font-size: var(--text-sm); }
  nav.instruments { display: flex; flex-direction: column; gap: .25rem; }
  nav.instruments > a .hint { margin-inline-start: auto; color: var(--color-ash); font-size: var(--text-xs); }
  nav.instruments > a { display: flex; align-items: center; gap: .75rem; padding: .55rem .7rem; color: var(--color-ash); font-size: var(--text-sm); text-decoration: none; min-height: 2.75rem; border: 1px solid transparent; border-radius: var(--radius-rune); transition: color var(--duration-drift), background var(--duration-drift); }
  nav.instruments > a :global(svg), .application-menu :global(svg) { color: currentColor; flex: 0 0 auto; }
  nav.instruments > a:hover { color: var(--color-bone); background: var(--color-obsidian-2); }
  nav.instruments > a[aria-current] { color: var(--color-accent); text-shadow: none; border-color: color-mix(in srgb,var(--color-accent) 25%,var(--color-engraving)); background: color-mix(in srgb,var(--color-accent) 10%,var(--color-obsidian)); }
  .altar-sidebar[data-expanded="false"] nav.instruments > a, .altar-sidebar[data-expanded="false"] .application-menu > summary { justify-content: center; padding-inline: 0; }
  .sigil { position: relative; display: flex; align-items: center; gap: .6rem; min-height: 2.5rem; border-radius: var(--radius-glyph); padding: .5rem .7rem; box-shadow: none; animation: none; border-color: transparent; }
  .sigil[data-state="lit"] { border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent); background: color-mix(in srgb, var(--color-accent) 10%, transparent); color: var(--color-accent); }
  .altar-sidebar[data-expanded="false"] .sigil[data-state="lit"] { border-color: transparent; background: transparent; }
  .sigil-count { display: none; position: absolute; inset-block-start: .1rem; inset-inline-end: .1rem; min-width: 1.1rem; padding: 0 .25rem; border-radius: 999px; background: var(--color-frost); color: var(--color-void); font-size: var(--text-2xs); line-height: 1.1rem; text-align: center; }
  .altar-sidebar[data-expanded="false"] .sigil { justify-content: center; padding-inline: 0; }
  .altar-sidebar[data-expanded="false"] .sigil-count { display: block; }
  .sigil-identity { display: flex; align-items: center; gap: .65rem; padding: .35rem .5rem; }
  .altar-sidebar[data-expanded="false"] .sigil-identity { justify-content: center; padding-inline: 0; }
  .avatar { display: grid; place-items: center; flex: 0 0 auto; width: 2rem; height: 2rem; border: 1px solid var(--color-engraving); border-radius: 50%; color: var(--color-bone); font-size: var(--text-xs); font-weight: 600; }
  .sigil-identity b { display: block; color: var(--color-bone); font-size: var(--text-sm); }
  .sigil-identity small { display: block; color: var(--color-ash); font: var(--text-2xs)/1.4 var(--font-glyph); }
  .offline-status { display: flex; align-items: center; gap: .6rem; color: var(--color-ash); font-size: var(--text-xs); }
  .altar-sidebar[data-expanded="false"] .offline-status { justify-content: center; }
  .application-menu > summary { display: flex; align-items: center; gap: .75rem; list-style: none; min-height: 2.75rem; padding: .55rem .7rem; border-radius:var(--radius-rune); color: var(--color-ash); cursor: pointer; font-size: var(--text-sm); }
  .application-menu > summary:hover { color:var(--color-bone); background:var(--color-obsidian-2); }
  .application-menu > summary::-webkit-details-marker { display: none; }
  .application-menu .caret { display: grid; margin-inline-start: auto; transition: transform var(--duration-drift, 160ms) ease; }
  .application-menu[open] .caret { transform: rotate(180deg); }
  .altar-sidebar[data-expanded="false"] .application-menu .caret { display: none; }
  .application-menu nav { display: flex; flex-direction: column; gap: .15rem; padding-inline-start: 1.25rem; }
  .altar-sidebar[data-expanded="false"] .application-menu nav { padding-inline-start: 0; }
  .application-menu a { display: flex; align-items: center; gap: .75rem; min-height: 2.5rem; padding: .45rem .7rem; border-radius: var(--radius-rune); font-size: var(--text-sm); letter-spacing: 0; text-transform: none; text-decoration: none; color: var(--color-ash); }
  .altar-sidebar[data-expanded="false"] .application-menu a { justify-content: center; padding-inline: 0; }
  .application-menu a:hover, .application-menu a[aria-current="page"] { color: var(--color-bone); background: var(--color-obsidian-2); }
  .altar-workbench { position: relative; display: flex; flex: 1 1 0; height: 100%; min-width: 0; min-height: 0; overflow: hidden; background: var(--color-void); }
  #altar-main { flex: 1 1 0; min-width: 0; min-height: 0; overflow: auto; background: var(--color-void); container-type: inline-size; container-name: work-area; }
  #altar-main::before, #altar-main::after { display: none; }
  main[hidden] { display: none; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (prefers-reduced-motion: reduce) { .altar-sidebar, nav.instruments > a, .application-menu .caret { transition: none; } }
</style>
