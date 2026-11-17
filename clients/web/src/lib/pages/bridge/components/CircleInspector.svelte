<!--
  Bridge's Run inspector ("Circle"). Shows only served Run fields; station progress
  has no served contract, so none is inferred here.
-->
<script lang="ts">
  import type { LiveTurn } from "$lib/pages/bridge/state/projection";
  import { runEvidenceHref, runScoreHref } from "$lib/pages/bridge/state/run-links";
  import InspectorLinks from "$lib/components/shared/InspectorLinks.svelte";
  import InspectorPanel from "$lib/components/shared/InspectorPanel.svelte";
  import InspectorSection from "$lib/components/shared/InspectorSection.svelte";
  import KeyValueList, { type KeyValueItem } from "$lib/components/shared/KeyValueList.svelte";
  import StatusPill, { type PillTone } from "$lib/components/shared/StatusPill.svelte";

  let { runId, turn, pending = 0 }: {
    runId: string;
    turn?: LiveTurn;
    pending?: number;
  } = $props();

  const status = $derived(pending > 0 ? "Waiting for consent" : turn ? label(turn.runStatus) : "Retained reply");
  const tone = $derived<PillTone>(pending > 0 ? "attention" : turn?.runStatus === "failed" ? "fault" : turn?.runStatus === "done" ? "success" : "neutral");
  const facts = $derived<KeyValueItem[]>([
    { term: "Run", value: runId, glyph: true },
    ...(turn ? [
      { term: "Pattern", value: turn.patternId ? `${turn.patternId}${turn.patternRevision ? `@${turn.patternRevision}` : ""}` : "Not available", glyph: !!turn.patternId },
      { term: "Capability", value: turn.capabilityKey ?? "Not available", glyph: !!turn.capabilityKey }
    ] : []),
    { term: "Sigil", value: "Local · Magus" },
    ...(turn ? [{ term: "Capture", value: turn.evidenceCapture.replaceAll("_", "-"), glyph: true }] : [])
  ]);

  function label(value: string): string {
    if (value === "awaiting_hardware") return "Awaiting animators";
    if (value === "awaiting_delegate") return "Delegated labor";
    const text = value.replaceAll("_", " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }
</script>

<InspectorPanel title="Circle">
  {#snippet meta()}<StatusPill {tone} dot>{status}</StatusPill>{/snippet}
  <InspectorSection>
    <KeyValueList items={facts} />
  </InspectorSection>
  <InspectorSection>
    <InspectorLinks label="Run inspection" links={[
      { href: runScoreHref(runId, turn), label: "Open score in Loom" },
      { href: runEvidenceHref(runId, turn), label: "Inspect Run in Orb" }
    ]} />
  </InspectorSection>
</InspectorPanel>
