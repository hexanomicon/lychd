---
title: Tech Scavenger
icon: material/chip
---

# :material-chip: Tech Scavenger

!!! warning "Reference design — not a working Bazoš buyer"
    Tech Scavenger is an accepted Composition study. Current LychD has no Scout provider, Bazoš
    adapter, browser-session custody, hardware evidence parser, marketplace messenger, purchase
    ledger, shipment tracker, or Composition registry. Nothing on this page authorizes scraping,
    messaging, buying, payment, or disclosure of a delivery address.
    [State of the Work](../state-of-the-work.md) remains the delivery authority.

**Tech Scavenger** lets a person describe the computer they want, the money and month they have,
the distance they will travel, and the proof they need from a seller. It turns that intent into a
finite purchase campaign: look for compatible parts at least once a day, rank new listings,
request the right test, negotiate inside exact limits, and either ask for the final blessing or
complete one preauthorized cash-on-delivery agreement.

The visible promise is deliberately ordinary:

> “I want a 1080p gaming PC within the next month for at most €900. Search once a day. Prefer
> Bratislava within 50 km, but accept shipping for RAM and SSDs. Ask for the tests I selected and
> never exceed my all-in limits.”

The person does not need to understand crawler syntax, SMART attribute names, memory ranks, socket
compatibility, or marketplace negotiation. Those become inspectable campaign policy, not hidden
agent instinct.

## Why this application matters now

Research snapshot: **2026-07-29**.

