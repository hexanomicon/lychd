---
title: Scavenger
icon: material/magnify
---

# :material-magnify: Scavenger

Scavenger turns one bounded hunt through listings and sellers into an evidence-backed acquisition
decision. A RAM stick on Bazoš, a used machine, and a home are not the same object, but they share
one campaign spine: state the need, observe a finite market, keep unknowns visible, compare what the
evidence supports, negotiate inside a closed envelope, and stop before authority runs out.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `scavenger` revision `1` |
| **Principal Pattern** | `scavenger.plan_hunt@1` |
| **Application begins with** | A revisioned subject profile, concrete need, known inventory, budget, deadline, region, evidence standard, source policy, and autonomy ceiling |
| **Application can return** | A durable hunt, evidence-bound shortlist, seller thread, negotiated outcome, commitment record, expected parcel, inspection outcome, or human diligence packet |
| **Application stops before** | Unbounded scraping, spam, false identity or leverage, hidden criteria changes, professional certification, unapproved commitment, payment, deposit, signature, or settlement |

Scavenger owns hunts, criteria, observations, evidence, rankings, seller threads, offers,
reservations, commitments, parcels, inspections, and diligence packets. Scout adapters own bounded
acquisition and interaction receipts. The Magus owns exceptions, private disclosure, final
commitment, payment, acceptance, dispute, and every property transaction. A Mind may extract,
draft, rank, and explain; deterministic tools own hard predicates, money, caps, route arithmetic,
compatibility, effect identity, and state transitions.

Its other Patterns are `scavenger.observe_market@1`, `scavenger.qualify_candidate@1`,
`scavenger.rank_candidates@1`, `scavenger.negotiate@1`, `scavenger.commit@1`, and
`scavenger.receive@1`.

## One hunt, several subjects

A subject profile is a versioned rule set inside Scavenger, not another Composition and not a
source adapter. It fixes the typed facts, hard gates, evidence tiers, scoring inputs, permitted
effects, and finish condition for that kind of hunt.

| Profile | Distinct judgment | Revision-one consequence |
| --- | --- | --- |
| **Bazaar** | identity, condition, attributable seller claims, landed cost, and bounded negotiation for Bazoš-style listings | terms, one approved COD commitment, expected parcel, inspection, dispute, or refusal |
| **Technology** | exact CPU, board, BIOS, cooling, memory, GPU, storage, case, PSU, firmware, and connector compatibility | the Bazaar consequence only after compatibility and evidence are freshly revalidated |
| **Property** | transaction type, area, rooms, locality, route and amenity observations, listing contradictions, and professional questions | ranked shortlist and diligence packet; no contact, viewing, offer, reservation, deposit, signature, or payment |

Selecting a profile cannot activate a source, disclose a private anchor, widen money, or grant an
effect. One hunt may pin only the profiles it actually needs; a technology profile can refine a
Bazaar subject, while property rules never leak into hardware or parcel judgment.

## Need to decision

1. `scavenger.plan_hunt@1` records the subject, desired outcome, existing inventory, hard criteria,
   weighted preferences, budgets, deadlines, evidence tier, delivery or travel semantics,
   disclosure policy, and Watch, Concierge, or fully pinned Bounded Autopilot mode.
2. `scavenger.observe_market@1` admits finite source snapshots, normalizes and deduplicates them,
   retains retrieval time and source claims, and coalesces scheduled observations instead of
   building a backlog.
3. `scavenger.qualify_candidate@1` applies profile hard gates before preferences. `false` rejects,
   `true` admits, and `unknown` remains reviewable; a model cannot invent an address, fee, area,
   socket, clearance, firmware, condition, serial, stock state, or seller fact.
4. `scavenger.rank_candidates@1` orders only eligible candidates using declared weights and dated
   evidence. It exposes known utility, a conservative lower bound, an upper bound containing the
   unknown weight, the tie-breaks, and every input revision.
5. `scavenger.negotiate@1` may ask only approved questions or make offers inside one immutable
   envelope. Refusal, opt-out, abuse, silence, sale, changed subject, changed payment rail, failed
   evidence, expiry, or exhausted caps closes automatic messaging.
6. `scavenger.commit@1` freshly validates subject, evidence, terms, budget, exposure, authority,
   delivery method, and permitted disclosure before one effect. Property revision one is
   ineligible for this Pattern.
7. `scavenger.receive@1` compares an expected parcel with carrier, tracking, amount, identity, and
   package notes, then records acceptance, rejection, dispute, return, or loss. COD proves neither
   contents nor condition.

For comparable candidates, the projection remains inspectable:

```text
eligible      = all mandatory predicates are supported
known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

Price is an attributable interval across dated retail or listing observations, condition,
warranty, age, bundle value, fees, and uncertainty—not an invented universal fair price. A route
observation proves access at one time, not title, structural condition, financing, insurance,
future development, or final transaction cost.

## Sources, messages, and private anchors

Each Scout profile fixes permitted origins and paths, user agent, pacing, concurrency, page and
byte caps, cache and expiry, policy and robots decision, selectors, fixtures, session needs,
CAPTCHA handling, and a kill switch. A `bazos.sk` adapter can observe or carry an admitted message;
it cannot choose the subject, pass a profile gate, negotiate by default, or own the hunt.

A negotiation envelope pins the candidate, questions, evidence needs, opening and all-in ceilings,
currency, delivery constraints, concessions, truthful automation disclosure, prohibited claims,
caps, expiry, and stop signals. Every send has a stable effect identity and a redacted receipt. A
missing acknowledgement becomes `unknown_send`; restart parks the thread and can neither resend
nor create a second commitment until reconciliation establishes what happened.

School, work, family, health, routine, address, and phone data receive least-data handling. Sources
and prompts see only the coarse region, opaque anchor or delivery reference, or derived observation
required by the admitted step. Only a deterministic sender may resolve approved delivery fields
after fresh authority. Seller messages, evidence, serial fragments, and private anchors are not
memory or training material.

## Custody and return

Hunts, source snapshots, criteria, profile revisions, score inputs, seller claims, evidence,
messages, approvals, sends, offers, commitments, parcels, inspections, disputes, and diligence
questions remain separately attributable. Checkpoints pin Pattern, source, selector, catalogue,
parser, template, and policy revisions; they never replace the campaign or inbox.

Restart reuses pinned observations and idempotency keys. Changed or missing source state parks the
occurrence rather than authorizing contact or consequence. Export separates private anchors,
messages, evidence, and delivery data. Deletion disables schedules and sessions, inventories open
commitments, parcels, and disputes, revokes profile access, removes permitted local records and
artifacts, and does not claim to erase a seller's copy.

## Proving the hunt

Use network-disabled Slovak fixtures for one Bazoš RAM hunt and one two-room property hunt. Prove
DDR4/DDR5 and SODIMM/UDIMM rejection, dated price intervals, bounded seller replies, truthful stop
rules, lost-acknowledgement recovery, exact-street through deleted property listings, offline route
uncertainty, reproducible score intervals, and restart without duplicate observation or message.
No live crawl, seller, credential, private coordinate, delivery profile, payment, deposit,
signature, or professional query enters the slice.

Related: [Composition Portfolio](index.md) · [Workflow](../adr/28-workflow.md)
