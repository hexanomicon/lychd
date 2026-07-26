<script lang="ts">
  import { createNexusSwap, getNexusPlan, getNexusSnapshot, listenToSwap } from "$lib/api/client";
  import type { NexusCovenRow, NexusSnapshot, SwapTicket, TransitionPlan } from "$lib/api/models";

  let snapshot = $state<NexusSnapshot | null>(null);
  let plan = $state<TransitionPlan | null>(null);
  let selectedTarget = $state("");
  let ticket = $state<SwapTicket | null>(null);
  let loading = $state(true);
  let busy = $state(false);
  let error = $state("");
  let closeStream: (() => void) | null = null;

  $effect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(false), 5000);
    return () => {
      window.clearInterval(timer);
      closeStream?.();
    };
  });

  async function refresh(showLoading = true) {
    if (showLoading) loading = true;
    try {
      snapshot = await getNexusSnapshot();
      error = "";
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "The Nexus cannot be read.";
    } finally {
      loading = false;
    }
  }

  async function scry(target: string) {
    selectedTarget = target;
    ticket = null;
    try {
      plan = await getNexusPlan(target);
      error = "";
    } catch (cause) {
      plan = null;
      error = cause instanceof Error ? cause.message : "The transition cannot be calculated.";
    }
  }

  async function swap() {
    if (!selectedTarget || busy) return;
    busy = true;
    try {
      const accepted = await createNexusSwap(selectedTarget);
      ticket = accepted.ticket;
      closeStream?.();
      closeStream = listenToSwap(
        accepted.ticket.id,
        (event) => {
          ticket = event.ticket;
          if (event.ticket.state !== "warming") {
            closeStream = null;
            void refresh(false);
          }
        },
        (message) => {
          window.dispatchEvent(new CustomEvent("altar:omen", { detail: { text: message, fault: false } }));
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
<div class="instrument-deck" aria-label="Nexus">
  <div class="nexus-main">
    {#if loading}
      <div class="mist"></div><div class="mist"></div>
    {:else if snapshot}
      <div class="coven-grid">
        {#each snapshot.board.covens as [name, rows]}
          <section class="panel coven-card" data-state={dominantState(rows)}>
            <div class="panel-head">
              <span class="rune-head">{name}</span>
              <span class="kind">coven</span>
            </div>
            {#each rows as row}
              <div class="cap">
                <span class="key">{row.capability_key}</span>
                <span class="chip" data-state={row.state}>{row.state}</span>
                <button class="scry" disabled={row.state === "fault"} onclick={() => scry(row.capability_key)}>
                  scry
                </button>
              </div>
            {/each}
          </section>
        {/each}
        {#if snapshot.board.portals.length}
          <section class="panel coven-card" data-state={dominantState(snapshot.board.portals)}>
            <div class="panel-head">
              <span class="rune-head">Portals</span>
              <span class="kind">remote</span>
            </div>
            {#each snapshot.board.portals as row}
              <div class="cap">
                <span class="key">{row.capability_key}</span>
                <span class="chip" data-state={row.state}>{row.state}</span>
                <button class="scry" disabled={row.state === "fault"} onclick={() => scry(row.capability_key)}>
                  scry
                </button>
              </div>
            {/each}
          </section>
        {/if}
      </div>
    {:else}
      <p class="nexus-empty glyph">No covens risen.</p>
    {/if}
  </div>

  <aside class="panel nexus-plan" aria-live="polite">
    <div class="panel-head"><span class="rune-head">Transition Scrying</span></div>
    {#if plan}
      <div class="plan-verdict" data-state={plan.action_type === "NO_OP" ? "clean" : "change"}>
        {plan.action_type}
      </div>
      <div class="plan-list">
        <div class="row"><span class="l">target</span><span class="v launch">{selectedTarget}</span></div>
        <div class="row"><span class="l">evict</span><span class="v evict">{plan.evict_coven_ids.join(", ") || "none"}</span></div>
        <div class="row"><span class="l">launch</span><span class="v launch">{plan.launch_coven_ids.join(", ") || "none"}</span></div>
        <div class="row"><span class="l">metabolic cost</span><span class="v">{plan.total_metabolic_cost}</span></div>
      </div>
      <div class="plan-act">
        <button class="rune-btn rune-btn--frost" disabled={busy || plan.action_type === "NO_OP"} onclick={swap}>
          Request transition
        </button>
        <span class="warn">The Vessel recalculates and authorizes the mutation.</span>
      </div>
    {:else}
      <div class="nexus-hint">Scry a coven capability to preview its swap.</div>
    {/if}
    {#if ticket}
      <div class="swap-ticket" data-state={ticket.state}>{ticket.target} · {ticket.state}</div>
    {/if}
    {#if error}<div class="turn__fault">{error}</div>{/if}
  </aside>
</div>
