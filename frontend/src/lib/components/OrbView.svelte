<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { tick } from "svelte";

  import { getOrbRun } from "$lib/api/client";
  import type { OrbRunSnapshot } from "$lib/api/models";

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
  let snapshot = $state.raw<OrbRunSnapshot | null>(null);
  let selected = $state.raw<Evidence | null>(null);
  let loading = $state(false);
  let loadingMore = $state(false);
  let error = $state("");
  let selectionNote = $state("");
  let loadVersion = 0;
  let selectedInspector = $state<HTMLElement>();
  let requestedEventId = $derived(page.url.searchParams.get("event"));

  let timeline = $derived.by((): TimelineItem[] => {
    if (!snapshot) return [];
    const items: TimelineItem[] = snapshot.evidence.map((evidence) => ({
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
      snapshot = null;
      selected = null;
      loading = false;
    }
  });

  $effect(() => {
    const requested = requestedEventId;
    const current = snapshot;
    if (!current) return;
    if (!requested) {
      selected = null;
      selectionNote = "";
      return;
    }
    const found = current.evidence.find((event) => event.event_id === requested);
    selected = found ?? null;
    selectionNote = found
      ? ""
      : current.has_more
        ? "The linked event is outside this loaded page. Load more to continue the search."
        : "The linked event is no longer present in the retained evidence.";
  });

  async function load(id: string) {
    const version = ++loadVersion;
    loading = true;
    error = "";
    snapshot = null;
    try {
      const next = await getOrbRun(id, { limit: 100 });
      if (version !== loadVersion) return;
      snapshot = next;
    } catch (cause) {
      if (version === loadVersion) {
        error = cause instanceof Error ? cause.message : "The evidence could not be read.";
      }
    } finally {
      if (version === loadVersion) loading = false;
    }
  }

  async function loadMore() {
    const current = snapshot;
    const afterSeq = current?.next_after_seq;
    if (!runId || !current?.has_more || afterSeq == null || loadingMore) return;
    const version = loadVersion;
    loadingMore = true;
    try {
      const next = await getOrbRun(runId, { afterSeq, limit: 100 });
      if (version !== loadVersion || snapshot !== current) return;
      snapshot = {
        ...next,
        evidence: [...current.evidence, ...next.evidence],
        gaps: [...current.gaps, ...next.gaps]
      };
    } catch (cause) {
      if (version === loadVersion) {
        error = cause instanceof Error ? cause.message : "More evidence could not be read.";
      }
    } finally {
      if (version === loadVersion) loadingMore = false;
    }
  }

  async function selectEvidence(evidence: Evidence) {
    selected = evidence;
    selectionNote = "";
    const url = new URL(page.url);
    url.searchParams.set("event", evidence.event_id);
    await goto(`${url.pathname}${url.search}`, {
      replaceState: true,
      keepFocus: true,
      noScroll: true
    });
    if (window.matchMedia("(max-width: 760px)").matches) {
      await tick();
      selectedInspector?.focus();
    }
  }

  async function clearSelection() {
    const url = new URL(page.url);
    url.searchParams.delete("event");
    await goto(`${url.pathname}${url.search}`, {
      replaceState: true,
      keepFocus: true,
      noScroll: true
    });
  }
</script>

<svelte:head><title>Orb — LychD</title></svelte:head>
{#if !runId}
  <section class="orb-empty" aria-labelledby="orb-empty-title">
    <span class="glyph-big">◉</span>
    <h1 id="orb-empty-title" class="rune-head">Orb</h1>
    <p>Look into the Orb from a Bridge run to scry its retained structural evidence.</p>
    <a class="rune-btn" href="/bridge">Open Bridge</a>
  </section>
{:else}
  <div class="instrument-deck instrument-deck--orb">
    <section class="orb-main" aria-label="Selected run evidence">
      {#if loading}
        <div class="mist"></div><div class="mist"></div>
      {:else if error}
        <div class="turn__fault" role="alert">{error}</div>
      {:else if snapshot}
        <header class="run-identity">
          <div>
            <span class="eyebrow">Selected Run</span>
            <h1>Run {snapshot.run.run_id}</h1>
            <nav class="context-links" aria-label="Related instruments">
              <a href={snapshot.run.bridge_path}>Bridge</a>
              <span>{snapshot.pattern.pattern_id}@{snapshot.pattern.revision}</span>
              {#if snapshot.pattern.loom_path}
                <a href={snapshot.pattern.loom_path}>Exact Pattern →</a>
              {:else}
                <span class="context-unavailable">
                  Exact Pattern unavailable — the pinned manifest could not be validated against
                  the current registry.
                </span>
              {/if}
            </nav>
          </div>
          <div class="run-outcome">
            <span class="chip" data-state={snapshot.run.status}>{snapshot.run.status}</span>
            <span>{snapshot.capture.replaceAll("_", " ")}</span>
          </div>
        </header>

        {#if snapshot.run.error_present}
          <div class="evidence-failure" role="status">
            A failure record exists. Its private diagnostic detail is not exposed in this projection.
          </div>
        {/if}

        <section class="coverage-strip" aria-labelledby="coverage-title">
          <h2 id="coverage-title" class="visually-hidden">Evidence coverage</h2>
          <div><span>snapshot</span><strong>{new Date(snapshot.snapshot_at).toLocaleTimeString()}</strong></div>
          <div><span>retained through</span><strong>#{snapshot.ledger_head_seq}</strong></div>
          <div><span>loaded through</span><strong>{snapshot.page_end_seq ?? "none"}</strong></div>
          <div><span>live updates</span><strong>{snapshot.live_tail.replaceAll("_", " ")}</strong></div>
          <button class="text-action" type="button" onclick={() => void load(runId)}>Refresh</button>
        </section>

        <section class="evidence-panel panel" aria-labelledby="evidence-title">
          <div class="panel-head">
            <h2 id="evidence-title" class="rune-head">Ordered evidence</h2>
            <span>
              {snapshot.evidence.length} loaded event{snapshot.evidence.length === 1 ? "" : "s"}
              {snapshot.has_more ? " · more retained" : ""}
            </span>
          </div>
          <ol class="evidence-list">
            {#each timeline as item (`${item.type}-${item.seq}`)}
              {#if item.type === "gap"}
                <li class="evidence-gap">
                  <span class="evidence-seq">#{item.seq}–{item.endSeq}</span>
                  <strong>?</strong>
                  <span>Unknown or omitted interval</span>
                </li>
              {:else}
                <li>
                  <button
                    class:current={selected?.event_id === item.evidence.event_id}
                    class="evidence-row"
                    type="button"
                    onclick={() => void selectEvidence(item.evidence)}
                  >
                    <span class="evidence-seq">#{item.evidence.seq}</span>
                    <span
                      class="evidence-kind"
                      data-kind={item.evidence.kind}
                      data-phase={item.evidence.phase}
                    >{item.evidence.kind}</span>
                    <span class="evidence-summary">{item.evidence.summary}</span>
                    <time datetime={item.evidence.occurred_at}>
                      {new Date(item.evidence.occurred_at).toLocaleTimeString()}
                    </time>
                  </button>
                </li>
              {/if}
            {/each}
          </ol>
          {#if snapshot.has_more}
            <div class="evidence-more">
              <button class="rune-btn" disabled={loadingMore} type="button" onclick={loadMore}>
                {loadingMore ? "Reading…" : "Load more retained evidence"}
              </button>
            </div>
          {/if}
        </section>
      {/if}
    </section>

    <aside class="orb-inspector">
      {#if snapshot}
        <section class="panel">
          <div class="panel-head"><h2 class="rune-head">Evidence limits</h2></div>
          <ul class="limits-list">
            {#each snapshot.known_omissions as omission (omission)}<li>{omission}</li>{/each}
          </ul>
        </section>
      {/if}
      {#if selectionNote}
        <section class="panel selection-note" role="status">
          <p class="inspector-copy">{selectionNote}</p>
        </section>
      {/if}
      {#if selected}
        <section
          class="panel selected-evidence"
          bind:this={selectedInspector}
          tabindex="-1"
        >
          <div class="panel-head">
            <h2 class="rune-head">Selected event</h2>
            <button class="sheet-dismiss" type="button" onclick={clearSelection}>Close</button>
          </div>
          <dl class="kv">
            <dt>event</dt><dd class="glyph">{selected.event_id}</dd>
            <dt>sequence</dt><dd>#{selected.seq}</dd>
            <dt>kind</dt><dd>{selected.kind}</dd>
            <dt>subject</dt><dd>{selected.subject_key ?? "—"}</dd>
            <dt>phase</dt><dd>{selected.phase ?? "—"}</dd>
            <dt>occurrence</dt><dd class="glyph">{selected.occurrence_id ?? "—"}</dd>
            <dt>capture</dt><dd>{selected.capture.replaceAll("_", " ")}</dd>
          </dl>
          {#if selected.nexus_path}
            <a
              class="inspector-link"
              href={`${selected.nexus_path}&event=${encodeURIComponent(selected.event_id)}`}
            >
              Open transition in Nexus →
            </a>
          {/if}
        </section>
      {/if}
    </aside>
  </div>
{/if}
