---
title: Broadcast
icon: material/broadcast
---

# :material-broadcast: Broadcast

Broadcast turns admitted sources and creative assets into a publication candidate whose claims,
words, voice, captions, and cuts remain traceable. The editor can approve, correct, or refuse the
work before any platform receives it.

| Field | Reference contract |
| --- | --- |
| **Identity** | `broadcast.studio` revision `2` |
| **Principal Pattern** | `broadcast.build_local_package@1` |
| **Begins with** | frozen sources, an editorial brief, a target profile, and admitted visual and sonic assets |
| **Can return** | local `EditorialPackage@1` and `PublicationCandidate@1`; a receipt only after a separate release effect |
| **Stops before** | unattended publication, engagement farming, borrowed asset authority, or unreviewed egress |

## The work

- [Sources](sources.md) freezes evidence and binds factual claims to exact spans.
- [Script](script.md) owns the canonical article, narration, and formatted words.
- [Edit](edit.md) admits visual and sonic bundles and assembles the editorial timeline.
- [Render](render.md) produces a deterministic, accessible local candidate.
- [Release](release.md) governs review, publication effects, correction, takedown, and recovery.

Broadcast retains editorial judgment and destination receipts. [Voidlight](../voidlight/) retains
visual lineage; [Riffmaw](../riffmaw/) retains music, voice, effects, ambience, and mix lineage. An
adapter can deliver an approved payload but has no editorial authority.

Related: [Workflow](../../adr/28-workflow.md) · [Vision](../../adr/36-vision.md) ·
[Audio](../../adr/37-audio.md) · [Composition portfolio](../index.md)
