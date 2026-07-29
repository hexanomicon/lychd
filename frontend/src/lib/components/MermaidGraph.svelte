<script lang="ts">
  let { source, label }: { source: string; label: string } = $props();
  let node: HTMLElement;
  let failure = $state("");
  let renderVersion = 0;

  $effect(() => {
    source;
    const version = ++renderVersion;
    failure = "";
    node.textContent = source;
    node.removeAttribute("data-processed");
    void (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        if (version !== renderVersion) return;
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
        await mermaid.run({ nodes: [node], suppressErrors: false });
      } catch {
        if (version === renderVersion) failure = "Diagram unavailable. The semantic score remains authoritative.";
      }
    })();
  });
</script>

{#if failure}<p class="diagram-failure" role="status">{failure}</p>{/if}
<pre class="mermaid" bind:this={node} aria-label={label}>{source}</pre>
