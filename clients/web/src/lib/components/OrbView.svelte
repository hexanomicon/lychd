<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { onDestroy, tick } from "svelte";

  import { getOrbRun } from "$lib/api/client";
  import type { OrbRunSnapshot } from "$lib/api/models";
  import { loadedSubjects, subjectIdentity, attemptIdentity, conflictingStationAttempts } from "./orb-evidence";
  import { delegationStatusLabel } from "$lib/delegation/presentation";
  import DelegateMark from "./DelegateMark.svelte";
  import ArchiveRecallPanel from "./ArchiveRecallPanel.svelte";
  import AtlasLinks from "./AtlasLinks.svelte";
  import CreationSummary from "./CreationSummary.svelte";
  import BridgePreferenceSummary from "./BridgePreferenceSummary.svelte";
  import GraphCanvas from "./graph/GraphCanvas.svelte";
  import AnimatorRail from "./AnimatorRail.svelte";
  import { projectOrb, orbEvidenceNodeId, matchesOrbPattern, mergeOrbEvidence, mergeOrbGaps } from "$lib/graph/orb";
  import { listenToOrb, type OrbConnection } from "$lib/orb/live";
  import { bridgeConsentHref, bridgeRunHref, loomOriginHref, scavengerRunHref } from "$lib/navigation/instruments";

  type Evidence = OrbRunSnapshot["evidence"][number];
  type TimelineItem =
    | { type: "evidence"; seq: number; evidence: Evidence }
    | {
        type: "gap";
        seq: number;
        endSeq: number;
        classification: string;
      };

  let { runId }: { runId?: string } = $props();
  let history = $state.raw<OrbRunSnapshot | null>(null);
  let subjectFilter = $state("");
  let attemptFilter = $state("");
  let loading = $state(false);
  let loadingMore = $state(false);
  let error = $state("");
  let loadMoreError = $state("");
  let loadVersion = 0;
  let loadController: AbortController | undefined;
  let loadMoreController: AbortController | undefined;
  let activeRunId: string | undefined;
  let selectedInspector: HTMLElement | undefined;
  let selectionReturnFocus: HTMLElement | undefined;
  let livePage = $state.raw<OrbRunSnapshot | null>(null);
  let liveRecords = $state.raw<Evidence[]>([]);
  let liveGaps = $state.raw<OrbRunSnapshot["gaps"]>([]);
  let liveDropped = $state(0);
  let liveCursor = $state(-1);
  let connection = $state<OrbConnection>("closed");
  let feedNote = $state("");
  let following = $state(true);
  let playbackCursor = $state<number | null>(null);
  let playbackSnapshot = $state.raw<OrbRunSnapshot | null>(null);
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let graphSelection = $state<string | null>(null);
  let pinnedEvidence = $state.raw<Evidence | null>(null);
  let stopLive: (() => void) | undefined;
  let metadataVersion = 0;
  let resetRecoveryUsed = false;
  let snapshot = $derived.by((): OrbRunSnapshot | null => {
    if (!history) return null;
    const latest = livePage ?? history;
    return { ...history, ...latest,
      evidence: mergeOrbEvidence(history.evidence, liveRecords, pinnedEvidence ? [pinnedEvidence] : []),
      gaps: mergeOrbGaps(history.gaps, liveGaps),
      has_more: history.has_more || (liveDropped > 0 && latest.ledger_head_seq > (history.page_end_seq ?? -1)),
      page_end_seq: history.page_end_seq,
      next_after_seq: history.next_after_seq ?? history.page_end_seq
    };
  });
  let pattern = $derived(snapshot?.workflow && matchesOrbPattern(snapshot, snapshot.workflow) ? snapshot.workflow : null);
  let playbackSource = $derived(playbackSnapshot ?? snapshot);
  let graph = $derived(playbackSource ? projectOrb(playbackSource, pattern, playbackCursor) : null);
  let playbackIndex = $derived(playbackSource ? playbackSource.evidence.findLastIndex((record) => playbackCursor === null || record.seq <= playbackCursor) : -1);
  let playbackRecord = $derived(playbackIndex >= 0 ? playbackSource?.evidence[playbackIndex] : undefined);
  let evidenceHeading: HTMLElement | undefined;
  let consumedJobRequest: { runId: string; jobId: string | null } | undefined;
  let bridgeHref = $derived(snapshot ? bridgeRunHref(snapshot.run.bridge_path, snapshot.run.run_id) : null);
  let applicationHref = $derived(scavengerRunHref(snapshot?.run.application_path));
  let loomHref = $derived(snapshot?.pattern.loom_path ? loomOriginHref(snapshot.pattern.loom_path, snapshot.run.run_id, page.url.search) : null);
  let requestedEventId = $derived(page.url.searchParams.get("event"));
  let requestedJobId = $derived(page.url.searchParams.get("job"));
  let selectedEventId = $derived(requestedEventId);
  let selected = $derived(snapshot?.evidence.find((event) => event.event_id === selectedEventId) ?? null);
  let selectedConsentHref = $derived(snapshot && selected?.kind === "consent" && selected.consent_id
    ? bridgeConsentHref(snapshot.run.bridge_path, snapshot.run.run_id, selected.consent_id, selected.event_id)
    : null);
  let selectionNote = $derived(snapshot && selectedEventId && !selected
    ? snapshot.has_more
      ? "The linked event is outside this loaded page. Load more to continue the search."
      : "The linked event was not found in retained evidence at this read."
    : "");
  let loadedEvidence = $derived([...(snapshot?.evidence ?? [])].sort((left, right) => left.seq - right.seq));
  let subjects = $derived(loadedSubjects(loadedEvidence));
  let selectedSubject = $derived(subjects.find((subject) => subject.key === subjectFilter));
  let visibleEvidence = $derived(loadedEvidence.filter((event) =>
    (!subjectFilter || subjectIdentity(event) === subjectFilter) &&
    (!attemptFilter || attemptIdentity(event) === attemptFilter)
  ));
  let selectedIndex = $derived(loadedEvidence.findIndex((event) => event.event_id === selected?.event_id));
  let previousEvidence = $derived(selectedIndex > 0 ? loadedEvidence[selectedIndex - 1] : undefined);
  let nextEvidence = $derived(selectedIndex >= 0 ? loadedEvidence[selectedIndex + 1] : undefined);
  let conflictingAttempts = $derived(conflictingStationAttempts(loadedEvidence));
  let selectedGraphId = $derived(selected && (playbackCursor === null || selected.seq <= playbackCursor) ? orbEvidenceNodeId(selected, pattern) : graphSelection);
  let selectedGraphNode = $derived(graph?.nodes.find((node) => node.id === selectedGraphId));
  let linkedJobUnavailable = $derived(Boolean(
    snapshot && requestedJobId && !snapshot.delegated_jobs.some((job) => job.job_id === requestedJobId)
  ));

  function delegatedJobElementId(jobId: string): string {
    return `delegated-job-${jobId}`;
  }

  let timeline = $derived.by((): TimelineItem[] => {
    if (!snapshot) return [];
    const items: TimelineItem[] = visibleEvidence.map((evidence) => ({
      type: "evidence",
      seq: evidence.seq,
      evidence
    }));
    for (const gap of snapshot.gaps) {
      items.push({
        type: "gap",
        seq: gap.start_seq,
        endSeq: gap.end_seq,
        classification: gap.classification
      });
    }
    return items.sort((left, right) => left.seq - right.seq);
  });

  $effect(() => {
    if (runId) void load(runId);
    else {
      loadVersion++;
      stopLive?.();
      livePage = null; liveRecords = []; liveGaps = []; pinnedEvidence = null;
      loadController?.abort();
      loadMoreController?.abort();
      loadController = undefined;
      loadMoreController = undefined;
      activeRunId = undefined;
      history = null;
      playbackSnapshot = null; playbackCursor = null;
      loading = false;
      loadingMore = false;
      loadMoreError = "";
    }
  });

  onDestroy(() => {
    loadVersion++;
    stopLive?.();
    loadController?.abort();
    loadMoreController?.abort();
  });

  $effect(() => {
    const jobId = requestedJobId;
    const current = snapshot;
    if (!current || current.run.run_id !== runId) return;
    if (consumedJobRequest?.runId === runId && consumedJobRequest.jobId === jobId) return;
    // A later snapshot may resolve this hint, but only navigation requests focus.
    const request = { runId: current.run.run_id, jobId };
    consumedJobRequest = request;
    if (!jobId || !current.delegated_jobs.some((job) => job.job_id === jobId)) return;
    void tick().then(() => {
      const target = document.getElementById(delegatedJobElementId(jobId));
      if (!target || consumedJobRequest !== request || runId !== request.runId || snapshot?.run.run_id !== request.runId || requestedJobId !== jobId) return;
      target.scrollIntoView?.({ block: "nearest" });
      target.focus({ preventScroll: true });
    });
  });


  function retryRead() {
    if (loading || !error || snapshot) return;
    void load(runId, false, true);
  }

  async function load(id: string | undefined, recovering = false, preserveReadError = false) {
    const version = ++loadVersion;
    stopLive?.();
    stopLive = undefined;
    connection = "closed";
    if (!recovering) resetRecoveryUsed = false;
    const controller = new AbortController();
    loadController?.abort();
    loadMoreController?.abort();
    loadController = controller;
    loadMoreController = undefined;
    const identityChanged = activeRunId !== id;
    activeRunId = id;
    loading = true;
    loadingMore = false;
    if (!preserveReadError) error = "";
    loadMoreError = "";
    if (identityChanged) {
      history = null;
      playbackCursor = null;
      playbackSnapshot = null;
      selectionReturnFocus = undefined;
      consumedJobRequest = undefined;
      subjectFilter = "";
      attemptFilter = "";
    }
    if (!id) {
      history = null;
      loading = false;
      loadController = undefined;
      return;
    }
    try {
      const next = await getOrbRun(id, { limit: 100, signal: controller.signal });
      if (version !== loadVersion) return;
      if (next.run.run_id !== id) {
        throw new Error("The Orb returned evidence for another Run.");
      }
      history = next;
      playbackSnapshot = null; playbackCursor = null;
      livePage = null; liveRecords = []; liveGaps = []; liveDropped = 0; pinnedEvidence = null;
      graphSelection = null; feedNote = "";
      connectLive(next, version);
      error = "";
    } catch (cause) {
      if (version === loadVersion) {
        error = cause instanceof Error ? cause.message : "The evidence could not be read.";
      }
    } finally {
      if (loadController === controller) loadController = undefined;
      if (version === loadVersion) loading = false;
    }
  }

  async function loadMore() {
    const current = history;
    const afterSeq = snapshot?.next_after_seq;
    if (!runId || !current || !snapshot?.has_more || afterSeq == null || loadingMore) return;
    const version = loadVersion;
    const liveVersion = metadataVersion;
    const controller = new AbortController();
    loadMoreController = controller;
    loadingMore = true;
    loadMoreError = "";
    try {
      const next = await getOrbRun(runId, {
        afterSeq,
        limit: 100,
        signal: controller.signal
      });
      if (version !== loadVersion || history !== current) return;
      if (next.run.run_id !== runId || next.run.run_id !== current.run.run_id) {
        throw new Error("The Orb returned evidence for another Run.");
      }
      history = {
        ...next,
        evidence: mergeOrbEvidence(current.evidence, next.evidence),
        gaps: mergeOrbGaps(current.gaps, next.gaps)
      };
      if (liveVersion === metadataVersion) livePage = next;
    } catch (cause) {
      if (version === loadVersion) {
        loadMoreError = cause instanceof Error ? cause.message : "More evidence could not be read.";
      }
    } finally {
      if (loadMoreController === controller) loadMoreController = undefined;
      if (version === loadVersion) loadingMore = false;
    }
  }

  function captureSelectedInspector(node: HTMLElement) {
    selectedInspector = node;
    return () => {
      if (selectedInspector === node) selectedInspector = undefined;
    };
  }

  function captureEvidenceHeading(node: HTMLElement) {
    evidenceHeading = node;
    return () => {
      if (evidenceHeading === node) evidenceHeading = undefined;
    };
  }

  function browseSubject(value: string) {
    subjectFilter = value;
    attemptFilter = "";
  }

  async function stepEvidence(evidence: Evidence) {
    // Explicit stepping follows the Run account, including records outside a subject filter.
    if (!visibleEvidence.some((event) => event.event_id === evidence.event_id)) browseSubject("");
    await selectEvidence(evidence);
  }

  async function selectEvidence(evidence: Evidence, opener?: HTMLElement) {
    if (!runId) return;
    selectionReturnFocus = opener;
    following = false;
    pinnedEvidence = evidence;
    selectedEventId = evidence.event_id;
    const url = new URL(page.url);
    url.searchParams.set("event", evidence.event_id);
    const orbPath = `/orb/${encodeURIComponent(runId)}${url.search}` as `/orb/${string}`;
    await goto(resolve(orbPath), {
      replaceState: true,
      keepFocus: true,
      noScroll: true
    });
    await tick();
    if (snapshot?.run.run_id === runId && selected?.event_id === evidence.event_id) {
      selectedInspector?.focus();
    }
  }

  async function clearSelection() {
    if (!runId) return;
    const target = selectionReturnFocus ?? document.getElementById(`orb-event-${selectedEventId}`);
    selectedEventId = null;
    selectionReturnFocus = undefined;
    graphSelection = null;
    pinnedEvidence = null;
    const url = new URL(page.url);
    url.searchParams.delete("event");
    const orbPath = `/orb/${encodeURIComponent(runId)}${url.search}` as `/orb/${string}`;
    await goto(resolve(orbPath), {
      replaceState: true,
      keepFocus: true,
      noScroll: true
    });
    await tick();
    if (target?.isConnected) target.focus();
    else evidenceHeading?.focus();
  }

  function connectLive(initial: OrbRunSnapshot, version: number) {
    liveCursor = initial.ledger_head_seq;
    if (typeof EventSource === "undefined") return;
    stopLive = listenToOrb(initial.run.run_id, initial.ledger_head_seq, {
      onConnection: (state) => { if (version === loadVersion) connection = state; },
      onFault: (message) => { if (version === loadVersion) feedNote = message; },
      onReset: () => {
        if (version !== loadVersion) return;
        if (resetRecoveryUsed) { feedNote = "The feed reset again. Refresh explicitly to retry."; return; }
        resetRecoveryUsed = true;
        feedNote = "The retained boundary changed. Reading a fresh account.";
        void load(initial.run.run_id, true);
      },
      onFrame: (frame) => {
        if (version !== loadVersion) return;
        metadataVersion++;
        liveCursor = frame.cursor;
        livePage = frame.snapshot;
        const records = mergeOrbEvidence(liveRecords, frame.snapshot.evidence);
        liveDropped += Math.max(0, records.length - 100);
        liveRecords = records.slice(-100);
        liveGaps = mergeOrbGaps(liveGaps, frame.snapshot.gaps).slice(-100);
        const last = frame.snapshot.evidence.at(-1);
        if (last && following && playbackCursor === null) { focusId = orbEvidenceNodeId(last, pattern); focusRevision++; }
      }
    });
  }

  async function selectGraphNode(id: string, opener?: HTMLElement) {
    graphSelection = id;
    following = false;
    const record = playbackSource?.evidence.filter((item) => (playbackCursor === null || item.seq <= playbackCursor) && orbEvidenceNodeId(item, pattern) === id).at(-1);
    if (record && opener) await selectEvidence(record, opener);
    else {
      const url = new URL(page.url);
      url.searchParams.delete("event");
      await goto(`/orb/${encodeURIComponent(runId!)}${url.search}` as `/orb/${string}`, { replaceState: true, keepFocus: true, noScroll: true });
    }
  }

  function toggleFollowing() {
    following = !following;
    if (following) {
      seek(null);
    }
  }

  function seek(seq: number | null) {
    if (seq !== null && playbackSnapshot === null) playbackSnapshot = snapshot;
    if (seq === null) playbackSnapshot = null;
    playbackCursor = seq;
    following = seq === null;
    graphSelection = null;
    const record = seq === null ? snapshot?.evidence.at(-1) : playbackSnapshot?.evidence.find((item) => item.seq === seq);
    if (record) { focusId = orbEvidenceNodeId(record, pattern); focusRevision++; }
  }
  function stepPlayback(delta: number) {
    const record = playbackSource?.evidence[playbackIndex + delta];
    if (record) seek(record.seq);
  }
