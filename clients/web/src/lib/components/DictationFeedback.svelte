<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import {
    listDictationCorrections, listDictationAttempts, getDictationAttempt, deleteDictationAttempt, listDictationLexicon,
    approveDictationLexicon, deleteDictationLexicon, getDictationSuggestions
  } from "$lib/api/client";
  import type {
    DictationCorrection, DictationAttemptSummary, DictationResult, DictationLexiconRule, DictationLexiconRuleRequest, DictationSuggestion
  } from "$lib/api/models";

  let { attemptId, originalText, finalText, language, savedRevision, applySuggestion, active = true }: {
    attemptId: string | null;
    originalText: string;
    finalText: string;
    language: string;
    savedRevision: number;
    applySuggestion: (text: string) => boolean;
    active?: boolean;
  } = $props();

  const id = $props.id();
  type ReadState = "idle" | "loading" | "ready" | "error";
  type Deletions = Record<string, "busy" | "unknown">;
  let alive = true;
  let visibilityEpoch = 0;
  let visible = $state(true);
  let historyOpen = $state(false);
  let lexiconOpen = $state(false);
  let suggestionOpen = $state(false);
  let historyReload = $state(0);
  let lexiconReload = $state(0);
  let suggestionReload = $state(0);
  let historyState = $state<ReadState>("idle");
  let lexiconState = $state<ReadState>("idle");
  let suggestionState = $state<ReadState>("idle");
  let corrections = $state.raw<DictationCorrection[]>([]);
  let attempts = $state.raw<DictationAttemptSummary[]>([]);
  let historyCount = $state(25);
  let historyError = $state("");
  let correctionError = $state("");
  let correctionsLoading = $state(false);
  let correctionByAttempt = $derived(new Map(corrections.map((item) => [item.attempt_id, item])));
  let inspectedId = $state<string | null>(null);
  let inspectionState = $state<ReadState>("idle");
  let inspectionResult = $state.raw<DictationResult | null>(null);
  let inspectionController: AbortController | null = null;
  let rules = $state.raw<DictationLexiconRule[]>([]);
  let suggestion = $state.raw<DictationSuggestion | null>(null);
  let suggestionDraft = "";
  let historyDeletes = $state.raw<Deletions>({});
  let ruleDeletes = $state.raw<Deletions>({});
  let historyNotice = $state("");
  let lexiconNotice = $state("");
  let suggestionNotice = $state("");
  let historySummary: HTMLElement;
  let lexiconSummary: HTMLElement;
  let editedLanguage = $state<string | null>(null);
  let ruleLanguage = $derived(editedLanguage ?? language);
  let heard = $state("");
  let replacement = $state("");
  let approved = $state(false);
  let approvalState = $state<"idle" | "saving" | "unknown">("idle");
  let pendingApproval = $state.raw<DictationLexiconRuleRequest | null>(null);
  let approvalChecked = $state(false);
  let suggestionVersion = 0;
  const deletionFocusCleanups = new Set<() => void>();
  // Spread props may invalidate together. Only a semantic request change may
  // restart a suggestion and capture a new draft baseline.
  let suggestionReadKey = $derived(JSON.stringify([
    suggestionOpen, visible, active, attemptId, originalText, language, suggestionReload
  ]));

  onDestroy(() => {
    alive = false;
    visibilityEpoch += 1;
    inspectionController?.abort();
    for (const dispose of deletionFocusCleanups) dispose();
  });

  function suspendMutations() {
    visibilityEpoch += 1;
    for (const dispose of deletionFocusCleanups) dispose();
    historyDeletes = Object.fromEntries(Object.keys(historyDeletes).map((key) => [key, "unknown"] as const));
    ruleDeletes = Object.fromEntries(Object.keys(ruleDeletes).map((key) => [key, "unknown"] as const));
    if (approvalState === "saving") {
      approvalState = "unknown";
      lexiconNotice = "Approval outcome is unknown. Check approved vocabulary before another approval.";
    }
  }

  function visibilityChanged() {
    visible = document.visibilityState !== "hidden";
    if (!visible) suspendMutations();
  }

  function freezeFormLanguage() {
    // A pristine form follows the transcript; an edited/submitted form owns its tag.
    if (editedLanguage === null) editedLanguage = ruleLanguage;
  }

  function expiry(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  function readHistory() {
    const controller = new AbortController();
    historyState = "loading";
    historyError = "";
    correctionError = "";
    corrections = [];
    correctionsLoading = true;
    cancelInspection();
    void listDictationAttempts(controller.signal).then((catalogue) => {
      if (!alive || controller.signal.aborted || !visible || !active) return;
      if (catalogue.length > 1000) {
        historyError = "Voice history exceeded the supported 1,000-attempt limit. Refresh history; no incomplete list is shown.";
        historyState = "error";
        return;
      }
      attempts = catalogue;
      historyDeletes = Object.fromEntries(Object.entries(historyDeletes).filter(([, state]) => state === "busy"));
      historyState = "ready";
    }).catch(() => {
      if (!alive || controller.signal.aborted || !visible || !active) return;
      historyError = "Could not load voice history.";
      historyState = "error";
    });
    void listDictationCorrections(controller.signal).then((edits) => {
      if (!alive || controller.signal.aborted || !visible || !active) return;
      correctionsLoading = false;
      if (edits.length <= 1000) corrections = edits;
      else correctionError = "Saved corrections exceeded the supported limit. Attempt inspection and deletion remain available. Refresh history to retry.";
    }).catch(() => {
      if (!alive || controller.signal.aborted || !visible || !active) return;
      correctionsLoading = false;
      correctionError = "Saved corrections could not be loaded completely. Attempt inspection and deletion remain available. Refresh history to retry.";
    });
    return () => { controller.abort(); cancelInspection(); };
  }

  function cancelInspection() {
    inspectionController?.abort();
    inspectionController = null;
    inspectedId = null;
    inspectionResult = null;
    inspectionState = "idle";
  }

  async function inspectAttempt(itemId: string) {
    if (!active || !visible || !historyOpen || historyDeletes[itemId]) return;
    cancelInspection();
    const controller = new AbortController();
    inspectionController = controller;
    inspectedId = itemId;
    inspectionState = "loading";
    try {
      const result = await getDictationAttempt(itemId, controller.signal);
      if (!alive || !active || !visible || !historyOpen || controller.signal.aborted
        || inspectionController !== controller) return;
      if (result.attempt_id !== itemId) {
        inspectionState = "error";
        return;
      }
      inspectionResult = result;
      inspectionState = "ready";
    } catch {
      if (alive && active && visible && historyOpen && !controller.signal.aborted
        && inspectionController === controller) inspectionState = "error";
    }
  }

  function readLexicon() {
    const controller = new AbortController();
    lexiconState = "loading";
    void listDictationLexicon(controller.signal).then((result) => {
      if (!alive || controller.signal.aborted || !visible || !active) return;
      rules = result.slice(0, 128);
      ruleDeletes = Object.fromEntries(Object.entries(ruleDeletes).filter(([, state]) => state === "busy"));
      lexiconState = "ready";
      if (pendingApproval && approvalState === "unknown") {
        const pending = pendingApproval;
        const found = rules.find((rule) => rule.language === pending.language.toLowerCase()
          && rule.heard === pending.heard.normalize("NFC") && rule.replacement === pending.replacement.normalize("NFC"));
        if (found) {
          approvalState = "idle";
          pendingApproval = null;
          approved = false;
          lexiconNotice = "Approval confirmed in retained vocabulary.";
        } else {
          approvalChecked = true;
          lexiconNotice = "No matching retained rule was found. The previous approval remains unconfirmed; your form is preserved.";
        }
      }
    }).catch(() => {
      if (alive && !controller.signal.aborted && visible && active) lexiconState = "error";
    });
    return () => controller.abort();
  }

  function readSuggestion(currentAttempt: string, currentOriginal: string, currentLanguage: string) {
    const controller = new AbortController();
    const version = ++suggestionVersion;
    const draft = finalText;
    suggestion = null;
    suggestionNotice = "";
    suggestionState = "loading";
    void getDictationSuggestions({ attempt_id: currentAttempt }, controller.signal).then((result) => {
      if (!alive || !visible || !active || controller.signal.aborted || version !== suggestionVersion
        || attemptId !== currentAttempt || originalText !== currentOriginal || language !== currentLanguage) return;
      if (result.attempt_id !== currentAttempt || result.original_text !== currentOriginal
        || result.language.toLowerCase() !== currentLanguage.toLowerCase()) {
        suggestionState = "error";
        return;
      }
      suggestionDraft = draft;
      suggestion = result;
      suggestionState = "ready";
    }).catch(() => {
      if (alive && visible && active && !controller.signal.aborted && version === suggestionVersion) suggestionState = "error";
    });
    return () => { controller.abort(); suggestionVersion += 1; };
  }

  // These effects synchronize explicit disclosures with private server reads.
  $effect(() => {
    if (!active) untrack(suspendMutations);
  });
  $effect(() => {
    void savedRevision; void historyReload;
    if (historyOpen && visible && active) return untrack(readHistory);
  });
  $effect(() => {
    void lexiconReload;
    if (lexiconOpen && visible && active) return untrack(readLexicon);
  });
  $effect(() => {
    void suggestionReadKey;
    return untrack(() => {
      if (suggestionOpen && visible && active && attemptId) {
        return readSuggestion(attemptId, originalText, language);
      }
    });
  });

  async function remove(kind: "correction" | "rule", itemId: string, button: HTMLButtonElement) {
    const states = kind === "correction" ? historyDeletes : ruleDeletes;
    if (states[itemId] || !visible || !active) return;
    const epoch = visibilityEpoch;
    const opener = button;
    const row = button.closest("li");
    const initiallyOwnedFocus = document.activeElement === opener || !!row?.contains(document.activeElement);
    let focusMovedElsewhere = false;
    const trackFocus = (event: FocusEvent) => {
      if (event.target instanceof Node && event.target !== document.body && !row?.contains(event.target)) {
        focusMovedElsewhere = true;
      }
    };
    const trackPointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !row?.contains(event.target)) focusMovedElsewhere = true;
    };
    const disposeFocusTracking = () => {
      document.removeEventListener("focusin", trackFocus);
      document.removeEventListener("pointerdown", trackPointer, true);
      deletionFocusCleanups.delete(disposeFocusTracking);
    };
    document.addEventListener("focusin", trackFocus);
    document.addEventListener("pointerdown", trackPointer, true);
    deletionFocusCleanups.add(disposeFocusTracking);
    if (kind === "correction") historyDeletes = { ...historyDeletes, [itemId]: "busy" };
    else ruleDeletes = { ...ruleDeletes, [itemId]: "busy" };
    try {
      if (kind === "correction") await deleteDictationAttempt(itemId);
      else await deleteDictationLexicon(itemId);
      if (!alive || !visible || !active || epoch !== visibilityEpoch) return;
      // Check current ownership immediately before removing the row. The operator
      // may have moved to the draft while the deletion request was pending.
      const focusedBeforeRemoval = document.activeElement;
      const restoreFocus = focusedBeforeRemoval === opener || !!row?.contains(focusedBeforeRemoval)
        // Disabling the active native button may move focus to body without an
        // operator gesture. Restore only if no later focus/pointer intent moved away.
        || (initiallyOwnedFocus && !focusMovedElsewhere && focusedBeforeRemoval === document.body);
      // The summary is already mounted outside the changing list. Transfer focus
      // before removing the row, avoiding a body-focus gap and a second async race.
      if (restoreFocus) {
        if (kind === "correction" && historyOpen) historySummary?.focus();
        if (kind === "rule" && lexiconOpen) lexiconSummary?.focus();
      }
      if (kind === "correction") {
        if (inspectedId === itemId) cancelInspection();
        attempts = attempts.filter((item) => item.attempt_id !== itemId);
        corrections = corrections.filter((item) => item.attempt_id !== itemId);
        historyNotice = "Retained attempt and any saved correction deleted.";
        historyReload += 1;
      } else {
        rules = rules.filter((item) => item.id !== itemId);
        lexiconNotice = "Approved rule removed.";
        lexiconReload += 1;
      }
      suggestion = null;
      suggestionState = "idle";
      suggestionNotice = "Retained data changed. Refresh the suggestion before using it.";
      suggestionVersion += 1;
    } catch {
      if (!alive || !visible || !active || epoch !== visibilityEpoch) return;
      if (kind === "correction") {
        historyDeletes = { ...historyDeletes, [itemId]: "unknown" };
        historyNotice = "Deletion could not be confirmed. Refresh history before trying again.";
      } else {
        ruleDeletes = { ...ruleDeletes, [itemId]: "unknown" };
        lexiconNotice = "Removal could not be confirmed. Refresh vocabulary before trying again.";
      }
    } finally {
      disposeFocusTracking();
    }
  }

  async function approveRule(event: SubmitEvent) {
    event.preventDefault();
    if (!visible || !active || approvalState !== "idle" || !approved || !heard.trim() || !replacement.trim() || !ruleLanguage.trim()) return;
    freezeFormLanguage();
    const body: DictationLexiconRuleRequest = { language: ruleLanguage.trim(), heard, replacement, approved: true };
    pendingApproval = body;
    approvalState = "saving";
    approvalChecked = false;
    const epoch = visibilityEpoch;
    try {
      await approveDictationLexicon(body);
      if (!alive || !visible || !active || epoch !== visibilityEpoch) return;
      pendingApproval = null;
      approvalState = "idle";
      approved = false;
      lexiconNotice = "Vocabulary rule approved. Suggestions still require your review.";
      lexiconReload += 1;
      suggestion = null;
      suggestionState = "idle";
      suggestionNotice = "Vocabulary changed. Refresh the suggestion before using it.";
      suggestionVersion += 1;
    } catch {
      if (!alive || !visible || !active || epoch !== visibilityEpoch) return;
      approvalState = "unknown";
      lexiconNotice = "Approval could not be confirmed. Check approved vocabulary before another approval.";
    }
  }

  function useSuggestion() {
    if (!visible || !active || !suggestion || suggestion.attempt_id !== attemptId
      || suggestion.original_text !== originalText || finalText !== suggestionDraft
      || suggestion.rules.some((rule) => new Date(rule.expires_at).getTime() <= Date.now())) {
      suggestionNotice = "Suggestion not applied: the draft or attempt changed. Review the current draft.";
      return;
    }
    suggestionNotice = applySuggestion(suggestion.suggested_text)
      ? "Suggestion applied to the draft. Review it before sending."
      : "Suggestion not applied: the draft or attempt changed. Review the current draft.";
  }
