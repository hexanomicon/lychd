<script lang="ts">
  import { ApiError, decideConsent } from "$lib/api/client";
  import type { ConsentCard } from "$lib/api/models";

  let {
    consent,
    onauthority,
    ondecided,
    onrefresh
  }: {
    consent: ConsentCard;
    onauthority: () => number;
    ondecided: (consent: ConsentCard, pending: number, authorityVersion: number) => void;
    onrefresh: () => void;
  } = $props();
  let busy = $state(false);
  let error = $state("");
  let uncertainVerdict = $state<"approve" | "deny" | null>(null);
  let consentLabel = $derived(
    consent.state === "pending_consent"
      ? "pending consent"
      : consent.state === "consented"
        ? "approved consent"
        : `${consent.state} consent`
  );

  async function decide(verdict: "approve" | "deny") {
    if (busy || (uncertainVerdict !== null && uncertainVerdict !== verdict)) return;
    const authorityVersion = onauthority();
    busy = true;
    error = "";
    try {
      const result = await decideConsent(consent.id, verdict);
      uncertainVerdict = null;
      ondecided(result.consent, result.pending_count, authorityVersion);
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.status === undefined || cause.status >= 500) {
        uncertainVerdict = verdict;
      }
      error = cause instanceof Error ? cause.message : "The verdict was not admitted.";
      onrefresh();
    } finally {
      busy = false;
    }
  }
</script>

<section
  class="consent-card"
  data-fragment="bridge.consent"
  data-state={consent.state}
  data-run-id={consent.run_id}
  role="group"
  aria-label={consentLabel}
>
  <div class="head">
    <span class="rune-head">⬡ Consent sought</span>
    <span class="glyph">{consent.tool_name}</span>
  </div>
  <div class="vision"><em>Vision:</em> {consent.vision}</div>
  <dl class="args">
    {#each Object.entries(consent.args) as [name, value] (name)}
      <dt>{name}</dt><dd>{String(value)}</dd>
    {/each}
  </dl>
  {#if consent.state === "pending_consent"}
    <div class="verdicts">
      <button
        disabled={busy || uncertainVerdict === "deny"}
        class="rune-btn rune-btn--frost"
        onclick={() => decide("approve")}
      >Consecrate</button>
      <button
        disabled={busy || uncertainVerdict === "approve"}
        class="rune-btn rune-btn--ash"
        onclick={() => decide("deny")}
      >Refuse</button>
      <span class="note">the Vessel decides; this card only asks</span>
    </div>
  {:else}
    <div class="verdicts">
      <span
        class="chip"
        data-state={consent.state === "consented" ? "active" : consent.state === "cancelled" ? "cancelled" : "fault"}
      >
        {consent.state === "consented" ? "consecrated" : consent.state}
      </span>
      <span class="note">
        {consent.state === "cancelled" ? "the Run withdrew this request" : "the Magus has spoken"}
      </span>
    </div>
  {/if}
  {#if error}<div class="turn__fault">{error}</div>{/if}
</section>
