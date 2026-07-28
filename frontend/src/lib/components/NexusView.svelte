<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { tick } from "svelte";

  import {
    createNexusSwap,
    getNexusPlan,
    getNexusSnapshot,
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

  type Preview = { target: string; plan: TransitionPlan };

  let snapshot = $state.raw<NexusSnapshot | null>(null);
  let preview = $state.raw<Preview | null>(null);
  let selectedTransition = $state.raw<TransitionRecordView | null>(null);
  let ticket = $state.raw<SwapTicket | null>(null);
  let loading = $state(true);
  let busy = $state(false);
  let error = $state("");
  let transitionNote = $state("");
  let previewVersion = 0;
  let refreshVersion = 0;
  let transitionVersion = 0;
  let closeStream: (() => void) | null = null;
  let planInspector = $state<HTMLElement>();
  let transitionInspector = $state<HTMLElement>();

  let requestedTransitionId = $derived(page.url.searchParams.get("transition"));
  let requestedEventId = $derived(page.url.searchParams.get("event"));

  $effect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(false), 5000);
    return () => {
      window.clearInterval(timer);
      closeStream?.();
    };
  });

  $effect(() => {
    const requestId = requestedTransitionId;
    if (requestId) void selectTransition(requestId);
    else {
      transitionVersion++;
      selectedTransition = null;
      transitionNote = "";
    }
  });

  async function refresh(showLoading = true) {
    const version = ++refreshVersion;
    if (showLoading) loading = true;
    try {
      const next = await getNexusSnapshot();
      if (version !== refreshVersion) return;
      snapshot = next;
      error = "";
      if (requestedTransitionId) {
        await selectTransition(requestedTransitionId, false);
      }
    } catch (cause) {
      if (version === refreshVersion) {
        error = cause instanceof Error ? cause.message : "The Nexus cannot be read.";
      }
    } finally {
      if (version === refreshVersion) loading = false;
    }
  }

  async function selectTransition(requestId: string, focus = true) {
    const version = ++transitionVersion;
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
      if (version !== transitionVersion) return;
      selectedTransition = exact;
      if (focus) await focusOnMobile(transitionInspector);
    } catch (cause) {
      if (version !== transitionVersion) return;
      selectedTransition = null;
      const message = cause instanceof Error ? cause.message : "The exact request could not be read.";
      transitionNote = message.includes("not retained")
        ? "This process no longer retains that transition’s latest observation."
        : `The selected transition could not be refreshed: ${message}`;
    }
  }

  async function scry(target: string) {
    await clearTransition();
    const version = ++previewVersion;
    preview = null;
    ticket = null;
    error = "";
    try {
      const plan = await getNexusPlan(target);
      if (version === previewVersion) {
        preview = { target, plan };
        await focusOnMobile(planInspector);
      }
    } catch (cause) {
      if (version === previewVersion) {
        error = cause instanceof Error ? cause.message : "The transition cannot be calculated.";
      }
    }
  }

  async function focusOnMobile(element: HTMLElement | undefined) {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
    await tick();
    element?.focus();
  }

  async function clearTransition() {
    transitionVersion++;
    selectedTransition = null;
    transitionNote = "";
    if (!requestedTransitionId) return;
    const url = new URL(page.url);
    url.searchParams.delete("transition");
    url.searchParams.delete("event");
    await goto(`${url.pathname}${url.search}`, {
      replaceState: true,
      keepFocus: true,
      noScroll: true
    });
  }

  async function swap() {
    const selected = preview;
    if (!selected || busy || selected.plan.action_type === "NO_OP") return;
    busy = true;
    error = "";
    try {
      const accepted = await createNexusSwap(selected.target);
      ticket = accepted.ticket;
      closeStream?.();
      closeStream = listenToSwap(
        accepted.ticket.id,
        (event) => {
          ticket = event.ticket;
          if (event.ticket.state !== "warming") {
            closeStream = null;
            void refresh(false);
            void selectTransition(event.ticket.request_id);
          }
        },
        (message) => {
          window.dispatchEvent(
            new CustomEvent("altar:omen", { detail: { text: message, fault: false } })
          );
        }
      );
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "The transition was refused.";
    } finally {
      busy = false;
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
                <button class="scry" type="button" onclick={() => scry(row.capability_key)}>
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
                  href="/nexus?transition={transition.request_id}"
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
      bind:this={planInspector}
      tabindex="-1"
    >
      <div class="panel-head">
        <h2 class="rune-head">Non-binding preview</h2>
        {#if preview}<button class="sheet-dismiss" type="button" onclick={() => (preview = null)}>Close</button>{/if}
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
            disabled={busy || preview.plan.action_type === "NO_OP"}
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
        <div class="swap-ticket" data-state={ticket.state}>
          <span>{ticket.target}</span>
          <strong>{ticket.phase}</strong>
          <code>{ticket.request_id.slice(0, 12)}</code>
        </div>
      {/if}
      {#if error}<div class="turn__fault" role="alert">{error}</div>{/if}
    </section>

    <section
      class="panel transition-inspector"
      data-open={selectedTransition !== null}
      bind:this={transitionInspector}
      tabindex="-1"
    >
      <div class="panel-head">
        <h2 class="rune-head">Selected transition observation</h2>
        {#if selectedTransition}
          <button class="sheet-dismiss" type="button" onclick={clearTransition}>Close</button>
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
            href={
              requestedEventId
                ? `${selectedTransition.orb_path}?event=${encodeURIComponent(requestedEventId)}`
                : selectedTransition.orb_path
            }
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
