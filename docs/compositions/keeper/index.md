---
title: Keeper
icon: material/paw
---

# Keeper

A queen arrives in a test tube. Months of observations, feeding, and changes of accommodation
must remain attached to the same colony. Keeper preserves that history for animals and colonies,
from a household pet to a livestock group. Its identity is `keeper.husbandry`, revision `1`.
Pet and livestock purposes may overlap; neither determines a subject's entire record.

This Native Reference Composition is **Designed**. The [portfolio delivery
record](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery status; these
pages establish no implemented tables, migrations, or registrations.

## Enter through the work

| Reader journey | Pinned Pattern | Primary records |
| --- | --- | --- |
| [Identify a subject and preserve observations](subjects.md) | `keeper.record_subject@1` | `KeeperSubject@1`, `KeeperObservation@1`, `KeeperCareProfile@1` |
| [Assess accommodation and placement](territory.md) | `keeper.assess_territory@1` | `KeeperTerritory@1`, `KeeperPlacement@1`, `KeeperEnvironmentNeed@1` |
| [Review changing life requirements](lifecycle.md) | `keeper.review_lifecycle@1` | `KeeperLifecycle@1` |
| [Propose feeding and request supplies](feeding.md) | `keeper.plan_feeding@1` | `KeeperFeedingPlan@1`, `KeeperSupplyNeed@1` |
| [Record care and collected material](care.md) | `keeper.record_care@1` | `KeeperCareEvent@1`, `KeeperCareResult@1`, optional `KeeperYieldReceipt@1` |

These five Patterns are independently invocable. Each Invocation ends with a committed observation or assessment,
proposed plan, confirmed care result, refusal, blocked or infeasible result, partial result,
cancellation or interruption, or an explicitly unknown physical effect. Continuing subject
history does not create an endless Run. [Workflow law](../../adr/28-workflow.md) governs execution;
a proposal grants no authority to perform it.

## Admission, privacy, and recovery

Admission identifies the responsible keeper, custody and permissions, exact subject, placement and
care-profile revisions, the requested work, observe/advise/record posture, hazards and resource
limits, and permitted disclosures. Uncertain identity or suitability must
remain visible; insufficient evidence can stop a plan. Keeper supplies no clinical diagnosis or
treatment authority. Human-approved bounds and separately admitted owners constrain physical work.

Records belong in local PostgreSQL under [persistence law](../../adr/06-persistence.md). These
logical contracts prescribe neither a physical SQL schema nor a Markdown shadow database.
Retain relational links, record and profile versions, authored observation time and recording
time, actor and source, units and uncertainty, permitted attachment references, idempotency
identity, and correlation. Corrections preserve earlier claims; current views derive from history.
The same event identity with changed contents requires an explicit correction or refuses as a
conflict. Subject, placement, lifecycle, plan, and event references remain independently versioned;
an edit to one never silently changes a previously admitted action.

[Homestead](../homestead/index.md) owns optional infrastructure, supply custody, and commissioned
effects; [Cultivator](../cultivator/index.md) owns plants and cultivated fungi even in a shared
enclosure. Neither is required to record manual animal care. The [stewardship handoff](../products-and-suites.md#homestead-keeper-and-cultivator)
defines when exact references suffice and when a Suite must coordinate live work.

Minimize access to addresses, human photographs, and veterinary documents. Export and deletion
respect custody and retention. Deletion stops schedules and disclosure; pending care effects need
reconciliation or handoff before authorized erasure. Deleting a record never means abandoning or
releasing an animal. After restart, recover the last settled result and outstanding effects;
lost acknowledgments block blind retries.

## Falsifying fixture

The required synthetic fixture is a design test, not a claimed run. Begin a colony with uncertain
identity and counts in a tube; add an arena, then leave a move unconfirmed. Review seasonal mode
independently of placement. Duplicate a feeding event and lose its acknowledgment; reconcile exact
supply-use events without inventing consumption. Reuse the model for a dog with a pet role and a
hen group with a collected-egg receipt. Restart, correct an observation, export, and request
deletion. Fail the design if it duplicates an effect, assumes the move succeeded, collapses life
axes, or erases unresolved custody obligations.

---

[Composition portfolio](../index.md)