</script>

<svelte:document onvisibilitychange={visibilityChanged} />

<section class="dictation-feedback" aria-label="Dictation feedback" hidden={!active}>
  <details bind:open={suggestionOpen}>
    <summary>Vocabulary suggestion</summary>
    {#if suggestionOpen}
      {#if !attemptId}<p>Record a transcript to check approved vocabulary.</p>
      {:else}
        {#if suggestionState === "loading"}<p role="status">Checking approved vocabulary…</p>
        {:else if suggestionState === "error"}<p role="alert">Suggestion unavailable. The retained attempt may have expired or been deleted.</p>
        {:else if suggestion && suggestion.attempt_id === attemptId}
          {#if suggestion.applied_rule_ids.length}
            <label for={`${id}-suggestion`}>Suggested text</label>
            <textarea id={`${id}-suggestion`} rows="3" readonly value={suggestion.suggested_text}></textarea>
            <p>Applied rules ({suggestion.language})</p>
            <ul class="bounded" aria-label="Applied vocabulary rules">
              {#each suggestion.rules.slice(0, 128) as rule (rule.id)}<li><span>{rule.heard}</span> → <span>{rule.replacement}</span></li>{/each}
            </ul>
            <button type="button" onclick={useSuggestion}>Use suggestion</button>
          {:else}<p>No approved rules matched this transcript.</p>{/if}
        {/if}
        <button type="button" disabled={suggestionState === "loading"} onclick={() => suggestionReload += 1}>{suggestionState === "error" ? "Retry suggestion" : "Refresh suggestion"}</button>
      {/if}
      {#if suggestionNotice}<p role="status">{suggestionNotice}</p>{/if}
    {/if}
  </details>

  <details bind:open={historyOpen}>
    <summary bind:this={historySummary}>Voice history</summary>
    {#if historyOpen}
      <p>Retained attempts, including those without saved corrections. Inspect reads an existing outcome; it never restarts transcription. Deleting an attempt also removes any saved correction.</p>
      <button type="button" disabled={historyState === "loading"} onclick={() => historyReload += 1}>{historyState === "error" ? "Retry history" : "Refresh history"}</button>
      {#if historyState === "loading"}<p role="status">Loading voice history…</p>
      {:else if historyState === "error"}<p role="alert">{historyError}</p>
      {:else if historyState === "ready"}
        {#if correctionError}<p role="alert">{correctionError}</p>{/if}
        <p role="status">Showing {Math.min(historyCount, attempts.length)} of {attempts.length} retained attempts.</p>
        <ul class="bounded records" aria-label="Retained voice attempts">
          {#each attempts.slice(0, historyCount) as attempt (attempt.attempt_id)}
            {@const correction = correctionByAttempt.get(attempt.attempt_id)}
            <li>
              <p>{attempt.language} · {attempt.status.replaceAll("_", " ")}</p>
              <p>Expires <time datetime={attempt.expires_at}>{expiry(attempt.expires_at)}</time> · Created <time datetime={attempt.created_at}>{expiry(attempt.created_at)}</time></p>
              <p>{attempt.audio_available ? "Audio retained until" : "Audio no longer available; retention deadline"} <time datetime={attempt.audio_expires_at}>{expiry(attempt.audio_expires_at)}</time></p>
              {#if correction}
                <details><summary>Original and final text</summary><dl><dt>Original transcript</dt><dd>{correction.original_text}</dd><dt>Final saved correction</dt><dd>{correction.final_text}</dd></dl></details>
              {:else if attempt.has_correction && correctionsLoading}<p role="status">Loading saved correction…</p>
              {:else}<p>{attempt.has_correction ? "Saved correction is not available in this history read." : "No saved correction."}</p>{/if}
              <button type="button" disabled={!!historyDeletes[attempt.attempt_id] || (inspectedId === attempt.attempt_id && inspectionState === "loading")} aria-label={`Inspect retained attempt ${attempt.attempt_id}`} onclick={() => void inspectAttempt(attempt.attempt_id)}>{attempt.status === "unknown" ? "Check outcome" : "Inspect attempt"}</button>
              {#if inspectedId === attempt.attempt_id}
                {#if inspectionState === "loading"}<p role="status">Checking retained outcome…</p>
                {:else if inspectionState === "error"}<p role="alert">Could not inspect this attempt. It may have expired or been deleted. Use Inspect or Check outcome to retry the read.</p>
                {:else if inspectionResult}
                  <p role="status">Retained outcome: {inspectionResult.status.replaceAll("_", " ")}.</p>
                  {#if inspectionResult.status === "transcribed" && inspectionResult.original_text !== null}
                    <label for={`${id}-history-original`}>Original transcript for this attempt</label>
                    <textarea id={`${id}-history-original`} rows="3" readonly value={inspectionResult.original_text ?? ""}></textarea>
                    <p>Read-only history. Select and copy text if needed; it is not inserted into the current draft or command target.</p>
                  {:else if inspectionResult.status === "unknown"}<p>Outcome remains unknown. This check does not restart transcription.</p>
                  {:else}<p>No transcript is available for this retained outcome.</p>{/if}
                {/if}
              {/if}
              <button type="button" disabled={!!historyDeletes[attempt.attempt_id]} aria-label={`Delete retained attempt ${attempt.attempt_id}`} onclick={(event) => void remove("correction", attempt.attempt_id, event.currentTarget)}>{historyDeletes[attempt.attempt_id] === "busy" ? "Deleting…" : "Delete attempt"}</button>
              {#if historyDeletes[attempt.attempt_id] === "unknown"}<p role="status">Deletion unconfirmed; refresh history.</p>{/if}
            </li>
          {:else}<li>No retained voice attempts.</li>{/each}
        </ul>
        {#if historyCount < attempts.length}<button type="button" onclick={() => historyCount = Math.min(historyCount + 25, attempts.length, 1000)}>Show more attempts</button>{/if}
      {/if}
      {#if historyNotice}<p role="status">{historyNotice}</p>{/if}
    {/if}
  </details>

  <details bind:open={lexiconOpen}>
    <summary bind:this={lexiconSummary}>Approved vocabulary</summary>
    {#if lexiconOpen}
      <p>Approve exact phrases for one language. Corrections never create rules automatically. This does not train the model.</p>
      <form onsubmit={approveRule}>
        <fieldset disabled={approvalState !== "idle"}>
          <legend>Add a vocabulary rule</legend>
          <label for={`${id}-language`}>Rule language</label>
          <input id={`${id}-language`} type="text" value={ruleLanguage} oninput={(event) => editedLanguage = event.currentTarget.value} placeholder="en" required maxlength="35" autocomplete="off" autocapitalize="none" spellcheck="false" />
          <p>Use the transcript’s exact language tag, for example en or en-us.</p>
          <label for={`${id}-heard`}>Heard phrase</label>
          <input id={`${id}-heard`} type="text" bind:value={heard} oninput={freezeFormLanguage} required maxlength="128" autocomplete="off" />
          <label for={`${id}-replacement`}>Replacement phrase</label>
          <input id={`${id}-replacement`} type="text" bind:value={replacement} oninput={freezeFormLanguage} required maxlength="128" autocomplete="off" />
          <label class="check"><input type="checkbox" bind:checked={approved} onchange={freezeFormLanguage} /> I approve this language and phrase replacement</label>
          <button type="submit" disabled={!approved || !heard.trim() || !replacement.trim() || !ruleLanguage.trim()}>{approvalState === "saving" ? "Approving…" : "Approve rule"}</button>
        </fieldset>
      </form>
      {#if approvalState === "unknown"}
        <p role="alert">Approval is unconfirmed. The submitted form is held unchanged.</p>
        <button type="button" disabled={lexiconState === "loading"} onclick={() => lexiconReload += 1}>Check saved approval</button>
        {#if approvalChecked}<button type="button" onclick={() => { pendingApproval = null; approvalState = "idle"; approvalChecked = false; approved = false; }}>Review form for a new approval</button>{/if}
      {/if}
      <button type="button" disabled={lexiconState === "loading"} onclick={() => lexiconReload += 1}>{lexiconState === "error" ? "Retry vocabulary" : "Refresh vocabulary"}</button>
      {#if lexiconState === "loading"}<p role="status">Loading approved vocabulary…</p>
      {:else if lexiconState === "error"}<p role="alert">Could not load approved vocabulary.</p>
      {:else if lexiconState === "ready"}
        <ul class="bounded records" aria-label="Approved vocabulary rules">
          {#each rules as rule (rule.id)}
            <li><p>{rule.language}: <span>{rule.heard}</span> → <span>{rule.replacement}</span></p>
              <p>Expires <time datetime={rule.expires_at}>{expiry(rule.expires_at)}</time></p>
              <button type="button" disabled={!!ruleDeletes[rule.id]} aria-label={`Remove vocabulary rule ${rule.heard} (${rule.language})`} onclick={(event) => void remove("rule", rule.id, event.currentTarget)}>{ruleDeletes[rule.id] === "busy" ? "Removing…" : "Remove rule"}</button>
              {#if ruleDeletes[rule.id] === "unknown"}<p role="status">Removal unconfirmed; refresh vocabulary.</p>{/if}
            </li>
          {:else}<li>No approved vocabulary rules.</li>{/each}
        </ul>
        {#if rules.length === 128}<p>Showing up to 128 approved rules.</p>{/if}
      {/if}
      {#if lexiconNotice}<p role="status">{lexiconNotice}</p>{/if}
    {/if}
  </details>
</section>

<style>
  .dictation-feedback { min-width: 0; font-size: var(--text-sm); color: var(--color-parchment); }
  details { min-width: 0; border-top: 1px solid var(--color-engraving); }
  summary { min-height: 2.75rem; align-content: center; cursor: pointer; overflow-wrap: anywhere; }
  p { margin: .5rem 0; line-height: 1.5; overflow-wrap: anywhere; }
  label { display: block; margin-block: .4rem; }
  fieldset { min-width: 0; margin: .6rem 0; padding: .6rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-glyph); }
  legend { padding-inline: .25rem; }
  input:not([type="checkbox"]), textarea { box-sizing: border-box; display: block; width: 100%; min-width: 0; min-height: 2.75rem; padding: .5rem; font: inherit; color: var(--color-bone); background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); }
  textarea { resize: vertical; max-height: 12rem; }
  .check { display: flex; align-items: center; gap: .6rem; min-height: 2.75rem; }
  .check input { flex: 0 0 auto; }
  button { max-width: 100%; min-height: 2.75rem; margin: .25rem .25rem .25rem 0; padding: .4rem .6rem; font: inherit; overflow-wrap: anywhere; color: var(--color-bone); background: var(--color-obsidian); border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); cursor: pointer; }
  button:disabled { opacity: .55; cursor: default; }
  .bounded { max-height: 20rem; overflow-y: auto; padding: .25rem .25rem .25rem 1.3rem; overflow-wrap: anywhere; }
  .records { list-style: none; padding-left: .25rem; }
  .records > li { padding-block: .5rem; border-bottom: 1px solid var(--color-engraving); }
  dl { margin: .5rem 0; }
  dt { color: var(--color-bone); }
  dd { margin: .25rem 0 .75rem; white-space: pre-wrap; overflow-wrap: anywhere; max-height: 10rem; overflow-y: auto; }
  span { white-space: pre-wrap; }
  button:focus-visible, input:focus-visible, textarea:focus-visible, summary:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
