<script lang="ts">
  import { page } from "$app/state";
  import BridgeView from "$lib/components/BridgeView.svelte";
</script>

<BridgeView sessionId={page.params.session_id} />
