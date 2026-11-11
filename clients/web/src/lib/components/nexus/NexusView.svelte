<script lang="ts">
  import { beforeNavigate, goto } from "$app/navigation";
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import { page } from "$app/state";
  import { onMount, tick, untrack } from "svelte";

  import {
    ApiError,
    createNexusSwap,
    getNexusPlan,
    getNexusSnapshot,
    getNexusSwap,
    getNexusTransition,
    listenToSwap
  } from "$lib/api/client";
  import type {
    NexusCovenRow,
    NexusSnapshot,
    SwapTicket,
    TransitionPlan,
    TransitionRecordView
  } from "$lib/api/models";
  import DelegateMark from "../shared/DelegateMark.svelte";
  import NexusMap from "./NexusMap.svelte";
  import NexusProperties from "./NexusProperties.svelte";
  import PageHeader from "../shared/PageHeader.svelte";
  import { createNexusMap } from "$lib/nexus/map";

  type Preview = { target: string; plan: TransitionPlan };

  let snapshot = $state.raw<NexusSnapshot | null>(null);
  let preview = $state.raw<Preview | null>(null);
  let viewMode = $state<"map" | "list">("map");
  const viewStorageKey = "lychd.nexus.view.v1";
  let selectedObjectId = $state<string | null>(null);
  let objectInspector: HTMLElement | undefined;
  let objectReturnFocus: HTMLElement | undefined;
  const mapModel = $derived(snapshot ? createNexusMap(snapshot, preview?.plan ?? null, preview?.target ?? null) : null);
  const selectedObject = $derived(mapModel?.objects.find((object) => object.id === selectedObjectId) ?? null);
  onMount(() => {
    let saved: string | null = null;
    try { saved = localStorage.getItem(viewStorageKey); } catch { /* Optional view preference. */ }
    viewMode = saved === "map" || saved === "list" ? saved : window.matchMedia?.("(max-width: 48rem)").matches ? "list" : "map";
  });
  function changeView(mode: "map" | "list") {
    viewMode = mode;
    try { localStorage.setItem(viewStorageKey, mode); } catch { /* Optional view preference. */ }
  }
  function selectObject(id: string, opener?: HTMLElement) {
    selectedObjectId = id;
    objectReturnFocus = opener;
    void tick().then(() => { if (!destroyed) objectInspector?.focus(); });
  }
  function inspectCapability(key: string, opener: HTMLElement, scope: "managed" | "portal" = "managed") {
    const object = mapModel?.objects.find((item) => item.kind === "capability" && item.scope === scope && item.row.capability_key === key);
    if (object) selectObject(object.id, opener);
  }
  function inspectRuntime(id: string, opener: HTMLElement) {
    const object = mapModel?.objects.find((item) => item.kind === "delegated" && item.runtime.runtime_id === id);
    if (object) selectObject(object.id, opener);
  }
  async function closeObject() {
    selectedObjectId = null;
    await tick();
    const visibleOpener = objectReturnFocus?.isConnected && !objectReturnFocus.closest("[hidden], [inert], details:not([open])");
    const target = visibleOpener ? objectReturnFocus : document.querySelector<HTMLButtonElement>(".nexus-viewbar button[aria-pressed='true']");
    target?.focus();
    objectReturnFocus = undefined;
  }
  function captureObjectInspector(node: HTMLElement) {
    objectInspector = node;
    return () => { if (objectInspector === node) objectInspector = undefined; };
  }
  let previewTarget = $state<string | null>(null);
  let previewLoading = $state(false);
  let selectedTransition = $state.raw<TransitionRecordView | null>(null);
  let selectedTransitionRequestId: string | null = null;
  let ticket = $state.raw<SwapTicket | null>(null);
  let ticketStale = $state(false);
  let loading = $state(true);
  let refreshing = $state(false);
  let snapshotStale = $state(false);
  let busy = $state(false);
  let submittingTarget = $state<string | null>(null);
  let error = $state("");
  let transitionNote = $state("");
  let previewVersion = 0;
  let transitionVersion = 0;
  let refreshInFlight: Promise<void> | null = null;
  let refreshQueued = false;
  let closeStream: (() => void) | null = null;
  let planInspector: HTMLElement | undefined;
  let transitionInspector: HTMLElement | undefined;
  let planReturnFocus: HTMLElement | undefined;
  let transitionReturnFocus: HTMLElement | undefined;
  let destroyed = false;
  const recoveredTickets = new Set<string>();
  let swapAttempts = $state.raw<ReadonlyMap<string, string>>(new Map());

  beforeNavigate((navigation) => {
    if (!swapAttempts.size) return;
    if (!navigation.willUnload && navigation.to && navigation.from && navigation.to.url.origin === navigation.from.url.origin &&
        navigation.to.url.pathname === navigation.from.url.pathname) return;
    if (navigation.type === "leave" || !window.confirm(busy
      ? "A transition request is still in progress. Leave before its outcome is known?"
      : "The transition outcome is unknown. Leave Nexus and lose the prepared retry?")) navigation.cancel();
  });

  let requestedTransitionId = $derived(page.url.searchParams.get("transition"));
  let requestedEventId = $derived(page.url.searchParams.get("event"));

  $effect(() => {
    let cancelled = false;
    let timer: number | undefined;
    let initial = true;

    async function poll() {
      await refresh(initial);
      initial = false;
      if (!cancelled) timer = window.setTimeout(() => void poll(), 5000);
    }

    void poll();
    return () => {
      cancelled = true;
      destroyed = true;
      if (timer !== undefined) window.clearTimeout(timer);
      closeStream?.();
    };
  });

  $effect(() => {
    const requestId = requestedTransitionId;
    if (requestId) untrack(() => void selectTransition(requestId));
    else {
      transitionVersion++;
      selectedTransitionRequestId = null;
      selectedTransition = null;
      transitionNote = "";
    }
  });

  function refresh(showLoading = true): Promise<void> {
    if (destroyed) return Promise.resolve();
    if (refreshInFlight) {
      refreshQueued = true;
      return refreshInFlight;
    }
    const pending = performRefresh(showLoading);
    refreshInFlight = pending;
    void pending.finally(() => {
      if (refreshInFlight !== pending) return;
      refreshInFlight = null;
      if (refreshQueued && !destroyed) {
        refreshQueued = false;
        void refresh(false);
      }
    });
    return pending;
  }

  async function performRefresh(showLoading: boolean) {
    refreshing = true;
    if (showLoading) loading = true;
    try {
      const next = await getNexusSnapshot();
      if (destroyed) return;
      snapshot = next;
      snapshotStale = false;
      error = "";
      const transitionRequestId = requestedTransitionId ?? selectedTransitionRequestId;
      if (transitionRequestId) {
        await selectTransition(transitionRequestId, false);
      }
    } catch (cause) {
      if (!destroyed) {
        snapshotStale = true;
        if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
          snapshot = null;
          previewVersion++;
          preview = null;
          previewTarget = null;
          previewLoading = false;
          transitionVersion++;
          selectedTransition = null;
          closeStream?.();
          closeStream = null;
          ticket = null;
        }
        error = cause instanceof Error ? cause.message : "The Nexus cannot be read.";
      }
    } finally {
      if (!destroyed) {
        refreshing = false;
        if (showLoading) loading = false;
      }
    }
  }

  async function selectTransition(requestId: string, focus = true) {
    if (destroyed) return;
    selectedTransitionRequestId = requestId;
    const version = ++transitionVersion;
    previewVersion++;
    preview = null;
    previewTarget = null;
    previewLoading = false;
    transitionNote = "";
    const retained = snapshot?.transitions.find((item) => item.request_id === requestId);
    if (retained) {
      selectedTransition = retained;
      if (focus) await focusInspector(transitionInspector);
      return;
    }
    try {
      const exact = await getNexusTransition(requestId);
      if (destroyed || version !== transitionVersion) return;
      selectedTransition = exact;
      if (focus) await focusInspector(transitionInspector);
    } catch (cause) {
      if (destroyed || version !== transitionVersion) return;
      selectedTransition = null;
      const message = cause instanceof Error ? cause.message : "The exact request could not be read.";
      transitionNote = message.includes("not retained")
        ? "This process no longer retains that transition’s latest observation."
        : `The selected transition could not be refreshed: ${message}`;
    }
  }

  async function previewTransition(target: string, opener?: HTMLElement) {
    if (destroyed || busy) return;
    planReturnFocus = opener;
    const version = ++previewVersion;
    preview = null;
    previewTarget = target;
    previewLoading = true;
    error = "";
    await clearTransition(false);
    if (destroyed || version !== previewVersion) return;
    await focusInspector(planInspector);
    try {
      const plan = await getNexusPlan(target);
      if (!destroyed && version === previewVersion) {
        preview = { target, plan };
      }
    } catch (cause) {
      if (!destroyed && version === previewVersion) {
        error = cause instanceof Error ? cause.message : "The transition cannot be calculated.";
      }
    } finally {
      if (!destroyed && version === previewVersion) previewLoading = false;
    }
  }

  async function closePreview() {
    const target = planReturnFocus;
    planReturnFocus = undefined;
    previewVersion++;
    preview = null;
    previewTarget = null;
    previewLoading = false;
    await tick();
    if (target?.isConnected && !target.closest("[hidden], [inert]")) target.focus();
    else document.querySelector<HTMLButtonElement>(".nexus-viewbar button[aria-pressed='true']")?.focus();
  }

  async function focusInspector(element: HTMLElement | undefined) {
    await tick();
    if (!destroyed) element?.focus();
  }

  function capturePlanInspector(node: HTMLElement) {
    planInspector = node;
    return () => {
      if (planInspector === node) planInspector = undefined;
    };
  }

  function captureTransitionInspector(node: HTMLElement) {
    transitionInspector = node;
    return () => {
      if (transitionInspector === node) transitionInspector = undefined;
    };
  }

  async function clearTransition(restoreFocus = true) {
    const target = restoreFocus ? transitionReturnFocus : undefined;
    transitionReturnFocus = undefined;
    transitionVersion++;
    selectedTransitionRequestId = null;
    selectedTransition = null;
    transitionNote = "";
    if (!requestedTransitionId) {
      await tick();
      if (target?.isConnected) target.focus();
      return;
    }
    const url = new URL(page.url.href);
    url.searchParams.delete("transition");
    url.searchParams.delete("event");
    const nexusPath = `/nexus${url.search}` as "/nexus" | `/nexus?${string}`;
    await goto(resolve(nexusPath), {
      replace: true,
      reset: false
    });
    await tick();
    if (target?.isConnected) target.focus();
  }

  async function swap() {
    const selected = preview;
    if (destroyed || !selected || busy || snapshotStale || snapshot?.containment_reason || selected.plan.action_type === "NO_OP") return;
    const previousRequestId = swapAttempts.get(selected.target);
    const requestId = previousRequestId ?? crypto.randomUUID();
    swapAttempts = new Map([...swapAttempts, [selected.target, requestId]]);
    busy = true;
    submittingTarget = selected.target;
    error = "";
    try {
      const accepted = await createNexusSwap(selected.target, requestId);
      if (destroyed) return;
      ticket = accepted.ticket;
      ticketStale = false;
      forgetAttempt(selected.target);
      followTicket(accepted.ticket.id);
    } catch (cause) {
      if (destroyed) return;
      const definitiveRejection =
        previousRequestId === undefined &&
        cause instanceof ApiError &&
        cause.status !== undefined &&
        cause.status < 500 &&
        cause.status !== 409 &&
        cause.status !== 408;
      if (definitiveRejection) forgetAttempt(selected.target);
      error = cause instanceof Error ? cause.message : "The transition was refused.";
    } finally {
      if (!destroyed) { busy = false; submittingTarget = null; }
    }
  }

  function forgetAttempt(target: string) {
    swapAttempts = new Map([...swapAttempts].filter(([key]) => key !== target));
  }

  function followTicket(ticketId: string) {
    if (destroyed) return;
    closeStream?.();
    let hardClosed = false;
    let close: (() => void) | undefined;
    close = listenToSwap(
      ticketId,
      (event) => {
        if (destroyed) return;
        ticket = event.ticket;
        ticketStale = false;
        if (event.ticket.state !== "warming") {
          closeStream = null;
          void refresh(false);
          void selectTransition(event.ticket.request_id);
        }
      },
      (message) => {
        if (destroyed) return;
        window.dispatchEvent(
          new CustomEvent("altar:omen", { detail: { text: message, fault: false } })
        );
      },
      {
        onHardClose: () => {
          if (destroyed) return;
          hardClosed = true;
          if (close === undefined || closeStream === close) closeStream = null;
          if (ticket?.id === ticketId && ticket.state === "warming") {
            ticketStale = true;
          }
          void recoverHardClosedTicket(ticketId);
        }
      }
    );
    if (!hardClosed) closeStream = close;
  }

  async function recoverHardClosedTicket(ticketId: string) {
    if (recoveredTickets.has(ticketId)) return;
    recoveredTickets.add(ticketId);
    try {
      const recovered = await getNexusSwap(ticketId);
      if (destroyed || ticket?.id !== ticketId) return;
      ticket = recovered.ticket;
      ticketStale = false;
      if (recovered.ticket.state === "warming") {
        followTicket(ticketId);
      } else {
        void refresh(false);
        void selectTransition(recovered.ticket.request_id);
      }
    } catch {
      if (!destroyed) {
        window.dispatchEvent(
          new CustomEvent("altar:omen", {
            detail: {
              text: "The transition projection remains stale; refresh the Nexus to retry.",
              fault: true
            }
          })
        );
      }
    }
  }


