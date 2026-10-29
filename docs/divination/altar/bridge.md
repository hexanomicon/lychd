---
title: Bridge
icon: material/bridge
---

# :material-bridge: Bridge

Use Bridge to offer an Intent and stay with the answer as you inspect other Altar instruments or
applications. Its session, or séance, holds the continuing conversation. Each admitted turn opens
its own [Circle](circle.md), whose Run lets you follow that one request through to its result.

Open it with **Bridge** in the top masthead. Resize its divider, choose the left or right side,
or collapse it while retaining the conversation. Ordinary instrument navigation does not destroy
the selected session, its live reconstruction or a later draft. On a narrow window, the panel is
a modal sheet; Escape closes it and returns focus to its opener. The layout's remembered width,
side and open state contain no conversation text or request bodies.

After completing [Altar setup](index.md), open `http://127.0.0.1:7134/bridge` in the dedicated
browser profile on the same host. Existing session, Run and consent URLs open their exact Bridge
focus. Keep the listener on literal `127.0.0.1`; do not proxy, tunnel, or forward it.

## Offer one Intent {#follow-a-turn-to-settlement}

Choose **New Séance**, or select an existing session, and submit your message once. Bridge gives
the request an identity that an identical retry reuses, allowing the server to return the same
canonical Run. If the response is lost, **Retry original offering** resends that immutable request.
The next offering stays disabled until its outcome is resolved: a later refusal cannot erase an
earlier unknown outcome.

You can write a later draft while waiting. If the original offering is definitely refused, Bridge
keeps its text beside that later draft so you can restore or dismiss it.

Drafts and unresolved offerings remain separate for each session when you visit another Altar
instrument. They last while this browser document stays open; reload or closing the tab warns
before losing them. This is not storage across browser restarts.

**Conversations** discloses the session rail; **Séance details** holds secondary identity and
session attention. The conversation remains the main reading area. If admission is unresolved or
another Run is unsettled, the composer explains why **Offer** is unavailable while keeping the
later draft editable; that draft is not queued.

The shell's consent count opens **Conversations awaiting consent**. Choose a marked session to
review its requests; its rail and inspector show that session's count. Requests without an
available Bridge conversation remain in the global count and are reported in the chooser.

When arriving from Atlas, choose a linked conversation or use the conversation chooser. The
project return link stays available, including after opening a new séance. **Link this conversation
to…** opens a prefilled Atlas form for an explicit save; it does not link or send project context
merely because you navigated.

The compact **Circle** beside the turn shows supplied canonical status and current activity.
Expand it for full Run identity and the supplied Pattern revision, with a link to its declared
score. Keep that identity when following the result into another instrument. Older retained
replies identify missing metadata explicitly. The [Circle guide](circle.md) separates these
controls from the fuller workspace still being designed.

If a consent card appears, read the pending request and choose one of its supported decisions.
The server validates the request, descriptor, reference and decision together. Your choice
applies to that pending request. Each Invocation has its own Sigil, Context boundary and
consequences; permission for another object, wider tools or a later effect needs its own
admission. Suggesting an action in conversation cannot authorize it.

## Read the result

When the Run settles, follow its strip to [Orb](orb.md) for evidence. Failed and cancelled Runs
remain visible even if they produced no settled agent turn. In that case, the conversation can
contain your admitted message with no answer beside it.

If text from a failed Run is still projected live, Bridge marks it as an incomplete answer. A
terminal event may already have supplied a retained failure message; the notice does not identify
the text's provenance. When a retained agent turn becomes available in the session snapshot, it
replaces that live projection. Orb records the presence of failure while keeping private
diagnostic reasons private; it neither authorizes an automatic retry nor performs one.

