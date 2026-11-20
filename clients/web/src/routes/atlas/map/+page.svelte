<script lang="ts">
  import { page } from "$app/state";
  import AtlasKnowledgeMap from "$lib/pages/atlas/components/AtlasKnowledgeMap.svelte";
  const project = $derived(page.url.searchParams.get("project"));
  const session = $derived(page.url.searchParams.get("session"));
</script>

{#key JSON.stringify([project, session])}
  <AtlasKnowledgeMap projectId={project} sessionId={session} />
{/key}
