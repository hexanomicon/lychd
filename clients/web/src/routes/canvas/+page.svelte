<script lang="ts">
  import { page } from "$app/state";
  import CanvasWorkspace from "$lib/pages/canvas/components/CanvasWorkspace.svelte";
</script>

<CanvasWorkspace newRequested={page.url.searchParams.get("new") === "1"} />
