<script lang="ts">
  import { onDestroy } from "svelte";
  import { ApiError, getBridgeSnapshot } from "$lib/api/client";
  import { materialKinds, materialMarkdown, seanceHref, sourceSignature, type MaterialKind, type SeanceMaterial } from "$lib/seances/material";
  import { materialCharacterLimit, materialLimit, type SeancesWorkspace } from "$lib/seances/workspace.svelte";
  import { navigationId } from "$lib/navigation/instruments";

  let { work, sessionId, title, onInspect }: { work: SeancesWorkspace; sessionId?: string; title?: string; onInspect?: (item: SeanceMaterial) => void | Promise<void> } = $props();
  const groups = $derived([...work.materials.entries()].filter(([id]) => !sessionId || sessionId === id));
  const selections = $derived(groups.flatMap(([, items]) => items));
  let notice = $state("");
  let checking = $state(false);
  let alive = true;
  let generation = 0;
  onDestroy(() => { alive = false; ++generation; });
  function editNote(item: SeanceMaterial, element: HTMLTextAreaElement) {
    const error = work.update(item.sessionId, item.id, { note: element.value });
    if (error) { notice = error; element.value = item.note; }
  }
  async function inspect(item: SeanceMaterial) {
    if (onInspect) { await onInspect(item); return; }
    const version = ++generation, access = work.accessEpoch;
    checking = true; notice = "";
    try {
      const snapshot = await getBridgeSnapshot(item.sessionId);
      if (!alive || version !== generation || access !== work.accessEpoch) return;
      if (snapshot.session?.id !== item.sessionId) throw new Error("The exact source séance was not returned. No other conversation has been selected.");
      notice = snapshot.session.turns?.some((turn) => sourceSignature(turn) === sourceSignature(item.source))
        ? `Exact quotation found in the retained read of Session ${item.sessionId}.`
        : "The selected quotation is not present in this retained read. Its captured bytes have not been replaced.";
    } catch (cause) {
      if (!alive || version !== generation || access !== work.accessEpoch) return;
      const denied = cause instanceof ApiError && [401, 403].includes(cause.status ?? 0);
      if (denied) work.refuseAccess();
      notice = denied ? "The exact source is unavailable because access was refused. Read it again after access is restored."
        : "The exact source check failed. Captured quotation bytes have not been changed. Retry explicitly.";
    } finally { if (alive && version === generation) checking = false; }
  }
  function markdown() {
    return groups.map(([id, items]) => materialMarkdown(sessionId && title ? title : `Session ${id}`, items)).join("\n");
  }
  async function copy() {
    try { await navigator.clipboard.writeText(markdown()); notice = "Working material copied. Keep the copy somewhere safe before closing this tab."; }
    catch { notice = "Clipboard access is unavailable. Use Export Markdown to keep this material."; }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([markdown()], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url;
    link.download = sessionId ? `seance-${sessionId}.md` : "working-material.md"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    notice = "Markdown download requested. Check the file before closing this tab.";
  }
</script>

<section class="working-material" aria-label="Working material · this tab">
  <header><h2>Working material · this tab</h2><p>This browser document · export to keep. Manually selected quotations and attributed notes. Not saved to Archive or submitted to a model.</p>
    <p>Up to {materialLimit} selections and {materialCharacterLimit.toLocaleString("en")} quotation and note characters across this tab.</p>
    <div class="actions"><button type="button" disabled={!selections.length} onclick={copy}>Copy material</button><button type="button" disabled={!selections.length} onclick={download}>Export Markdown</button></div>
  </header>
  {#if notice}<p role="status">{notice}</p>{/if}
  {#each groups as [id, items] (id)}
    <section aria-label={`Material from Session ${id}`}><h3>Session <code>{id}</code></h3><a href={seanceHref(id)}>Open source séance</a>
      {#each items as item (item.id)}
        <article>
          <label>Use as <select value={item.kind} onchange={(event) => work.update(item.sessionId, item.id, { kind: event.currentTarget.value as MaterialKind })}>{#each materialKinds as kind (kind)}<option>{kind}</option>{/each}</select></label>
          <blockquote>{item.source.content}</blockquote><p class="provenance">{item.source.role === "user" ? "You" : "LychD"} · {item.source.created_at} · Session {item.sessionId}{item.source.run_id ? ` · Run ${item.source.run_id}` : " · No supplied Run identity"}</p>
          {#if navigationId(item.source.run_id)}<a href={`/orb/${encodeURIComponent(item.source.run_id!)}`}>Run evidence →</a>{/if}
          <label>Your note<textarea value={item.note} oninput={(event) => editNote(item, event.currentTarget)} rows="2" placeholder="Why keep this?"></textarea></label>
          <div class="actions"><button type="button" disabled={checking} onclick={() => inspect(item)}>Inspect source</button><button type="button" onclick={() => work.remove(item.sessionId, item.id)}>Remove selection</button></div>
        </article>
      {/each}
    </section>
  {:else}<p>Select a quotation in a Séance transcript, then mark it as a topic, open question or material for later use. Nothing is extracted automatically.</p>{/each}
</section>

<style>
  .working-material { display: grid; gap: 1.5rem; padding: 1.25rem; min-width: 0; color: var(--color-parchment); }
  h2, h3 { color: var(--color-bone); font: 600 var(--text-lg)/1.4 var(--font-body); }
  h3 { font-size: var(--text-base); }
  p { margin: .6rem 0; line-height: 1.6; }
  header > p, .provenance { color: var(--color-ash); font-size: var(--text-xs); }
  section, article { min-width: 0; }
  article { padding: 1.25rem 0; border-bottom: 1px solid var(--color-engraving); }
  blockquote { margin: 1rem 0; padding-left: 1rem; border-left: 2px solid var(--color-accent); white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.75; }
  .actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: .75rem; }
  label { display: block; margin-top: .75rem; color: var(--color-ash); font-size: var(--text-sm); }
  button, select, textarea { font: inherit; color: var(--color-parchment); background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); }
  button { min-height: 2.75rem; padding: .45rem .75rem; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  select { padding: .5rem; margin-left: .5rem; }
  textarea { display: block; width: 100%; padding: .65rem; margin-top: .4rem; resize: vertical; }
  a { color: var(--color-rune); }
  code, a, .provenance { overflow-wrap: anywhere; }
  :focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
</style>
