<script lang="ts">
  import type { components } from "$lib/api/openapi";
  import { readCreationFeedback, ApiError } from "$lib/api/client";
  import { onMount, untrack } from "svelte";

  type FeedbackView = components["schemas"]["FeedbackView"];
  type FeedbackEntry = components["schemas"]["FeedbackEntry"];

  interface Props {
    caseId: string;
  }

  let { caseId }: Props = $props();

  type LoadState = "idle" | "loading" | "loaded" | "refused" | "unavailable";

  let phase: LoadState = $state<LoadState>("idle");
  let view: FeedbackView | null = $state<FeedbackView | null>(null);
  let controller: AbortController | null = $state<AbortController | null>(null);

  let activeCaseId: string = $state(untrack(() => caseId));

  function isString(v: unknown): v is string {
    return typeof v === "string";
  }

  function isRecord(v: unknown): v is Record<string, unknown> {
    return typeof v === "object" && v !== null && !Array.isArray(v);
  }

  function humanize(v: string): string {
    return v.replace(/_/g, " ");
  }

  const DISPOSITIONS = new Set(["accepted", "rejected", "partial", "incomplete"]);
  const EXTERNAL_DISPOSITIONS = new Set([
    "accepted",
    "rejected",
    "partial",
    "incomplete",
    "not_assessed",
  ]);
  const OWNER_ACTIONS = new Set(["hold", "reject"]);
  const STATUSES = new Set(["unassessed", "review_required", "hold", "rejected"]);
  const COVERAGE_VALUES = new Set(["submitter_annotation", "not_assessed"]);

  function currentAssessment(v: FeedbackView): FeedbackEntry | null {
    if (!isString(v.current_assessment_id)) return null;
    const found = v.assessments.find((a) => a.id === v.current_assessment_id);
    return found ?? null;
  }

  function currentDecision(v: FeedbackView): FeedbackEntry | null {
    if (!isString(v.current_decision_id)) return null;
    const found = v.decisions.find((d) => d.id === v.current_decision_id);
    return found ?? null;
  }

  function externalReport(entry: FeedbackEntry | null): string | null {
    if (!entry) return null;
    const body = entry.body;
    if (!isRecord(body)) return null;
    const report = body["report"];
    return isString(report) ? report : null;
  }

  function externalDisposition(entry: FeedbackEntry | null): string | null {
    if (!entry) return null;
    const body = entry.body;
    if (!isRecord(body)) return null;
    const d = body["disposition"];
    if (isString(d) && EXTERNAL_DISPOSITIONS.has(d)) return d;
    return null;
  }

  function ownerReason(entry: FeedbackEntry | null): string | null {
    if (!entry) return null;
    const body = entry.body;
    if (!isRecord(body)) return null;
    const reason = body["reason"];
    return isString(reason) ? reason : null;
  }

  function ownerAction(entry: FeedbackEntry | null): string | null {
    if (!entry) return null;
    const body = entry.body;
    if (!isRecord(body)) return null;
    const a = body["action"];
    if (isString(a) && OWNER_ACTIONS.has(a)) return a;
    return null;
  }

  function nativeDisposition(v: FeedbackView): string | null {
    const nv = v.native_verdict;
    if (!isRecord(nv)) return null;
    const d = nv["disposition"];
    if (isString(d) && DISPOSITIONS.has(d)) return d;
    return null;
  }

  function coverageEntries(entry: FeedbackEntry | null): { criterion: string; value: string }[] {
    if (!entry) return [];
    const cov = entry.criterion_coverage;
    if (!isRecord(cov)) return [];
    const out: { criterion: string; value: string }[] = [];
    for (const [k, val] of Object.entries(cov)) {
      if (isString(val) && COVERAGE_VALUES.has(val)) {
        out.push({ criterion: k, value: val });
      }
    }
    return out;
  }

  function clearProtected() {
    view = null;
    phase = "idle";
  }

  async function load() {
    if (phase === "loading") return;
    const requestedCase = caseId;
    const ac = new AbortController();
    controller = ac;
    phase = "loading";
    try {
      const data = await readCreationFeedback(requestedCase, ac.signal);
      if (ac.signal.aborted) return;
      if (data.case_id !== requestedCase) {
        phase = "unavailable";
        view = null;
        return;
      }
      view = data;
      phase = "loaded";
    } catch (err) {
      if (ac.signal.aborted) return;
      view = null;
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        phase = "refused";
      } else {
        phase = "unavailable";
      }
    } finally {
      if (controller === ac) controller = null;
    }
  }

  $effect(() => {
    const id = caseId;
    untrack(() => {
      if (id !== activeCaseId) {
        activeCaseId = id;
        if (controller) {
          controller.abort();
          controller = null;
        }
        clearProtected();
      }
    });
  });

  onMount(() => {
    return () => {
      if (controller) {
        controller.abort();
        controller = null;
      }
    };
  });

  const currentAssessmentEntry = $derived.by(() => (view ? currentAssessment(view) : null));
  const currentDecisionEntry = $derived.by(() => (view ? currentDecision(view) : null));
  const report = $derived.by(() => externalReport(currentAssessmentEntry));
  const reason = $derived.by(() => ownerReason(currentDecisionEntry));
  const coverage = $derived.by(() => coverageEntries(currentAssessmentEntry));
  const nativeDisp = $derived.by(() => (view ? nativeDisposition(view) : null));
  const extDisp = $derived.by(() => externalDisposition(currentAssessmentEntry));
  const ownerAct = $derived.by(() => ownerAction(currentDecisionEntry));
  const status = $derived.by(() =>
    view && isString(view.status) && STATUSES.has(view.status) ? view.status : null,
  );

  const buttonLabel = $derived.by(() =>
    phase === "loading"
      ? "Loading feedback…"
      : phase === "loaded"
        ? "Reload feedback"
        : phase === "refused" || phase === "unavailable"
          ? "Retry feedback"
          : "Load feedback",
  );
