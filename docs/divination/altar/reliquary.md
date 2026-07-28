---
title: Reliquary
icon: material/archive-star-outline
---

# :material-archive-star-outline: Reliquary

**Purpose.** Reliquary names a **designed artifact-custody lifecycle**, not one of the current four
Altar instruments. It would let the Magus return to an output after its active Invocation has
passed: inspecting what it is, where it came from, who may retrieve it, and how long it may remain.

**Current boundary.** No `/reliquary` route exists. LychD can carry immutable `ArtifactRef`
metadata through the supported run boundary, but it does not upload or hold bytes, list artifacts,
authorize retrieval, prove provenance, export an output, or enforce retention. Artifact references
remain contextual until custody, retrieval, authorization, and retention earn a dedicated
lifecycle. [State owns the current Orb
boundary](../../state-of-the-work.md#orb-instrument) and the separate [artifact-reference
contract](../../state-of-the-work.md#artifact-reference-contract).

**Law.** Reliquary would be a presentation and lifecycle instrument, not another store. The
[Phylactery](../../sepulcher/phylactery/index.md) owns committed application records at supported
boundaries, and any future byte-custody adapter must earn an explicit authorization, provenance,
and retention contract. The [Oculus](../../sepulcher/extensions/oculus.md) owns evidence, the
[Weaver](../../sepulcher/extensions/weaver.md) owns the work that produced an output,
[Context](../../adr/21-context.md) owns temporary cognitive material, and the
[Mirror](../../sepulcher/extensions/mirror.md) owns identity continuity. A shelf may expose links to
those owners. It may not become them.

> _“Not everything cast from the fire becomes a relic. A relic is what can be named, traced,
> guarded, and returned.”_

## When an Output Becomes a Relic

A response is fleeting. A file is merely bytes. An artifact becomes a **relic** only when the body
can preserve enough relation to answer:

- What immutable identity names it—a digest, media type, size, and classification?
- Which Invocation, step, tool, model, or human act produced or altered it?
- Where are its bytes held, and what receipt proves that custody?
- Which principal may inspect, export, share, retain, or delete it now?
- Which derivations descend from it, and which source objects fed it?
- What retention law applies, and what evidence remains after lawful deletion?

The current `ArtifactRef` begins only the first of these relations. It can preserve metadata through
a run ledger. It does not make the referenced bytes retrievable, safe, or present.

## Relic Is Not Memory

Reliquary and Karma touch without becoming synonyms. A generated report, image, model card,
evaluation bundle, or failure archive may deserve durable custody while never becoming a prior for
future reasoning. **Karma** is selected past experience admitted into memory under its own
consecration and curation law. The [Mirror](../../sepulcher/extensions/mirror.md) may later bind
trusted Karma into identity; it must not treat every object on a shelf as character.

Likewise, the [Riddle](../../sepulcher/extensions/riddle.md) may measure an artifact, but storage
does not confer a passing verdict. The Oculus may preserve evidence about its production, but a
trace is not the artifact. Context may carry a reference into a later run, but the context window
is not custody.

## The Future Shelf Must Remain a Projection

A useful Reliquary should eventually project typed server-owned records as small, accessible
fragments: identity and classification first, provenance and authorization beside them, and
retrieval or retention acts only where the Vessel can validate them. On a narrow screen, each
record should stack rather than force a wide asset table.

No browser cache, generated preview, model-written URL, or client-side object may become the
canonical relic. The Vessel validates every request; the custody service returns bytes only under
current authority; the durable record preserves provenance without exposing secret material.

## Open the Relic Where It Appears

Artifact metadata may eventually open contextually from a Bridge result or the exact Orb evidence
record that cites it. That convenience would transfer neither custody to Bridge nor evidence
ownership to the artifact lifecycle. No full-record route exists today.

Where immutable artifact revisions and parent relations exist, the full instrument may offer:

- a lineage graph whose edges name their provenance record;
- comparison between exact source, branch, and result revisions;
- evaluation links owned by Riddle; and
- retention state and authorized retrieval or deletion actions.

Lineage gaps remain visible breaks. The client may not connect two revisions because their text
looks similar, treat a digest as complete provenance, or reconstruct an intermediate artifact that
was never retained.

A future **Return to Bridge** or **Pin and Ask** action creates a new Intent with a previewed,
currently authorized artifact reference. It does not copy a browser blob into canonical custody or
silently inject bytes, rendered text, or derived content into Context.

Until such custody exists, perform the one check that prevents a false offering:

> _[Read the artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract)
> before giving LychD an artifact-bearing Intent; do not treat the Reliquary shell as storage._
