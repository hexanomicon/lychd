<script lang="ts">
  import PaneGrip from "$lib/components/layout/PaneGrip.svelte";
  import AltarIcon from "./AltarIcon.svelte";
  import type { createLocalFiles } from "$lib/shell/state/local-files.svelte";

  let {
    focused = false,
    active = $bindable("bridge"),
    files,
    pages = $bindable([]),
  }: {
    focused?: boolean;
    active?: string;
    files: ReturnType<typeof createLocalFiles>;
    pages?: string[];
  } = $props();

  const tools = [
    { id: "bridge", name: "Walking Bridge" },
    { id: "files", name: "Files" },
    { id: "terminal", name: "Terminal" },
    { id: "web", name: "Web" },
  ];
  const visibleTools = $derived(focused ? tools.slice(1) : tools);
  let tree = $state(true);
  let treeWidth = $state(125);
  let ledger = $state(false);
  let address = $state("");
  let notice = $state("");

  async function openFiles(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const selected = Array.from(input.files ?? []);
    input.value = "";
    for (const file of selected) await files.open(file);
    tree = true;
  }

  function selectTool(id: string) {
    if (id === "files") tree = true;
    active = id;
  }

  function visit(event: SubmitEvent) {
    event.preventDefault();
    try {
      const url = new URL(address);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
        throw new Error("Invalid web address");
      }
      pages = [url.href, ...pages.filter((page) => page !== url.href)].slice(0, 32);
      window.open(url.href, "_blank", "noopener,noreferrer");
      notice = "";
    } catch {
      notice = "Enter an HTTP or HTTPS address without credentials.";
    }
  }
</script>

<div class="work-tabs" role="group" aria-label="Side panel tools">
  {#each visibleTools as tool (tool.id)}
    <button
      type="button"
      title={tool.name}
      aria-label={tool.name}
      aria-pressed={tool.id === active}
      onclick={() => selectTool(tool.id)}
    >
      <AltarIcon name={tool.id} size={17} />
    </button>
  {/each}
</div>

{#if active === "files"}
  <section class="work-body" aria-label="Files">
    <header>
      <h2>Files</h2>
      <button type="button" aria-expanded={tree} onclick={() => (tree = !tree)}
        >{tree ? "Hide" : "Show"} file tree</button
      >
    </header>
    <label class="open-file">Open text files<input type="file" multiple onchange={openFiles} /></label>
    {#if files.notice}<p role="status">{files.notice}</p>{/if}
    <div class="file-split">
      <div class="editor">
        {#if files.current}
          <h3>{files.current.name}</h3>
          <label>Draft<textarea rows="10" bind:value={files.current.draft}></textarea></label>
          <div class="actions">
            <button type="button" disabled={files.current.text === files.current.draft} onclick={files.save}
              >Save revision</button
            >
            <button
              type="button"
              disabled={files.current.text !== files.current.draft}
              onclick={files.download}>Download revision</button
            >
          </div>
          <button type="button" class="ledger" aria-expanded={ledger} onclick={() => (ledger = !ledger)}
            >Change ledger · {files.current.history.length}</button
          >
          {#if ledger}
            <ol>
              {#each files.current.history as entry (entry.id)}
                <li>
                  <strong>{entry.action}</strong><time datetime={entry.time}
                    >{entry.time.slice(11, 19)} UTC</time
                  >
                  <p>{entry.detail}</p>
                </li>
              {/each}
            </ol>
          {/if}
          <p>Revisions stay in this tab. Download a copy to keep them.</p>
        {:else}
          <p>Choose a local text file to read or edit.</p>
        {/if}
      </div>
      {#if tree}
        <nav class="file-tree" aria-label="Open files" style:--tree-width={treeWidth + "px"}>
          <PaneGrip bind:width={treeWidth} name="File tree width" min={80} max={280} />
          <h3>Open files</h3>
          {#each files.all as file (file.id)}
            <button
              type="button"
              aria-pressed={files.current?.id === file.id}
              onclick={() => files.select(file.id)}>{file.name}</button
            >
          {:else}<p>No files open.</p>{/each}
        </nav>
      {/if}
    </div>
  </section>
{:else if active === "terminal"}
  <section class="work-body">
    <h2>Terminal</h2>
    <p>No terminal transport is connected to this Altar.</p>
  </section>
{:else if active === "web"}
  <section class="work-body">
    <h2>Web</h2>
    <form onsubmit={visit}>
      <label>Web address<input type="url" required bind:value={address} placeholder="https://" /></label
      ><button type="submit">Open in browser ↗</button>
    </form>
    {#if notice}<p role="status">{notice}</p>{/if}
    {#if pages.length}
      <nav aria-label="Opened web pages">
        <ul>
          {#each pages as url (url)}<li>
              <a href={url} target="_blank" rel="noopener noreferrer">{url}</a>
            </li>{/each}
        </ul>
      </nav>
    {/if}
  </section>
{/if}

<style>
  .work-tabs {
    display: flex;
    gap: 0.2rem;
    padding: 0.3rem 0.7rem;
    border-bottom: 1px solid var(--color-engraving);
  }
  button {
    cursor: pointer;
    color: var(--color-parchment);
    background: var(--color-obsidian-2);
    border: 1px solid var(--color-engraving);
    padding: 0.4rem 0.6rem;
    border-radius: 5px;
    font: var(--text-xs)/1.4 var(--font-body);
  }
  .work-tabs button {
    border: 0;
    background: transparent;
    display: grid;
    place-items: center;
    min-width: 2.2rem;
    min-height: 2.2rem;
  }
  button[aria-pressed="true"] {
    color: var(--color-bone);
    background: color-mix(in srgb, var(--color-accent) 20%, var(--color-obsidian));
  }
  .work-body {
    padding: 1rem;
    min-width: 0;
    overflow: auto;
    flex: 1;
  }
  h2,
  h3 {
    font: 500 1.5rem var(--font-rune);
    margin: 0.3rem 0 0.7rem;
  }
  h3 {
    font-size: 1.15rem;
    overflow-wrap: anywhere;
  }
  p,
  label,
  time {
    font-size: var(--text-xs);
    color: var(--color-ash);
  }
  header,
  .actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.3rem;
    flex-wrap: wrap;
  }
  label {
    display: grid;
    gap: 0.35rem;
    margin: 0.6rem 0;
  }
  input,
  textarea {
    min-width: 0;
    max-width: 100%;
    width: 100%;
    padding: 0.4rem;
    color: var(--color-bone);
    background: var(--color-void);
    border: 1px solid var(--color-control-border);
    border-radius: 5px;
  }
  textarea {
    resize: vertical;
    font-family: var(--font-glyph);
  }
  .file-split {
    display: flex;
    min-height: 12rem;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  .editor {
    flex: 1;
    min-width: 0;
  }
  .file-tree {
    position: relative;
    width: min(var(--tree-width), 48%);
    padding-inline-start: 0.6rem;
    border-inline-start: 1px solid var(--color-engraving);
  }
  .file-tree h3 {
    font: 600 var(--text-xs)/1.5 var(--font-body);
  }
  .file-tree button {
    display: block;
    max-width: 100%;
    overflow-wrap: anywhere;
    text-align: left;
    margin-block: 0.25rem;
  }
  .ledger {
    margin: 0.75rem 0 0.25rem;
  }
  ol,
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li {
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--color-engraving);
    overflow-wrap: anywhere;
  }
  time {
    margin-inline-start: 0.5rem;
  }
  li p {
    margin: 0;
  }
  button:disabled {
    opacity: 0.6;
  }
</style>
