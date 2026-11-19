<script lang="ts">
  import type { OrbRunSnapshot } from "$lib/api/models";
  import { appraisalSource, type LocalAppraisal } from "../state/affect";

  type Evidence = OrbRunSnapshot["evidence"][number];
  let {
    runId,
    record,
    notes,
    onchange,
    onhold,
    open = $bindable(false),
    ledger,
    oninspect,
  }: {
    runId: string;
    record: Evidence | undefined;
    notes: LocalAppraisal[];
    onchange: (value: LocalAppraisal[]) => void;
    onhold: () => void;
    open?: boolean;
    ledger: LocalAppraisal[];
    oninspect: (id: string) => void;
  } = $props();
  const limit = 24;
  const uid = $props.id();
  let source = $derived(record ? appraisalSource(runId, record) : null);
  let note = $derived(notes.find((item) => item.source === source));
  let editing = $state<string | null>(null);
  let gain = $state("");
  let emotion = $state("");
  let finding = $state("");
  let next = $state("");
  let reason = $state("");
  const gainOptions = [
    "Changed the decision",
    "Repeated existing evidence",
    "Insufficient evidence",
    "Conflicting evidence",
  ];
  const emotions = ["Curiosity", "Concern", "Satisfaction", "Frustration", "Neutral"];
  const findings = [
    "No mistake claimed",
    "Suspected mistake",
    "Repair needs checking",
    "Repair evidence observed",
  ];
  const nextOptions = ["Consider one bounded probe", "Stop probing", "Request owner review"];

  function appraise() {
    if (!record || !source) return;
    onhold();
    editing = source;
    gain = note?.gain ?? "";
    emotion = note?.emotion ?? "";
    finding = note?.finding ?? findings[0]!;
    next = note?.next ?? "";
    reason = note?.reason ?? "";
  }

  function save(event: SubmitEvent) {
    event.preventDefault();
    if (
      !record ||
      !source ||
      source !== editing ||
      !emotion ||
      !gain ||
      !next ||
      !reason.trim() ||
      (!note && notes.length >= limit)
    )
      return;
    onchange([
      ...notes.filter((item) => item.source !== source),
      {
        source,
        eventId: record.event_id,
        seq: record.seq,
        gain,
        emotion,
        finding,
        next,
        reason: reason.trim(),
        at: new Date().toISOString(),
      },
    ]);
    editing = null;
  }
</script>

