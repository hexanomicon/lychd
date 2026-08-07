---
title: Render
icon: material/movie-cog-outline
---

# :material-movie-cog-outline: Render

Render turns an accepted timeline into a deterministic local candidate. It owns reproduction and
validation of the presented bytes, not the claims or creative lineage behind them.

The render pins every input digest plus renderer, fonts, codecs, filters, colour settings, channel
layout, loudness target, caption format, command or project revision, and target profile. Probes
record duration, dimensions, frame rate, codec, color and audio facts, caption presence, checksum,
and declared tolerances.

Accessibility is part of the candidate, not release decoration. Captions retain their script and
timing lineage; contrast, legibility, flashing or motion hazards, audio intelligibility, language,
and channel-specific alternatives are reviewed against the declared audience. Automated probes
support that review but do not certify lived accessibility.

A renderer may have completed an output before acknowledgement was lost. The effect remains
**unknown** until the destination and checksum are reconciled; blind retry could create competing
outputs or hide a partial write. A stale input, missing font, non-deterministic dependency,
unsupported target, failed probe, or accessibility finding returns a failed render or correction
request.

An accepted render joins its script, timeline, claim, source, and asset manifests in
`EditorialPackage@1` and `PublicationCandidate@1`. The local candidate passes to
[Release](release.md); successful rendering grants no destination authority.