The 2026 memory shock makes patient, evidence-aware second-hand buying more than a hobbyist
optimization. [TrendForce projected PC DRAM contract prices to rise by more than 100% quarter over
quarter in 1Q26](https://www.trendforce.com/presscenter/news/20260202-12911.html), then projected
[consumer DRAM to rise another 45–50% quarter over quarter in
2Q26](https://www.trendforce.com/presscenter/news/20260407-13001.html). A
[Geizhals-based German retail sample published by
3DCenter](https://www.3dcenter.org/artikel/speicherkrise-preisindex-juli-2026) measured many DDR5
kits at roughly **267–431% above July 2025 prices** and its eight-product memory sample at
**275% above** that baseline.

Those are contract and German retail observations, not a Slovak Bazoš price oracle. They must
never be copied into an offer as if every used DIMM tripled in value. They establish the product
pressure: when new-component prices move this violently, a month of disciplined local search,
compatibility checking, and seller evidence can save real money without forcing an ordinary buyer
to watch listings all day.

## Composition descriptor

| Field | Accepted design value |
| --- | --- |
| Stable id / revision | `scavenger.tech` / `1` |
| Specification owner | `project:lychd`; Bazoš, hardware-catalogue, messaging, and shipment contribution owners remain future |
| Support tier | Architecture-only reference; unsupported |
| Purpose | Complete one bounded, evidence-aware used-technology purchase campaign |
| Default manual Pattern | `scavenger.plan_campaign@1` |
| Default scheduled Pattern | `scavenger.daily_hunt@1` |
| Primary projection | Campaign board: build slots, candidates, seller threads, commitments, and expected parcels |
| Provider binding | Scout effects, deterministic catalogues/parsers, and operator-selected local `chat`/`vision` Runes |
| Principal non-goal | Unbounded scraping, spam, undisclosed impersonation, autonomous payment, or a resale business |

## The simple setup

The setup surface asks for outcomes before component jargon:

1. **What must the PC do?** Games and resolution, applications, storage, acoustics, size, network,
   and upgrade expectations.
2. **What already exists?** Case, display, power supply, motherboard, platform, parts, and their
   trusted specifications.
3. **What are the limits?** Total campaign budget, per-slot ceiling, deadline, maximum outstanding
   cash-on-delivery exposure, and maximum number of purchases.
4. **How far may it hunt?** Home region represented only by a coarse search origin, personal-pickup
   radius, travel-cost policy, and acceptable shipping territory.
5. **What proof is enough?** Listing-only alert, remote screenshot/report, challenge-bound video,
   personal test, warranty receipt, or a component-specific combination.
6. **How much autonomy is wanted?** Watch, Concierge, or bounded Autopilot.

| Mode | What the Composition may do |
| --- | --- |
| **Watch** | Search, normalize, score, and notify. It sends nothing. |
| **Concierge** | Draft and, when separately authorized, send test questions or offers. The Magus approves the final price, delivery, and address disclosure. |
| **Bounded Autopilot** | Send transparent messages, negotiate, reserve one slot, and disclose one approved delivery profile only when every standing-authority predicate passes. |

Autopilot is not a generic “buy for me” toggle. Its standing authority pins the campaign, component
slot, maximum all-in price, acceptable condition and evidence tier, delivery method, seller-risk
floor, address profile, expiry, concurrent parcel exposure, and maximum purchase count. Any changed
fact falls back to Concierge or refusal.

## Ownership and trust boundaries

| Concern | Owner |
| --- | --- |
| Campaign, Pattern revision, schedules, overlap, logical priority, and slot lifecycle | Weaver |
| Search, fetch, extract, render, interaction, credential, and session effects | Scout under separate grants |
| Bazoš selectors, page normalization, message forms, and site receipts | Future site-specific Scout adapter |
| Principal, browser-profile authority, delivery-profile access, and revocation | Ward |
| Component compatibility, price arithmetic, evidence rules, and hard offer predicates | Deterministic application tools |
| Ambiguous listing interpretation, question drafting, and visual evidence triage | Replaceable local Mind/Eye |
| Listing, seller-thread, evidence, offer, commitment, parcel, and inspection records | Application-owned Phylactery schemas |
| Screenshot, report, and video bytes admitted for retention | Future Reliquary custody |
| Significant purchase, novel seller risk, and policy exceptions | HitL / Magus |
| Monetary settlement | Human at delivery; future economic adapters remain governed by Toll |
| Courier possession, delivery event, and package condition | External carrier observations plus the Magus's receipt record |

Bazoš is a contact surface, not an escrow, condition authority, courier, or guarantor. Its
[terms say that the operator only mediates contact and does not guarantee quality, origin,
delivery, collection, payment, or usability](https://www.bazos.sk/podmienky.php). A listing,
seller statement, rating, screenshot, test, cash-on-delivery label, and successful boot are
different evidence.

## Campaign continuity and daily Occurrences

A “one-month agent” is not one immortal process. The campaign is durable application state; every
schedule firing is one finite Occurrence and, if admitted, one revision-pinned Invocation:

```text
campaign
├── desired PC and compatibility graph
├── acquisition slots with reserved budgets
├── daily Occurrences
├── listing observations and seller threads
├── at most one active commitment per slot
└── expected parcels and inspection outcomes
```

The default daily schedule uses `coalesce`: if yesterday's scan is still running, today's firing
does not build a stale queue. A daily Invocation has a wall-time, page, listing, model-call,
message, evidence-byte, and retry budget. The deadline ends new acquisition and leaves open
commitments visible; it does not erase a parcel already in transit.

One component slot has a monotonic state such as:

```text
open → candidate → evidence_pending → offer_open
     → reserved → committed → in_transit → received → accepted
```

`rejected`, `expired`, `seller_withdrew`, `delivery_refused`, `inspection_failed`, and `cancelled`
remain explicit terminal or recovery states. Reservation closes competing commitment effects for
that slot while keeping alternate candidates visible. An unknown message or shipment result holds
the reservation for reconciliation; it never triggers a second automatic purchase.

## Pattern catalogue

### `scavenger.plan_campaign@1`

```text
CaptureOutcomeAndInventory
→ NormalizeBudgetDeadlineAndRegion
→ ResolveCompatibilityQuestions
→ ProposeBuildAndSubstitutions
→ AssignSlotEvidenceAndDeliveryPolicy
→ ReviewAutonomyAndDisclosurePolicy
→ CommitCampaignAndSchedule
→ End
```

The output is a versioned shopping plan, not a promise that the recommended parts or prices will
remain available. Unknown existing hardware creates a question or a blocked compatibility edge; a
model guess never becomes a socket, clearance, power, firmware, or memory-support fact.

### `scavenger.daily_hunt@1`

```text
AdmitDailyOccurrence
→ LoadOpenSlotsAndBudgets
→ AcquirePermittedListingPages
→ NormalizeAndDeduplicate
→ MatchHardCompatibility
→ EstimateCurrentPriceInterval
→ ScoreEvidenceDistanceAndLandedCost
→ JoinWithKnownSellerThreads
→ NotifyOrStartQualifiedThread
→ CommitDailyDigest
→ End
```

The first slice only notifies. Messaging becomes a child Invocation after search and ranking can
be proven without external social effects.

### `scavenger.qualify_listing@1`

```text
PinListingObservation
→ DetectMissingMaterialFacts
→ SelectComponentEvidenceProfile
→ DraftTransparentQuestion
→ AuthorizeAndSendOnce
→ AwaitSellerReply
→ AcquireReplyAndEvidence
→ ParseDeterministically
→ ReviewClaimsAndContradictions
→ Qualify | AskOneFollowUp | Reject | Expire
```

Questions are material and finite. The Pattern does not ask every seller to run every benchmark,
re-contact a refusal, or hide automation behind a fake human story.

### `scavenger.negotiate_and_commit_cod@1`

```text
LoadQualifiedCandidate
→ ComputeOpeningAndMaximumAllInPrice
→ DraftGroundedOffer
→ AuthorizeAndSendOnce
→ ReconcileReplyOrUnknownSend
→ ValidateFinalItemEvidencePriceAndDelivery
→ ReserveBudgetAndComponentSlot
→ ResolveLiveConsentOrStandingAuthority
→ ConstructAddressMessageOutsideTheMind
→ ReauthorizeAndSendAddressOnce
→ CreateExpectedParcel
→ End
```

The final effect is exactly the one requested by this Composition: after an accepted cash-on-
delivery deal, the adapter sends the approved recipient name, delivery address, and phone number,
then creates an expected parcel for the Magus to receive. The model receives only an opaque
`delivery_profile_id`; a deterministic effect handler obtains the current address after Ward
reauthorization and inserts it into the reviewed template.

### `scavenger.receive_and_verify@1`

```text
ReconcileTrackingAndExpectedTotal
→ NotifyMagusBeforeDelivery
→ RecordAcceptOrRefuseAtDoor
→ InspectAgainstEvidenceProfile
→ RecordOutcomeAndVariance
→ Accept | EscalateSellerDispute | ReturnWhenAgreed | CloseWithLoss
→ ReleaseSlotAndCampaignBudget
→ End
```

Cash on delivery changes when money moves; it does not prove what is inside the package. The
delivery card therefore displays seller, carrier, tracking, expected amount, component, and
package notes. An unrecognized parcel or mismatched amount should be refused rather than paid
because it merely resembles an expected order.

## Compatibility and value law

Compatibility is a hard gate before preference. The deterministic catalogue must represent at
least:

- CPU socket, chipset support, BIOS floor, cooling and power envelope;
- memory generation, form factor, capacity, rank/kit assumptions, supported speed and slot plan;
- GPU dimensions, slot width, power connectors, power-supply headroom, case clearance, and display
  outputs;
- storage interface, keying, lane/SATA conflicts, form factor, capacity, endurance observations,
  and boot constraints;
- case form factor, cooler/radiator clearance, drive bays, and airflow assumptions; and
- power-supply exact model, revision, rated rails, connectors, age evidence, and known exclusions.

Catalogued facts carry source, observed version/date, and confidence. A compatible socket does not
prove a stable BIOS, adequate VRM, sufficient transient response, physical clearance, or healthy
used part.

Price is an interval derived from attributable observations, never one hallucinated “fair price.”
The application keeps new-retail, recent comparable used listings, sold/withdrawn observations
where legitimately available, condition, warranty, age, and bundle value separate. Ranking uses:

```text
landed cost = agreed price + shipping + cash-on-delivery fee + configured travel cost
```

and orders only after hard compatibility by expected value, evidence confidence, delivery fit,
distance, campaign urgency, and a visible risk reserve. A listing far away may beat a nearby one
for low-risk RAM with strong proof; a fragile GPU or unprovable PSU may remain pickup-only even
when shipping is cheaper.

The model may explain a score. It does not set the price ceiling, change arithmetic, or mark its
own interpretation as evidence.

## Evidence tiers and component profiles

Every seller artifact is hostile external content and a claim about one item. A test reduces a
named uncertainty; it does not create a universal “healthy” verdict. The campaign selects a
minimum tier by component, price, delivery method, and risk:

| Tier | Minimum evidence | Appropriate use |
| --- | --- | --- |
| `E0 listing` | Listing text and ordinary photographs only | Alerting; never enough for automatic remote commitment |
| `E1 identity` | Exact model/part-number label, current condition photos, visible defects, accessories, and proof-of-purchase claim when relevant | Low-value parts or prerequisite for stronger tests |
| `E2 diagnostic` | Full, legible report or screenshot with tool version, item identity, relevant counters, time, and system context | Remote qualification when forgery/reuse risk is accepted |
| `E3 challenge` | Fresh thread nonce bound to an uncut screen/video path from item identity through test result | Higher-value shipped parts |
| `E4 witnessed` | Personal or trusted-shop inspection with the configured test and recorded outcome | Fragile, unsafe, expensive, or weakly testable parts |

Serials and account identifiers are minimized or partially masked while retaining enough stable
characters to join the label, report, parcel, and received item. Reverse-image similarity, old
timestamps, impossible tool fields, mismatched capacities, cropped warning rows, reused media, and
inconsistent model identifiers are risk signals, not automatic accusations.

| Component | Candidate remote proof | Important limit |
| --- | --- | --- |
| HDD / SSD | Exact label plus full [CrystalDiskInfo](https://crystalmark.info/en/software/crystaldiskinfo/) screenshot and Text Copy, or a bounded `smartctl` report; model, capacity, health flags, power-on hours, total writes, unsafe shutdowns, media/data-integrity errors, and temperature remain visible | SMART can be incomplete, vendor-specific, reset, forged, or unable to predict failure; shipping damage remains possible |
| RAM | Label and kit identity; [CPU-Z](https://www.cpuid.com/softwares/cpu-z.html) Memory/SPD evidence; complete [MemTest86](https://www.memtest86.com/) result at declared settings | A screenshot proves neither long-term stability nor compatibility in the buyer's board; errors may involve CPU, board, settings, or the module |
| GPU | Both sides and connectors; exact model/BIOS evidence; sensor report and a challenge-bound uncut load test showing clock, temperature, fan, errors, artifacts, and completion | One benchmark cannot exclude intermittent faults, repaired boards, memory errors, mining history, or shipping damage |
| CPU / motherboard | Socket and pin close-ups, exact model/revision, POST and inventory evidence, short stability/temperature result, ports and included accessories | Bent pins, marginal memory channels, firmware support, and damaged ports often require personal testing |
| PSU | Exact model/revision and label, age and purchase proof, cable inventory, noise/damage disclosure, and a suitable witnessed bench or system test | No ordinary screenshot proves capacitor condition, protections, ripple, or safe internal state; opening it is not a seller test |
| Whole PC | Inventory report, storage evidence, combined load and temperature record, boot/restart, ports, noise, and an uncut walkaround | A bundle can hide a weak PSU, mismatched parts, unstable tuning, licensing issues, or faults outside the short test |

The application stores the requested profile, the seller's exact response, tool/version, parsed
facts, raw-artifact reference when admitted, contradictions, reviewer verdict, and what remains
unknown. It never silently converts “CrystalDiskInfo says Good” into “the disk cannot fail.”

## Bazoš.sk acquisition profile

Bazoš is the first named adapter, not a permission exception to [Scout](../adr/30-webcrawler.md).
The site's public PC surface currently exposes category, text, postal-code radius, and price
filters plus an RSS link. Its [help page](https://www.bazos.sk/pomoc.php) documents bulk automatic
imports only for real-estate listings; that facility is not a general PC API or permission to
crawl.

Before each adapter revision is enabled, its maintained site profile records:

- exact allowed origins and public paths, acquisition effect, declared user agent, pacing,
  concurrency, page/byte ceilings, cache and expiry;
- the then-current robots observation, site terms, privacy notice, and operator decision;
- selectors and fixture digests for listing id, category, title, price, locality, description,
  images, seller-rating link, contact surface, and pagination;
- whether an official RSS/search path can satisfy the campaign before Crawl or Render is considered;
- verified-device, cookie, session, and contact requirements;
- message and follow-up caps, stop signals, CAPTCHA outcomes, and account-block recovery; and
- an emergency kill switch that disables acquisition and interaction independently.

[Bazoš help currently says that actions beyond browsing—including sending email and revealing a
phone number—require a device verified by SMS, with additional bank-account linkage by
micro-payment](https://www.bazos.sk/pomoc.php). The operator performs those identity steps.
Tech Scavenger never reads an SMS, initiates a verification payment, defeats a CAPTCHA, rotates
identities around refusal, or upgrades a public fetch into a credentialed browser session.

### Portable bazaar contract

The reusable Tech Scavenger core owns campaign, compatibility, evidence, negotiation, commitment,
parcel, and trade contracts. Bazoš-specific search fields, Slovak language, locality grammar,
selectors, verification steps, source policy, and fixtures belong to one versioned market/source
adapter. An identity such as `marketplace.bazos.sk@1` is illustrative until the Composition
registry exists.

Another country does not fork the campaign engine. It contributes a target-market adapter that
maps its public listing, seller-contact, locality, price, delivery, and deletion observations into
the same typed contracts, and it keeps source acquisition separate from any credentialed message
channel. Exact home location remains private; a campaign may receive only a chosen region, radius,
or locally derived distance.

The future Smith may read this Reference Composition, Scout law, routed scopes, Bazoš fixtures,
and the target bazaar's attributable public surfaces to fabricate a candidate adapter and tests
in the Lab. It must re-establish target terms, robots behavior, identity requirements, fields,
rate limits, language, failure modes, and effect receipts. It cannot translate selectors and call
that a port. The operator may also author or install the adapter directly; Smith is a default
artificer path, not a mandatory runtime dependency.

Model/provider selection remains independent. A local or remote Mind may assist ambiguous text
under its privacy policy, but listing ids, prices, compatibility, budgets, message idempotency,
and authority keep deterministic owners across every market.

The adapter prefers the least powerful adequate track:

```text
official RSS or bounded search page
→ static fetch and network-free extraction
→ render only when separately permitted and necessary
→ interaction/session only for one separately authorized message effect
```

Every listing observation keeps URL, listing id, observation time, extraction revision, content
digest, displayed price and locality, and deletion/change status. TOP placement, repeated wording,
seller rating, view count, and model interpretation are ranking inputs at most. None proves item
identity or honest delivery.

## Messaging and negotiation law

The first outgoing contact is truthful and compact. A Slovak template may begin:

> Dobrý deň, píšem v mene kupujúceho ako automatizovaný nákupný asistent. Je ponuka ešte aktuálna?
> Pred rozhodnutím by sme potrebovali overiť presný model a tento test: {bounded request}.

An offer states the exact basis and does not invent competing buyers, defects, market prices, or
deadlines:

> Ak stav a výsledok testu sedia, môžeme ponúknuť {price} €; maximálny dohodnutý súčet vrátane
> dopravy a dobierky musí zostať do {all_in_cap} €.

The Agent may ask one material follow-up after an incomplete response. Seller refusal, opt-out,
abuse, inactivity, sold status, price above the ceiling, changed identity, or evidence failure
closes automatic messaging. Per-origin and per-seller caps prevent one campaign from becoming
spam.

Each send has a prepared receipt with thread, template revision, redacted payload digest, action
class, consent or standing-authority reference, and expected postcondition. If the site provides no
idempotency key and the acknowledgement is lost, the outcome is `unknown_send`; the Pattern parks
for reconciliation or the Magus rather than sending the same message again.

## Cash-on-delivery commitment and address disclosure

Before the final address message, the seller must have confirmed:

- the exact item or kit and included accessories;
- the represented condition and accepted evidence profile;
- agreed item price, shipping, cash-on-delivery fee, and maximum all-in total;
- carrier or delivery method, dispatch window, package expectations, and tracking handoff; and
- that no deposit, link payment, remote-access session, cryptocurrency, gift card, or changed
  payment rail is required.

The commitment gate rechecks campaign expiry, listing freshness, seller/thread identity, open slot,
compatibility, evidence, all-in cap, outstanding parcel exposure, and purchase count. It then
requires either live visual/touch consent or one exact matching standing authority.

Only the deterministic sender can resolve `delivery_profile_id`. The final template confirms the
deal and inserts the minimum recipient data required by the chosen carrier:

> Dohodnuté: {item}, stav podľa konverzácie, celkom najviac {all_in_total} € vrátane dobierky.
> Prosím odošlite na {recipient_name}, {delivery_address}, tel. {recipient_phone}. Po odoslaní
> pošlite dopravcu a sledovacie číslo.

The raw address and phone number do not enter model prompts, search queries, ranking artifacts, or
ordinary traces. A pickup point, parcel locker, or purpose-specific delivery alias is preferred
when the carrier and operator allow it. A personal-pickup thread never receives the home address
merely because the campaign stores one.

Address disclosure creates social and privacy consequence even before money moves. The receipt
therefore pins the seller thread, data fields disclosed, policy and approval, payload digest,
remote result, expected parcel, and revocation state. It does not retain the address in routine
telemetry.

## Capabilities and researched provider candidates

The Composition asks for capabilities, not one model brand:

| Need | Capability or tool shape |
| --- | --- |
| Listing acquisition | Scout `search`/`fetch`/`extract`; later separately gated `render`, `interact`, `session`, and `credential` |
| Structured interpretation and Slovak messaging | Local `chat`, structured output, tool semantics, Slovak fixture score |
| Photo and diagnostic review | `vision` or `chat` with `image` input; OCR and field parsing remain attributable derivations |
| Compatibility and price arithmetic | Deterministic catalogue, unit/money types, rules, and time-bounded price observations |
| Evidence parsing | Versioned parsers for text exports/reports; visual review never replaces raw field validation where available |
| External effects | Site-specific `message.send`, address disclosure, and shipment-observation adapters with receipts |

Research snapshot: **2026-07-29**.

| Role | Candidate | Fit and caveat |
| --- | --- | --- |
| Local structured Mind | [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | Candidate for local Slovak classification, extraction, and structured drafting; must pass adversarial listing, JSON, and negotiation fixtures before binding |
| Local visual Mind | [Gemma 4 12B](https://ai.google.dev/gemma/docs/get_started) | Candidate for photographs and screenshots under an image-capable profile; visual confidence never becomes hardware truth |
| Storage report source | [CrystalDiskInfo](https://crystalmark.info/en/software/crystaldiskinfo/) | Official page documents HDD/SSD/NVMe support and Text Copy; parser support must pin exact output revisions |
| System inventory source | [CPU-Z](https://www.cpuid.com/softwares/cpu-z.html) | Official page documents CPU, board, memory, SPD, screenshot, validation, and text/HTML reports; it is inventory evidence, not a full stability test |
| RAM test source | [MemTest86](https://www.memtest86.com/) | Stand-alone memory test and report path; a pass is bounded to the tested system, settings, duration, and algorithms |

Remote model Portals are off by default because listing queries, seller messages, contact data,
evidence, location, and the delivery decision are private. An operator may opt into a named Portal
for a classified step, but the delivery profile remains excluded and no provider failure permits a
privacy downgrade.

## Priority, overlap, and budgets

| Work | Target priority | Overlap and residency |
| --- | ---: | --- |
| Delivery mismatch, cancellation, or suspected fraud | `100` | Deterministic notification and hold; no model authority escalation |
| Magus campaign setup, candidate review, or consent | `70` | Interactive local Mind warm preferred |
| Seller reply classification and time-sensitive qualified offer | `50` | Queue once per thread; safe after effect receipt |
| Daily search, price refresh, and evidence parsing | `20` | Coalesce daily scans; warm-only preference; never force a disruptive swap |
| Historical compaction and expired-artifact pruning | `20` | Background, bounded, and independently recoverable |

Budgets include campaign days, open component slots, total and per-slot money, outstanding parcel
exposure, queries, pages, listings, seller contacts, follow-ups, evidence bytes, model calls,
travel distance, and retries. Spending urgency does not increase message, privacy, or price
authority.

## Durable data, provenance, and recovery

The future application owner needs versioned schemas for:

- campaign, target build, existing inventory, component slot, compatibility edge, substitution,
  budget reservation, and schedule;
- listing observation, normalized item, seller handle, seller rating observation, price
  observation, extraction provenance, and duplicate group;
- seller thread, inbound/outbound message, evidence request, evidence artifact reference, parsed
  field, contradiction, and verdict;
- offer, counteroffer, standing authority, live consent, commitment, address-disclosure receipt,
  and unknown effect;
- expected parcel, tracking observation, delivery decision, received-item identity, inspection,
  dispute, refund/return agreement, loss, and campaign close.

Graph checkpoints own one Invocation cursor, never the campaign database or seller inbox. A
checkpoint pins Pattern, adapter, selector, catalogue, evidence-profile, parser, template, and
policy revisions. An incompatible upgrade drains, migrates explicitly, or ends non-complete.

Listing and message content remains attributable to source and observation time. Corrections append;
they do not rewrite the original claim. Media bytes need Reliquary custody before an `ArtifactRef`
can promise retrieval. Crash recovery reconciles prepared sends, slot reservations, seller
responses, address disclosures, tracking, and payment-at-door outcomes before any repeat effect.

## Privacy, retention, export, and deletion

- Coarse search location is separate from the exact delivery profile.
- Seller phone, email, address, ratings, messages, serial fragments, and evidence are private
  third-party data, not general memory or training material.
- Raw delivery data is field-encrypted or held behind an equivalent narrow secret boundary and
  projected only to the deterministic send effect.
- Seller evidence may contain serials, usernames, desktop content, IPs, licenses, and unrelated
  files. Censoring may only remove unnecessary fields after acquisition authority permits the
  input; it cannot invent permission.
- Default retention should expire rejected-listing bodies and seller contact data shortly after
  the campaign, while preserving redacted commitment, parcel, and loss receipts for an
  operator-selected accountability period.
- Export contains the campaign plan, selected observations permitted for export, compatibility and
  price rationale, thread transcript, evidence lineage, approvals, receipts, and checksums. The
  delivery address is opt-in and separately encrypted.
- Deletion disables schedules and site sessions first, inventories unresolved parcels and disputes,
  revokes delivery-profile access, then removes application records and admitted artifacts
  according to third-party and accounting retention obligations. It never claims to erase a
  message already received by a seller.

Seller rating is a claim surface with sybil, retaliation, mistaken-identity, and sparse-history
risk. Tech Scavenger may display it with source and date; it cannot turn reputation into identity
or guilt.

## Necropolis horizon: `trade.*` over A2A

Tech Scavenger can eventually outgrow one centralized classifieds site without turning the
Necropolis into another marketplace owner. A future Lich may advertise only the things its human
has explicitly made available, while another Lich searches on behalf of its human.

This should be a versioned A2A skill family carried through the existing
[`/a2a` Intercom](../adr/26-a2a.md), not a second unauthenticated `/trade` protocol:

| Candidate skill | Bounded intent |
| --- | --- |
| `trade.catalog.query@1` | Ask an admitted peer for offers matching typed compatibility, region, price, delivery, and evidence constraints |
| `trade.offer.publish@1` | Advertise one revocable, expiring, human-authorized item offer |
| `trade.evidence.request@1` | Request one declared test profile and receive attributable artifact references or refusal |
| `trade.counteroffer@1` | Exchange one price/delivery proposal without creating a sale |
| `trade.reserve@1` | Request a finite reservation under both humans' policies |
| `trade.fulfillment.propose@1` | Propose pickup or shipping terms; disclosure and commitment remain separately authorized |

A public offer may contain item identity, represented condition, quantity, price, currency,
coarse region, delivery methods, evidence profiles available, expiry, and revocation reference.
It must not publish a home address, phone number, full serial, private memory, unrestricted
callback, payment credential, or proof that reveals another person.

Discovery and schema matching create no commitment. Each side's Ward authenticates the peer;
each human owns inventory and current authority; each model may propose but cannot mint consent.
Reservation, address disclosure, shipping, payment, refund, and dispute have separate signed
receipt chains. A peer reputation assertion remains one attributable claim, not shared truth.

The long horizon is concrete sovereignty: two local systems can match compatible material,
evidence, price, and delivery while their humans remain distinct owners and their Phylacteries
remain private. This is one small trade-shaped path toward the coordination described by
[Infinity](../divination/transcendence/infinity.md), not proof that the peer economy or the Great
Work is delivered.

## Smallest proving slice

1. Create one campaign fixture: buy one compatible 32 GB RAM kit within 30 days, one Slovak region,
   one radius, one shipped fallback, one all-in ceiling, and no automatic messaging.
2. Pin one manually approved Bazoš search/RSS profile, terms snapshot, robots decision, selectors,
   pacing budget, and recorded HTML fixtures.
3. Normalize listing id, URL, title, exact price, locality, description, images, and observation
   time; prove update, deletion, TOP movement, and duplicate handling.
4. Match a small deterministic DDR4/DDR5/SODIMM/UDIMM compatibility catalogue and reject deliberate
   near-matches.
5. Build an attributable price interval from fixed retail and used-listing fixtures; show why a
   candidate ranks without asking a model for arithmetic.
6. Render one daily digest and coalesce overlapping Occurrences without contacting a seller.
7. Add a local structured Mind only for ambiguous Slovak listing extraction and compare it against
   labeled fixtures; unsupported fields remain unknown.
8. Kill the worker after listing acquisition and before daily commit; resume without duplicating
   observations or notifications.
9. End with an exportable campaign, digest, provenance, and explicit delivery gaps.

This proves that a simple person can describe one need and receive a reliable daily shortlist
before the system acquires social, privacy, or economic consequence.

## Staged roadmap

1. **Watch-only RAM campaign:** bounded Bazoš acquisition, deterministic compatibility, daily
   schedule, deduplication, price interval, and digest.
2. **Evidence concierge:** seller-thread import, component profiles, CrystalDiskInfo/CPU-Z/
   MemTest86 parsing, visual triage, and bounded question drafts.
3. **One authorized message:** verified operator session, transparent template, effect receipt,
   opt-out, rate caps, and unknown-send recovery.
4. **Negotiation:** deterministic opening/max price, all-in arithmetic, one counteroffer loop, and
   no fabricated claims.
5. **Manual commitment:** slot and budget reservation, visual/touch consent, deterministic address
   insertion, expected parcel, and delivery mismatch alert.
6. **Bounded Autopilot:** standing authority, one low-risk component class, one delivery profile,
   purchase and exposure caps, adversarial seller fixtures, and revocation.
7. **Full PC campaign:** dependency-aware multi-slot plan, substitutions, order timing, and
   received-part compatibility reconciliation.
8. **Broader hardware:** GPU, storage, board, CPU, PSU, whole-PC, personal-test, repair, and return
   profiles only after each has bounded evidence and loss policy.
9. **Portable market adapters:** one adapter per origin with independent permission, selectors,
   credentials, sessions, pacing, and kill switch; prove one non-Slovak synthetic port and the
   Smith Lab→test→review path before calling the contract reusable.
10. **Peer trade lab:** signed `trade.*` A2A schemas, fake goods and sybil trials, bilateral
    consent, revocation, reservation, fulfillment, and dispute receipts before public discovery.

## Current delivery gaps

Scout and Toll are Designed, not implemented. The current Core proves pieces such as Pattern
identity, bounded Graph continuity, consent parking, narrow effect policy, capability metadata,
and priority propagation. It does not prove any marketplace acquisition, scheduling Portfolio,
hardware catalogue, report parser, visual artifact custody, site session, seller inbox/outbox,
message reconciliation, purchase commitment, address secret, parcel tracking, settlement,
consumer dispute, or A2A trade skill.

No current command can enable this Composition. Its Bazoš specificity is an application contract
and proving burden, not evidence that automated use is permitted or technically available.

## Continue

- Read [Scout](../sepulcher/extensions/scout.md) before implementing any Bazoš acquisition or
  browser effect.
- Read [Weaver](../sepulcher/extensions/weaver.md) for campaign Patterns, schedules, and
  Occurrences.
- Read [Sovereign Consent](../adr/25-hitl.md), [Ward](../sepulcher/extensions/ward.md), and
  [Toll](../sepulcher/extensions/toll.md) before messaging, commitment, address disclosure, or
  payment.
- Read [A2A](../adr/26-a2a.md) before shaping the future `trade.*` skill family.
- Return to the [Composition Portfolio](index.md).
