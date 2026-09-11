---
title: Keeper feeding
icon: material/food
---

# Keeper feeding

Food removed from storage is not proof that an animal consumed it. `keeper.plan_feeding@1`
produces a proposed `KeeperFeedingPlan@1` and any `KeeperSupplyNeed@1`, preserving that distinction.

## Propose from reviewed requirements

Tie a plan to its subjects, current life-state evidence, source-reviewed [care profile](subjects.md#keep-the-care-profile-attributable),
revision, and review window. Keep quantities, units, uncertainties, and exclusions explicit. These
contracts prescribe no generic food or clinical diet. Missing applicable evidence can block the
plan; a proposed substitution requires Keeper review before changing it.

Consult exact Homestead `SupplySnapshot@1` and `ProvisionResult@1` references for stock and
availability. A supply need binds its originating owner and revision, and discloses only necessary
product traits, quantity and units, exclusions, purpose, validity/expiry, privacy class, and unknowns.
Raw husbandry histories and veterinary journals do not accompany a
stock request. Availability does not certify husbandry suitability.

## Reconcile distinct evidence

Record offered or delivered quantities separately from observed consumption, leftovers, and
disposal. Each has its own source, time, units, and uncertainty; unknown consumption stays unknown.
Confirmed feeding work is recorded through [care](care.md).

Reconcile stock changes using exact supply-use event identifiers. Duplicate delivery of the same
event must not remove stock twice or create a second feeding. An amount removed from stock cannot
automatically become an amount consumed. Lost acknowledgment requires reconciliation before a
physical retry; a ledger correction alone cannot settle whether feeding occurred.

## Finish with a proposed plan

Return a plan and bounded supply needs, or a partial, refused, blocked, or infeasible result.
Execution needs human confirmation or a separately admitted owner. Close the invocation when its
result is recorded; the plan's review window does not keep it open.

---

[Keeper](index.md) · [Homestead](../homestead/index.md) · [Composition portfolio](../index.md)
