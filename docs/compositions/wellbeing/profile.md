---
title: Profile
icon: material/account-heart-outline
---

# :material-account-heart-outline: Profile

Profile keeps the reviewed human constraints under which Wellbeing may plan. It is private input,
not a diagnosis or a permanent claim about the person.

`wellbeing.profile@1` creates an immutable profile revision from restrictions, preferences, time,
equipment, enabled modes, consent, and privacy choices. Relaxing a hard restriction requires a
confirmed successor profile. Records distinguish `user_entered`, `source_imported`,
`model_proposed`, `deterministically_derived`, and `user_confirmed`; one generic health blob owns
none of them.

Storage and inference are local by default. Remote providers, lookup, reminders, retained media,
calorie or weight features, imports, sharing, export, or research use require revocable,
purpose-specific consent. Journals, measurements, symptoms, diagnoses, medication, clinical
records, movement history, and genetics never enter [Homestead](../homestead/index.md), shop
queries, catalogues, carts, providers, or merchant messages.

`wellbeing.export@1` creates only the approved export. `wellbeing.delete@1` fences admission,
disables schedules, drains atomic work, removes permitted records and derivatives, verifies
absence, and leaves a content-free receipt. Restored backups reapply tombstones before reopening
data.

Return to [Wellbeing](index.md).
