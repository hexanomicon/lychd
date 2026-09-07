<script lang="ts">
  import { page } from "$app/state";
  import AtlasView from "$lib/components/AtlasView.svelte";
</script>

<AtlasView
  linkKind={page.url.searchParams.get("link_kind")}
  linkId={page.url.searchParams.get("link_id")}
/>
