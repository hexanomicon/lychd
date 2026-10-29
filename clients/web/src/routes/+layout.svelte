<script lang="ts">
  import "../app.css";
  import { setContext, untrack } from "svelte";
  import { page } from "$app/state";
  import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/bridge/workspace.svelte";
  import AltarShell from "$lib/components/AltarShell.svelte";

  let { children } = $props();
  const offlineProfile = untrack(() => import.meta.env.DEV && page.url.pathname === "/canvas");
  const bridgeWorkspace = setContext(bridgeWorkspaceKey, createBridgeWorkspace());
  function guardUnload(event: BeforeUnloadEvent) {
    if (!bridgeWorkspace.needsUnloadWarning) return;
    event.preventDefault();
    event.returnValue = "";
  }
</script>

<svelte:window onbeforeunload={guardUnload} />

<AltarShell offline={offlineProfile}>
  {@render children()}
</AltarShell>
