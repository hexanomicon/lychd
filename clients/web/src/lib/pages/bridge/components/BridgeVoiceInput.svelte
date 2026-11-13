<script lang="ts">
  import { onMount, untrack, type Snippet } from "svelte";
  import { ApiError, getDictationDiscovery, getDictationAttempt, transcribeDictation, recordDictationCorrection } from "$lib/api/client";
  import type { DictationDiscovery } from "$lib/api/models";
  import type { CommandTarget } from "$lib/pages/bridge/state/work-commands";
  import { createVoiceCapture, VOICE_MAX_WAV_BYTES, type VoiceCaptureState } from "$lib/pages/bridge/state/voice/capture";
  import { createDictationCoordinator, newDictationAttemptId, type DictationCapture, type DictationDraft, type DictationOptions } from "$lib/pages/bridge/state/voice/dictation";

  interface Props {
    snapshot: DictationDraft;
    target: CommandTarget | null;
    onadopt: DictationOptions["adopt"];
    onsubmit: DictationOptions["submit"];
    readSnapshot?: () => DictationDraft;
    isTargetCurrent?: (target: CommandTarget) => boolean;
    feedback?: Snippet<[{ attemptId: string | null; originalText: string; finalText: string; language: string; savedRevision: number; active: boolean; applySuggestion: (text: string) => boolean }]>;
  }
  let { snapshot, target, onadopt, onsubmit, readSnapshot, isTargetCurrent, feedback }: Props = $props();
  const id = $props.id();
  let discovery = $state.raw<DictationDiscovery | null>(null);
  let discoveryMessage = $state("Checking voice availability…");
  let discovering = $state(false);
  let optionsOpen = $state(false);
  let feedbackMounted = $state(false);
  let recoveryToken = $state.raw<DictationCapture | null>(null);
  let recovering = $state(false);
  let recoveryMessage = $state("");
  let recoveredText = $state("");
  let language = $state("");
  let captureState = $state.raw<Readonly<VoiceCaptureState>>({ status: "idle", elapsedMs: 0, limitMs: 30_000 });
  let processing = $state(false);
  let error = $state("");
  let rememberCorrections = $state(false);
  let correctionMessage = $state("");
  let savedRevision = $state(0);
  let attemptId = $state<string | null>(null);
  let pinnedLanguage = $state("");
  let pinnedTarget = $state("");
  let now = $state(Date.now());
  let alive = true;
  let generation = 0;
  let discoveryGeneration = 0;
  let controller: AbortController | null = null;
  let recoveryController: AbortController | null = null;
  let capture: ReturnType<typeof createVoiceCapture> | null = null;
  let observed: DictationDraft | null = null;
  let dispatched: DictationDraft | null = null;
  let eventSnapshot: DictationDraft | null = null;
  let adoption: DictationDraft | null = null;
  let adoptedPrefix = "";
  let currentCapture: DictationCapture | null = null;
  let audioSubmitted = false;
  const read = () => eventSnapshot ?? readSnapshot?.() ?? snapshot;
  const coordinator = createDictationCoordinator({
    read,
    adopt: (expected, text) => {
      const result = onadopt(expected, text);
      if (result) { adoption = result; adoptedPrefix = expected.draftText; }
      return result;
    },
    isTargetCurrent: (value) => isTargetCurrent?.(value) === true,
    onChange: (value) => { view = value; now = Date.now(); },
    submit: (draft, meta) => {
      dispatched = draft;
      const save = rememberCorrections;
      const context = generation;
      // Invoke Bridge synchronously: its offering identity/busy claim precedes any await.
      const result = onsubmit(draft, meta);
      if (save) {
        correctionMessage = "Saving private correction…";
        void recordDictationCorrection({ attempt_id: meta.attemptId, final_text: draft.draftText.trim() }).then(() => {
          if (!alive || context !== generation) return;
          correctionMessage = "Private correction saved. Vocabulary changes require separate approval.";
          savedRevision += 1;
        }).catch(() => {
          if (alive && context === generation) correctionMessage = "Correction storage could not be confirmed. No learning is claimed.";
        });
      }
      return result;
    }
  });
  let view = $state.raw(coordinator.view);
  const recording = $derived(["requesting", "recording", "stopping"].includes(captureState.status));
  const available = $derived(discovery?.status === "available" && !!discovery.profile_digest && !!language && discovery.languages?.includes(language));
  const seconds = $derived(view.deadline === null ? 0 : Math.max(0, Math.ceil((view.deadline - now) / 1000)));
  const status = $derived(processing ? "Transcribing…" : captureState.status === "requesting" ? "Waiting for microphone permission…" :
    captureState.status === "recording" ? `Recording ${Math.floor(captureState.elapsedMs / 1000)} / 30 seconds` :
    captureState.status === "stopping" ? "Finishing recording…" : attemptId && view.adopted && view.phase !== "submitted" ?
    "Transcript added to draft. Review and send." : discoveryMessage);

  async function discover() {
    const ticket = ++discoveryGeneration;
    discovering = true;
    discovery = null;
    discoveryMessage = "Checking voice availability…";
    try {
      const result = await getDictationDiscovery();
      if (!alive || ticket !== discoveryGeneration) return;
      discovery = result;
      language = result.languages?.includes(language) ? language : result.languages?.[0] ?? "";
      discoveryMessage = result.status === "available" && result.profile_digest && language ?
        "Local transcription configured; microphone and recognition quality unverified." :
        `Voice unavailable: ${(result.reason ?? "no declared language").replaceAll("_", " ")}.`;
    } catch {
      if (alive && ticket === discoveryGeneration) discoveryMessage = "Voice availability could not be checked. Typed messages remain available.";
    } finally {
      if (alive && ticket === discoveryGeneration) discovering = false;
    }
  }

  function cancelCapture(preserveRecovery = false) {
    const pending = audioSubmitted ? currentCapture : null;
    generation += 1;
    controller?.abort(); controller = null;
    recoveryController?.abort(); recoveryController = null; recovering = false;
    if (pending) {
      recoveryToken = pending;
      recoveryMessage = "Local transcription wait cancelled. The server outcome may be unknown; check the attempt without resending audio.";
    } else if (!preserveRecovery) { recoveryToken = null; recoveryMessage = ""; recoveredText = ""; }
    capture?.dispose(); capture = null;
    processing = false;
    captureState = { status: "cancelled", elapsedMs: 0, limitMs: 30_000 };
    coordinator.cancel();
    attemptId = null;
    currentCapture = null;
    audioSubmitted = false;
  }

  /** The shell hides this mounted conversation without leaving capture armed. */
  export function suspend() { cancelCapture(true); }

  function sameContext(a: DictationDraft, b: DictationDraft) {
    return a.sessionId === b.sessionId && a.mode === b.mode && a.contextEpoch === b.contextEpoch && a.targetEpoch === b.targetEpoch;
  }

  /** Call in parent edit/IME/navigation handlers, before a batched UI update can hide a transient change. */
  export function notifyChanged(next: DictationDraft = read()) {
    if (!alive) return;
    eventSnapshot = next;
    try {
      if (observed && !sameContext(observed, next)) {
        cancelCapture(true);
        correctionMessage = "";
        pinnedTarget = "";
        void discover();
      } else if (dispatched && (dispatched.draftRevision !== next.draftRevision || dispatched.draftText !== next.draftText)) {
        // The ordinary Bridge cleared/replaced a consumed draft; a later typed draft is ordinary.
        coordinator.cancel(); attemptId = null; dispatched = null;
      }
      observed = { ...next };
      coordinator.notifyChanged();
    } finally { eventSnapshot = null; }
  }

  /** true means the voice coordinator owns Send, including a refused or already-consumed claim. */
  export function handleSend(): boolean {
    notifyChanged();
    if (attemptId !== null && view.adopted) {
      coordinator.sendManual();
      return true;
    }
    coordinator.cancelAutosend();
    return false;
  }

  function applySuggestion(text: string): boolean {
    coordinator.cancelAutosend();
    if (!attemptId || !text.trim()) return false;
    if (!view.adopted) return coordinator.setFinalText(text);
    const current = read();
    if (!adoption || !sameContext(adoption, current) || current.draftRevision !== adoption.draftRevision ||
        current.draftText !== adoption.draftText || current.busy || current.composing || view.phase === "submitted") return false;
    const nextText = adoptedPrefix + (adoptedPrefix && !/\s$/.test(adoptedPrefix) ? " " : "") + text;
    const result = onadopt(current, nextText);
    if (!result) return false;
    adoption = result;
    notifyChanged(result);
    return true;
  }

  async function recoverAttempt() {
    const token = recoveryToken;
    if (!alive || !token || recovering) return;
    const request = new AbortController(); recoveryController = request;
    recovering = true; recoveryMessage = "Checking transcription outcome…";
    try {
      const result = await getDictationAttempt(token.attemptId, request.signal);
      if (!alive || request.signal.aborted || recoveryToken !== token) return;
      if (result.attempt_id !== token.attemptId) throw new Error("Mismatched attempt");
      if (result.status === "unknown") {
        recoveryMessage = "Transcription outcome is still unknown. You can check again; audio will not be resent.";
      } else if (result.status === "transcribed") {
        error = "";
        coordinator.cancelAutosend();
        if (sameContext(token.draft, read()) && coordinator.receive(token, result)) {
          recoveryMessage = view.adopted ? "Recovered transcript added to draft. Review and send manually." : "Recovered transcript kept separately for review.";
        } else {
          recoveredText = result.original_text ?? "";
          recoveryMessage = "Recovered transcript belongs to an earlier context. Review it separately; it has not changed this draft.";
        }
        recoveryToken = null;
      } else {
        error = "";
        recoveryMessage = `Transcription ${result.status}: ${(result.reason ?? "unavailable").replaceAll("_", " ")}. No transcript was adopted.`;
        recoveryToken = null;
      }
    } catch (failure) {
      if (!alive || request.signal.aborted || recoveryToken !== token) return;
      if (failure instanceof ApiError && failure.status === 404) error = "";
      recoveryMessage = failure instanceof ApiError && failure.status === 404 ?
        "This attempt is unavailable. It may have expired or been deleted; no transcript can be recovered." :
        "Could not check this attempt. Its transcription outcome remains unknown.";
    } finally {
      if (recoveryController === request) { recoveryController = null; recovering = false; }
    }
  }

  function encodeBlobBase64(blob: Blob, signal: AbortSignal): Promise<string> {
    if (blob.size < 46 || blob.size > VOICE_MAX_WAV_BYTES || signal.aborted) return Promise.reject(new Error("Audio unavailable"));
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      const finish = () => signal.removeEventListener("abort", abort);
      const abort = () => { reader.abort(); finish(); reject(new Error("Cancelled")); };
      signal.addEventListener("abort", abort, { once: true });
      reader.onerror = () => { finish(); reject(new Error("Audio could not be encoded")); };
      reader.onload = () => {
        finish();
        if (signal.aborted || typeof reader.result !== "string") { reject(new Error("Cancelled")); return; }
        const separator = reader.result.indexOf(",");
        if (separator < 0) { reject(new Error("Invalid audio encoding")); return; }
        resolve(reader.result.slice(separator + 1));
      };
      reader.readAsDataURL(blob);
    });
  }

  async function start() {
    const current = read();
    if (!alive || !available || recording || processing || recovering || current.busy || current.composing || !current.sessionId ||
        (current.mode === "work" && (!target || isTargetCurrent?.(target) !== true))) return;
    error = ""; correctionMessage = ""; dispatched = null;
    recoveryToken = null; recoveryMessage = ""; recoveredText = "";
    const ticket = ++generation;
    const request = new AbortController(); controller = request;
    const token = coordinator.beginCapture(newDictationAttemptId(), target);
    currentCapture = token;
    audioSubmitted = false;
    attemptId = token.attemptId;
    pinnedLanguage = language;
    pinnedTarget = current.mode === "work" ? target?.label ?? "Work" : "Conversation";
    const recorder = createVoiceCapture({ onstate: (state) => {
      if (alive && ticket === generation) captureState = state;
    } });
    capture = recorder;
    let submittedAudio = false;
    try {
      const recordingResult = await recorder.start();
      if (!alive || ticket !== generation || request.signal.aborted) return;
      if (!sameContext(token.draft, read())) { cancelCapture(); return; }
      if (!recordingResult) {
        error = captureState.error ?? "Recording cancelled. Your draft is preserved.";
        coordinator.cancel(); attemptId = null;
        return;
      }
      processing = true;
      const audio = await encodeBlobBase64(recordingResult.blob, request.signal);
      if (!alive || ticket !== generation || request.signal.aborted) return;
      if (!sameContext(token.draft, read())) { cancelCapture(); return; }
      submittedAudio = true;
      audioSubmitted = true;
      const result = await transcribeDictation({ attempt_id: token.attemptId, audio_base64: audio, language: pinnedLanguage }, request.signal);
      if (!alive || ticket !== generation || request.signal.aborted) return;
      if (result.status === "unknown") {
        coordinator.cancelAutosend(); recoveryToken = token;
        error = "Transcription outcome unknown. Check this attempt to recover its result; audio will not be resent.";
      } else coordinator.receive(token, result);
    } catch {
      if (alive && ticket === generation && !request.signal.aborted) {
        if (submittedAudio) { coordinator.cancelAutosend(); recoveryToken = token; }
        else { coordinator.cancel(); attemptId = null; }
        error = "Transcription could not be confirmed. No automatic retry or send.";
      }
    } finally {
      recorder.dispose();
      if (alive && ticket === generation) {
        capture = null; controller = null; processing = false;
        currentCapture = null; audioSubmitted = false;
      }
    }
  }

  $effect(() => {
    const latest = snapshot;
    untrack(() => notifyChanged(latest));
  });
  $effect(() => {
    if (view.deadline === null) return;
    const timer = setInterval(() => { now = Date.now(); }, 100);
    return () => clearInterval(timer);
  });
  onMount(() => {
    void discover();
    return () => {
      alive = false; generation += 1; discoveryGeneration += 1;
      controller?.abort(); recoveryController?.abort(); capture?.dispose(); coordinator.destroy();
    };
  });
