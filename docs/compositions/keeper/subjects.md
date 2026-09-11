---
title: Keeper subjects
icon: material/fingerprint
---

# Keeper subjects

A colony remains the same subject when its accommodation changes. Begin with
`keeper.record_subject@1` to establish a durable identity and attach evidence, producing
`KeeperSubject@1` and `KeeperObservation@1`.

## Establish identity without inventing certainty

A subject may be an individual, pair, group, or colony. Record its stable identifier, responsible
keeper and permissions, acquisition origin, species identification with confidence and care-profile reference,
age estimates, count intervals, membership and lineage, purpose roles, and status history. Pet and
livestock are non-exclusive roles. An uncertain identification remains uncertain when a later
observation is recorded.

An ant colony can reference an individually identified queen while keeping worker and brood
counts aggregate. Do not manufacture individual identities from an estimated count. Explicit
split, merge, and transfer events preserve predecessor and successor links, custody changes, and
effective times. Corrections cannot silently merge subjects or rewrite lineage.

For example, subject `colony-a` can link queen `queen-a`, placement `placement-1` in territory
`tube-t1`, a lifecycle review, and separate feeding and observation events. `placement-2` can later
refer to `formicarium-f1` without replacing `colony-a`. These are illustrative record keys, not
deployed database rows. The colony's current view joins those references; it is not one journal
entry whose latest text replaces the previous account.

## Keep the care profile attributable

`KeeperCareProfile@1` is Keeper's own versioned husbandry profile: a stable profile id and revision,
applicable species or group, source references and dates, reviewed life/seasonal conditions,
care requirements with units and bounds, excluded or uncertain cases, and reviewer. It can be
recorded alongside the subject through `keeper.record_subject@1`; accepting source material and
admitting its use for a specific subject remain separate judgments. A species label does not
select an unreviewed generic care schedule. Plans pin the applicable profile revision, and a later
revision identifies which active plans require review without rewriting previous care.

## Preserve the evidence

Each observation separates what was seen from interpretation, with effective and recorded times,
actor or source, units, uncertainty, applicable profile revision, and permitted attachment
references. Idempotency identity and correlation distinguish retries from new observations.
Amend an older claim through a linked correction; derive the current snapshot without erasing the
claim it replaces.

Shared enclosure flora and fauna need not fit an exclusive taxonomy. Keeper records animals and
their husbandry relationships; it does not put live animals into Homestead's stock ledger.

## Finish with a record

The outcome is a committed subject or observation, a partial record with named gaps, or a stopped
result explaining missing evidence or permission. Registration neither certifies species identity
nor authorizes acquisition, movement, or care. Export and deletion follow the custody and recovery
boundary in [Keeper](index.md).

---

[Keeper](index.md) · [Composition portfolio](../index.md)
