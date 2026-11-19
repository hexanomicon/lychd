<script lang="ts">
  import { onMount } from "svelte";
  import { createApplicationPins, setApplicationPins } from "$lib/navigation/application-pins.svelte";
  import AltarRail from "$lib/shell/components/AltarRail.svelte";
  import ApplicationsView from "./ApplicationsView.svelte";

  const pins = createApplicationPins();
  setApplicationPins(pins);
  onMount(pins.load);
</script>

<AltarRail instruments={[]} pathname="/applications" available={false} pending={null} suspended={false}>
  {#snippet brand()}Altar{/snippet}
</AltarRail>
<ApplicationsView />