</script>

<svelte:head><title>Orb — LychD</title></svelte:head>
{#if !runId}
  <section class="orb-empty" aria-labelledby="orb-empty-title">
    <span class="glyph-big">◉</span>
    <h1 id="orb-empty-title" class="rune-head">Orb</h1>
    <p>Look into the Orb from a Bridge run to scry its retained structural evidence.</p>
    <a class="rune-btn" href={resolve("/bridge")}>Open Bridge</a>
  </section>
{:else}
  <div class="instrument-deck instrument-deck--orb">
    <section class="orb-main" aria-label="Selected run evidence">
      {#if error && !snapshot}
        <div class="turn__fault" role="alert">{error}</div>
        <button class="rune-btn" type="button" disabled={loading} aria-busy={loading} onclick={retryRead}>
          {loading ? "Reading…" : "Retry read"}
        </button>
      {:else if loading && !snapshot}
        <div class="mist"></div><div class="mist"></div>
      {:else if snapshot}
        {#if error}<div class="turn__fault" role="alert">{error}</div>{/if}
        <header class="run-identity">
          <div>
            <span class="eyebrow">Selected Run · workflow and evidence</span>
            <h1>Orb</h1>
            <p class="run-id"><span>Run</span> {snapshot.run.run_id}</p>
            <nav class="context-links" aria-label="Related instruments">
              <a href={resolve("/orb")}>All Runs</a>
              {#if applicationHref}<a href={applicationHref}>Scavenger market</a>
              {:else if bridgeHref}<a href={resolve(bridgeHref)}>Bridge</a>{:else}<span>Bridge context unavailable</span>{/if}
              <span>{snapshot.pattern.pattern_id}@{snapshot.pattern.revision}</span>
              {#if loomHref}
                <a href={resolve(loomHref)}>Exact Pattern →</a>
              {:else}
                <span class="context-unavailable">
                  Exact Pattern unavailable — the pinned manifest could not be validated against
                  the current registry.
                </span>
              {/if}
            </nav>
          </div>
          <div class="run-outcome">
            <span class="eyebrow">Latest fetched Run status</span>
            <span class="chip run-status" data-state={snapshot.run.status}>{snapshot.run.status.replaceAll("_", " ")}</span>
            <span class="capture-label">Capture · {snapshot.capture.replaceAll("_", " ")}</span>
          </div>
        </header>

        {#if linkedJobUnavailable}
          <p class="context-unavailable" role="status">
            The linked delegated job is not present in this Run's bounded snapshot.
            Its relationship to this Run could not be verified.
          </p>
        {/if}

        {#if snapshot.run.error_present}
          <div class="evidence-failure" role="status">
            A failure record exists. Its private diagnostic detail is not exposed in this projection.
          </div>
        {/if}

        <section class="coverage-strip" aria-labelledby="coverage-title">
          <h2 id="coverage-title" class="visually-hidden">Evidence coverage</h2>
          <div><span>snapshot · local time</span><strong><time datetime={snapshot.snapshot_at}>{new Date(snapshot.snapshot_at).toLocaleString()}</time></strong></div>
          <div><span>retained through</span><strong>#{snapshot.ledger_head_seq}</strong></div>
          <div><span>history page through</span><strong>{snapshot.page_end_seq == null ? "none" : `#${snapshot.page_end_seq}`}</strong></div>
          <div><span>live updates</span><strong>{snapshot.live_tail.replaceAll("_", " ")}</strong></div>
          <button class="text-action" type="button" disabled={loading} onclick={() => void load(runId)}>{loading ? "Refreshing…" : "Refresh"}</button>
        </section>

        <CreationSummary summary={snapshot.creation?.run_id === snapshot.run.run_id ? snapshot.creation : null} />

        <section class="orb-graph-panel" aria-labelledby="orb-graph-title">
          <header class="graph-heading">
            <div><h2 id="orb-graph-title">Workflow field</h2><p>{pattern ? "Edges: declared permissions · badges: loaded records" : "Exact workflow unavailable · supplied subject groups only"}</p></div>
            <button type="button" class="text-action" aria-pressed={following} onclick={toggleFollowing}>{following ? "Pause following" : "Follow latest"}</button>
          </header>
          <div class="live-connection" role="status">Live feed: <strong>{connection}</strong> · retained cursor {liveCursor < 0 ? "none" : `#${liveCursor}`} · connection is not Run status</div>
          {#if feedNote}<p class="feed-note" role="status">{feedNote}</p>{/if}
          <div class="graph-and-animators">
            <div class="selected-spatial-field">{#if graph}<GraphCanvas projection={graph} selectedId={selectedGraphId} onselect={selectGraphNode} label="Selected Run workflow graph" presentation="orb" hideMinimap={true} {focusId} {focusRevision} onviewportinteraction={() => following = false} />{/if}</div>
            <AnimatorRail evidence={playbackSource?.evidence ?? []} cursor={playbackCursor} onselect={seek} />
          </div>
          <div class="playback-controls" role="group" aria-label="Recorded graph playback">
            <button type="button" class="text-action" disabled={playbackIndex <= 0} onclick={() => stepPlayback(-1)}>Previous record</button>
            <label>Record cursor
              <input type="range" min="0" max={Math.max(0,((playbackSource?.evidence.length ?? 0) - 1))} value={Math.max(0,playbackIndex)}
                disabled={!playbackSource?.evidence.length} aria-valuetext={playbackRecord ? `Record #${playbackRecord.seq}` : "No loaded records"}
                oninput={(event) => { const record = playbackSource?.evidence[Number(event.currentTarget.value)]; if (record) seek(record.seq); }} />
            </label>
            <button type="button" class="text-action" disabled={playbackIndex >= (playbackSource?.evidence.length ?? 0) - 1} onclick={() => stepPlayback(1)}>Next record</button>
            <button type="button" class="text-action" aria-pressed={playbackCursor === null} onclick={() => seek(null)}>LIVE</button>
            <span class="playback-position">{playbackCursor === null ? "Latest loaded evidence" : `Recorded view through #${playbackCursor}`} · {playbackRecord ? new Date(playbackRecord.occurred_at).toLocaleString() : "No loaded record"}</span>
          </div>
          {#if selectedGraphNode && !selected}<p class="graph-selection-note"><strong>{selectedGraphNode.label}</strong> — {selectedGraphNode.detail}. No loaded record is selected.</p>{/if}
          <p class="graph-boundary">Glow marks the latest supplied record or playback cursor, not continuous work. The cursor filters loaded graph observations; Run status above remains current. Record spacing is sequence, not elapsed time. Subworkflow structure requires supplied identities.</p>
          {#if liveDropped}<p class="feed-note">The live window keeps the latest 100 records; {liveDropped} earlier live records left that window. Load retained evidence to inspect older records.</p>{/if}
        </section>

        <section class="coverage-limits" aria-labelledby="limits-title">
          <h2 id="limits-title">Evidence limits</h2>
          <p>This is a bounded snapshot. Sequence gaps and known omissions qualify the records below.</p>
          {#if snapshot.known_omissions.length}
            <ul class="limits-list">
              {#each snapshot.known_omissions as omission (omission)}<li>{omission}</li>{/each}
            </ul>
          {:else}
            <p>No additional omissions are reported by this snapshot.</p>
          {/if}
        </section>

        <section class="loaded-browsing panel" aria-labelledby="loaded-browsing-title">
          <h2 id="loaded-browsing-title" class="rune-head">Browse loaded evidence</h2>
          <p class="inspector-copy">Subjects and station attempts contain only records loaded here.</p>
          <label for="orb-subject">Recorded subject</label>
          <select id="orb-subject" bind:value={() => subjectFilter, browseSubject}>
            <option value="">All loaded evidence · {loadedEvidence.length} loaded records</option>
            {#if subjectFilter && !selectedSubject}
              <option value={subjectFilter}>Previously selected subject · 0 loaded records</option>
            {/if}
            {#each subjects as subject (subject.key)}
              <option value={subject.key}>{subject.label} · {subject.records.length} loaded records</option>
            {/each}
          </select>
          {#if selectedSubject?.kind === "node"}
            <label for="orb-attempt">Station attempt</label>
            <select id="orb-attempt" bind:value={attemptFilter}>
              <option value="">All loaded station attempts</option>
              {#if attemptFilter && !selectedSubject.attempts.some((attempt) => attempt.key === attemptFilter)}
                <option value={attemptFilter}>Previously selected station attempt · 0 loaded records</option>
              {/if}
              {#each selectedSubject.attempts as attempt (attempt.key)}
                <option value={attempt.key}>{attempt.label} · {attempt.count} loaded records</option>
              {/each}
            </select>
          {/if}
          {#if conflictingAttempts.length}
            <p class="context-unavailable">
              Station attempt IDs appear under multiple station subjects in loaded evidence:
              {conflictingAttempts.join(", ")}. Those subjects remain separate.
            </p>
          {/if}
        </section>

        <section class="evidence-panel panel" aria-labelledby="evidence-title">
          <div class="panel-head">
            <h2 id="evidence-title" class="rune-head" tabindex="-1" {@attach captureEvidenceHeading}>Ordered evidence</h2>
            <span>
              {snapshot.evidence.length} loaded records
              {snapshot.has_more ? " · more retained" : ""}
            </span>
          </div>
          <p id="evidence-order-note" class="evidence-order-note">Sequence is order, not elapsed time or causality. Timestamps use local time.</p>
          {#if subjectFilter}
            <p class="inspector-copy" role="status">
              Showing {visibleEvidence.length} of {loadedEvidence.length} loaded records.
              Other subjects or attempts are filtered out; sequence jumps alone are not evidence gaps.
            </p>
            <button class="text-action" type="button" onclick={() => browseSubject("")}>Show all loaded evidence</button>
          {/if}
          <ol class="evidence-list" aria-describedby="evidence-order-note">
            {#each timeline as item (item.type === "evidence" ? item.evidence.event_id : `gap-${item.seq}-${item.endSeq}`)}
              {#if item.type === "gap"}
                <li class="evidence-gap">
                  <span class="evidence-seq">#{item.seq}–{item.endSeq}</span>
                  <div><strong>Unknown or omitted interval</strong><p>The reason for this gap is not supplied.</p></div>
                </li>
              {:else}
                <li>
                  <button
                    id={`orb-event-${item.evidence.event_id}`}
                    aria-current={selected?.event_id === item.evidence.event_id ? "true" : undefined}
                    class:current={selected?.event_id === item.evidence.event_id}
                    class="evidence-row"
                    type="button"
                    onclick={(event) => void selectEvidence(item.evidence, event.currentTarget)}
                  >
                    <span class="evidence-seq">
                      #{item.evidence.seq}
                      {#if selected?.event_id === item.evidence.event_id}<span class="selection-marker">Selected</span>{/if}
                    </span>
                    <span
                      class="evidence-kind"
                      data-kind={item.evidence.kind}
                      data-phase={item.evidence.phase}
                    >{item.evidence.kind}</span>
                    <span class="evidence-description">
                      <span class="evidence-summary">{item.evidence.summary}</span>
                      <span class="evidence-subject">Subject · {item.evidence.subject_key ?? "unknown"}</span>
                    </span>
                    <time datetime={item.evidence.occurred_at}>
                      {new Date(item.evidence.occurred_at).toLocaleString()}
                    </time>
                  </button>
                </li>
              {/if}
            {:else}
              <li class="evidence-empty">No evidence records or sequence gaps are supplied in this snapshot.</li>
            {/each}
          </ol>
          {#if snapshot.has_more}
            <div class="evidence-more">
              {#if loadMoreError}
                <div id="orb-load-more-error" class="turn__fault" role="alert">{loadMoreError}</div>
              {/if}
              <button
                class="rune-btn"
                disabled={loadingMore}
                type="button"
                onclick={loadMore}
                aria-describedby={loadMoreError ? "orb-load-more-error" : undefined}
              >
                {loadingMore
                  ? "Reading…"
                  : loadMoreError
                    ? "Retry loading retained evidence"
                    : "Load more retained evidence"}
              </button>
            </div>
          {/if}
        </section>

        <AtlasLinks kind="run" targetId={snapshot.run.run_id} />
      {/if}
    </section>

    <aside class="orb-inspector">
      {#key runId}
        <ArchiveRecallPanel {runId} />
      {/key}
      {#if selectionNote}
        <section class="panel selection-note" role="status">
          <p class="inspector-copy">{selectionNote}</p>
        </section>
      {/if}
      {#if selected}
        <section
          class="panel selected-evidence"
          {@attach captureSelectedInspector}
          aria-labelledby="selected-event-title"
          tabindex="-1"
        >
          <div class="panel-head">
            <h2 id="selected-event-title" class="rune-head">Selected event</h2>
            <p class="inspector-copy">Selected historical evidence</p>
            <button class="sheet-dismiss" type="button" onclick={clearSelection}>Close</button>
          </div>
          <nav class="record-navigation" aria-label="Loaded record navigation">
            <button class="text-action" type="button" disabled={!previousEvidence} onclick={() => previousEvidence && stepEvidence(previousEvidence)}>Previous loaded record</button>
            <button class="text-action" type="button" disabled={!nextEvidence} onclick={() => nextEvidence && stepEvidence(nextEvidence)}>Next loaded record</button>
          </nav>
          <p class="inspector-copy">Run sequence across all loaded records.
            {#if !previousEvidence}Start of loaded evidence. {/if}
            {#if !nextEvidence}End of loaded evidence{snapshot?.has_more ? "; load more retained evidence to continue" : " at this read"}.{/if}
          </p>
          {#if !visibleEvidence.some((event) => event.event_id === selected?.event_id)}
            <p class="inspector-copy">The selected record is outside the current subject or attempt filter.</p>
          {/if}
          <p class="selected-evidence-summary">{selected.summary}</p>
          <dl class="kv">
            <dt>event</dt><dd class="glyph">{selected.event_id}</dd>
            <dt>sequence</dt><dd>#{selected.seq}</dd>
            <dt>recorded at</dt><dd><time datetime={selected.occurred_at}>{new Date(selected.occurred_at).toLocaleString()}</time> (local)</dd>
            <dt>kind</dt><dd>{selected.kind}</dd>
            <dt>{selected.kind === "node" ? "station" : selected.kind === "dispatch" ? "capability" : "subject"}</dt><dd>{selected.subject_key ?? "No recorded subject"}</dd>
            <dt>recorded at</dt><dd><time datetime={selected.occurred_at}>{new Date(selected.occurred_at).toLocaleString()}</time></dd>
            <dt>phase</dt><dd>{selected.phase ?? "—"}</dd>
            <dt>station attempt (occurrence_id)</dt><dd class="glyph">{selected.occurrence_id ?? "No recorded attempt"}</dd>
            <dt>capture</dt><dd>{selected.capture.replaceAll("_", " ")}</dd>
          </dl>
          {#if selectedConsentHref}
            <a class="inspector-link" href={resolve(selectedConsentHref)}>Open exact consent in Bridge →</a>
            <p class="inspector-copy">Historical reference; current availability is checked in Bridge.</p>
          {/if}
          {#if selected.nexus_path}
            <a
              class="inspector-link"
              href={resolve(
                `${selected.nexus_path}&event=${encodeURIComponent(selected.event_id)}` as `/nexus?${string}`
              )}
            >
              Open transition in Nexus →
            </a>
          {/if}
        </section>
      {:else if snapshot && !selectionNote}
        <section class="panel inspector-empty">
          <h2 class="rune-head">Inspect a record</h2>
          <p>Select an evidence row to read its exact identity, recorded fields, and available counterpart links.</p>
        </section>
      {/if}
      <BridgePreferenceSummary summary={snapshot?.bridge_preference} />
    </aside>

    {#if snapshot?.delegated_jobs.length}
      <details class="delegated-jobs panel" open={Boolean(requestedJobId && !linkedJobUnavailable)}>
        <summary>
          <span class="rune-head">Delegated jobs</span>
          <span>{snapshot.delegated_jobs.length} in this bounded snapshot</span>
        </summary>
        <p class="job-sequence-note">Job lifecycle sequences belong to each AgentJob; they are separate from the Run sequence.</p>
        <ol class="delegated-job-list">
          {#each snapshot.delegated_jobs as job (job.job_id)}
            <li
              id={delegatedJobElementId(job.job_id)}
              class={["delegated-job", { current: requestedJobId === job.job_id }]}
              data-state={job.status}
              aria-current={requestedJobId === job.job_id ? "true" : undefined}
              tabindex="-1"
            >
              <header>
                <span class="delegated-job__title"><DelegateMark /> AgentJob {job.job_id}</span>
                <span class="chip" data-state={job.status}>{delegationStatusLabel(job.status)}</span>
              </header>
              <dl class="kv">
                <dt>runtime</dt><dd>{job.runtime}</dd>
                <dt>coffin</dt><dd>{job.profile}</dd>
                <dt>station</dt><dd>{job.step_id}</dd>
                <dt>result</dt>
                <dd>
                  {job.output_present ? "bounded output retained" : "no textual output"}
                  · {job.artifact_count} artifact reference{job.artifact_count === 1 ? "" : "s"}
                  {job.error_present ? " · private error retained" : ""}
                </dd>
              </dl>
              <ol class="delegated-event-list" aria-label="AgentJob lifecycle">
                {#each job.events as event (event.event_id)}
                  <li>
                    <span>#{event.seq}</span>
                    <strong>{delegationStatusLabel(event.status)}</strong>
                    <time datetime={event.occurred_at}>{new Date(event.occurred_at).toLocaleTimeString()}</time>
                  </li>
                {/each}
              </ol>
              {#if job.events_truncated}
                <p class="inspector-copy">Older lifecycle events are outside this bounded snapshot.</p>
              {/if}
            </li>
          {/each}
        </ol>
      </details>
    {/if}

  </div>
{/if}

<style>
  .graph-and-animators { display:grid; grid-template-columns:minmax(0,1fr) minmax(12rem,15rem); gap:1rem; align-items:start; }
  .selected-spatial-field { height:clamp(340px,55vh,650px); min-width:0; background:#000; }
  .playback-controls { display:flex; align-items:center; flex-wrap:wrap; gap:.75rem; padding:.8rem 1rem; border-top:1px solid var(--color-engraving); background:var(--color-void); }
  .playback-controls label { display:flex; align-items:center; gap:.5rem; font-size:var(--text-sm); }
  .playback-controls input { accent-color:var(--color-rune); min-width:10rem; }
  .playback-controls input:focus-visible { outline:2px solid var(--color-rune); outline-offset:3px; }
  .playback-position { font-size:var(--text-xs); color:var(--color-parchment); }
  @media(max-width:70rem) { .graph-and-animators { grid-template-columns:minmax(0,1fr); } }
  .orb-graph-panel { min-width: 0; border: 1px solid var(--color-engraving); border-radius: var(--radius-panel); overflow: hidden; background: var(--color-obsidian); }
  .graph-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1rem; }
  .graph-heading h2 { font: 500 1.2rem/1.3 var(--font-body); color: var(--color-bone); }
  .graph-heading p, .live-connection, .feed-note, .graph-boundary, .graph-selection-note { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .live-connection, .feed-note, .graph-boundary, .graph-selection-note { padding: .5rem 1rem; }
  .live-connection strong { color: var(--color-bone); }
  .graph-heading button { flex-shrink: 0; min-height: 2.75rem; padding: .4rem .75rem; border: 1px solid var(--color-engraving); border-radius: var(--radius-rune); }
  .graph-boundary { border-top: 1px solid var(--color-engraving); }
  @media (max-width: 48rem) { .graph-heading { align-items: flex-start; flex-direction: column; } }

  .instrument-deck--orb {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem);
    align-content: start;
    align-items: start;
    gap: 1.4rem;
    background: var(--color-void);
  }

  .orb-main { gap: 1.2rem; }
  .orb-inspector { width: auto; min-width: 0; display: flex; flex-direction: column; gap: 1rem; position: sticky; top: 4.5rem; }
  .panel { background: var(--color-obsidian); box-shadow: none; }
  .panel-head { flex-wrap: wrap; padding: 1rem; }
  .panel-head::before { content: none; }
  .rune-head { font-variant: normal; letter-spacing: 0; }
  .panel-head .rune-head { font-size: var(--text-lg); }
  .run-identity { gap: 1.25rem; }
  .run-identity > div { min-width: 0; }
  .run-identity h1 { font: 600 clamp(1.6rem, 2.2vw, 2rem)/1.2 var(--font-body); }
  .eyebrow { color: var(--color-parchment); letter-spacing: 0.08em; }
  .run-id { margin: 0.65rem 0 0; color: var(--color-bone); font: var(--text-sm)/1.6 var(--font-glyph); overflow-wrap: anywhere; }
  .run-id > span { color: var(--color-parchment); }
  .run-outcome { flex-shrink: 0; gap: 0.5rem; }
  .run-outcome .run-status { font-size: var(--text-sm); }
  .chip { max-width: 100%; white-space: normal; overflow-wrap: anywhere; }
  .chip, .chip::before { animation: none; box-shadow: none; }
  .capture-label { color: var(--color-parchment); font-size: var(--text-sm); }
  .context-links { flex-wrap: wrap; align-items: baseline; gap: 0.45rem 1rem; margin-top: 0.8rem; }
  .context-links a, .context-links span { font-size: var(--text-sm); overflow-wrap: anywhere; }
  .context-links span { color: var(--color-parchment); }
  .context-links a { padding-block: 0.35rem; text-underline-offset: 0.25em; }
  .context-links a:hover { text-decoration: underline; }

  .coverage-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .coverage-strip > div { min-width: 0; padding: 0.8rem; }
  .coverage-strip span { color: var(--color-parchment); font-size: var(--text-sm); letter-spacing: 0; text-transform: none; }
  .coverage-strip strong { margin-top: 0.35rem; font: 500 var(--text-sm)/1.5 var(--font-body); overflow-wrap: anywhere; }
  .coverage-strip .text-action { grid-column: 1 / -1; min-height: 2.5rem; font-size: var(--text-sm); }
  .coverage-limits { padding: 0 0.1rem; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.6; }
  .coverage-limits h2 { color: var(--color-bone); font: 600 var(--text-sm)/1.5 var(--font-body); }
  .coverage-limits p { margin-top: 0.3rem; }
  .limits-list { padding: 0.4rem 0 0 1.2rem; color: var(--color-parchment); font-size: var(--text-sm); }
  .limits-list li + li { margin-top: 0.3rem; }

  .evidence-panel .panel-head > span { color: var(--color-parchment); font-size: var(--text-sm); }
  .evidence-order-note { padding: 0.8rem 1rem; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; border-bottom: 1px solid var(--color-engraving); }
  .evidence-list { max-height: none; overflow: visible; }
  .evidence-row { grid-template-columns: 3rem 5.5rem minmax(0, 1fr) 9rem; gap: 0.75rem; padding: 1rem; }
  .evidence-row > * { min-width: 0; overflow-wrap: anywhere; }
  .evidence-row.current { background: color-mix(in srgb, var(--color-rune) 8%, var(--color-obsidian)); }
  .evidence-row:focus-visible { outline-offset: -3px; }
  .evidence-seq, .evidence-kind { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .selection-marker { display: block; margin-top: 0.4rem; color: var(--color-rune); font: var(--text-xs)/1.5 var(--font-body); }
  .evidence-description { display: grid; gap: 0.35rem; }
  .evidence-summary { color: var(--color-bone); font-size: var(--text-base); line-height: 1.5; }
  .evidence-subject { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .evidence-row time { color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .evidence-gap { grid-template-columns: 3rem minmax(0, 1fr); gap: 0.75rem; padding: 0.9rem 1rem; border-inline: 0; }
  .evidence-gap strong { color: var(--color-bone); font: 500 var(--text-sm)/1.5 var(--font-body); }
  .evidence-gap p { margin-top: 0.25rem; color: var(--color-parchment); font-size: var(--text-sm); }
  .evidence-empty { padding: 1.2rem 1rem; color: var(--color-parchment); font-size: var(--text-base); }
  .evidence-more { padding: 1rem; }
  .evidence-more .rune-btn { max-width: 100%; white-space: normal; }

  .selected-evidence { min-width: 0; }
  .selected-evidence-summary { padding-top: 1rem; font-size: var(--text-base); }
  .selected-evidence .kv { grid-template-columns: 5.25rem minmax(0, 1fr); padding-block: 1rem; gap: 0.75rem; font-size: var(--text-sm); }
  .selected-evidence .kv dt { color: var(--color-parchment); }
  .selected-evidence .kv dd { min-width: 0; }
  .selected-evidence .glyph { color: var(--color-bone); font-size: var(--text-sm); }
  .sheet-dismiss { min-height: 2rem; font-size: var(--text-sm); }
  .inspector-link { font-size: var(--text-sm); line-height: 1.5; }
  .inspector-empty { padding: 1.1rem; }
  .inspector-empty h2 { font-size: var(--text-lg); }
  .inspector-empty p, .selection-note .inspector-copy { margin-top: 0.6rem; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.6; }

  .delegated-jobs { grid-column: 1 / -1; min-width: 0; }
  .delegated-jobs > summary { padding: 1rem; color: var(--color-bone); cursor: pointer; }
  .delegated-jobs > summary .rune-head { font-size: var(--text-lg); }
  .delegated-jobs > summary > span + span { margin-left: 0.75rem; color: var(--color-parchment); font-size: var(--text-sm); }
  .job-sequence-note { padding: 0 1rem 1rem; color: var(--color-parchment); font-size: var(--text-sm); line-height: 1.5; }
  .delegated-job { min-width: 0; box-shadow: none; }
  .delegated-job.current { box-shadow: inset 2px 0 var(--color-rune); }
  .delegated-job > header { flex-wrap: wrap; }
  .delegated-job__title { min-width: 0; overflow-wrap: anywhere; }
  .delegated-job .kv { grid-template-columns: 5rem minmax(0, 1fr); }
  .delegated-event-list { font-size: var(--text-sm); }

  @media (max-width: 75rem) {
    .evidence-row { grid-template-columns: 2.5rem 4.5rem minmax(0, 1fr); }
    .evidence-row time { grid-column: 3; }
    .run-identity { flex-direction: column; }
    .run-outcome { align-items: flex-start; }
  }

  @media (max-width: 68rem) {
    .instrument-deck--orb { grid-template-columns: minmax(0, 1fr); }
    .orb-inspector { position: static; }
    .evidence-row { grid-template-columns: 3rem 5.5rem minmax(0, 1fr) 9rem; }
    .evidence-row time { grid-column: auto; }
  }

  @media (max-width: 48rem) {
    .instrument-deck--orb { display: grid; gap: 1rem; }
    .coverage-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .evidence-panel .panel-head > span { margin-left: 0; }
    .evidence-row { grid-template-columns: 2.5rem minmax(0, 1fr); gap: 0.4rem 0.7rem; }
    .evidence-description, .evidence-row time { grid-column: 2; }
    .evidence-gap { grid-template-columns: minmax(0, 1fr); }
    .selected-evidence { max-height: min(70dvh, 36rem); box-shadow: 0 -0.5rem 2rem color-mix(in srgb, var(--color-void) 85%, transparent); }
    .delegated-jobs > summary > span + span { display: block; margin: 0.35rem 0 0; }
  }

  @media (prefers-reduced-motion: reduce) {
    .evidence-row, .chip, .chip::before { transition: none; animation: none; }
  }
</style>
