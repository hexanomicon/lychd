<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { tick } from "svelte";

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
  import DelegateMark from "./DelegateMark.svelte";

  type Preview = { target: string; plan: TransitionPlan };

  let snapshot = $state.raw<NexusSnapshot | null>(null);
  let preview = $state.raw<Preview | null>(null);
  let selectedTransition = $state.raw<TransitionRecordView | null>(null);
  let selectedTransitionRequestId: string | null = null;
  let ticket = $state.raw<SwapTicket | null>(null);
  let ticketStale = $state(false);
  let loading = $state(true);
  let snapshotStale = $state(false);
  let busy = $state(false);
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
  const swapAttempts = new Map<string, string>();

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
    if (requestId) void selectTransition(requestId);
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
        error = cause instanceof Error ? cause.message : "The Nexus cannot be read.";
      }
    } finally {
      if (!destroyed && showLoading) loading = false;
    }
  }

  async function selectTransition(requestId: string, focus = true) {
    if (destroyed) return;
    selectedTransitionRequestId = requestId;
    const version = ++transitionVersion;
    previewVersion++;
    preview = null;
    transitionNote = "";
    const retained = snapshot?.transitions.find((item) => item.request_id === requestId);
    if (retained) {
      selectedTransition = retained;
      if (focus) await focusOnMobile(transitionInspector);
      return;
    }
    try {
      const exact = await getNexusTransition(requestId);
      if (destroyed || version !== transitionVersion) return;
      selectedTransition = exact;
      if (focus) await focusOnMobile(transitionInspector);
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
    ticket = null;
    error = "";
    await clearTransition(false);
    if (destroyed || version !== previewVersion) return;
    try {
      const plan = await getNexusPlan(target);
      if (!destroyed && version === previewVersion) {
        preview = { target, plan };
        await focusOnMobile(planInspector);
      }
    } catch (cause) {
      if (!destroyed && version === previewVersion) {
        error = cause instanceof Error ? cause.message : "The transition cannot be calculated.";
      }
    }
  }

  async function closePreview() {
    const target = planReturnFocus;
    planReturnFocus = undefined;
    preview = null;
    await tick();
    if (target?.isConnected) target.focus();
  }

  async function focusOnMobile(element: HTMLElement | undefined) {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
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
    const url = new URL(page.url);
    url.searchParams.delete("transition");
    url.searchParams.delete("event");
    const nexusPath = `/nexus${url.search}` as "/nexus" | `/nexus?${string}`;
    await goto(resolve(nexusPath), {
      replaceState: true,
      keepFocus: target !== undefined,
      noScroll: true
    });
    await tick();
    if (target?.isConnected) target.focus();
  }

  async function swap() {
    const selected = preview;
    if (destroyed || !selected || busy || snapshotStale || selected.plan.action_type === "NO_OP") return;
    const requestId = swapAttempts.get(selected.target) ?? crypto.randomUUID();
    swapAttempts.set(selected.target, requestId);
    busy = true;
    error = "";
    try {
      const accepted = await createNexusSwap(selected.target, requestId);
      if (destroyed) return;
      ticket = accepted.ticket;
      ticketStale = false;
      swapAttempts.delete(selected.target);
      followTicket(accepted.ticket.id);
    } catch (cause) {
      if (destroyed) return;
      const definitiveRejection =
        cause instanceof ApiError &&
        cause.status !== undefined &&
        cause.status < 500 &&
        cause.status !== 409;
      if (definitiveRejection) swapAttempts.delete(selected.target);
      error = cause instanceof Error ? cause.message : "The transition was refused.";
    } finally {
      if (!destroyed) busy = false;
    }
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

  function dominantState(rows: NexusCovenRow[]): string {
    if (rows.some((row) => row.state === "fault")) return "fault";
    if (rows.some((row) => row.state === "active")) return "active";
    if (rows.some((row) => row.state === "warming")) return "warming";
    if (rows.some((row) => row.state === "awaited")) return "awaited";
    return "cold";
  }
</script>

<svelte:head><title>Nexus — LychD</title></svelte:head>
<div class="instrument-deck instrument-deck--nexus">
  <section class="nexus-main" aria-label="Capability observations">
    <header class="instrument-header">
      <div>
        <span class="eyebrow">Observed world</span>
        <h1 class="rune-head">Nexus</h1>
        <p>Capability bodies, cached readiness observations, and retained transition observations.</p>
      </div>
      {#if snapshot}
        <time datetime={snapshot.snapshot_at}>Snapshot {new Date(snapshot.snapshot_at).toLocaleTimeString()}</time>
      {/if}
    </header>

    {#if snapshot?.containment_reason}
      <div class="containment" role="alert">
        Runtime admission is contained: {snapshot.containment_reason}
      </div>
    {/if}
    {#if snapshot && snapshotStale}
      <div class="containment" role="alert">
        The Nexus board is stale. Lifecycle mutations are unavailable until a fresh snapshot loads.
      </div>
    {/if}
    {#if loading}
      <div class="mist"></div><div class="mist"></div>
    {:else if snapshot}
      <section class="coven-grid" aria-label="Observed capabilities">
        {#each snapshot.board.covens as [name, rows] (name)}
          <section class="panel coven-card" data-state={dominantState(rows)}>
            <div class="panel-head">
              <h2 class="rune-head">{name}</h2>
              <span class="kind">managed coven</span>
            </div>
            {#each rows as row (row.capability_key)}
              <div class="cap">
                <span class="key">{row.capability_key}</span>
                <span class="chip" data-state={row.state}>{row.state}</span>
                <time class="probe-time" datetime={row.checked_at ?? undefined}>
                  {row.checked_at ? `checked ${new Date(row.checked_at).toLocaleTimeString()}` : "freshness unknown"}
                </time>
                <button
                  class="preview-trigger"
                  type="button"
                  disabled={busy}
                  onclick={(event) => previewTransition(row.capability_key, event.currentTarget)}
                >
                  Preview
                </button>
              </div>
            {/each}
          </section>
        {/each}
        {#if snapshot.board.portals.length}
          <section class="panel coven-card" data-state={dominantState(snapshot.board.portals)}>
            <div class="panel-head">
              <h2 class="rune-head">Portals</h2>
              <span class="kind">observed remote</span>
            </div>
            {#each snapshot.board.portals as row (row.capability_key)}
              <div class="cap">
                <span class="key">{row.capability_key}</span>
                <span class="chip" data-state={row.state}>{row.state}</span>
                <time class="probe-time" datetime={row.checked_at ?? undefined}>
                  {row.checked_at ? `checked ${new Date(row.checked_at).toLocaleTimeString()}` : "freshness unknown"}
                </time>
                <span class="read-only">read only</span>
              </div>
            {/each}
          </section>
        {/if}
      </section>

      <section class="delegated-runtime-pools panel" aria-labelledby="delegated-runtime-title">
        <div class="panel-head">
          <h2 id="delegated-runtime-title" class="rune-head">Delegated runtime pools</h2>
          <span>selected extensions · read only</span>
        </div>
        {#if snapshot.delegated_runtimes.length}
          <div class="delegated-runtime-grid">
            {#each snapshot.delegated_runtimes as runtime (runtime.runtime_id)}
              <article class="delegated-runtime" data-state={runtime.delivery}>
                <header>
                  <span class="delegated-runtime__title"><DelegateMark /> {runtime.display_name}</span>
                  <span class="chip" data-state={runtime.runnable ? "active" : "cold"}>
                    {runtime.runnable ? "available" : runtime.delivery}
                  </span>
                </header>
                <dl class="kv">
                  <dt>adapter</dt><dd>{runtime.runtime_id} · {runtime.transport}</dd>
                  <dt>extension</dt><dd>{runtime.provider_id}</dd>
                  <dt>coffin</dt>
                  <dd>{runtime.coffin_profiles.length ? runtime.coffin_profiles.join(" · ") : "not required"}</dd>
                  <dt>Provider Gate</dt><dd>{runtime.provider_gate.replaceAll("_", " ")}</dd>
                  <dt>capacity</dt><dd>{runtime.capacity_posture.replaceAll("_", " ")}</dd>
                </dl>
                {#if runtime.limitations.length}
                  <ul class="limits-list">
                    {#each runtime.limitations as limitation (limitation)}<li>{limitation}</li>{/each}
                  </ul>
                {/if}
              </article>
            {/each}
          </div>
        {:else}
          <p class="inspector-copy">
            No delegated runtime extension is selected for this Vessel.
          </p>
        {/if}
      </section>

      <section class="transition-ledger panel" aria-labelledby="transition-ledger-title">
        <div class="panel-head">
          <h2 id="transition-ledger-title" class="rune-head">Latest transition observations</h2>
          <span>process-local · bounded</span>
        </div>
        {#if snapshot.transitions.length}
          <ol>
            {#each snapshot.transitions as transition (transition.request_id)}
              <li>
                <a
                  class:current={selectedTransition?.request_id === transition.request_id}
                  href={resolve(`/nexus?transition=${encodeURIComponent(transition.request_id)}`)}
                  onclick={(event) => (transitionReturnFocus = event.currentTarget)}
                >
                  <span class="transition-source">{transition.source}</span>
                  <strong>{transition.target_capability_key}</strong>
                  <span>{transition.phase}</span>
                  <code>{transition.request_id.slice(0, 12)}</code>
                </a>
              </li>
            {/each}
          </ol>
        {:else}
          <p class="inspector-copy">No transition request is retained in this process yet.</p>
        {/if}
      </section>
    {:else}
      <p class="nexus-empty glyph">No covens risen.</p>
    {/if}
  </section>

  <aside class="nexus-side">
    <section
      class="panel nexus-plan"
      data-open={preview !== null}
      {@attach capturePlanInspector}
      tabindex="-1"
    >
      <div class="panel-head">
        <h2 class="rune-head">Non-binding preview</h2>
        {#if preview}<button class="sheet-dismiss" type="button" onclick={closePreview}>Close</button>{/if}
      </div>
      {#if preview}
        <div class="plan-verdict" data-state={preview.plan.action_type === "NO_OP" ? "clean" : "change"}>
          {preview.plan.action_type}
        </div>
        <div class="plan-list">
          <div class="row"><span class="l">target</span><span class="v launch">{preview.target}</span></div>
          <div class="row"><span class="l">evict</span><span class="v evict">{preview.plan.evict_coven_ids.join(", ") || "none"}</span></div>
          <div class="row"><span class="l">launch</span><span class="v launch">{preview.plan.launch_coven_ids.join(", ") || "none"}</span></div>
          <div class="row">
            <span class="l">policy cost (planned evictions)</span>
            <span class="v">{preview.plan.total_metabolic_cost}</span>
          </div>
        </div>
        <div class="plan-act">
          <button
            class="rune-btn"
            disabled={busy || snapshotStale || preview.plan.action_type === "NO_OP"}
            type="button"
            onclick={swap}
          >
            Request transition
          </button>
          <span class="warn">
            Real maximum-priority lifecycle mutation. The Orchestrator recalculates the
            non-binding preview before acting.
          </span>
        </div>
      {:else}
        <p class="nexus-hint">Choose Preview on a managed capability.</p>
      {/if}
      {#if ticket}
        <div class="swap-ticket" data-state={ticketStale ? "stale" : ticket.state}>
          <span>{ticket.target}</span>
          <strong>{ticketStale ? "projection stale" : ticket.phase}</strong>
          <code>{ticket.request_id.slice(0, 12)}</code>
        </div>
      {/if}
      {#if error}<div class="turn__fault" role="alert">{error}</div>{/if}
    </section>

    <section
      class="panel transition-inspector"
      data-open={selectedTransition !== null}
      {@attach captureTransitionInspector}
      tabindex="-1"
    >
      <div class="panel-head">
        <h2 class="rune-head">Selected transition observation</h2>
        {#if selectedTransition}
          <button class="sheet-dismiss" type="button" onclick={() => void clearTransition()}>Close</button>
        {/if}
      </div>
      {#if selectedTransition}
        <dl class="kv">
          <dt>request</dt><dd class="glyph">{selectedTransition.request_id}</dd>
          <dt>source</dt><dd>{selectedTransition.source}</dd>
          <dt>target</dt><dd>{selectedTransition.target_capability_key}</dd>
          <dt>phase</dt><dd>{selectedTransition.phase}</dd>
          <dt>action</dt><dd>{selectedTransition.action_type ?? "not chosen"}</dd>
          <dt>occurrence</dt><dd class="glyph">{selectedTransition.occurrence_id ?? "—"}</dd>
          <dt>physical</dt><dd class="glyph">{selectedTransition.physical_transition_id ?? "none"}</dd>
          <dt>restoration</dt><dd class="glyph">{selectedTransition.compensation_transition_id ?? "none"}</dd>
        </dl>
        {#if selectedTransition.orb_path}
          <a
            class="inspector-link"
            href={resolve(
              (requestedEventId
                ? `${selectedTransition.orb_path}?event=${encodeURIComponent(requestedEventId)}`
                : selectedTransition.orb_path) as `/orb/${string}`
            )}
          >
            Return to evidence in the Orb →
          </a>
        {/if}
      {:else}
        <p class="inspector-copy">{transitionNote || "Select a retained request to inspect correlation."}</p>
      {/if}
    </section>
  </aside>
</div>