</script>

<svelte:document onvisibilitychange={() => {
  if (document.visibilityState === "hidden") {
    if (recording || processing) cancelCapture();
    else coordinator.cancelAutosend();
  }
}} />

<section class="voice-input" aria-label="Voice input">
  <div class="voice-toolbar">
    <div class="voice-row">
      <button type="button" class="mic" aria-label="Record voice" aria-describedby={`${id}-status`}
        disabled={!available || recording || processing || recovering || snapshot.busy || snapshot.composing || (snapshot.mode === "work" && !target)}
        onclick={() => void start()}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" />
        </svg>
        <span class="voice-mic-label">Record voice</span>
      </button>
      {#if recording}<button type="button" onclick={() => void capture?.stop()} disabled={captureState.status !== "recording"}>Stop</button>{/if}
      {#if recording || processing}<button type="button" onclick={() => cancelCapture()}>{processing ? "Cancel transcription" : "Cancel recording"}</button>{/if}
    </div>
    <details class="voice-settings" bind:open={optionsOpen} ontoggle={(event) => { if (event.currentTarget.open) feedbackMounted = true; }}>
      <summary>Voice options</summary>
      <div class="voice-options" role="region" aria-label="Voice options controls">
        <label for={`${id}-language`}>Language</label>
        <select id={`${id}-language`} bind:value={language} disabled={recording || processing || !discovery?.languages?.length}>
          {#each discovery?.languages ?? [] as declared (declared)}<option value={declared}>{declared}</option>{/each}
        </select>
        <label class="check"><input type="checkbox" checked={view.autosend} onchange={(event) => coordinator.setAutosend(event.currentTarget.checked)} /> Automatically send after 2 seconds</label>
        <label class="check"><input type="checkbox" bind:checked={rememberCorrections} /> Remember corrections when sending</label>
        <p>Remembers the original transcript and sent draft privately. No automatic vocabulary changes or model training.</p>
        {#if pinnedTarget && attemptId}<p>{pinnedTarget} · {pinnedLanguage}</p>{/if}
        {#if view.originalText && attemptId}
          <label for={`${id}-original`}>Original transcript</label>
          <textarea id={`${id}-original`} rows="2" readonly value={view.originalText}></textarea>
          {#if view.adopted}<p>Edit the final text in the Bridge draft above.</p>{/if}
        {/if}
        {#if feedbackMounted}
          {@render feedback?.({ attemptId, originalText: attemptId ? view.originalText : "", finalText: attemptId ? (view.adopted ? snapshot.draftText : view.finalText) : "", language: pinnedLanguage || language, savedRevision, active: optionsOpen, applySuggestion })}
        {/if}
      </div>
    </details>
  </div>
  <div class="voice-status-row">
    <p class="voice-status" id={`${id}-status`} role="status">{status}</p>
    {#if !available && !discovering}<button type="button" onclick={() => void discover()}>Check voice again</button>{/if}
  </div>
  {#if view.deadline !== null}
    <div class="voice-row countdown"><p role="status">Sending in {seconds} seconds</p><button type="button" onclick={() => coordinator.cancelAutosend()}>Cancel automatic send</button></div>
  {/if}
  {#if error}<p role="alert">{error}</p>{/if}
  {#if view.reason && view.phase !== "capturing" && view.phase !== "cancelled" && view.deadline === null}<p role="status">{view.reason.replaceAll("_", " ")}</p>{/if}
  {#if correctionMessage}<p role="status">{correctionMessage}</p>{/if}
  {#if recoveryToken}<button type="button" disabled={recovering} onclick={() => void recoverAttempt()}>Check transcription outcome</button>{/if}
  {#if recoveryMessage}<p role="status">{recoveryMessage}</p>{/if}
  {#if recoveredText}
    <label for={`${id}-recovered`}>Recovered transcript from earlier context</label>
    <textarea id={`${id}-recovered`} rows="2" readonly value={recoveredText}></textarea>
  {/if}
  {#if view.originalText && attemptId && !view.adopted}
    <label for={`${id}-suggestion`}>Transcript suggestion</label>
    <textarea id={`${id}-suggestion`} rows="2" value={view.finalText} oninput={(event) => coordinator.setFinalText(event.currentTarget.value)}></textarea>
    <button type="button" disabled={snapshot.busy || snapshot.composing} onclick={() => coordinator.insert()}>Insert into draft</button>
  {/if}
</section>

<style>
  .voice-input { min-width: 0; margin: 0; color: var(--color-parchment); font: var(--text-sm)/1.5 var(--font-body); }
  .voice-toolbar { display: flex; align-items: flex-start; flex-wrap: wrap; gap: .15rem .5rem; min-width: 0; min-height: 2.75rem; padding-inline-end: var(--voice-action-reserve, 0px); }
  .voice-row { display: flex; align-items: center; flex-wrap: wrap; gap: .35rem .5rem; min-width: 0; }
  .voice-settings { flex: 1 1 auto; min-width: 0; }
  .voice-settings[open] { flex-basis: 100%; }
  .voice-mic-label { display: var(--voice-label-display, inline); }
  .voice-status-row { display: flex; align-items: center; flex-wrap: wrap; gap: .15rem .5rem; min-width: 0; margin-top: .2rem; }
  .voice-status { flex: 1 1 7rem; min-width: 0; margin: 0; color: var(--color-ash); }
  .voice-status-row button { flex: 0 0 auto; font-size: var(--text-xs); }
  p { margin: .4rem 0 0; overflow-wrap: anywhere; line-height: 1.6; }
  button, select { min-height: 2.75rem; padding: .4rem .65rem; color: var(--color-bone); border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); background: var(--color-obsidian); font: inherit; }
  button { cursor: pointer; }
  button:hover:not(:disabled) { border-color: var(--color-rune); background: var(--color-obsidian-2); }
  button:disabled { opacity: .55; cursor: default; }
  .mic { display: inline-flex; align-items: center; justify-content: center; gap: .5rem; min-width: 2.75rem; border-color: transparent; padding-inline: .35rem; background: transparent; }
  .mic svg { flex: 0 0 auto; }
  summary { min-height: 2.75rem; padding-block: .4rem; align-content: center; cursor: pointer; color: var(--color-parchment); }
  .voice-options { display: grid; box-sizing: border-box; width: calc(100% + var(--voice-action-reserve, 0px)); gap: .5rem; margin-top: .35rem; padding: .75rem 0 .25rem; max-height: min(22rem, 42dvh); overflow: auto; overscroll-behavior: contain; min-width: 0; scrollbar-gutter: stable; border-top: 1px solid var(--color-engraving); }
  label { display: block; line-height: 1.5; }
  .check { display: flex; gap: .6rem; align-items: flex-start; min-height: 2.75rem; padding-block: .5rem; }
  .check input { flex: 0 0 auto; margin-top: .15rem; }
  textarea { display: block; width: 100%; min-height: 3rem; max-height: 12rem; resize: vertical; color: var(--color-bone); background: var(--color-obsidian-2); border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); padding: .6rem; font: inherit; line-height: 1.6; }
  select { width: 100%; background: var(--color-obsidian-2); }
  .countdown { margin-top: .5rem; padding-left: .65rem; border-left: 2px solid var(--color-rune); }
  .countdown p { margin: 0; color: var(--color-bone); }
  button:focus-visible, select:focus-visible, input:focus-visible, textarea:focus-visible, summary:focus-visible, .voice-options:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
