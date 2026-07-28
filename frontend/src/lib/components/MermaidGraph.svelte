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
            background: "#0b0c10",
            primaryColor: "#17171f",
            primaryTextColor: "#e7e4ee",
            primaryBorderColor: "#8c63ff",
            lineColor: "#6f5aa8",
            tertiaryColor: "#101117",
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
