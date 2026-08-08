---
title: Edit
icon: material/timeline-text-outline
---

# :material-timeline-text-outline: Edit

Edit assembles approved words, visual material, and sound into the final editorial timeline. This
is where audiovisual relation becomes Broadcast's judgment rather than an implicit side effect of
either producing craft.

## Admit the assets

Each `VisualAssetBundle@1` and `SonicAssetBundle@1` enters by exact digest, semantic role,
constraints, provenance, use boundary, validators, findings, and approval. Broadcast records its
own asset-admission receipt. It cannot amend Voidlight or Riffmaw lineage, and a producer cannot
publish through an asset request.

`VisualAssetRequest@1` asks [Voidlight](../voidlight/) for a visual role, target profile, timing,
constraints, source or likeness requirements, and request digest. `SonicAssetRequest@1` asks
[Riffmaw](../riffmaw/) for music, voice, effects, or ambience under exact words, timing, authority,
and request digest. Neither handoff shares a Sigil, secret, provider session, approval, or
downstream authority.

## Own the timeline

The edit binds script spans, narration, captions, storyboard decisions, visual revisions, sonic
revisions, and transitions to one explicit timebase. A `SyncCueMap@1` can expose sonic events;
Broadcast decides the final placement and cut. Retime, replacement, or changed words create a new
timeline revision and stale affected approvals.

Review can return attributed findings against pacing, claim-to-image relation, continuity,
caption timing, legibility, loudness balance, or the target profile. `broadcast.review_package@1`
does not change accepted material. `broadcast.revise_from_correction@1` admits one bounded forward
repair. A mismatched digest, timebase, claim revision, or use boundary produces a finding or
refusal rather than a best-effort edit.

Generative video editing remains an upstream visual effect even when it accepts a source clip.
Broadcast may request a new Voidlight revision, but it does not hide stochastic regeneration
inside a deterministic trim. FFmpeg and equivalent pinned tools may execute probing, trim,
concat, retime, overlay, mix, mux, and encode operations under this timeline; the executable does
not own editorial judgment or silently approve a generated visual or sonic candidate.

The accepted timeline passes to [Render](render.md); it contains no permission to publish.
