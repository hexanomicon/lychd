<script lang="ts">
  import { page } from "$app/state";
  import CanvasWorkspace from "$lib/pages/canvas/components/CanvasWorkspace.svelte";
</script>

<CanvasWorkspace projectId={page.params.project_id} />