After reload or restart, a turn may be presented as **Retained reply** rather than its former
live activity card. Failed text can remain in history without retaining every live status badge.
Use the exact Run in Orb for canonical status. The fixed trusted source-browser journey has a
separate [evidence boundary](../../state-of-the-work.md#current-evidence-envelope); it does not
qualify every casting, Consent interaction or ordinary installed browser profile.

Incoming text preserves your place when you scroll into older work. **Latest turn** returns to
the conversation's end and releases a linked Run focus without changing your draft.

Follow the question raised by the result: [Loom](loom.md) shows the declared score, Orb shows
Run evidence, and [Nexus](nexus.md) shows physical observations. Each instrument keeps its own
controls and owners for any action it offers.

## When a turn cannot advance

| What you encounter | What it means or what to do |
| --- | --- |
| Another Run in this séance is still nonterminal | A different message is refused; an identical retry returns the same canonical Run. Wait for terminal ledger status before starting a new turn. |
| The activity stream lags or remains open | Use durable Run status to establish lifecycle state. An open stream, spinner or advancing clock cannot independently establish that work is advancing. |
| Cancellation is followed by a failed session refresh | The selected session's consent cards and count have already been cleared. Those actions stay revoked until authoritative session truth is available. |

The interface currently shows activity without a structured **Why waiting?** explanation or an
evidence-freshness indicator.

## What the next turn remembers

In revisions 1 and 2, Bridge builds the next turn's history from recent, complete, settled turns.
It takes the newest whole turns that fit the configured turn and character budgets. Your message
may appear in the conversation earlier, but it joins this history only when its agent turn settles.
This path supplies neither full-session replay nor Archive retrieval. The opt-in public-note
revision below instead answers each question independently, without replaying those turns.

??? info "How Bridge retains and restores a turn"

    Only a settled agent turn appends one complete Pydantic AI history unit. Bridge validates
    typed messages, normalizes provider hops to their owning LychD Run, and keeps a consent
    return paired with its original tool call. For a later Invocation it rebuilds the Stable
    Floor for the newly granted capability. Consent resume preserves the current call chain
    while fitting older settled turns to that grant's bounds.
    A policy stop retains results of already completed tools and marks the known refused request
    as denied. The stopped reply does not claim that earlier actions were undone.

    Closed, server-validated GenUI fragments survive a terminal refresh. Older rows retain inert
    compatibility keys and stay outside the current renderer. Replaying an identical settled
    outcome makes no change. Reusing a Run and role identity with different visible content,
    state or fragments is rejected. An older recovery snapshot cannot replace a newer cursor
    or generation.

    Admission has a durable database delivery outbox. Conversation streaming has a narrower
    lifetime: semantic events and their reconstruction remain process-local, with no durable
    token or event delivery. The single-active-Run rule does not create a conversation queue
    across multiple processes. The existing consent round is supported; general multi-approval
    flows and notifications remain unavailable. The [Bridge delivery
    record](../../state-of-the-work.md#bridge-surface) gives the current scope.

## Investigate public source

Choose **Investigate public source** when you have a bounded software question and public material
for it to examine. Supply the declared repository, base revision and tree/patch digest, your
question, literal named public sources, and explicit criteria. State omissions and non-goals so
the investigation's boundary is clear, and confirm that every supplied item is public. You supply
the material yourself; this operation acquires no repository or file.

The form shows UTF-8 byte limits and preserves the material exactly, without truncation or silent
normalization. The fixed [Creation investigation](../../compositions/creation/index.md) uses no
tools: it produces an investigation without editing source, executing a workspace, or promoting a
change.

Submit once. If the response is lost, **Admission unconfirmed** retains the original case UUID and
body. Use **Check this case** to read that identity. A 404 can arrive while submission is still in
flight, so it does not establish refusal. **Replay identical request** explicitly resends the
original body and is available only while this document still retains it. Timeouts, reconnects,
and navigation never retry POST automatically.

To move on, **Start different request** opens a consequence review. **Keep current request** keeps
the draft and replay body; **Discard draft and replay body** clears them but leaves earlier
uncertain UUIDs visible. Selecting one valid case within this focus preserves the transient
state without a loss prompt or automatic read. A missing, invalid, or duplicate selection leaves
the focus and retains its loss warning.

The URL retains only the case UUID. Sources and submitted bodies have no durable browser draft;
reload warns before discarding transient material and cannot recover an identical replay body.
After reload, explicitly Check the case using its UUID. Opening an investigation does not select
a different ordinary séance or discard its drafts and consent. **Return to conversation** leaves
this focus, and the global Bridge link keeps its ordinary session behavior.

Read the question and source alongside the candidate findings and their citations, then examine
the separate verifier verdict. Completion tells you the Run finished; judging the report still
requires this comparison. The exact admitted Run opens in Orb for execution evidence.

**Load feedback** reads the report's separately protected historical judgments: native verdict,
external assessment, owner disposition, and feedback status. Keep the external report, owner
reason, and annotation coverage distinct. Native acceptance supplies no owner permission, and
coverage does not establish semantic adequacy. A newer assessment needs owner review rather than
inheriting an older hold. **Reload feedback** reads later changes. A refused read clears the
feedback; unavailable feedback and an unassessed report remain different states.

The detail read may expire an overdue case; the historical feedback read does not. Use **Refresh
retained case** for later case changes. An unavailable case, missing report, refused read and
unconfirmed admission are separate states. Viewing appends no feedback and authorizes no
continuation, cancellation or successor.

## Public-note answers {#public-note-answers}

Use this opt-in profile for questions about explicitly retained **public** notes on the same host.
It requires the PostgreSQL binding and migrations from [Summoning](../../summoning.md), an exact
local chat capability, and the existing loopback Altar access boundary. It does not automatically
read your files or save conversations as memory. The [delivery record](../../state-of-the-work.md#karma-semantic-memory)
distinguishes portable tests, dated native operator observations and installed operation.

Select revision 3 in the Weaver configuration, using the exact capability key observed in
[Nexus](nexus.md). This example's capability is a placeholder; namespace and owner identify one
new public-note collection and must remain stable once material is retained.

```toml
[weaver.bridge]
revision = "3"
capability_key = "replace-with-the-exact-local-chat-capability"

[weaver.bridge.archive]
profile = "local-public-notes@1"
namespace_id = "9d340d97-7a12-47ed-af2b-c4742ed690f6"
policy_revision = "local-notes-policy@1"

[weaver.bridge.archive.owner_subject]
identity = "local-notes-owner"
```

Configuration binds the trusted local caller to that owner; the API cannot supply another subject.
Changing the namespace's owner or policy revision does not migrate existing notes. Follow the
normal [configuration lifecycle](../../sepulcher/extensions/weaver/index.md#choose-a-bridge-capability)
when changing the selected revision. An already admitted Run keeps its original profile and
capability; changed current authority can refuse its continuation.

### Manage public notes

Choose **Manage public notes** in Bridge. The **Configured profile** identifies the collection;
**Current Bridge default** separately says whether the actual default requests this exact profile.
Unavailable and failed reads stay distinct. This configuration establishes neither storage/model
readiness, the next routed Run nor an earlier Run's binding.

1. Choose **New public note**, supply source key, source revision, producer, observation time with
   timezone and complete text, then explicitly declare the material public. **Prepare public
   intake** freezes the UUID, observation time, exact submitted UTF-8 digest and body for review.
   **Submit candidate once** retains a candidate; **Promote this candidate** is a separate decision.
2. **Manage notes** shows bounded metadata across all lifecycles. An exact source-key filter and
   **Load more metadata** select further pages; the loaded count is not a total. A record link
   recovers its current metadata independently of the loaded page. **Check exact record** refreshes
   that version without replaying an effect.
3. **Stage correction** keeps the source key fixed and starts with empty replacement text and a
   new revision label. Supply the complete replacement and a different revision, then prepare and
   submit it. The prior promoted revision remains eligible until separate promotion supersedes it.
   Existing text is not read back or prefilled; revision labels imply no ordering.
4. **Review revoke** displays the exact namespace, source/revision, record, digest and expected
   version. **Confirm exact revoke** removes controlled text and retains the anti-reingestion
   tombstone. Earlier answers and backups are outside that promise.

For intake, **Replay identical intake** can resend the frozen original body. Use it deliberately:
a metadata lookup cannot establish which intake occurrence committed. A lost response therefore
remains unknown even when you can read current metadata.

Lifecycle commands have a different recovery path and no replay action. Check the exact record,
then make a fresh explicit decision. An unchanged version, missing read, or later refusal cannot
prove rollback. A newer version establishes current state, without identifying the author of the
attempted occurrence. Refresh and navigation never send writes automatically, and a late response
cannot replace a newer selected focus.

Drafts and frozen bodies remain in this browser document only. Departure/reload warns before
losing them; reload recovers authorized metadata, not the original body or identical replay ability.
Keep unknown request/source/record identities when needed. Current refusal clears protected
material. Ordinary conversation drafts, unresolved offerings and Consent remain separate;
**Return to conversation** follows the shell's ordinary Bridge selection.

The authenticated API supports the same recovery. These reads reveal no note text, search vectors
or embeddings:

| GET path | Result |
| --- | --- |
| `/api/v1/archive/profile` | The currently configured public-note profile, namespace, owner and policy. This performs no storage or model work and does not prove that retained material accepts that binding. |
| `/api/v1/archive/bridge-default` | The actual admission default and its complete managed-profile match, or unavailable. This reveals no other collection and performs no storage, history, readiness or Run work. |
| `/api/v1/archive/notes` | Metadata for every lifecycle, including candidates, archived revisions and revoked tombstones. `limit` is 1–50; optional `source_key` matches exactly. Follow the opaque `next_cursor` with the same source filter; absence returns an empty page, while changed binding or storage failure refuses. |
| `/api/v1/archive/notes/{record_id}` | One retained record's current metadata and lifecycle version. A missing record refuses rather than replaying an effect or restoring revoked content. |

After an uncertain lifecycle response, read the exact record, inspect its current version and make
a new explicit decision. Do not automatically repeat a stale transition. Listing metadata does
not make a note eligible for recall or establish which profile an admitted Bridge Run uses.

The existing writes require the same local access and CSRF protection as other Altar mutations:

| POST path | Body and result |
| --- | --- |
| `/api/v1/archive/notes` | Submit the proposal below; retain the returned `reference.record_id` and `reference.lifecycle_version`. Intake creates a candidate, which recall excludes. |
| `/api/v1/archive/notes/{record_id}/promote` | `{"expected_version": 1}` for a fresh candidate; makes it eligible and archives a prior promoted revision of the same source. |
| `/api/v1/archive/notes/{record_id}/archive` | Supply the current `expected_version`; removes a promoted note from recall while retaining its text. |
| `/api/v1/archive/notes/{record_id}/revoke` | Supply the current `expected_version`; removes controlled text and retains a tombstone preventing reingestion of that source revision. |
| `/api/v1/archive/recalls` | Supply `namespace_id`, a new UUID `request_id`, and `query`; returns a receipt with selected source references, scores and omissions. |
| `/api/v1/archive/recalls/{receipt_id}/resolve` | Supply `{"receipt_digest": "the-returned-digest"}`; returns the exact selected text only while current authority and source lifecycle still permit it. |

For example, this proposal's digest binds its exact UTF-8 text, including punctuation. Use a new
request identity for new material; an identical retry reuses the original request identity.

```json
{
  "namespace_id": "9d340d97-7a12-47ed-af2b-c4742ed690f6",
  "request_id": "fe6444d6-4267-44e6-afca-c592f3340f31",
  "source_key": "observatory-hours",
  "source_revision": "1",
  "source_digest": "5ed3a3ecd485ad5b2d58439f0d3ca781979499c5e5d230fa6cd4cd5c7997179f",
  "text": "Example note: the test observatory closes at 21:00 UTC.",
  "producer": "operator-public-note",
  "observed_at": "2026-10-11T00:00:00Z",
  "classification": "public"
}
```

After explicit promotion, offer `observatory` in Bridge to exercise lexical matching against the
example. Retrieval uses PostgreSQL `simple` word matching, not semantic similarity or synonym
expansion. A question is bounded to 2,000 characters; a note to 16,000. Bridge recall selects at
most five notes within an 8,000-character text budget, omitting whole notes that do not fit. The
receipt reports those omissions; database failure is never reported as an empty match.

The answer profile has no model tools and does not replay prior answers. Each request receives
the exact selected notes as attributed data, with room reserved in Context. The source envelope
is transient; receipts retain identifiers and digests. The model is instructed to cite source keys
and revisions, but its generated claims still need judgment.

The [19 October observation](../../state-of-the-work.md#karma-semantic-memory) follows the same
question through candidate, promotion, correction and revocation on a real local model. The
answer changes with the eligible source revision and abstains when none remains. That one terse
lexical case does not establish general question answering or semantic retrieval.

To correct a note, submit a new `source_revision` and explicitly promote it. Prior receipts then
refuse the superseded revision. Revocation also prevents future resolution, including before a
pending answer settles, but cannot erase output already generated or streamed. A timeout after a
mutation may leave it committed: retry exact intake with its original identity; a stale lifecycle
version refuses rather than repeating the transition.

### Prepare a promoted note for semantic recall

Open the exact record from **Manage public notes**. Preparation works on this promoted public
revision and the configured generation; source text stays on the server. The exact embedding
runtime must already be warm through its [Orchestrator owner](../../adr/23-orchestrator.md).
Configuration alone proves neither registration, source preparation nor readiness.

1. **Check preparation** reads metadata for the exact generation and source reference. It performs
   no embedding. Distinguish not checked, missing generation/derivation, prepared, running,
   expired, complete, failed and invalidated from a refused or unavailable read.
2. **Register configured generation** is a separately named mutation of the shared generation.
   Inspect the configured profile/reference before acting. It performs no embedding; an exact
   explicit repeat can observe retained active/retired state, but cannot revive retirement.
3. Review this source key/revision, namespace, complete source reference and generation, then
   choose **Prepare this promoted revision**. The request may acquire a local embedding lease and
   derive that exact note. It does not promote the note, activate a model, start a Run or submit a
   recall. Oversize or changed sources refuse; no truncation or automatic correction occurs.

Read a derivation UUID as the identity of a durable row. Its row and attempt versions, together
with server times, describe the latest state. They do not identify a particular browser HTTP call
or account for all compute spent. A successful **Check** therefore leaves a lost preparation
response uncertain.

Prepared, failed, or DB-expired state can admit new work even for the same body. Choosing to prepare
again may repeat compute; it never retries automatically. Observing expiry neither stops earlier
work nor proves its transport has settled. Only the server can establish an eligible completed
replay that performs no new work.

Keep the frozen generation and exact source reference while recovering an uncertain call. After a
lifecycle change, the newer current reference may not locate historical status; reload cannot
reconstruct an older lifecycle version. Leaving, clearing or aborting a read proves no rollback or
cancellation. Current authority/profile changes clear protected display and fence late responses.
Source preparation and intake/lifecycle writes are locally serialized.

**Complete** means a retained derivation for that exact row. It promises neither corpus coverage,
future eligibility nor a selected answer. Open **Recall public sources** separately to choose a
query and threshold; completion never launches it automatically.

### Recall semantic sources

Choose **Recall public sources** in Bridge, or open `/bridge?notes=recall`. This separate view
returns attributed public-note sources; it does not generate an answer or admit a Run. Ordinary
revision 3 public-note answers remain lexical. Opening the view reads only the authorized configured
profile and generation. These metadata do not prove that semantic recall is enabled, that the
generation is registered, that notes have eligible derivations, or that the exact model is warm.

Prepare those prerequisites separately through the existing [Archive derivation and semantic
contract](../../adr/27-memory.md). Intake and promotion alone do not derive a note. This view
never registers a generation, derives notes or activates a model. Installed runtime preparation
and general retrieval quality retain their [delivery boundary](../../state-of-the-work.md#karma-semantic-memory).

1. Enter a public query and an explicit minimum cosine similarity between −1 and 1. Similarity
   locates context; it is not answer confidence or a truth score. Review the result and source
   character bounds. **Query and load exact sources once** freezes the exact query, namespace,
   generation, bounds and a fresh request UUID, then requests a selection and resolves its exact
   receipt digest under current authority.
2. Read coverage and whole-source budget omissions alongside the ordered sources. Each source
   identifies its key, immutable revision, record/lifecycle version and similarity. Selection time
   describes the retained snapshot; source resolution time describes this browser's later read.
   Partial derivation coverage and an empty selection are distinct from an unavailable model or
   refused request. Source text is data and grants no instruction or effect authority.
3. If the query response is lost, **Check exact request metadata only** inspects the same frozen
   request without embedding or loading text. No receipt yet does not prove that an in-flight
   query failed. A recovered receipt requires **Load exact current sources**; correction,
   revocation or changed authority may refuse the old selection. No automatic query retry occurs.

Query drafts, frozen bodies and resolved text stay in this browser document. Departure warns before
losing them; they do not enter the URL or browser storage. Clearing or leaving does not cancel
model work, undo a selection or prove rollback. A later explicit submission uses a new UUID and
may incur new work. Current refusal and profile changes clear protected display; late responses
cannot replace a newer focus. Return to conversation preserves its separate drafts, unresolved
offerings and Consent.

### Answer from a semantic generation

The separate revision 5 uses the configured semantic generation to supply sources to a native
answer workflow. Its [delivery record](../../state-of-the-work.md#karma-semantic-memory) separates
component, PostgreSQL and actual model acceptance. Enable it deliberately through the normal
[configuration lifecycle](../../sepulcher/extensions/weaver/index.md#choose-a-bridge-capability);
opening **Recall public sources** does not change conversation routing.

Use the existing independent `archive.profile`, `archive.derivation` and `archive.semantic = true`
selection. Keep the retained namespace, owner and policy unchanged. When moving from revision 3's
legacy `weaver.bridge.archive` configuration, move that same profile to `archive.profile`; revision 5
does not accept `weaver.bridge.archive`. Generation registration and promoted-note preparation
remain explicit [management operations](#prepare-a-promoted-note-for-semantic-recall).

```toml
[weaver.bridge]
revision = "5"
capability_key = "replace-with-the-exact-local-chat-capability"

[weaver.bridge.semantic]
min_cosine = 0.5
max_results = 5
char_budget = 8000
```

The threshold is an explicit operator choice, not a confidence calibration. Composition requires
PostgreSQL, local access and declared exact chat and embedding bindings; it starts no model or
preparation. Bridge's composer identifies the configured semantic default without claiming current
readiness. Each admitted Run retains its bindings; an older Run keeps its own revision. There is
no per-message mode selector.

Ask about the promoted public notes. Loom shows recall, answer and settlement; Orb follows their
actual Run events. A managed dedicated model can enter bounded hardware waiting through the
existing Orchestrator. Missing generation, revoked sources and service failure refuse the Run;
they are not successful empty searches. Returned context can be irrelevant, and coverage can be
partial. Inspect the answer's source keys, revisions, uncertainty and conflicts rather than
treating a similarity score as proof.

If generation reaches its output limit, the semantic request fails with `answer_output_limit`
rather than publishing a normal settled answer or new SDK message history. Text already streamed
is provisional and may remain in Run evidence. Open the linked Orb to inspect the failure; review
the configured generation budget before making a new offering. There is no automatic retry or
budget increase, and replaying the same admitted request does not create another inference.
When a successful current recall selects no notes, the workflow returns a labelled deterministic
recall result without calling the answer-generation model. It explains which boundary applied:
no notes were searchable, none met the threshold, or the retrieved notes did not fit the character
limit. The result includes the receipt's coverage at recall; partial coverage cannot establish an
exhaustive search.

Fresh query embedding still consumes its admitted work, and this visible outcome adds no SDK
message history. Source or service refusal produces a failed Run. Even successful completion
cannot certify answer truth or universal provider completeness.

This revision has no tools and does not replay earlier conversation history. It resolves the
same receipt again before outbound model work and settlement. The full escaped source envelope
has a separate 16000-character ceiling; overly large projections refuse rather than truncate.
Source text stays transient, while the generated answer and ordinary messages may quote it and
persist. Revocation blocks future use without erasing earlier influence. The existing matching
Archive inspector remains revision-3 selection evidence; this mode does not create a stronger
capture or transmission receipt.

## Public-page answers

When Scout is the configured Bridge default, the composer shows its command instructions and a
two-line example. These instructions follow the current default, even in an older conversation;
they do not establish that a request is authorized or ready to run. Use **Shift + Enter** to put
the question on the next line:

```text
/read-public https://example.com/page
What does this page claim?
```

With the opt-in [Scout profile](../../sepulcher/extensions/scout.md#public-page-answers), offer
`/read-public` followed by one exact public HTTPS URL, then a newline and your question. Review
the complete URL, resolver disclosure, limits and local answer capability on the consent card
before approving. The answer may quote the page and is retained in this conversation.

This profile answers one page independently, using no earlier conversation history or model tools.
It does not search for URLs, follow redirects or retry a lost acquisition. A refused or expired
review grants no contact. Loom shows the exact `bridge_chat@4` score; Orb keeps the Run outcome.

## Consent history direction

The planned [consent history](../../adr/25-hitl.md#consent-history-and-proposal-branches) lets you
follow a proposed action through review, revisions and its reported result. Related proposals
appear as branches, with your decision shown separately from what the executor actually did:

```text
Configuration change
└─ Proposal A
   ├─ Decision: denied
   └─ Proposal B: revises A
      ├─ Review: exact base and diff
      ├─ Decision: approved
      └─ Execution receipt: applied
```

A file proposal links the exact reviewed diff and artifact revision; a page acquisition shows
its destination and limits. Each type supplies its own review details. You can inspect a refused
version and a later alternative without approval carrying between them. A missing receipt means
the result is unavailable, not that an approved action succeeded. Withdrawing approval cannot
undo an effect that already happened.

This tree and its revision/explanation controls are not available in the current Bridge. The
current consent card still judges one exact request; denial does not automatically ask an Agent
to revise it. [State of Work](../../state-of-the-work.md#graph-stasis-consent) records the remaining
storage, recovery and interface work.

## Two crossings still being designed

**Pin and Ask** would begin a new Intent from an authorized typed reference. Before admission,
you would review which reference is being carried, what material would be included or summarized,
what is unavailable or redacted, and what permission is involved. The Vessel would then
reauthorize the request. Pinning itself would grant neither retrieval nor mutation authority.

**Propose in Loom** would turn selected conversation material into an attributed, inert charcoal Scroll candidate against a specified base Pattern revision. A future Spellweaver draft contract would have to validate it and publish a new revision before it could become executable work. The selection must become a typed handoff; copied prose or canvas coordinates alone cannot supply it.

Neither action is available yet. Follow their development through [Loom](loom.md) and the [delivery record](../../state-of-the-work.md#bridge-surface).

## Reading direction

For interface review and design, use the following composition and acceptance case.

Give the conversation the widest readable area so a reader can follow one offered text through
its exact Run status to a reply, an explicit missing reply, consent, or unresolved admission.
Keep each permission request's actual target and scope beside its decision controls. Conversation
selection stays accessible while secondary metadata unfolds on demand.

Judge the composition by what survives a detour: returning from Orb should recover the originating
Run while preserving the later draft and the reader's place. Project origin, saved membership,
and material in model Context must remain distinguishable. Circle's links should carry the reader
to the owning view; its fuller workspace remains a separate design.

Acceptance case: lose an offering's admission response, write a later draft, inspect another
instrument, and attend to consent in a different session. Return to the original session with
the same request identity and original text, the later draft intact, and correctly scoped
attention. Test unknown admission and accepted-Run consent independently; a mock must not suggest
two unrelated active offerings are permitted in one session. Browser restart recovery needs a
persistence contract beyond the current open-document state. These are [presentation
targets](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction), not a new queue, memory,
or recovery service.
