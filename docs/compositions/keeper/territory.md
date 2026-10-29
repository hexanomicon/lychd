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

Before requesting an environmental change, record the conditions, source evidence, units,
observation freshness, validity and expiry, resource ceiling, uncertainties, and human-approved
bounds. Bind that environment need to its originating owner, subject, placement and profile
revisions, admission generation, and target zones/assets. A later profile or arrangement change requires review of whether the need still applies; these
references identify the requirements under review.

Once settled, the requirement can enter separately admitted [Homestead work](../homestead/utilities.md#meet-an-environment-request).
Keeper assesses the technical evidence returned in its exact `HomesteadEnvironmentResult@1`.
If one joint result must start and await that work, a Suite owns the coordination. Keeper's
assessment supplies neither controller credentials nor direct actuation authority, and local
controller safety takes precedence over the proposed husbandry condition.

## Finish with an assessment

The outcome is a committed assessment or proposed placement and environmental needs, including
unresolved suitability. Block or mark infeasible a request whose bounds cannot be supported.
Assessment does not execute relocation or prove a controller achieved a condition; confirmed
physical work returns through [care](care.md).

---

[Keeper](index.md) · [Composition portfolio](../index.md)
