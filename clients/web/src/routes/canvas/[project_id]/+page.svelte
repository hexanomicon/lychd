<script lang="ts">
  import { page } from "$app/state";
  import CanvasWorkspace from "$lib/components/CanvasWorkspace.svelte";
</script>

<CanvasWorkspace projectId={page.params.project_id} />
