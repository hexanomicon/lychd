---
title: Keeper territory
icon: material/map-marker
---

# Keeper territory

Observed occupancy, accessible space, and suitable accommodation answer different questions.
`keeper.assess_territory@1` records their relationship through `KeeperTerritory@1`,
`KeeperPlacement@1`, and `KeeperEnvironmentNeed@1`.

## Describe the arrangement

For a generic ant-colony data model, colony A starts in test tube T1. Record the tube's dimensions,
material, setup condition, and nest zone. Later add arena A1 and formicarium F1 with their zones
and connections. Record where ants were observed, which connections permit access, and the
evidence supporting a suitability assessment separately. This example establishes no species
temperature, diet, diapause, or other care rules.

A proposed move names its source and destination and remains proposed until confirmed. A
confirmed move retains the same colony identity. Missing acknowledgment leaves placement effects
unknown; it does not establish arrival or justify repeating the move.

Each territory has an identity and arrangement revision; each placement links a subject to zones,
with proposed and observed occupancy intervals. Setup history includes water provision, substrate
or lining, ventilation, access barriers, cleaning, and observed condition where relevant to the
profile. Missing measurements stay unknown. A single colony may occupy connected zones, and one
enclosure may hold several separately identified subjects.

Keeper owns the husbandry arrangement even without sensors or Homestead. An actual device or
enclosure asset may reference [Homestead](../homestead/index.md); reuse its infrastructure record
instead of copying it. Shared enclosure relationships can include flora and fauna.

## Bound environmental requests

An environment need names its originating owner, subject, placement and profile revisions,
admission generation, target zones/assets, requested conditions, source evidence, units,
observation freshness, validity and expiry, resource ceiling, uncertainties, and human-approved
bounds. A change of profile or arrangement requires reviewing the need's applicability.

A settled requirement can enter separately admitted [Homestead work](../homestead/utilities.md#meet-an-environment-request).
Its exact `HomesteadEnvironmentResult@1` returns technical evidence for Keeper's assessment.
Starting and awaiting that work within a joint result requires a Suite. Keeper's assessment
supplies no controller credentials or direct actuation authority; local controller safety takes
precedence over a proposed husbandry condition.

## Finish with an assessment

The outcome is a committed assessment or proposed placement and environmental needs, including
unresolved suitability. Block or mark infeasible a request whose bounds cannot be supported.
Assessment does not execute relocation or prove a controller achieved a condition; confirmed
physical work returns through [care](care.md).

---

[Keeper](index.md) · [Composition portfolio](../index.md)