</script>

<section aria-labelledby="creation-feedback-heading" class="creation-feedback">
  <h2 id="creation-feedback-heading">External feedback</h2>

  {#if phase === "idle"}
    <p class="state">Not loaded.</p>
  {:else if phase === "loading"}
    <p class="state" aria-busy="true">Loading feedback…</p>
  {:else if phase === "refused"}
    <p class="state refused" role="status">Refused. No protected feedback is displayed.</p>
  {:else if phase === "unavailable"}
    <p class="state unavailable" role="status">Feedback unavailable.</p>
  {:else if phase === "loaded" && view}
    <dl class="feedback-dl">
      <dt>Native verdict</dt>
      <dd>{nativeDisp ? humanize(nativeDisp) : "not assessed"}</dd>

      <dt>External assessment</dt>
      <dd>{currentAssessmentEntry ? (extDisp ? humanize(extDisp) : "not assessed") : "No external assessment"}</dd>

      <dt>Owner disposition</dt>
      <dd>{currentDecisionEntry ? (ownerAct ? humanize(ownerAct) : "not assessed") : "No current owner decision"}</dd>

      <dt>Feedback status</dt>
      <dd>{status ? humanize(status) : "not assessed"}</dd>
    </dl>

    {#if currentAssessmentEntry}
      {#if report}
        <div class="detail">
          <h3 class="detail-heading">External report</h3>
          <p class="report">{report}</p>
        </div>
      {/if}
      {#if coverage.length}
        <div class="detail">
          <h3 class="detail-heading">Criterion coverage</h3>
          <ul class="coverage">
            {#each coverage as c (c.criterion)}
              <li>{c.criterion}: {c.value === "not_assessed" ? "not assessed" : "submitter annotation"}</li>
            {/each}
          </ul>
        </div>
      {/if}
    {/if}

    {#if currentDecisionEntry && reason}
      <div class="detail">
        <h3 class="detail-heading">Owner reason</h3>
        <p class="reason">{reason}</p>
      </div>
    {/if}

    <p class="note">
      Native acceptance does not establish owner permission. Coverage labels reflect only
      submitter annotation or that a criterion was not assessed; they are not semantic pass
      judgments.
    </p>
  {/if}

  <button
    type="button"
    class="load-btn"
    disabled={phase === "loading"}
    aria-busy={phase === "loading" ? "true" : undefined}
    onclick={load}
  >
    {buttonLabel}
  </button>
</section>

<style>
  .creation-feedback {
    display: block;
    border: 1px solid var(--color-engraving, currentcolor);
    border-radius: var(--radius-panel, 0.5rem);
    padding: var(--text-sm, 0.75rem);
    background: var(--color-obsidian, transparent);
    color: var(--color-parchment, currentcolor);
  }
  .creation-feedback h2 {
    font-size: var(--text-lg, 1.125rem);
    margin: 0 0 var(--text-sm, 0.75rem);
    color: var(--color-bone, currentcolor);
  }
  .state {
    margin: 0 0 var(--text-sm, 0.75rem);
  }
  .state.refused,
  .state.unavailable {
    color: var(--color-ember, currentcolor);
  }
  .load-btn {
    font: inherit;
    padding: 0.25rem 0.75rem;
    border-radius: var(--radius-rune, 0.25rem);
    border: 1px solid var(--color-engraving, currentcolor);
    background: var(--color-obsidian, transparent);
    color: var(--color-bone, currentcolor);
    cursor: pointer;
  }
  .load-btn:focus-visible {
    outline: 2px solid var(--color-rune, currentcolor);
    outline-offset: 2px;
  }
  .load-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .feedback-dl {
    margin: 0 0 var(--text-sm, 0.75rem);
  }
  .feedback-dl dt {
    font-weight: 600;
    margin-top: var(--text-xs, 0.5rem);
  }
  .feedback-dl dd {
    margin: 0.125rem 0 0;
  }
  .detail {
    margin: 0 0 var(--text-sm, 0.75rem);
  }
  .detail-heading {
    font-size: var(--text-sm, 0.875rem);
    margin: 0 0 0.25rem;
  }
  .report,
  .reason {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .coverage {
    margin: 0;
    padding-left: 1.25rem;
  }
  .note {
    font-size: var(--text-sm, 0.875rem);
    margin: 0 0 var(--text-sm, 0.75rem);
  }
</style>