</script>

<svelte:head><title>Nexus — LychD</title></svelte:head>

{#snippet capability(row: NexusCovenRow, readOnly = false)}
  {@const inspecting = selectedObject?.kind === "capability" && selectedObject.scope === (readOnly ? "portal" : "managed") && selectedObject.row.capability_key === row.capability_key}
  <article class="capability-row" data-selected={inspecting} data-preview={!readOnly && previewTarget === row.capability_key}>
    <div class="cap">
      <button class="key inspect-object" type="button" id={`${readOnly ? "remote" : "managed"}-${row.capability_key}`}
        aria-label={`Inspect ${readOnly ? "portal" : "managed"} capability ${row.capability_key}`}
        aria-pressed={inspecting}
        onclick={(event) => inspectCapability(row.capability_key, event.currentTarget, readOnly ? "portal" : "managed")}>{row.capability_key}</button>
      <span class="chip" data-state={row.state}>{row.state}</span>
      {#if !readOnly && previewTarget === row.capability_key}<span class="preview-marker">Preview target</span>{/if}
      <time class="probe-time" datetime={row.checked_at ?? undefined} title={row.checked_at ?? undefined}>
        {row.checked_at ? `checked ${new Date(row.checked_at).toLocaleTimeString()}` : "freshness unknown"}
      </time>
      {#if readOnly}<span class="read-only">read only</span>
      {:else}
        <button class="preview-trigger" type="button" disabled={busy}
          aria-describedby={`managed-${row.capability_key}`} aria-controls="nexus-preview"
          aria-expanded={previewTarget === row.capability_key}
          onclick={(event) => previewTransition(row.capability_key, event.currentTarget)}>Preview</button>
      {/if}
    </div>
    <details class="capability-detail">
      <summary aria-label={`Observation details for ${row.capability_key}`}>Observation details</summary>
      <dl class="kv">
        <dt>Animator</dt><dd>{row.animator_name}</dd>
        <dt>family</dt><dd>{row.family}</dd>
        <dt>model</dt><dd>{row.model_id}</dd>
        <dt>runtime</dt><dd>{row.runtime}</dd>
        <dt>health</dt><dd>{row.health}</dd>
        <dt>warm</dt><dd>{row.warm ? "yes" : "no"}</dd>
        <dt>reason</dt><dd>{row.reason ?? "none reported"}</dd>
      </dl>
    </details>
  </article>
{/snippet}

<div class="instrument-deck instrument-deck--nexus">
  <section class="nexus-main" aria-label="Capability observations">
    <PageHeader title="Nexus" kicker="Capability observations" description="Inspect an object. Preview what a change would affect." />
    <div class="snapshot-bar">
      <div>
        {#if snapshot}<time datetime={snapshot.snapshot_at}>Snapshot {new Date(snapshot.snapshot_at).toLocaleString()}</time>
        {:else}<span>Snapshot unavailable</span>{/if}
        <span class="snapshot-caption">Cached observations · refreshes every 5 seconds</span>
      </div>
      <button class="refresh-observations" type="button" disabled={refreshing} onclick={() => void refresh(false)}>{refreshing ? "Refreshing…" : "Refresh"}</button>
    </div>
    {#if snapshot?.containment_reason}<div class="containment" role="alert">Runtime admission is contained: {snapshot.containment_reason}</div>{/if}
    {#if snapshot && snapshotStale}<div class="containment" role="alert">The Nexus board is stale. Lifecycle mutations are unavailable until a fresh snapshot loads.</div>{/if}
    {#if loading}<p class="nexus-empty" role="status">Reading capability observations…</p>
    {:else if snapshot}
      <div class="nexus-viewbar"><span class="section-label">{mapModel?.objects.length ?? 0} observed objects</span>
        <div role="group" aria-label="Nexus view"><button type="button" aria-pressed={viewMode === "map"} onclick={() => changeView("map")}>Map</button><button type="button" aria-pressed={viewMode === "list"} onclick={() => changeView("list")}>List</button></div>
      </div>
      {#if mapModel}
      <div class="nexus-map-view" hidden={viewMode !== "map"}>
        <NexusMap model={mapModel} selectedId={selectedObjectId} onselect={selectObject} stale={snapshotStale} />
        {#if preview}<p class="nexus-plan-context">Preview target: <code>{preview.target}</code> · {preview.plan.action_type} · planned effects only</p>{/if}
      </div>
      {/if}
      <div hidden={viewMode !== "list"} class="nexus-list">
      <div class="board-introduction"><h2 class="section-label">Observe capabilities</h2><p>Readiness is an observation. It does not grant permission or reserve capacity.</p></div>
      <div class="animator-index" role="group" aria-label="Observed Animators">
        {#each mapModel?.objects.filter((object) => object.kind === "animator") ?? [] as object (object.id)}
          <button type="button" onclick={(event) => selectObject(object.id, event.currentTarget)}>Inspect Animator {object.label}</button>
        {/each}
      </div>
      <section class="coven-grid" aria-label="Observed capabilities">
        {#each snapshot.board.covens as [name, rows] (name)}
          <details class="panel coven-card" open>
            <summary class="coven-heading"><h3 class="rune-head">{name}</h3><span class="kind">managed coven · {rows.length} {rows.length === 1 ? "capability" : "capabilities"}</span></summary>
            {#each rows as row (row.capability_key)}{@render capability(row)}{/each}
          </details>
        {:else}<p class="nexus-empty">No managed capabilities in this snapshot.</p>{/each}
        {#if snapshot.board.portals.length}
          <details class="panel coven-card">
            <summary class="coven-heading"><h3 class="rune-head">Portals</h3><span class="kind">observed remote · read only</span></summary>
            {#each snapshot.board.portals as row (row.capability_key)}{@render capability(row, true)}{/each}
          </details>
        {/if}
      </section>
      <details class="delegated-runtime-pools panel">
        <summary class="coven-heading"><h2 class="rune-head">Delegated runtime pools</h2><span class="kind">selected extensions · read only</span></summary>
        {#if snapshot.delegated_runtimes.length}
          <div class="delegated-runtime-grid">
            {#each snapshot.delegated_runtimes as runtime (runtime.runtime_id)}
              <article class="delegated-runtime" data-state={runtime.delivery}>
                <header><button class="delegated-runtime__title inspect-object" type="button" aria-label={`Inspect delegated runtime ${runtime.runtime_id}`} onclick={(event) => inspectRuntime(runtime.runtime_id, event.currentTarget)}><DelegateMark /> {runtime.display_name}</button>
                  <span class="chip" data-state={runtime.runnable ? "awaited" : "cold"}>{runtime.runnable ? "available" : runtime.delivery}</span></header>
                <dl class="kv">
                  <dt>adapter</dt><dd>{runtime.runtime_id} · {runtime.transport}</dd>
                  <dt>registrant</dt><dd>{runtime.registrant_id}</dd>
                  <dt>coffin</dt><dd>{runtime.coffin_profiles.length ? runtime.coffin_profiles.join(" · ") : "not required"}</dd>
                  <dt>Provider Gate</dt><dd>{runtime.provider_gate.replaceAll("_", " ")}</dd>
                  <dt>capacity</dt><dd>{runtime.capacity_posture.replaceAll("_", " ")}</dd>
                </dl>
                {#if runtime.limitations.length}<ul class="limits-list">{#each runtime.limitations as limitation (limitation)}<li>{limitation}</li>{/each}</ul>{/if}
              </article>
            {/each}
          </div>
        {:else}<p class="inspector-copy">No delegated runtime extension is selected for this Vessel.</p>{/if}
      </details>
      </div>
      <section class="transition-ledger panel" aria-labelledby="transition-ledger-title">
        <div class="panel-head"><div><h2 id="transition-ledger-title" class="rune-head">Latest transition observations</h2><p class="section-caption">Up to 24 retained requests · process-local · not complete history</p></div></div>
        {#if snapshot.transitions.length}
          <ol>{#each snapshot.transitions as transition (transition.request_id)}
            <li><a class={selectedTransition?.request_id === transition.request_id ? "current" : ""}
              aria-current={selectedTransition?.request_id === transition.request_id ? "true" : undefined}
              href={resolve(`/nexus?transition=${encodeURIComponent(transition.request_id)}`)}
              onclick={(event) => (transitionReturnFocus = event.currentTarget)}>
              <span class="transition-source">{transition.source}</span><strong>{transition.target_capability_key}</strong>
              <span class="transition-phase">{transition.phase}</span><code>{transition.request_id}</code>
              <time datetime={transition.observed_at}>Observed {new Date(transition.observed_at).toLocaleString()}</time>
            </a></li>
          {/each}</ol>
        {:else}<p class="inspector-copy">No transition request is retained in this process yet.</p>{/if}
      </section>
    {:else}<p class="nexus-empty">The capability board could not be read. Refresh to try again.</p>{/if}
  </section>
  <aside class="nexus-side" class:nexus-side--selected={selectedObjectId !== null || previewTarget !== null} aria-label="Preview and transition outcomes">
    <section class="panel nexus-object-inspector" aria-labelledby="nexus-object-title" tabindex="-1" {@attach captureObjectInspector}>
      <div class="panel-head"><h2 id="nexus-object-title" class="rune-head">Selected object</h2>
        {#if selectedObjectId}<button class="sheet-dismiss" type="button" onclick={closeObject}>Close object</button>{/if}
      </div>
      {#if selectedObject}
        <NexusProperties object={selectedObject} {busy} {previewTarget} allowPreview={viewMode === "map"} onpreview={previewTransition} oninspect={inspectCapability} />
      {:else if selectedObjectId}
        <p class="inspector-copy" role="status">The selected object is not present in the latest available snapshot. Refresh or choose another object.</p>
      {:else}
        <p class="inspector-copy">Select an object to inspect its observed properties. Selection does not request a transition.</p>
      {/if}
    </section>
    <section id="nexus-preview" class="panel nexus-plan" class:nexus-plan--idle={previewTarget === null && !error} data-open={previewTarget !== null}
      aria-labelledby="nexus-preview-title" aria-busy={previewLoading} {@attach capturePlanInspector} tabindex="-1">
      <div class="panel-head"><div><span class="section-label">Plan a change</span><h2 id="nexus-preview-title" class="rune-head">Non-binding preview</h2></div>
        {#if previewTarget}<button class="sheet-dismiss" type="button" onclick={closePreview}>Close</button>{/if}</div>
      {#if previewTarget}<div class="preview-identity"><span>Selected capability</span><code>{previewTarget}</code></div>{/if}
      {#if previewLoading}<p class="nexus-hint" role="status">Calculating preview… This read does not request a transition.</p>
      {:else if preview}
        <div class="plan-verdict" data-state={preview.plan.action_type === "NO_OP" ? "clean" : "change"}>{preview.plan.action_type}</div>
        <div class="plan-consequences">
          <div><h3>Evict Animator</h3><ul class="animator-list" aria-label="Animators to evict">{#each preview.plan.evict_coven_ids as animator (animator)}<li><code>{animator}</code></li>{:else}<li>none</li>{/each}</ul></div>
          <div><h3>Launch Animator</h3><ul class="animator-list" aria-label="Animators to launch">{#each preview.plan.launch_coven_ids as animator (animator)}<li><code>{animator}</code></li>{:else}<li>none</li>{/each}</ul></div>
        </div>
        <p class="policy-cost">Policy cost <strong>{preview.plan.total_metabolic_cost}</strong><span>planned evictions</span></p>
        <div class="plan-act">
          <p class="warn">Real maximum-priority lifecycle mutation. The Orchestrator recalculates the non-binding preview before acting. Preview reserves nothing.</p>
          {#if snapshot?.containment_reason}<p class="action-note">Request unavailable while runtime admission is contained.</p>
          {:else if snapshotStale}<p class="action-note">Refresh the stale snapshot before requesting a transition.</p>
          {:else if preview.plan.action_type === "NO_OP"}<p class="action-note">No lifecycle change is planned for this target.</p>{/if}
          <button class="rune-btn" disabled={busy || snapshotStale || Boolean(snapshot?.containment_reason) || preview.plan.action_type === "NO_OP"} type="button" onclick={swap}>Request transition</button>
          {#if busy}<p class="action-note" role="status">Submitting the prepared request…</p>{/if}
          {#if swapAttempts.has(preview.target) && !busy}<p class="action-note">Retry keeps the original request identity and target.</p>{/if}
        </div>
      {:else if !previewTarget}
        <div class="preview-empty"><span class="empty-number" aria-hidden="true">01 → 02</span><h3>Start with an observation</h3><p>Choose Preview on a managed capability to inspect the planned evictions and launches before requesting a change.</p></div>
      {/if}
      {#if error}<div class="turn__fault" role="alert">{error}</div>{/if}
    </section>
    {#if swapAttempts.size}
      <section class="panel pending-requests" aria-labelledby="pending-requests-title">
        <div class="panel-head"><h2 id="pending-requests-title" class="rune-head">Request outcomes</h2></div>
        <p class="inspector-copy">Keep the original request identity while reconciling the outcome.</p>
        <ul>{#each swapAttempts as [target, requestId] (requestId)}<li><strong>{target}</strong><span>{submittingTarget === target ? "Submitting request…" : "Response uncertain"}</span><code>{requestId}</code></li>{/each}</ul>
      </section>
    {/if}
    {#if ticket}
      <section class="panel ticket-panel" aria-labelledby="ticket-title">
        <div class="panel-head"><h2 id="ticket-title" class="rune-head">Request ticket</h2></div>
        <div class="swap-ticket" data-state={ticketStale ? "stale" : ticket.state} role="status"><span>{ticket.target}</span><strong>{ticketStale ? "projection stale" : ticket.phase}</strong><code>{ticket.request_id}</code></div>
        <p class="inspector-copy">
          {#if ticketStale}The latest ticket result is unknown. Reconcile this request before judging its outcome.
          {:else if ticket.state === "settled"}The task returned. Read the physical transition observation separately to understand its outcome.
          {:else if ticket.state === "failed"}The task raised or was cancelled. Read the physical transition observation before judging the host state.
          {:else}No terminal task result has been observed.{/if}
        </p>
      </section>
    {/if}
    <section class="panel transition-inspector" class:transition-inspector--idle={!selectedTransition && !transitionNote} data-open={selectedTransition !== null}
      aria-labelledby="transition-inspector-title" {@attach captureTransitionInspector} tabindex="-1">
      <div class="panel-head"><h2 id="transition-inspector-title" class="rune-head">Selected transition observation</h2>
        {#if selectedTransition}<button class="sheet-dismiss" type="button" onclick={() => void clearTransition()}>Close</button>{/if}</div>
      {#if selectedTransition}
        <dl class="kv">
          <dt>request</dt><dd class="glyph">{selectedTransition.request_id}</dd>
          <dt>source</dt><dd>{selectedTransition.source}</dd>
          <dt>target</dt><dd>{selectedTransition.target_capability_key}</dd>
          <dt>phase</dt><dd>{selectedTransition.phase}</dd>
          <dt>observed</dt><dd><time datetime={selectedTransition.observed_at}>{new Date(selectedTransition.observed_at).toLocaleString()}</time></dd>
          <dt>requested</dt><dd><time datetime={selectedTransition.requested_at}>{new Date(selectedTransition.requested_at).toLocaleString()}</time></dd>
          <dt>action</dt><dd>{selectedTransition.action_type ?? "not chosen"}</dd>
          <dt>occurrence</dt><dd class="glyph">{selectedTransition.occurrence_id ?? "—"}</dd>
          <dt>physical</dt><dd class="glyph">{selectedTransition.physical_transition_id ?? "none"}</dd>
          <dt>restoration</dt><dd class="glyph">{selectedTransition.compensation_transition_id ?? "none"}</dd>
        </dl>
        {#if selectedTransition.detail}<p class="inspector-copy">{selectedTransition.detail}</p>{/if}
        {#if selectedTransition.orb_path}<a class="inspector-link" href={resolve((requestedEventId ? `${selectedTransition.orb_path}?event=${encodeURIComponent(requestedEventId)}` : selectedTransition.orb_path) as `/orb/${string}`)}>Return to evidence in the Orb →</a>{/if}
      {:else}<p class="inspector-copy">{transitionNote || "Select a retained request to inspect correlation."}</p>{/if}
    </section>
  </aside>
</div>

<style>
  .instrument-deck--nexus { display: flex; flex-direction: row; align-items: start; gap: 2rem; padding: 1rem clamp(1rem, 2vw, 2rem); }
  .nexus-main { flex: 1 1 0; min-width: 0; gap: .75rem; }
  .nexus-viewbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .5rem; }
  .nexus-viewbar .section-label { margin: 0; }
  .nexus-viewbar [role="group"] { display: flex; gap: .25rem; }
  .nexus-viewbar button { min-height: 2.5rem; padding: .4rem .85rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); color: var(--color-parchment); background: var(--color-obsidian); cursor: pointer; }
  .nexus-viewbar button[aria-pressed="true"] { border-color: var(--color-rune); color: var(--color-bone); }
  .nexus-list[hidden], .nexus-map-view[hidden] { display: none; }
  .animator-index { display: flex; gap: .5rem; flex-wrap: wrap; margin-block: .75rem; }
  .animator-index button { min-height: 2.5rem; padding: .4rem .7rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); background: var(--color-obsidian); color: var(--color-parchment); cursor: pointer; overflow-wrap: anywhere; }
  .inspect-object { padding: 0; border: 0; background: none; text-align: start; cursor: pointer; font: inherit; overflow-wrap: anywhere; }
  .nexus-plan-context { color: var(--color-parchment); font-size: var(--text-xs); overflow-wrap: anywhere; }
  .nexus-object-inspector { width: 100%; }
  .nexus-side.nexus-side--selected { border-inline-start-color: var(--color-control-border); }
  .nexus-plan.nexus-plan--idle { border: 0; }
  .nexus-plan--idle .panel-head, .nexus-plan--idle .empty-number, .nexus-plan--idle .preview-empty h3 { display: none; }
  .nexus-plan--idle .preview-empty { padding-top: 0; }
  .transition-inspector--idle { display: none; }
  .nexus-object-inspector:focus { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  .nexus-side { display: flex; flex-direction: column; flex: 0 0 21rem; position: sticky; top: 1.25rem; width: 21rem; min-width: 0; gap: 0; padding: .25rem 0; border-inline-start: 1px solid var(--color-engraving); background: var(--color-tertiary); }
  .panel { box-shadow: none; background: transparent; border: 0; border-bottom: 1px solid var(--color-engraving); border-radius: 0; }
  .nexus-side > .panel:last-child { border-bottom: 0; }
  .panel-head { padding: 1.25rem 1.25rem 1rem; align-items: center; gap: .75rem; }
  .panel-head h2 { font-size: 1rem; font-family: var(--font-body); font-weight: 550; }
  .panel-head h2 { line-height: 1.35; }
  .sheet-dismiss { display: inline-block; flex-shrink: 0; min-height: 2.25rem; }
  .snapshot-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1rem 0; border-block: 1px solid var(--color-engraving); color: var(--color-bone); font-size: var(--text-sm); }
  .snapshot-caption { display: block; color: var(--color-parchment); margin-top: 0.25rem; }
  .refresh-observations { border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); padding: 0.6rem 0.8rem; background: transparent; color: var(--color-rune); min-height: 2.5rem; }
  .refresh-observations:disabled { color: var(--color-ash); cursor: wait; }
  .board-introduction { padding-top: 0.25rem; }
  .section-label { display: block; font-family: var(--font-body); font-size: var(--text-xs); font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-parchment); margin-bottom: 0.375rem; }
  .board-introduction p, .section-caption { margin: 0.25rem 0 0; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .coven-grid { grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
  .coven-card { display: block; min-width: 0; }
  .coven-heading { padding: 1.25rem .25rem; cursor: pointer; color: var(--color-parchment); }
  .coven-heading::marker { color: var(--color-rune); }
  .coven-heading h2, .coven-heading h3 { display: inline; font: 550 var(--text-lg)/1.4 var(--font-body); margin: 0; color: var(--color-bone); }
  .coven-heading .kind { display: block; margin: 0.375rem 0 0 1rem; text-transform: none; letter-spacing: normal; color: var(--color-parchment); font-family: var(--font-body); font-size: var(--text-xs); }
  .capability-row { border-top: 1px solid var(--color-engraving); border-inline-start: 2px solid transparent; }
  .capability-row[data-selected="true"] { border-inline-start-color: var(--color-rune); background: color-mix(in srgb, var(--color-rune) 4%, var(--color-obsidian)); }
  .preview-marker { color: var(--color-heat); font-size: var(--text-xs); grid-column: 1 / -1; }
  .cap { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: .65rem 1rem; padding: 1.25rem .5rem .5rem; border: 0; }
  .cap .key { font-size: var(--text-sm); color: var(--color-bone); }
  .cap .chip { justify-self: start; font-size: var(--text-xs); box-shadow: none; animation: none; }
  .probe-time { grid-column: 1 / 3; grid-row: 2; font-size: var(--text-xs); color: var(--color-parchment); white-space: normal; }
  .cap .preview-trigger, .read-only { grid-column: 3; grid-row: 1 / 3; }
  .cap .preview-trigger { min-height: 2.5rem; padding: 0.5rem 0.7rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); color: var(--color-rune); font-family: var(--font-body); }
  .capability-row[data-selected="true"] .preview-trigger { border-color: var(--color-rune); }
  .read-only { color: var(--color-parchment); font-size: var(--text-xs); }
  .capability-detail { padding: 0 .5rem 1rem; }
  .capability-detail summary { cursor: pointer; color: var(--color-parchment); font-size: var(--text-sm); min-height: 2.5rem; padding-top: .5rem; }
  .kv { min-width: 0; grid-template-columns: minmax(4.75rem, auto) minmax(0, 1fr); gap: 0.6rem 0.85rem; font-size: var(--text-sm); }
  .kv dd, .kv dt { min-width: 0; overflow-wrap: anywhere; }
  .kv dt { color: var(--color-parchment); }
  .capability-detail .kv { padding: 0.75rem 0 0; margin: 0; }
  .delegated-runtime-grid { grid-template-columns: minmax(0, 1fr); padding-top: 0; }
  .delegated-runtime { background: none; border-inline: 0; border-bottom: 0; border-radius: 0; }
  .delegated-runtime header { flex-wrap: wrap; }
  .transition-ledger a { grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.5rem 0.75rem; padding: 0.875rem 1.125rem; }
  .transition-ledger strong { font-size: var(--text-sm); overflow-wrap: anywhere; }
  .transition-ledger code { grid-column: 2 / -1; font-size: var(--text-xs); overflow-wrap: anywhere; white-space: normal; }
  .transition-ledger time { grid-column: 2 / -1; color: var(--color-parchment); font-size: var(--text-xs); }
  .transition-source { color: var(--color-parchment); }
  .transition-phase { overflow-wrap: anywhere; color: var(--color-bone); font-size: var(--text-xs); }
  .nexus-plan { width: 100%; position: static; background: transparent; border-color: var(--color-tertiary-edge); }
  .preview-identity { display: grid; gap: 0.5rem; padding: 1rem 1.125rem 0.25rem; }
  .preview-identity span { font-size: var(--text-xs); color: var(--color-parchment); }
  .preview-identity code { font-size: var(--text-sm); overflow-wrap: anywhere; }
  .plan-verdict { margin: .5rem 1.125rem 1rem; background: transparent; color: var(--color-bone); font: 600 var(--text-base)/1.5 var(--font-glyph); padding: 0; border: 0; }
  .plan-consequences { display: grid; gap: 1rem; padding: 0.5rem 1.125rem; }
  .plan-consequences h3 { font-family: var(--font-body); font-size: var(--text-sm); font-weight: 500; margin-bottom: 0.5rem; color: var(--color-bone); }
  .animator-list { list-style: none; margin: 0; padding: 0; color: var(--color-parchment); font-size: var(--text-sm); }
  .animator-list li { border-inline-start: 2px solid var(--color-engraving); padding: 0.25rem 0.75rem; overflow-wrap: anywhere; }
  .animator-list code { font-size: var(--text-xs); }
  .policy-cost { display: flex; flex-wrap: wrap; gap: 0.35rem 0.6rem; margin: 0.75rem 1.125rem 0; padding-top: 0.875rem; border-top: 1px solid var(--color-engraving); color: var(--color-parchment); font-size: var(--text-sm); }
  .policy-cost strong { color: var(--color-bone); }
  .policy-cost span { font-size: var(--text-xs); align-self: center; }
  .plan-act { padding: 1rem 1.125rem 1.125rem; gap: 0.75rem; }
  .plan-act .warn, .action-note { margin: 0; font-size: var(--text-sm); color: var(--color-parchment); line-height: 1.55; }
  .plan-act .rune-btn { min-height: 2.75rem; box-shadow: none; font-size: var(--text-sm); color: var(--color-void); background: var(--color-bone); border-color: var(--color-bone); font-weight: 600; }
  .plan-act .rune-btn:disabled { color: var(--color-ash); background: var(--color-obsidian-2); border-color: var(--color-control-border); }
  .preview-empty { padding: 1rem 1.125rem 1.25rem; }
  .empty-number { color: var(--color-rune-dim); font-family: var(--font-glyph); font-size: var(--text-xs); }
  .preview-empty h3 { font-weight: 400; font-size: var(--text-lg); margin: 1rem 0 0.75rem; }
  .preview-empty p { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.65; margin: 0; }
  .inspector-copy, .nexus-hint, .nexus-empty { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.6; }
  .pending-requests { border-inline-start: 2px solid var(--color-heat); }
  .pending-requests ul { margin: 0; padding: 0 1.125rem 1rem; list-style: none; }
  .pending-requests li { display: grid; gap: 0.5rem; padding-block: 0.5rem; font-size: var(--text-sm); }
  .pending-requests code { font-size: var(--text-xs); }
  .pending-requests strong, .pending-requests code { overflow-wrap: anywhere; }
  .swap-ticket { display: grid; gap: 0.5rem; background: var(--color-obsidian-2); margin: 0.25rem 1.125rem; box-shadow: none; }
  .swap-ticket span, .swap-ticket code, .swap-ticket strong { overflow-wrap: anywhere; white-space: normal; }
  .swap-ticket code { font-size: var(--text-xs); }
  .ticket-panel .inspector-copy { margin-top: 0.5rem; }
  .transition-inspector .kv { padding: 1rem 1.125rem; }
  .containment, .turn__fault { overflow-wrap: anywhere; }
  :is(button, summary, a):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  :is(.nexus-plan, .transition-inspector):focus { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @container work-area (max-width: 68rem) { .instrument-deck--nexus { gap: 1.25rem; } .nexus-side { flex-basis: 19rem; width: 19rem; } }
  @media (max-width: 900px) {
    .instrument-deck--nexus { display: flex; flex-direction: column; }
    .nexus-main, .nexus-side { width: 100%; }
    .nexus-side { flex: auto; position: static; padding-top: 0; border-inline-start: 0; border-top: 1px solid var(--color-engraving); }
    .nexus-plan[data-open="true"], .transition-inspector[data-open="true"] { position: static; max-height: none; overflow: visible; box-shadow: none; }
  }
  @container work-area (max-width: 68rem) {
    .instrument-deck--nexus { flex-direction: column; }
    .nexus-main, .nexus-side { width: 100%; }
    .nexus-side { flex: auto; position: static; padding-top: 0; border-inline-start: 0; border-top: 1px solid var(--color-engraving); }
    .nexus-plan[data-open="true"], .transition-inspector[data-open="true"] { position: static; max-height: none; overflow: visible; box-shadow: none; }
  }
  @container work-area (max-width: 35rem) {
    .instrument-deck--nexus { padding: 1rem; }
    .cap { grid-template-columns: minmax(0, 1fr) auto; }
    .cap .key { grid-column: 1 / -1; }
    .cap .chip { grid-column: 1; grid-row: 2; }
    .cap .preview-trigger, .read-only { grid-column: 2; grid-row: 2 / 4; }
    .probe-time { grid-column: 1; grid-row: 3; }
    .transition-ledger a { grid-template-columns: minmax(0, 1fr); }
    .transition-ledger code, .transition-ledger time { grid-column: 1; }
  }
  .snapshot-bar { padding:.35rem 0; border:0; background:transparent; }
  .snapshot-bar > div { display:flex; align-items:baseline; flex-wrap:wrap; gap:.25rem 1rem; }
  .containment { padding:.65rem .8rem; font-size:var(--text-xs); line-height:1.5; }
  @media (max-width: 480px) {
    .snapshot-bar { align-items: flex-start; gap: 0.5rem; }
    .cap { grid-template-columns: minmax(0, 1fr) auto; gap: 0.5rem; }
    .cap .key { grid-column: 1 / -1; }
    .cap .chip { grid-column: 1; grid-row: 2; }
    .cap .preview-trigger, .read-only { grid-column: 2; grid-row: 2 / 4; }
    .probe-time { grid-column: 1; grid-row: 3; }
    .transition-ledger a { grid-template-columns: minmax(0, 1fr); }
    .transition-ledger code, .transition-ledger time { grid-column: 1; }
    .panel-head { align-items: flex-start; }
  }
  @media (forced-colors: active) {
    .capability-row[data-selected="true"] { border-inline-start-color: Highlight; }
    :is(button, summary, a):focus-visible, :is(.nexus-plan, .transition-inspector):focus { outline-color: Highlight; }
  }
</style>
