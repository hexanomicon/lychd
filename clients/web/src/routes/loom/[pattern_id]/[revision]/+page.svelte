<script lang="ts">
  import { page } from "$app/state";
  import LoomView from "$lib/components/loom/LoomView.svelte";
</script>

<LoomView patternId={page.params.pattern_id} revision={page.params.revision} />
