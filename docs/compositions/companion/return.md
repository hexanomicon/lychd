---
title: Return
icon: material/sync
---

# :material-sync: Return

The connection drops after the utterance. Reconnect looks up Companion's settled handoff or presentation receipt by Principal and utterance identity; it does not resend audio, replay Intent, deliver expired commands, or take over the destination's work.

If an authorized terminal-result reference has already settled, a fresh presentation action can show or speak it. An offline recording is instead a short-lived draft requiring review after reconnect, never an automatically queued effect.

Reconnect preserves [Companion's control, speech, and custody boundaries](index.md#boundaries). Companion also retains local disclosure and interaction state. Tether supplies reachability; Ward still proves application, device, Principal, scopes, and object authority. Spellweaver, Workers, and Phylactery keep admission and Run delivery; the destination keeps its domain result and effects. The client carries no provider, database, workflow, or host-lifecycle credential.

Reconnection reapplies the original frame-admission rules and the session's separately admitted stop, presentation, privacy, and retention policy; it widens none of them. Enrollment revocation and destination export/deletion remain separate owner actions.

## Client-local interaction

The first client-only profile holds text drafts and observed presentations in memory. It handles
no recording bytes, credentials, transport, or authoritative Companion records. Every local session
has a fresh generation; restarting the process discards this local state. Native session and result
identities remain opaque inputs to a future authorized adapter.

Give each draft a fresh local identity and fixed deadline, using a positive caller-supplied
lifetime and monotonic clock. Editing, review, and reconnect do not renew it. Both review and
submission check the time, and equality with the deadline means expired.

A faulty clock must not revive the draft. Invalid or regressed time refuses eligibility without
moving the retained clock or deadline; equal readings are valid. Disconnection still invalidates
review, and local stop and cancel remain usable despite a clock fault. This profile supplies no
default retention lifetime and cannot prove elapsed time when its supplied clock is faulty.

Review binds the exact visible draft revision and connection generation. Editing or losing the
connection invalidates it; reconnect requires fresh review followed by a separate explicit submit.
Submission emits only a local request to submit that reviewed snapshot, correlated to its local
draft identity. It establishes no admission or settled handoff. That draft then becomes terminal:
editing, duplicate submit, reconnect, or a lost response cannot rearm it. Another utterance needs a
fresh draft identity. At most one signal follows along the accepted local state transitions; this
is no network deduplication or process-restart idempotency guarantee.

Bind connection updates to the expected current connection identity so an older generation cannot
change the current connection. Asynchronous observations similarly name the exact local session
generation and applicable draft, request, presentation, and playback-attempt identities. Stale
observations change neither current state nor its clock.

A presentation request accepts at most one terminal text observation; another result needs a
fresh request identity. That text is an opaque projection, not a client-minted Companion receipt.
Keep a playback request separate from observed start, completion, failure, or local stop. Late
callbacks cannot reopen a stopped attempt or replace a newer presentation.

Stopping speech closes local playback while keeping the interaction open. Cancelling the local
session closes interaction and invalidates its callbacks. Neither control cancels a destination
Invocation, and synthesis or playback failure preserves the observed committed text.

For the initial Android screen, the person chooses a positive whole-second lifetime before
starting a draft; there is no prefilled lifetime. Clock or arithmetic failure refuses eligibility
without replacing the existing draft. Configuration recreation within the same process preserves
the current session and deadline. Process death restores neither a draft nor unsubmitted form input.

The screen projects expiry from valid monotonic observations even while idle. A stale or regressed
observation cannot revive eligibility or affect a replacement session or draft. Expiry and local
cancellation do not claim erasure of retained text. Review and Submit remain unavailable while
disconnected; a simulation switch or device connectivity observation supplies no native admission.

## Proving the route

A fifteen-second local Android fixture uses distinct tunnel/application keys, local recognition, typed handoff sink, pre-settled text result, optional synthesis, ephemeral audio, durable text, and utterance-id reconnect. Prove no destination wait/cancel, stolen-tunnel-key refusal, revoked app key, replay, object guessing, transcript injection, disconnect, expiry, and locked-device playback. No public proxy, ambient capture, mobile approval, administration, or medical promise enters it.

Return to [Companion](index.md), or follow a new [Utterance](utterance.md).
