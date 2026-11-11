<script lang="ts">
  import { page } from "$app/state";
  import OrbView from "$lib/components/orb/OrbView.svelte";
</script>

<OrbView runId={page.params.run_id} />
