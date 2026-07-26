<script lang="ts">
  let { source }: { source: string } = $props();
  let node: HTMLElement;
  let renderVersion = 0;

  $effect(() => {
    source;
    const version = ++renderVersion;
    node.textContent = source;
    node.removeAttribute("data-processed");
    void (async () => {
      const { default: mermaid } = await import("mermaid");
      if (version !== renderVersion) return;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "base",
        themeVariables: {
          background: "#1a1a20",
          primaryColor: "#22222b",
          primaryTextColor: "#d9d7e4",
          primaryBorderColor: "#7c4dff",
          lineColor: "#5a4a8a",
          tertiaryColor: "#131318",
          fontFamily: "ui-monospace, monospace"
        }
      });
      await mermaid.run({ nodes: [node], suppressErrors: true });
    })();
  });
</script>

<pre class="mermaid" bind:this={node}>{source}</pre>
