<script lang="ts">
  import { decideConsent } from "$lib/api/client";
  import type { ConsentCard } from "$lib/api/models";

  let { consent, ondecided }: { consent: ConsentCard; ondecided: (consent: ConsentCard, pending: number) => void } =
    $props();
  let busy = $state(false);
  let error = $state("");

  async function decide(verdict: "approve" | "deny") {
    busy = true;
    error = "";
    try {
      const result = await decideConsent(consent.id, verdict);
      ondecided(result.consent, result.pending_count);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "The verdict was not admitted.";
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
  aria-label="pending consent"
>
  <div class="head">
    <span class="rune-head">◈ Consent sought</span>
    <span class="glyph">{consent.tool_name}</span>
  </div>
  <div class="vision"><em>Vision:</em> {consent.vision}</div>
  <dl class="args">
    {#each Object.entries(consent.args) as [name, value]}
      <dt>{name}</dt><dd>{String(value)}</dd>
    {/each}
  </dl>
  {#if consent.state === "pending_consent"}
    <div class="verdicts">
      <button disabled={busy} class="rune-btn rune-btn--frost" onclick={() => decide("approve")}>Consecrate</button>
      <button disabled={busy} class="rune-btn rune-btn--ash" onclick={() => decide("deny")}>Refuse</button>
      <span class="note">the Vessel decides; this card only asks</span>
    </div>
  {:else}
    <div class="verdicts">
      <span class="chip" data-state={consent.state === "consented" ? "active" : "fault"}>
        {consent.state === "consented" ? "consecrated" : "refused"}
      </span>
      <span class="note">the Magus has spoken</span>
    </div>
  {/if}
  {#if error}<div class="turn__fault">{error}</div>{/if}
</section>
