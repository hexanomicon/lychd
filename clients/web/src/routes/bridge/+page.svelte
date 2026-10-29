<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import PublicNoteRecall from "$lib/components/PublicNoteRecall.svelte";
  import PublicNotes from "$lib/components/PublicNotes.svelte";
  import { notesHref, notesFocusSelection } from "$lib/archive/notes";
  import CreationInvestigation from "$lib/components/CreationInvestigation.svelte";
  import { investigationHref, investigationSelection } from "$lib/creation/intake";

  const focus = $derived(page.url.searchParams.getAll("investigation"));
  const selected = $derived(focus.length === 1 ? investigationSelection(focus[0] ?? null) : null);
  const noteFocus = $derived(page.url.searchParams.getAll("notes"));
  const selectedNote = $derived(noteFocus.length === 1 ? notesFocusSelection(noteFocus[0] ?? null) : null);
  let navigationError = $state("");
  function selectCase(caseId: string | null) {
    navigationError = "";
    void goto(caseId ? investigationHref(caseId) : "/bridge?investigation=new", {
      replaceState: true, keepFocus: true, noScroll: true
    }).catch(() => { navigationError = "Navigation failed. Keep the displayed case UUID to Check it later."; });
  }
  function selectNote(selection: string) {
    navigationError = "";
    void goto(notesHref(selection), { replaceState: true, keepFocus: true, noScroll: true })
      .catch(() => { navigationError = "Navigation failed. Keep the displayed exact source and record identities."; });
  }
</script>

<svelte:head><title>Bridge — LychD</title></svelte:head>

{#if noteFocus.length > 0 && (focus.length > 0 || selectedNote === null)}
  <section aria-labelledby="invalid-notes"><h1 id="invalid-notes">Public-note selection unavailable</h1>
    <p role="alert">Choose one public-note focus: manage, new, recall or an exact record UUID. Investigation and notes cannot be selected together. No request was sent.</p>
    <a href="/bridge?notes=manage">Manage public notes</a><a href="/bridge">Return to conversation</a>
  </section>
{:else if selectedNote !== null}
  {#if navigationError}<p role="alert">{navigationError}</p>{/if}
  {#if selectedNote === "recall"}<PublicNoteRecall />
  {:else}<PublicNotes selection={selectedNote} onSelect={selectNote} />{/if}
{:else if focus.length === 0}
  <section class="shell-placeholder" aria-labelledby="bridge-landing-title">
    <h1 id="bridge-landing-title">The Altar</h1>
    <p>Your conversation is in the Bridge panel. Choose an instrument to continue your work beside it.</p>
    <nav aria-label="Start working"><a href="/atlas">Atlas</a><a href="/orb">Orb</a><a href="/loom">Loom</a><a href="/nexus">Nexus</a></nav>
  </section>
{:else if selected === null}
  <section aria-labelledby="invalid-investigation">
    <h1 id="invalid-investigation">Investigation selection unavailable</h1>
    <p role="alert">Choose one case UUID or start a new investigation. No request was sent.</p>
    <a href="/bridge?investigation=new">Investigate public source</a>
    <a href="/bridge">Return to conversation</a>
  </section>
{:else}
  {#if navigationError}<p role="alert">{navigationError}</p>{/if}
  <CreationInvestigation caseId={selected === "new" ? null : selected} onSelect={selectCase} />
{/if}
