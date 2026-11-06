<script lang="ts">
  import { page } from "$app/state";
  import SeancesWorkspace from "$lib/components/SeancesWorkspace.svelte";
</script>
<SeancesWorkspace sessionId={page.params.session_id} />
