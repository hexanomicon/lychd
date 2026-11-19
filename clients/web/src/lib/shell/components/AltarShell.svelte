<script lang="ts">
  import { page } from "$app/state";
  import { afterNavigate, beforeNavigate, goto } from "$app/navigation";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { onMount, setContext, tick, untrack, type Snippet } from "svelte";
  import MemoryPanel from "./MemoryPanel.svelte";
  import AltarRail from "./AltarRail.svelte";
  import AltarBrand from "./AltarBrand.svelte";
  import { createApplicationPins, setApplicationPins } from "$lib/navigation/application-pins.svelte";
  import { studioSession } from "$lib/pages/loom/studio/session";
  import { createEvaluationWorkspace, setEvaluationWorkspace } from "$lib/pages/loom/state/evaluation/workspace.svelte";
  import { createMemoryPanel, setMemoryPanel } from "$lib/memory/panel.svelte";
  import { notesFocusSelection } from "$lib/pages/bridge/state/archive/notes";
  import BridgeDock from "$lib/pages/bridge/components/BridgeDock.svelte";
  import BridgeView from "$lib/pages/bridge/components/BridgeView.svelte";
  import { altarNavigationContext, selectedBridgeHref, type AltarNavigation } from "$lib/navigation/instruments";

  import { createSeancesWorkspace, setSeancesWorkspace } from "$lib/seances/workspace.svelte";
  import { seanceHref } from "$lib/seances/material";
  import { navigationId } from "$lib/navigation/instruments";

  import { getAltarStatus } from "$lib/api/client";

  let { children, offline = false }: { children: Snippet; offline?: boolean } = $props();
  const applicationPins=setApplicationPins(createApplicationPins());
  onMount(()=>{applicationPins.load();});
  let connected = $state(false);
  const available = $derived(!offline || connected);
  let dockOpen = $state(true);
  let dockTool = $state("bridge");
  let narrow = $state(false);
  const bridgeFocused = $derived(
    !!selectedBridgeHref(page.url.pathname, resolve("/bridge")) ||
    ((page.url.pathname === resolve("/bridge") || page.url.pathname === `${resolve("/bridge")}/`) &&
      !page.url.searchParams.has("notes") && !page.url.searchParams.has("investigation"))
  );
  let resolvedBridgeSession = $state<string | null>(null);
  let bridgeView = $state<ReturnType<typeof BridgeView>>();
  function suspendBridgeVoice() { bridgeView?.suspendVoice(); }
  const memory = setMemoryPanel(createMemoryPanel(suspendBridgeVoice));
  const evaluationWorkspace = setEvaluationWorkspace(createEvaluationWorkspace());
  const bridgeModal = $derived(narrow && dockOpen && !bridgeFocused && !memory.isOpen);
  function memoryLocation(url?: { pathname: string; searchParams: Pick<URLSearchParams, "getAll" | "has"> }) {
    if (!url) return null;
    const root = url.pathname === resolve("/bridge") || url.pathname === `${resolve("/bridge")}/`;
    const values = url.searchParams.getAll("notes");
    const selection = values.length === 1 ? notesFocusSelection(values[0] ?? null) : null;
    return root && !url.searchParams.has("investigation") ? selection : null;
  }
  function readMemoryLocation() {
    const selection = memoryLocation(page.url);
    if (selection) memory.selectNotes(selection);
  }
  untrack(readMemoryLocation);
  function readBridgeVisibility() {
    return available && !memory.isOpen && ((dockOpen && dockTool === "bridge") || bridgeFocused) &&
      (typeof document === "undefined" || document.visibilityState !== "hidden");
  }
  let workHref = $state(untrack(() => bridgeFocused ? "/orb" : `${page.url.pathname}${page.url.search}`));
  const viewing = $derived.by(() => {
    const path = page.url.pathname;
    if (path.startsWith("/bridge")) return page.url.searchParams.has("notes") ? "Public notes" :
      page.url.searchParams.has("investigation") ? "Public source investigation" : "Conversation workspace";
    return ({ seances: "Séances", atlas: "Atlas", orb: "Orb", loom: "Loom", nexus: "Nexus", canvas: "Canvas", atelier: "Atelier", applications: "Applications", scavenger: "Scavenger market" } as Record<string, string>)[path.split("/")[1] ?? ""] ?? "Altar";
  });
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
    dockTool = "bridge";
    dockOpen = true;
  }));
  function guardMaterialUnload(event: BeforeUnloadEvent) {
    if (!seances.needsUnloadWarning && !evaluationWorkspace.needsUnloadWarning && !studioSession.dirty) return;
    event.preventDefault();
    event.returnValue = "";
  }

  const mainScroll = new Map<string, { top: number; left: number }>();
  let mainNavigation = 0;
  let navigatingFromBridge = false;
  beforeNavigate((event) => {
    memory.clearNotesNavigationApproval();
    const selection = memoryLocation(event.to?.url);
    if (selection && !memory.authorizeNotesNavigation(selection)) { event.cancel(); return; }
    const { from } = event;
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
    readMemoryLocation();
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
        if (version === mainNavigation && !memory.isOpen) document.getElementById("altar-main")?.focus({ preventScroll: true });
      });
    }
    if (selectedSession) {
      navigation.bridgePath = selectedSession;
      bridgeSession = decodeURIComponent(selectedSession.slice("/bridge/".length));
      bridgeSearch = search;
    } else if (ordinaryRoot) {
      bridgeSession = undefined;
      bridgeSearch = search;
    } else if (type !== "enter" && narrow && dockOpen && !memory.isOpen) {
      suspendBridgeVoice();
      dockOpen = false;
      void tick().then(() => { if (!memory.isOpen) document.getElementById("altar-main")?.focus({ preventScroll: true }); });
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
    { slug: "bridge", label: "Bridge", related: "/seances" },
    { slug: "atlas", label: "Atlas", related: "/canvas" },
    { slug: "loom", label: "Loom" },
    { slug: "orb", label: "Orb" },
    { slug: "nexus", label: "Nexus" }
  ] as const;

  function instrumentCurrent(instrument: typeof instruments[number], href: string): "page" | "location" | undefined {
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

<a inert={memory.isOpen} class="skip-link" href="#altar-main">Skip to instrument</a>
<div class="altar-frame">
<AltarRail instruments={instruments.map(item => {
  const href=resolve(item.slug==="bridge" ? navigation.bridgePath : `/${item.slug}`);
  return {...item,href,current:instrumentCurrent(item,href)};
})} pathname={page.url.pathname} {available} {pending} suspended={bridgeModal || memory.isOpen}>
  {#snippet brand()}<AltarBrand />{/snippet}
</AltarRail>
<div class="altar-workbench">
  <main id={bridgeFocused ? undefined : "altar-main"} tabindex="-1" hidden={bridgeFocused} inert={bridgeModal || memory.isOpen}>
    {@render children()}
  </main>
  <BridgeDock bind:tool={dockTool} suspended={memory.isOpen} bind:open={dockOpen} bind:narrow focused={bridgeFocused} focusHref={resolve(resolvedBridgeSession ? seanceHref(resolvedBridgeSession) : "/seances")} focusLabel={resolvedBridgeSession ? "Open Séance" : "Browse séances"} browseHref={resolve("/seances")} {workHref} {available} {viewing} onconnect={connect} onexpand={toggleBridge} onsuspend={suspendBridgeVoice}>
    {#if available}<BridgeView bind:this={bridgeView} visible={!memory.isOpen && ((dockOpen && dockTool === "bridge") || bridgeFocused)} isVisible={readBridgeVisibility} embedded={!bridgeFocused} sessionId={bridgeSession} search={bridgeSearch} onNavigate={selectConversation} onSessionResolved={(id) => { resolvedBridgeSession = id; }} />{/if}
  </BridgeDock>
</div>
</div>

<MemoryPanel state={memory} work={seances} liveSession={resolvedBridgeSession} />

<div inert={memory.isOpen} class="omen-stack" role="status" aria-live="polite">
  {#each omens as omen (omen.id)}
    <div class="omen" data-state={omen.fault ? "fault" : "info"}>
      <span>{omen.text}</span>
      <button class="dismiss" type="button" onclick={() => dismiss(omen.id)} aria-label="Dismiss">✕</button>
    </div>
  {/each}
</div>

<style>
  .altar-frame{display:flex;height:100dvh;min-height:0;min-width:0;background:var(--color-void)}
  .altar-workbench{position:relative;display:flex;flex:1;min-width:0;min-height:0;overflow:hidden;background:var(--color-void)}
  #altar-main{flex:1 1 0;min-width:0;min-height:0;overflow:auto;background:var(--color-void);container-type:inline-size;container-name:work-area}
  #altar-main::before,#altar-main::after{display:none}main[hidden]{display:none}
</style>
