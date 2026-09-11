<script lang="ts">
  import { ApiError, decideConsent } from "$lib/api/client";
  import type { ConsentCard } from "$lib/api/models";
  import type { BridgeWorkspace } from "$lib/bridge/workspace.svelte";

  let {
    consent,
    sessionId,
    decisions,
    onauthority,
    ondecided,
    onrefresh
  }: {
    consent: ConsentCard;
    sessionId: string;
    decisions: BridgeWorkspace["consentDecisions"];
    onauthority: () => number;
    ondecided: (consent: ConsentCard, pending: number, authorityVersion: number) => void;
    onrefresh: () => void;
  } = $props();
  let error = $state("");
  let decision = $derived(decisions.get(consent.id));
  let busy = $derived(Boolean(decision?.sending || decision?.settled));
  let decisionError = $derived(decision?.error || error);
  let consentLabel = $derived(
    consent.state === "pending_consent"
      ? "pending consent"
      : consent.state === "consented"
        ? "approved consent"
        : `${consent.state} consent`
  );

  async function decide(verdict: "approve" | "deny") {
    if (busy || consent.state !== "pending_consent" || (decision && decision.verdict !== verdict)) return;
    const consentId = consent.id;
    const previous = decision;
    const request = { sessionId, verdict, sending: true, error: "" };
    const authorityVersion = onauthority();
    decisions.set(consentId, request);
    error = "";
    try {
      const result = await decideConsent(consentId, verdict);
      decisions.set(consentId, { ...request, sending: false, settled: true });
      ondecided(result.consent, result.pending_count, authorityVersion);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "The verdict was not admitted.";
      if (previous || !(cause instanceof ApiError) || cause.status === undefined || cause.status >= 500 || cause.status === 408) {
        decisions.set(consentId, { ...request, sending: false, error });
      } else decisions.delete(consentId);
      onrefresh();
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
        disabled={busy || decision?.verdict === "deny"}
        class="rune-btn rune-btn--frost"
        onclick={() => decide("approve")}
      >Consecrate</button>
      <button
        disabled={busy || decision?.verdict === "approve"}
        class="rune-btn rune-btn--ash"
        onclick={() => decide("deny")}
      >Refuse</button>
      <span class="note">{decision?.settled ? "Refreshing the authoritative consent outcome." : "the Vessel decides; this card only asks"}</span>
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
  {#if decisionError}<div class="turn__fault" role="alert">{decisionError}</div>{/if}
</section>