<details id="orb-affect" class="orb-affect" bind:open>
  <summary>Affect at the cursor <span>{record ? `Record #${record.seq}` : "No loaded record"}</span></summary>
  {#if open}
    <div class="appraisal-body">
      {#if record}
        <section aria-labelledby={`${uid}-source`}>
          <h3 id={`${uid}-source`}>Recorded source</h3>
          <p class="source-text">{record.summary}</p>
          <dl>
            <dt>Run</dt>
            <dd><code>{runId}</code></dd>
            <dt>Event</dt>
            <dd><code>{record.event_id}</code> · #{record.seq}</dd>
            <dt>Recorded</dt>
            <dd>
              <time datetime={record.occurred_at}>{new Date(record.occurred_at).toLocaleString()}</time> · {record.capture.replaceAll(
                "_",
                " ",
              )}
            </dd>
            <dt>Subject</dt>
            <dd>{record.subject_key ?? "Unavailable"}{record.phase ? ` · ${record.phase}` : ""}</dd>
            <dt>Attempt</dt>
            <dd><code>{record.occurrence_id ?? "Unavailable"}</code></dd>
            <dt>Recorded affect</dt>
            <dd>Unavailable. This event carries no baseline, appraisal or signal-to-route decision.</dd>
          </dl>
        </section>
        <section class="operator" aria-labelledby={`${uid}-review`}>
          <h3 id={`${uid}-review`}>Operator appraisal</h3>
          {#if editing && editing === source}
            <form onsubmit={save}>
              <label
                >Your response
                <select required bind:value={emotion}
                  ><option value="" disabled>Select an emotion</option>
                  {#each emotions as item (item)}<option value={item}>{item}</option>{/each}
                </select>
              </label>
              <label
                >Evidence gain
                <select required bind:value={gain}
                  ><option value="" disabled>Select an appraisal</option>
                  {#each gainOptions as item (item)}<option value={item}>{item}</option>{/each}
                </select>
              </label>
              <label
                >Finding for the evidence ledger
                <select bind:value={finding}
                  >{#each findings as item (item)}<option value={item}>{item}</option>{/each}</select
                >
              </label>
              <label
                >Suggested follow-up
                <select required bind:value={next}
                  ><option value="" disabled>Select a recommendation</option>
                  {#each nextOptions as item (item)}<option value={item}>{item}</option>{/each}
                </select>
              </label>
              <label
                >Why this follow-up?
                <textarea
                  bind:value={reason}
                  required
                  maxlength="1000"
                  rows="3"
                  placeholder={next === nextOptions[0]
                    ? "Name one question, the observation it needs and its limit."
                    : "Which decision does this observation change or leave unresolved?"}></textarea>
              </label>
              <div class="actions">
                <button type="submit" disabled={!emotion || !gain || !next || !reason.trim()}
                  >Save local appraisal</button
                >
                <button type="button" onclick={() => (editing = null)}>Cancel</button>
              </div>
            </form>
          {:else if note}
            <div class="review" role="status">
              <p><strong>{note.emotion}</strong> · {note.gain}</p>
              <p>{note.next} · {note.finding}</p>
              <p>{note.reason}</p>
              <small>Your review · <time datetime={note.at}>{new Date(note.at).toLocaleString()}</time></small
              >
            </div>
            <div class="actions">
              <button type="button" onclick={appraise}>Edit local appraisal</button>
              <button type="button" onclick={() => onchange(notes.filter((item) => item.source !== source))}
                >Remove local appraisal</button
              >
            </div>
          {:else if notes.length < limit}
            <button type="button" onclick={appraise}>Appraise this record</button>
          {:else}
            <p>
              All {limit} local appraisal slots are in use. Remove an earlier appraisal to review another record.
            </p>
          {/if}
          <p class="scope">
            Your retrospective judgment stays in this Run view. It issues no probe and grants no network
            access.
          </p>
        </section>
      {:else}
        <p>A retained event is needed to anchor an appraisal. No event is loaded at this cursor.</p>
      {/if}
    </div>
    <section class="ledger" aria-labelledby={`${uid}-ledger`}>
      <h3 id={`${uid}-ledger`}>Mistakes &amp; evidence ledger</h3>
      {#if ledger.length}
        <ol>
          {#each ledger as item (item.source)}<li>
              <button type="button" onclick={() => oninspect(item.eventId)}>Inspect #{item.seq}</button>
              {item.finding} · {item.emotion}
            </li>{/each}
        </ol>
      {:else}<p>No operator findings attached to loaded records through this cursor.</p>{/if}
      <p class="scope">
        This ledger holds your observations in this view. File reads, edits and patches require a separately
        supplied source.
      </p>
    </section>
  {/if}
</details>

<style>
  .orb-affect {
    color: var(--color-parchment);
    font: var(--text-sm)/1.55 var(--font-body);
    border-block: 1px solid var(--color-engraving);
  }
  summary {
    padding: 0.8rem 0.15rem;
    color: var(--color-bone);
    cursor: pointer;
    font-weight: 600;
  }
  summary span {
    margin-inline-start: 0.7rem;
    color: var(--color-ash);
    font-size: var(--text-xs);
    font-weight: 400;
  }
  .appraisal-body {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr));
    gap: 1.2rem;
    padding: 0.6rem 0.1rem 1.1rem;
  }
  section {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  h3,
  strong {
    color: var(--color-bone);
  }
  h3 {
    margin: 0 0 0.65rem;
    font: 600 1rem/1.4 var(--font-body);
  }
  dl {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.4rem 0.8rem;
    margin-top: 0.7rem;
    font-size: var(--text-xs);
  }
  dt,
  small,
  .scope {
    color: var(--color-ash);
  }
  .source-text {
    color: var(--color-bone);
  }
  .scope {
    margin-top: 0.75rem;
    font-size: var(--text-xs);
  }
  .ledger {
    margin: 0.5rem 0 1rem;
  }
  .ledger ol {
    padding: 0;
    list-style: none;
  }
  .review {
    display: grid;
    gap: 0.35rem;
    padding: 0.55rem 0.7rem;
    margin-bottom: 0.65rem;
    border-inline-start: 2px solid var(--color-rune);
    background: var(--color-obsidian);
  }
  form,
  label {
    display: grid;
    gap: 0.35rem;
  }
  form {
    gap: 0.65rem;
  }
  label {
    font-size: var(--text-xs);
  }
  select,
  textarea,
  button {
    max-width: 100%;
    min-height: 2.4rem;
    padding: 0.4rem 0.55rem;
    color: var(--color-bone);
    background: var(--color-obsidian);
    border: 1px solid var(--color-control-border);
    border-radius: var(--radius-rune);
    font: inherit;
  }
  select,
  textarea {
    width: 100%;
    min-width: 0;
  }
  textarea {
    resize: vertical;
  }
  button {
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .actions {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
  }
  :is(summary, button, select, textarea):focus-visible {
    outline: 2px solid var(--color-rune);
    outline-offset: 3px;
  }
</style>
