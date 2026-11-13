<script lang="ts">
  import { page } from "$app/state";
  import SeancesWorkspace from "$lib/pages/seances/components/SeancesWorkspace.svelte";
</script>
<SeancesWorkspace sessionId={page.params.session_id} />
