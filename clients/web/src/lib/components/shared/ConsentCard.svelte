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
  let reviewRequired = $derived(consent.native_review_status !== "not_required");
  let review = $derived.by(() => {
    const document = consent.native_review;
    if (consent.native_review_status !== "available" || !document ||
        typeof document.title !== "string" || document.title.length === 0 ||
        !Array.isArray(document.facts) || document.facts.length === 0 ||
        !document.facts.every((fact) => fact &&
          typeof fact.key === "string" && fact.key.length > 0 &&
          typeof fact.label === "string" && fact.label.length > 0 &&
          typeof fact.value === "string" && fact.value.length > 0) ||
        new Set(document.facts.map((fact) => fact.key)).size !== document.facts.length ||
        typeof consent.review_binding_digest !== "string" || !consent.review_binding_digest.trim()) {
      return null;
    }
    return document;
  });
  let reviewBindingDigest = $derived(review ? consent.review_binding_digest! : undefined);
  let reviewChanged = $derived(Boolean(decision && (
    decision.reviewBindingDigest !== reviewBindingDigest || (reviewRequired && !review)
  )));
  let canDecide = $derived(consent.can_decide === true && (!reviewRequired || Boolean(review)));

  let consentLabel = $derived(
    consent.state === "pending_consent"
      ? "pending consent"
      : consent.state === "consented"
        ? "approved consent"
        : `${consent.state} consent`
  );

  async function decide(verdict: "approve" | "deny") {
    if (busy || !canDecide || reviewChanged || consent.state !== "pending_consent" || (decision && decision.verdict !== verdict)) return;
    const consentId = consent.id;
    const previous = decision;
    const request = previous
      ? { ...previous, sending: true, error: "" }
      : { sessionId, verdict, reviewBindingDigest, sending: true, error: "" };
    const authorityVersion = onauthority();
    decisions.set(consentId, request);
    error = "";
    try {
      const result = request.reviewBindingDigest === undefined
        ? await decideConsent(consentId, request.verdict)
        : await decideConsent(consentId, request.verdict, request.reviewBindingDigest);
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
  data-consent-id={consent.id}
  tabindex="-1"
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
  {#if review}
    <section class="native-review" aria-label="Required review">
      <h3>{review.title}</h3>
      <dl>
        {#each review.facts as fact (fact.key)}
          <dt>{fact.label}</dt>
          <dd>{fact.value}</dd>
        {/each}
      </dl>
    </section>
  {:else if reviewRequired}
    <p role="status">The required review is unavailable or incomplete. Refresh before deciding.</p>
  {/if}
  {#if consent.state === "pending_consent"}
    {#if decision && !decision.settled}
      <p role="status">
        {#if decision.sending}
          Sending your {decision.verdict === "approve" ? "approval" : "refusal"} to the Vessel.
        {:else}
          Your previous {decision.verdict === "approve" ? "approval" : "refusal"} is unconfirmed.
        {/if}
        {#if reviewChanged}
          The review has changed or is unavailable. Refresh the outcome before deciding again.
        {:else if !canDecide}
          Refresh the outcome before deciding again.
        {:else if !decision.sending}
          Refresh the outcome or retry the same decision.
        {/if}
      </p>
    {/if}
    {#if !consent.can_decide}
      <p role="status">Read-only: the Vessel has not permitted a decision on this request.</p>
    {/if}
    <div class="verdicts">
      <button
        disabled={busy || !canDecide || reviewChanged || decision?.verdict === "deny"}
        class="rune-btn rune-btn--frost"
        onclick={() => decide("approve")}
      >Consecrate</button>
      <button
        disabled={busy || !canDecide || reviewChanged || decision?.verdict === "approve"}
        class="rune-btn rune-btn--ash"
        onclick={() => decide("deny")}
      >Refuse</button>
      {#if !canDecide || decision}
        <button type="button" class="rune-btn" onclick={onrefresh}>
          {decision ? "Refresh outcome" : "Refresh review"}
        </button>
      {/if}
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

<style>
  .consent-card:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }

  .native-review {
    min-width: 0;
    padding: 12px 16px;
  }

  .native-review h3,
  .native-review dt,
  .native-review dd {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .native-review dl {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
    padding: 0;
  }

  .native-review dd {
    margin: 0 0 12px;
  }
</style>
