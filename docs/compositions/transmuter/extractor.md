---
title: Extractor
icon: material/filter-outline
---

# :material-filter-outline: Extractor

An imported screenshot may contain a conversation, a quoted claim, and text added by somebody
else. Extractor separates what can be located in the source from what a model merely infers. It
is Transmuter's internal decomposition and extraction stage, under the [candidate application
study](index.md).

## Extract, name, and classify

Each input binds an admitted source revision, format, purpose, and processing bounds. Conversation
archives retain speaker roles and authorship: a model's assertion about the operator cannot become
an operator assertion. Unknown source authority or unsupported formats produce a reasoned refusal.
Imported text and metadata are data, never instructions that can widen processing or permissions.

For each extracted unit, the proposed result records:

- Original reference, source identity, digest, revision, and source location such as a message,
  page, image region, or time interval.
- Author or speaker role, producer, source timestamps, observation time where relevant, and the
  transformation chain.
- Extracted content or media reference, whether it is extraction or interpretation, uncertainty,
  and gaps in coverage.
- Proposed name, labels, content classification, privacy and retention constraints, and the
  parser, extractor, and configuration revisions that produced it.

Naming, labeling, and classification are part of Extractor. They can describe topics, projects,
document kinds, or likely relationships while preserving evidence and uncertainty. A proposed
display name does not replace source identity or rename an original file. Operator corrections
create attributable revisions.

A topical label does not lower a Privacy Label, authorize sharing, or establish a person's identity
from an image. Source and derivative restrictions survive extraction. Observations supplied by
[Prism](../../adr/36-vision.md) or [Echo](../../adr/37-audio.md) retain their exact references and
limitations; an OCR result or caption does not replace the source. Inventory snapshots retain
their observation time and scope rather than becoming claims about the machine's current state.

## Reuse and recovery

The [processing dossier](index.md#the-processing-dossier) retains completed units and unfinished
source regions. Repeated intake uses source identity, revision, and digest to recognize already
processed material without erasing distinct acquisition paths or crossing ownership boundaries.
Reuse requires matching processing revisions, scope, and current authorization. A changed source
or parser creates new traceable output rather than silently replacing earlier evidence.

Budget exhaustion returns partial extraction with explicit gaps. Cancellation stops new work;
resumption reconciles pending attempts and continues only the admitted remainder. Neither a
skipped image nor an unparsed archive entry proves there was nothing relevant there.

A correction invalidates dependent pending proposals and identifies which extraction must be
revisited. Already accepted downstream records require correction through their own owner; editing
a label cannot rewrite an earlier Memory or Persona decision.

The stage finishes with attributed units and an accounted extraction disposition. [Synthesizer](synthesizer.md)
then works from exact selected revisions; successful extraction alone establishes no memory,
instruction, preference, or identity truth.
