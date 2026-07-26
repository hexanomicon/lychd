<script lang="ts">
  import { page } from "$app/state";
  import LoomView from "$lib/components/LoomView.svelte";
</script>

<LoomView workflowName={page.params.workflow} />
