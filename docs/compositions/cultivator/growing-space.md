---
title: Growing space
icon: material/greenhouse
---

# Growing space

A pot may be suitable for one culture and poorly understood for another. Keep the container,
growing medium, occupants, and the evidence behind suitability separately inspectable.

## Place and arrangement

`cultivator.assess_space@1` produces `CultivatorGrowingSpace@1`,
`CultivatorPlacement@1`, and `CultivatorEnvironmentNeed@1`.

A growing space may be a pot, bed, greenhouse compartment, or indoor grow container.
It records substrate or growing medium, batch and change history, and evidence about
drainage, light, and other relevant conditions. These are evidence fields, not universal
care recommendations. Unknown substrate or light cannot become fabricated suitability.

Placement records the culture's actual occupancy interval and count or density
estimates. A planned transplant does not change observed occupancy. Confirmed movement closes
the prior interval and establishes another while retaining culture identity; an uncertain move
keeps both the intended destination and the unresolved observation. Biological arrangement and assessed suitability belong
to Cultivator.

## Reviewed needs

An environment need binds its originating owner, exact subject, growing-space and placement
revisions, target zones/assets, profile revision, and admission generation to a condition, unit,
and reviewed desired interval. It carries freshness,
validity, expiry, resource limits, and supporting evidence. Review must distinguish
a desired range from a measured observation and preserve uncertainty.

[Homestead utilities](../homestead/utilities.md#meet-an-environment-request) may receive exact place, asset, or
controller references and the reviewed need. The infrastructure owner retains actual
control limits and actuation authority; Cultivator's need does not grant them.
Without that connection, human work and manual evidence still support assessment.
An exact `HomesteadEnvironmentResult@1` supplies technical evidence; Cultivator separately
assesses what the result establishes for the culture. A shared physical asset has one
infrastructure record, referenced rather than copied into this biological arrangement.

A mixed habitat may link [Keeper placements](../keeper/territory.md). Each Composition retains its subjects
and needs; neither silently overrides the other's requirements. Conflicting needs
require an explicit assessment outcome before action, including infeasible or unknown
where the evidence cannot support a coherent arrangement.

Return to [Cultivator](index.md).
