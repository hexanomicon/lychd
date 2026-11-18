---
title: Release
icon: material/publish
---

# :material-publish: Release

The candidate can remain local forever and still be finished. Release begins when the editor chooses to put those exact bytes before an external audience, with a destination and an attributable approval.

Broadcast owns release and correction of its editorial project. A separate Reach correspondence or
standalone social post need not become a Broadcast project; any use of a settled Broadcast
candidate remains subject to its admitted use boundaries.

## Review before effect

Source support, claims, voice/likeness authority, privacy/Portal use, accessibility, asset admission, and render checks supply their own receipts. Publication additionally binds candidate digest, destination, audience, visibility, schedule, disclosures, cost, and approving Principal.

Uploading a draft and publishing publicly are separate effects over the same
`PublicationCandidate@2`. Both `broadcast.publish_draft@2` and `broadcast.publish_public@2`
pin the idempotency key, payload and request digests, destination identity, reconciliation
lookup and `PublicationReceipt@1`.

Suppose the destination accepts the upload and the connection drops before the receipt returns.
Record the outcome as **unknown**. Use the pinned lookup to find out whether those bytes arrived.
Repeating the upload through a browser could create a second copy. A retry must still use the
authorized effect.

After release, a correction or removal must still be attributable to the publication it changes. `broadcast.correct_publication@2` creates a forward correction. `broadcast.takedown@2` requests removal while preserving the publication and receipt history. If a platform refuses, authority expires, the candidate changes, remote state remains uncertain, or a gate fails, return that exact blocker.

Recovery begins by resolving the pinned Pattern, source, handoff, script, timeline, renderer, adapter, and receipt revisions. Their retention needs differ: snapshots, rejected renders, candidates, destination receipts, and analytics retain separate policies. Deletion therefore inventories derivatives, requests authorized remote removal, and preserves a content-free receipt. Feeds and caches may still retain copies.

## Proving package

The proposed first test ends before any platform call. Build a three-to-five-minute piece from
frozen sources and linked claims. Trace the article or script into local narration, transcribe
the narration back for comparison, and place the admitted visuals, music, timed language,
picture sound and captions on an explicit timeline. Exercise a bounded repair and a deterministic
render. The outputs to inspect are `EditorialPackage@2` and `PublicationCandidate@2`. The
[Portfolio delivery record](../../state-of-the-work.md#composition-portfolio-delivery) identifies
which application Patterns can run today.

Return to [Broadcast](index.md), or inspect the local candidate in [Render](render.md).
