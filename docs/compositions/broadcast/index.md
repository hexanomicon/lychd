---
title: Broadcast
icon: material/broadcast
---

# :material-broadcast: Broadcast

Broadcast turns admitted sources and creative assets into a publication candidate whose claims,
words, voice, captions, picture sound, and cuts remain traceable. The editor can approve, correct,
or refuse the work before any platform receives it.

| Field | Reference contract |
| --- | --- |
| **Identity** | `broadcast.studio` revision `3` |
| **Principal Pattern** | `broadcast.build_local_package@2` |
| **Begins with** | frozen sources, an editorial brief, a target profile, and admitted visual, music, timed-language, and picture-sound assets |
| **Can return** | local `EditorialPackage@1` and `PublicationCandidate@1`; a receipt only after a separate release effect |
| **Stops before** | unattended publication, engagement farming, borrowed asset authority, or unreviewed egress |

Revision `3` supersedes the Designed-only `broadcast.studio` revision `2`, and principal Pattern
revision `2` supersedes `broadcast.build_local_package@1`: explicit timed-language and
picture-sound handoffs materially change the score. Neither older design was registered or run, so
there is no executable migration; historical references retain their old meaning.

## The work

- [Sources](sources.md) freezes evidence and binds factual claims to exact spans.
- [Script](script.md) owns the canonical article, narration, and formatted words.
- [Picture-Bound Sound](sound.md) owns effects, foley, room tone, and ambience whose meaning and
  acceptance depend on the locked picture and editorial purpose.
- [Edit](edit.md) admits visual, music, timed-language, and picture-sound bundles and assembles
  the editorial timeline.
- [Render](render.md) produces a deterministic, accessible local candidate.
- [Release](release.md) governs review, publication effects, correction, takedown, and recovery.

Broadcast retains canonical source words and claims, picture-bound sound, editorial judgment, and
destination receipts. [Voidlight](../voidlight/) retains visual/VFX lineage;
[Riffmaw](../riffmaw/) retains music and musical-production lineage; and
[Language Edition](../language-edition/) retains each admitted timed-language edition. An adapter can deliver an
approved payload but has no editorial authority.

Related: [Workflow](../../adr/28-workflow.md) · [Vision](../../adr/36-vision.md) ·
[Audio](../../adr/37-audio.md) · [Composition portfolio](../index.md)
