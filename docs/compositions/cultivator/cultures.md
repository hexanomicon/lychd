---
title: Culture records
icon: material/seed
---

# Culture records

A cutting can start a new culture while its parent continues growing. A move to a larger pot
preserves the existing plant. Culture records keep those two kinds of change distinguishable.

## Identity and lineage

`CultivatorCulture@1` represents a plant individual, sowing or planting batch, bed
cohort, perennial, or cultivated fungi culture. A stable identifier survives a change
of name, purpose, placement, or responsible person. Record species and cultivar when
known; an unknown identification remains explicit.

The record carries name, source and provenance, responsible people, profile revision,
origin and lineage, current count or quantity intervals, and exact lifecycle and
placement references. Quantity includes units and uncertainty; an estimate is not an
exact census.

Propagation, division, and explicit group splits or merges retain parent references
and their evidence. A cutting may establish a linked child culture. Transplanting or
moving an existing plant preserves its identity. Repeated harvest does not create
replacement cultures or silently terminate the source.

## Pin the growing profile

`CultivatorGrowingProfile@1` is Cultivator's owner-qualified profile record, with stable identity
and revision, applicable species/cultivar or culture class, attributed sources and dates, reviewed
cycle and tending requirements with units and bounds, exclusions, unresolved cases, and reviewer.
`cultivator.record_culture@1` may record it alongside a culture. Accepting a source does not make
every recommendation applicable to that culture and growing space. An active plan pins a reviewed
revision; a replacement identifies which plans require fresh review. Ornamental, food, and fungi
profiles share record discipline without acquiring one universal cycle or care schedule.

## Evidence graph

`cultivator.record_culture@1` produces culture records and
`CultivatorObservation@1` evidence. Observed symptoms, interpretations, and expert
findings remain distinguishable. An observation records its subject, effective time,
recorded time, source or actor, evidence references, units, uncertainty, and applicable
profile revision.

The same evidential discipline applies throughout the composition: preserve exact
parent and artifact references, correlation identifiers, and deduplication identity.
A late report keeps its actual effective time. A correction retains the earlier claim
and identifies what it supersedes; the latest view is derived from retained claims,
rather than overwriting history.
Replaying an event identity with different contents is a conflict unless admitted as an explicit
linked correction. Culture, placement, cycle, plan, and work revisions remain independent; changing
one cannot silently amend an already admitted action.

Placement, cycle, tending, work, and harvest records join through exact references.
No helper infers a missing collection, completed action, or healthy state from a gap
in that graph. Purpose-scoped media references carry retention context and access
boundaries alongside the evidence they support.

Return to [Cultivator](index.md).
