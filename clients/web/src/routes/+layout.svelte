<script lang="ts">
  import "../app.css";
  import { setContext, untrack } from "svelte";
  import { page } from "$app/state";
  import { beforeNavigate } from "$app/navigation";
  import { createWorkCommandRegistry, workCommandKey } from "$lib/shell/state/work-commands";
  import { bridgeWorkspaceKey, createBridgeWorkspace } from "$lib/shell/state/bridge-workspace.svelte";
  import AltarShell from "$lib/shell/components/AltarShell.svelte";

  let { children } = $props();
  const offlineProfile = untrack(() => import.meta.env.DEV && page.url.pathname === "/canvas/local");
  const bridgeWorkspace = setContext(bridgeWorkspaceKey, createBridgeWorkspace());
  const workCommands = setContext(workCommandKey, createWorkCommandRegistry());
  beforeNavigate(() => workCommands.invalidate());
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
