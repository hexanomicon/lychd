<script lang="ts">
  let { source, label }: { source: string; label: string } = $props();
  let node: HTMLElement;
  let failure = $state("");

  $effect(() => {
    const drawing = document.createElement("pre");
    drawing.className = "mermaid";
    drawing.textContent = source;
    node.replaceChildren(drawing);
    let cancelled = false;
    failure = "";
    void (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        if (cancelled) return;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          themeVariables: {
            background: "#0e141a",
            primaryColor: "#171d24",
            primaryTextColor: "#e1f8ff",
            primaryBorderColor: "#8be7ff",
            lineColor: "#447b91",
            secondaryColor: "#10281f",
            secondaryBorderColor: "#39ff8a",
            secondaryTextColor: "#d9ffe9",
            tertiaryColor: "#251738",
            tertiaryBorderColor: "#7c58bd",
            fontFamily: "ui-monospace, monospace"
          }
        });
        await mermaid.run({ nodes: [drawing], suppressErrors: false });
      } catch {
        if (!cancelled) failure = "Diagram unavailable. The semantic score remains authoritative.";
      }
    })();
    return () => {
      cancelled = true;
      // Mermaid may still finish, but its old target cannot replace a newer score.
      drawing.remove();
    };
  });
</script>

{#if failure}<p class="diagram-failure" role="status">{failure}</p>{/if}
<div bind:this={node} role="img" aria-label={label}></div>
