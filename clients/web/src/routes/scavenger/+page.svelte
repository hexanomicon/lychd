<script lang="ts">
  import { page } from "$app/state";
  import ObservationsScavengerView from "$lib/pages/observationsScavenger/components/ObservationsScavengerView.svelte";
  const selection = $derived(page.url.searchParams.getAll("observation"));
</script>

<ObservationsScavengerView admissionId={selection.length > 1 ? "invalid" : selection[0] ?? null} />
