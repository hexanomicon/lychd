---
title: Bridge
icon: material/bridge
---

# :material-bridge: Bridge

Bridge is where you offer work to the Lich and return to its reply. A session, or séance, keeps the conversation together. Each admitted turn opens its own [Circle](circle.md), with a Run you can follow from request to result.

After completing [Altar setup](index.md), open `http://127.0.0.1:7134/bridge` in the dedicated browser profile on the same host. Keep the listener on literal `127.0.0.1`; do not proxy, tunnel, or forward it.

## Offer one Intent {#follow-a-turn-to-settlement}

Choose **New Séance** to create a local session, or select an existing session to continue it.
Submit your message once. Its request receives an identity that retries reuse, so an identical
retry can return the same canonical Run. If the response is lost, **Retry original offering**
resends that immutable request. A later refusal does not erase an earlier unknown outcome; the
next offering stays disabled until the original is resolved. You can write a later draft while
waiting. If the original is definitely refused, its text is retained beside that draft for
restoration or dismissal.

Drafts and unresolved offerings remain separate for each session when you visit another Altar
instrument. They last while this browser document stays open; reload or closing the tab warns
before losing them. This is not storage across browser restarts.

The shell's consent count opens **Conversations awaiting consent**. Choose a marked session to
review its requests; its rail and inspector show that session's count. Requests without an
available Bridge conversation remain in the global count and are reported in the chooser.

When arriving from Atlas, choose a linked conversation or use the conversation chooser. The
project return link stays available, including after opening a new séance. **Link this conversation
to…** opens a prefilled Atlas form for an explicit save; it does not link or send project context
merely because you navigated.

The Run strip beside the turn shows the Pattern revision, canonical status and current activity.
Keep its Run identity when you follow the result into another instrument. This strip is the
present Circle interface; the fuller workspace is described in the [Circle guide](circle.md).

If a consent card appears, read the pending request and choose one of its supported decisions.
The server validates the request, descriptor, reference and decision together. Your choice
applies to that pending request. Each Invocation has its own Sigil, Context boundary and
consequences; permission for another object, wider tools or a later effect needs its own
admission. Suggesting an action in conversation cannot authorize it.

## Read the result

When the Run settles, follow the strip's link to [Orb](orb.md) to inspect its evidence. A failed
or cancelled Run stays visible even when it has no corresponding settled agent turn. Your
admitted message may therefore appear in the conversation without an answer beside it.

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

Bridge carries forward recent, complete, settled turns. It selects the newest whole turns that
fit the configured turn and character budgets. A visible user row can precede settlement; it
becomes part of this retained history only with the settled agent turn. Full-session replay and
Archive retrieval are outside this history path.

??? info "How Bridge retains and restores a turn"

    Only a settled agent turn appends one complete Pydantic AI history unit. Bridge validates
    typed messages, normalizes provider hops to their owning LychD Run, and keeps a consent
    return paired with its original tool call. For a later Invocation it rebuilds the Stable
    Floor for the newly granted capability. Consent resume preserves the current call chain
    while fitting older settled turns to that grant's bounds.

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

## Two crossings still being designed

**Pin and Ask** would carry an authorized typed reference into a new Intent. Before admission, a preview would identify the reference, show what material would be included or summarized, disclose unavailable or redacted material, and state the permission involved. The Vessel would then reauthorize the request. Pinning a reference grants no retrieval or mutation authority.

**Propose in Loom** would turn selected conversation material into an attributed, inert charcoal Scroll candidate against a specified base Pattern revision. A future Spellweaver draft contract would have to validate it and publish a new revision before it could become executable work. The selection must become a typed handoff; copied prose or canvas coordinates alone cannot supply it.

Neither action is available yet. Follow their development through [Loom](loom.md) and the [delivery record](../../state-of-the-work.md#bridge-surface).

## Reading direction

The planned composition gives the conversation the widest readable area, keeps conversation
selection accessible, and discloses secondary metadata on demand. The offered text, exact Run
status, reply or explicit missing reply, and any consent or unresolved admission form one reading
sequence. The next draft remains distinct. A permission request shows its actual target and
scope beside its supported decisions; a disabled offering explains what must resolve and does
not imply that the draft is queued.

Returning from Orb should bring the reader to the originating Run without displacing a later
draft. New activity preserves the reader's place in older text, with a separate path to the
latest turn. Project origin, saved membership, and material included in model Context remain
different facts. The run strip supplies links rather than a second execution graph; a composed
Circle still requires its own delivered contracts.

Acceptance case: lose an offering's admission response, write a later draft, inspect another
instrument, and attend to consent in a different session. Return to the original session with
the same request identity and original text, the later draft intact, and correctly scoped
attention. Test unknown admission and accepted-Run consent independently; a mock must not suggest
two unrelated active offerings are permitted in one session. Browser restart recovery needs a
persistence contract beyond the current open-document state. These are [presentation
targets](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction), not a new queue, memory,
or recovery service.
