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
  <section class="work-body files" aria-label="Files">
    <header class="file-head">
      <h2><AltarIcon name="files" size={16}/>{files.current?.name ?? "Files"}</h2>
      <label class="open-file" title="Open text files">Open…<input aria-label="Open text files" type="file" multiple onchange={openFiles} /></label>
      <button type="button" aria-label={tree ? "Hide file tree" : "Show file tree"} title={tree ? "Hide file tree" : "Show file tree"} aria-expanded={tree} onclick={() => (tree = !tree)}><AltarIcon name="panel" size={16}/></button>
    </header>
    {#if files.notice}<p role="status">{files.notice}</p>{/if}
    <div class="file-split">
      <div class="editor">
        {#if files.current}
          <label class="document"><span class="visually-hidden">Draft</span><textarea rows="12" spellcheck="false" bind:value={files.current.draft}></textarea></label>
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
          <h3>File tree</h3>
          {#each files.all as file (file.id)}
            <button
              type="button"
              aria-pressed={files.current?.id === file.id}
              onclick={() => files.select(file.id)}><AltarIcon name="document" size={13}/>{file.name}</button
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
  .work-body.files { display:flex; flex-direction:column; padding:0; }
  .file-head { min-height:2.7rem; justify-content:flex-start; gap:.4rem; padding:.3rem .7rem; border-bottom:1px solid var(--color-engraving); }
  .file-head h2 { display:flex; align-items:center; gap:.45rem; flex:1; min-width:0; margin:0; overflow-wrap:anywhere; font:600 .9rem/1.35 var(--font-body); }
  .file-head button,.open-file { position:relative; display:grid; place-items:center; margin:0; padding:.35rem .5rem; background:transparent; border:0; color:var(--color-parchment); cursor:pointer; }
  .open-file input { position:absolute; inset:0; width:100%; height:100%; opacity:0; cursor:pointer; }
  .open-file:focus-within { outline:2px solid var(--color-rune); }
  .file-split { flex:1; margin:0; gap:0; }
  .editor { display:flex; flex-direction:column; padding:1rem .8rem; overflow:auto; }
  .document { display:flex; flex:1; margin:0 0 .6rem; min-height:9rem; }
  .document textarea { resize:none; padding:.2rem; line-height:1.7; font-size:.86rem; border:0; background:transparent; }
  .file-tree { padding:.7rem .4rem; box-sizing:border-box; }
  .file-tree button { display:flex; align-items:center; gap:.4rem; border:0; background:transparent; overflow-wrap:anywhere; width:100%; padding:.3rem .4rem; }
  .file-tree button[aria-pressed=true] { background:color-mix(in srgb,var(--color-rune) 16%,transparent); color:var(--color-bone); }
  .actions { justify-content:flex-start; }
  .ledger { align-self:start; }
  .editor>p { margin:.3rem 0; }
  button:disabled {
    opacity: 0.6;
  }
</style>
