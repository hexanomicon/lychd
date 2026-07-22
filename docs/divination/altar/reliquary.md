---
title: Reliquary
icon: material/archive-star-outline
---

# :material-archive-star-outline: Reliquary

**Purpose.** Reliquary is the intended Altar instrument for returning to an output after its active
Invocation has passed: inspecting what it is, where it came from, who may retrieve it, and how long
it may remain.

**Current boundary.** The `/reliquary` route now returns the full Altar shell, marks this instrument
as active, shows the shared pending-consent sigil, and renders an explicit unbuilt placeholder. It
does not upload or hold bytes, list artifacts, authorize retrieval, prove provenance, export an
output, or enforce retention. An Intent can carry immutable artifact metadata, but that reference
is not custody. [State owns the exact Reliquary
boundary](../../state-of-the-work.md#reliquary-instrument) and the separate
[artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract).

**Law.** Reliquary is a presentation and lifecycle instrument, not another store. The
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

Until such custody exists, perform the one check that prevents a false offering:

> _[Read the artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract)
> before giving LychD an artifact-bearing Intent; do not treat the Reliquary shell as storage._
