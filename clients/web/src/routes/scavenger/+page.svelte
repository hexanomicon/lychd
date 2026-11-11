<script lang="ts">
  import { page } from "$app/state";
  import ScavengerView from "$lib/components/scavenger/ScavengerView.svelte";
  const selection = $derived(page.url.searchParams.getAll("observation"));
</script>

<ScavengerView admissionId={selection.length > 1 ? "invalid" : selection[0] ?? null} />
