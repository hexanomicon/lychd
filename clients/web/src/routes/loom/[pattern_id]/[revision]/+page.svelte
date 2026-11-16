<script lang="ts">
  import { page } from "$app/state";
  import LoomView from "$lib/pages/loom/components/LoomView.svelte";
</script>

<LoomView patternId={page.params.pattern_id} revision={page.params.revision} />
