---
title: Lifestyle Steward
icon: material/cart-heart
---

# :material-cart-heart: Lifestyle Steward

!!! warning "Reference design — not a delivered shopping or household application"
    Lifestyle Steward is an accepted Composition study. Current LychD has no receipt-byte custody,
    PaddleOCR Soulstone, merchant catalogue adapter, product ledger, pantry inventory, local route
    profile, restaurant-menu feed, shopping cart integration, checkout effect, or Composition
    registry. Nothing on this page can scrape a shop, infer what the Magus ate, or place an order.
    [State of Work](../state-of-the-work.md) remains the delivery authority.

**Lifestyle Steward** turns ordinary household evidence into an editable map of daily life. The
Magus can photograph a receipt; a local pipeline transcribes it into a clear table of what was
bought, where, when, in what quantity, at what unit price, and under which discount. Kaufland and
Lidl are first Slovak examples, not identities baked into the application. Later Patterns can
compare price trends, project pantry and fridge inventory, watch nearby catalogues and restaurant
menus, prepare a practical shopping trip, or build an online cart for explicit review.

The operator-facing experience may feel like one Lifestyle application. Its authority remains
divided underneath:

- [Health, Food & Movement](health-food-and-movement.md) owns wellness profiles, restrictions,
  meal plans, movement, and sensitive reflection.
- Lifestyle Steward owns receipts, product identities, household inventory, store topology,
  prices, catalogues, carts, orders, and deliveries.
- [Tech Scavenger](tech-scavenger.md) owns used-technology evidence, seller negotiation, and its
  specialized cash-on-delivery campaign.
- [Walking Communion](walking-communion.md) may later provide voice ingress; it owns neither
  lifestyle records nor purchase authority.

This is a composition of finite Patterns, not one ambient “life agent” that silently observes,
judges, or purchases.

## The arithmetic of daily life

The product can be understood through four ordinary operations:

```text
ADD       receipt + catalogue + inventory + preference + route
MULTIPLY  a cheap item × actual need × taste fit × permitted health fit
SUBTRACT  travel friction + uncertain stock + likely waste + delivery cost
DIVIDE    one friendly Lifestyle view across the offices that actually own each truth
```

The result is not “always buy the cheapest basket.” A Kaufland 100 metres away may win most days;
Lidl 200 metres away may win when its offers fit the list; Tesco 500 metres away may become worth
the extra trip only when a desired grill or another meaningful item outweighs the extra time and
uncertain stock. Distance, price, taste, routine, stock confidence, waste, and health constraints
remain visible rather than collapsing into unexplained AI taste.

## Composition descriptor

| Field | Accepted design value |
| --- | --- |
| Stable id / revision | `lifestyle.steward` / `1` |
| Specification owner | `project:lychd`; receipt, retail, route, menu, and checkout owners remain future |
| Support tier | Architecture-only reference; unsupported |
| Purpose | Turn consented household evidence into a private purchase ledger, inventory projection, and reviewable local or online provisioning choices |
| Default manual Pattern | `lifestyle.ingest_receipt@1` |
| Primary projection | Receipt table, price timeline, pantry/fridge view, local opportunity board, and cart review |
| Privacy ceiling | `restricted`; checkout credentials and payment material are `secret` |
| Provider binding | Local OCR and visual/text Runes plus deterministic parsers, catalogues, routing, and effect adapters |
| Principal non-goal | Financial accounting, clinical nutrition, surveillance, compulsive optimization, or autonomous discretionary shopping |

## Visible scenarios and non-goals

### A receipt becomes a reviewable ledger

The Magus photographs a crumpled receipt after returning from Kaufland. Lifestyle Steward:

1. preserves and normalizes the image under explicit retention;
2. runs local PaddleOCR and keeps text polygons, confidence, and reading order;
3. asks a local Qwen visual/text Mind to propose receipt fields and product aliases;
4. checks every monetary identity with exact decimal arithmetic;
5. displays uncertain rows beside their source crops; and
6. commits only the corrected table the Magus accepts.

The output can answer “what did I pay for this butter over the last eight weeks?” without treating
an OCR guess as financial truth.

### A new country starts from a proven example

The Magus selects a country and language, and may permit a coarse region or private local-distance
derivation. Lifestyle Steward first looks for installed market, merchant, receipt, catalogue, and
route adapters. If the target market is missing, the future Smith can study the nearest Reference
Composition and fabricate a candidate market pack in the Lab. A German, Czech, Polish, or other
operator should replace Slovak merchant assumptions without forking receipt arithmetic,
inventory truth, HitL checkout law, or the entire application.

The Smith does not become the grocery agent. It proposes typed source profiles, parsers, fixtures,
tests, and registration changes; Scout later performs permitted acquisition and Weaver runs the
promoted Patterns.

### A shopping trip respects real friction

The Magus can record private route anchors and preferences such as “Kaufland is effortless,”
“Lidl is fine,” and “Tesco is an extra trip unless it contains something I actually want.” The
planner can join a shopping list, likely inventory, catalogue offers, route time, store preference,
loyalty conditions, and stock uncertainty. It explains why a one-store or two-store plan wins.

### The fridge informs a plan without becoming omniscient

A receipt creates acquisition candidates. Confirmed barcode scans, pantry counts, expiry labels,
meal check-ins, disposals, and manual corrections refine them. A planned meal is not consumption;
a purchase is not consumption; silence is not an empty fridge. The surface says `confirmed`,
`inferred`, or `unknown`.

### Online exploration ends at a real decision

The Magus may say “find me some figurines on AliExpress.” Scout can later obtain permitted product
pages and the local Mind can group variants, seller terms, delivery estimates, reviews as claims,
and total costs. The Altar presents exact candidates. Only after a fresh HitL choice such as “yes,
this variant from this seller at this maximum total” may a checkout Pattern begin.

The Composition is not a bank ledger, tax record, medical device, diet authority, inventory sensor,
price-fixing engine, loyalty-card scraper, restaurant allergen guarantor, background location
tracker, social-profile miner, or autonomous payment agent. It does not infer eating from receipts,
calories from food photographs, health from baskets, or genetic recommendations from model lore.

## Ownership and trust boundaries

| Concern | Owner |
| --- | --- |
| Pattern revisions, schedules, Occurrences, overlap, priority, and child Invocations | Weaver |
| Receipt/photo byte custody and authorized materialization | Future Reliquary |
| Decode, orientation, crop, OCR, and visual observation | Prism and selected OCR/Vision Animators |
| Receipt schema, product identity, prices, inventory, preferences, routes, carts, orders, and deliveries | Future Lifestyle application owner |
| Search, fetch, catalogue acquisition, rendering, interaction, credentials, and sessions | Scout under separate effect grants |
| New market, merchant, parser, and source-adapter candidates | Smith in the Lab; promotion remains Assimilation and Magus authority |
| Identity, object visibility, merchant-session authority, delivery profiles, and revocation | Ward |
| Exact decimal arithmetic, receipt reconciliation, unit prices, constraint checks, and cart totals | Deterministic Tool Animators |
| Wellness plan, restrictions, journals, movement, and personal-health profile | Health, Food & Movement |
| Checkout approval, address disclosure, substitutions, and significant spend | HitL / Magus |
| Quote, reservation, payment rail, and settlement reconciliation | Future Toll |
| Merchant stock, order acceptance, fulfillment, refund, and delivery | External merchant/carrier observations joined to local receipts |

The model proposes aliases, explanations, menu interpretations, and candidate bundles. It never
owns totals, product identity, hard restrictions, inventory truth, checkout authority, or payment.

## Pattern catalogue

### `lifestyle.bootstrap_market@1`

```text
DeclareLocaleLanguageAndLocationConsent
→ DeriveMinimalCountryRegionAndCurrencyContext
→ LoadInstalledMarketAndMerchantProfiles
→ DiscoverPermittedPublicStoreCandidates
→ MatchReceiptCatalogueMenuRouteAndMarketplaceAdapters
→ ExplainCoverageSourcesGapsAndPrivateDataUse
→ DraftSmithPortBriefForMissingCoverage
→ MagusSelectsOrEditsMarketPlan
→ EnableOnlyReviewedProfiles
→ End
```

Location is optional. The Magus may select a country, city, stores, and merchants manually. Exact
home coordinates remain behind the location boundary; the bootstrap normally needs only a country
and coarse region, while local route tools can derive distance without disclosing the private
anchor to Smith, a remote model, a merchant, or a crawler.

The default path reuses an installed generic or market-specific adapter. Smith is invoked only for
a real coverage gap, and its result is an inert candidate until source policy, fixtures, tests,
review, and explicit promotion pass.

### `lifestyle.ingest_receipt@1`

```text
AdmitReceiptArtifact
→ ApplyDeclaredLensTransforms
→ RunLocalPaddleOCR
→ PreserveTokensBoxesAndConfidence
→ ProposeReceiptSchemaWithLocalQwen
→ NormalizeMerchantProductsUnitsAndMoney
→ ReconcileLinesDiscountsDepositsTaxesAndTotal
→ ShowUncertainFieldsAndSourceCrops
→ MagusCorrectsOrAccepts
→ CommitReceiptLedgerAndAcquisitionEvents
→ End
```

PaddleOCR and Qwen have different offices. OCR observes candidate glyphs and layout. Qwen proposes
semantic structure from the image plus attributed OCR output. Deterministic code validates money,
units, dates, and schema. The Magus resolves the remaining uncertainty. No stage overwrites its
parent evidence.

### `lifestyle.review_spending@1`

```text
PinReviewWindowAndProductIdentityRevision
→ LoadAcceptedReceiptLines
→ NormalizeComparableQuantities
→ ComputePricePurchaseAndStoreTrends
→ SeparateObservedFactsFromInterpretation
→ DraftNeutralSummary
→ CommitOrDiscardDerivedReview
```

The review may report exact observed spend, frequency, unit-price ranges, discount use, or store
mix. It may not infer household income, addiction, health, waste, consumption, inflation causes,
or moral virtue from a basket.

### `lifestyle.reconcile_inventory@1`

```text
LoadConfirmedAndInferredInventory
→ JoinNewAcquisitions
→ JoinConfirmedConsumptionDisposalAndCorrections
→ ApplyBoundedPackageArithmetic
→ MarkExpiryAndQuantityUncertainty
→ PresentReconciliation
→ CommitInventoryEvents
```

Inventory is an event projection, never a mutable number with hidden provenance. Every displayed
quantity links to acquisition, confirmation, consumption, disposal, correction, or a visible
decay assumption.

### `lifestyle.refresh_catalogues@1`

```text
AdmitScheduledOccurrence
→ LoadEnabledMerchantOriginProfiles
→ AcquireCurrentAndFuturePermittedOffers
→ ParseValidityStoreScopeLoyaltyAndUnitPrice
→ DeduplicateProductAndOfferObservations
→ CompareAgainstWatchlistInventoryAndPlans
→ CommitOpportunityDigest
→ End
```

A flyer or menu is an offer observation, not proof of shelf stock, checkout price, restaurant
availability, ingredient closure, or future delivery.

### `lifestyle.plan_shop@1`

```text
LoadShoppingIntentAndApprovedHFMShoppingList
→ LoadInventoryProjectionAndWasteRisk
→ RequestMinimalProvisionConstraints
→ ResolveEligibleProductCandidates
→ JoinCurrentOffersStorePreferencesAndRouteMatrix
→ SolveOneStoreAndBoundedMultiStorePlans
→ ExplainSavingsFrictionUncertaintyAndMissingItems
→ MagusEditsApprovesOrRejects
→ CommitTripPlan
```

The solver may recommend one nearby store instead of a theoretically cheaper three-stop tour. Extra
stops require an operator-configured improvement threshold and maximum detour.

### `lifestyle.choose_meal_out@1`

```text
LoadTimeRadiusCuisineBudgetAndProvisionConstraints
→ AcquirePermittedFreshMenus
→ ParseMealPriceAvailabilityAndDeclaredAllergens
→ MarkIngredientAndStockUnknowns
→ JoinWalkingRouteAndRestaurantPreferences
→ RankEligibleOrUnresolvedChoices
→ ExplainAndEnd
```

This Pattern proposes where eating out may be worthwhile. It does not book, call, order, certify
allergen safety, or convert a restaurant's social post into current kitchen truth.

### `lifestyle.build_cart@1`

```text
LoadApprovedListAndMerchantSurface
→ SearchPermittedCatalogue
→ ResolveExactProductsVariantsAndQuantities
→ ApplySubstitutionPolicy
→ RevalidatePriceStockLoyaltyDeliveryAndReturns
→ BuildCartDraft
→ ShowTotalUncertaintyAndDataDisclosure
→ ParkForMagus
```

### `lifestyle.checkout@1`

```text
LoadApprovedCartDraft
→ ReauthenticateMerchantSession
→ RevalidateSellerVariantPriceStockFeesTaxAndDelivery
→ ResolveSubstitutionsAndRecurringTerms
→ ReserveWorstCaseBudget
→ PresentExactHitL Decision
→ ReauthorizeDeliveryAndCheckoutEffects
→ SubmitOnce
→ ReconcileOrderPaymentAndUnknownOutcome
→ CreateExpectedDelivery
→ End
```

Every checkout begins from a selected cart but revalidates live terms. A changed price, seller,
variant, delivery date, address requirement, subscription, customs exposure, or substitution
returns to HitL.

## Receipt schema and reconciliation law

The application must avoid one opaque `receipt_json` blob. A candidate receipt records:

| Layer | Required fields |
| --- | --- |
| Source | Artifact digest, media type, capture time, transform chain, OCR provider/revision, schema provider/revision, and retention |
| Merchant | Merchant identity candidate, store identity/address candidate, terminal/store code, and confidence |
| Transaction | Local timestamp, currency, receipt number, subtotal, discount total, deposits, tax/VAT summaries when printed, rounding, grand total, and redacted payment descriptor |
| Line | Original text, source polygon/crop, quantity, unit, unit price, line total, discounts, deposits, printed product code/GTIN when present, and confidence |
| Identity | Exact product candidate, package size, brand, variant, canonical unit basis, alias decision, and reviewer |
| Reconciliation | Parsed equation, discrepancy, unresolved fields, accepted correction, and deterministic revision |

The original text and OCR geometry remain immutable evidence. Corrections append a reviewed value.
Product identity has levels:

```text
exact GTIN/SKU → merchant product → exact named package → product family → unresolved
```

Qwen may propose movement along that ladder but cannot invent a barcode, silently merge sizes,
convert “maslo” into one brand, or claim that two private labels are identical.

Money uses integer minor units or exact decimals with explicit currency and rounding. Receipt
validation attempts identities such as:

```text
sum(line totals) - line discounts - basket discounts
+ deposits + printed fees + rounding = printed grand total
```

The parser must support negative coupon lines, multipacks, weighed goods, loyalty prices, returned
containers, deposits, voids, and ambiguous abbreviations without forcing every merchant into one
grammar. A discrepancy remains visible; Qwen is never asked to “make the sum work.”

## Purchase, price, and consumption are different truths

Lifestyle Steward maintains three separate histories:

| History | What can establish it |
| --- | --- |
| **Price and purchase** | Accepted receipt, e-receipt, confirmed order, or attributable offer observation |
| **Household availability** | Confirmed count/scan plus acquisition, consumption, disposal, transfer, correction, and explicit inference |
| **Eating and wellness** | Magus-confirmed HFM check-in or journal under HFM ownership |

A receipt line can create an `acquired` inventory event. It never creates an HFM `consumed` event.
An approved HFM meal plan can create a `planned_need`; it never subtracts food from the fridge.
This separation prevents polished dashboards from manufacturing behavior.

Price comparison uses exact package identity where possible and a canonical unit basis only when
dimension and package content permit it. Loyalty, coupon, multibuy, delivery, deposit, and
marketplace prices remain separately conditioned observations. The system reports sample count,
date range, stores, identity level, and uncertainty beside every trend.

## Pantry and fridge projection

Household inventory may contain food, cleaning products, toiletries, pet supplies, hobby
consumables, and selected durable goods. Storage zones such as fridge, freezer, pantry, bathroom,
or workshop are operator-defined labels, not sensors.

Every projected item carries:

- product identity and original acquisition evidence;
- acquired, confirmed, opened, consumed, discarded, transferred, and corrected quantities;
- package and canonical unit;
- `confirmed`, `inferred`, or `unknown` status;
- printed expiry/best-before when actually observed;
- an optional visible depletion assumption with revision and last confirmation; and
- restriction, recall, or stale-source flags without pretending a remote catalogue controls the
  physical item.

An inferred expiry must not impersonate a printed date. “Probably low” is useful; “you have 220 g”
without evidence is not.

## Health, taste, and genetic boundary

Lifestyle Steward never reads the entire HFM profile. For one approved purpose, HFM may emit a
short-lived, versioned `ProvisionConstraintSet` containing only the fields the shopping or menu
Pattern needs:

- operator-declared hard ingredient/allergen exclusions;
- selected dietary pattern or food exclusions;
- optional operator-enabled nutrient target intervals;
- optional variety, preparation-time, and meal-plan requirements;
- profile revision, purpose, expiry, privacy class, and unresolved-source flags.

Raw journals, weight, measurements, symptoms, diagnoses, medications, movement history, clinical
documents, and genetic variants do not cross this bridge. A future clinically reviewed health
record might yield one narrow derived constraint, but raw genotype never enters product search,
restaurant queries, merchant sessions, catalogue artifacts, Qwen prompts, or checkout.

A model may not invent nutrigenomic advice. “Genetic profile says buy this food” is outside the
Composition unless a separately governed clinical project establishes the source, interpretation,
qualified review, safety, jurisdiction, expiry, and exact derived constraint. HFM's existing care
boundary remains intact.

Taste is operator testimony: liked, disliked, tired of, texture, cuisine, preparation effort, and
desired variety. Lifestyle may learn a corrigible preference from explicit choices. It does not
punish treats, optimize every meal, or turn deviations into adherence scores.

## Locale-neutral core and market packs

Lifestyle Steward is one Composition with three separately versioned layers:

| Layer | Owns | Must not own |
| --- | --- | --- |
| **Lifestyle core** | Receipt, product, offer, inventory, trip, cart, order, money, provenance, and uncertainty schemas plus reusable Patterns | Country merchant names, page selectors, model names, household address, or credentials |
| **Market pack** | Locale, language, currency, tax/deposit/unit conventions, merchant identities, public source profiles, receipt grammars, product aliases, catalogue/menu adapters, fixtures, and dated policy evidence | Household history, exact home, loyalty secrets, payment material, or automatic activation |
| **Household binding** | Selected stores, private anchors, route derivations, loyalty booleans, preferences, budgets, enabled sources, provider Runes, and retention | Shared market defaults or authority over another household |

Slovakia is the first example market pack, not a branch of the core. Names such as `market.sk@1`,
`receipt.kaufland.sk@1`, or `marketplace.bazos.sk@1` illustrate the desired stable identity shape;
they are not a current registry API. Another country composes equivalent identities around the
same core contracts.

Model choice is orthogonal to market choice. One operator may bind PaddleOCR and a local Qwen;
another may bind different OCR, vision, text, embedding, or routing providers that satisfy the
same measured capabilities. Domain schemas and deterministic reconciliation do not change merely
because an LLM changes.

### Source-pattern contract

Crawler extensibility belongs below the Composition as explicit Scout source profiles and typed
extractors. A market pack may contribute:

- official API, structured feed, HTML, PDF, rendered-page, or manually admitted document sources;
- store discovery and public merchant identity mappings;
- locale-specific receipt tokens, units, discounts, deposits, VAT labels, and date formats;
- selectors or extraction rules pinned to an origin, surface, revision, and fixture corpus;
- normalized output schemas and confidence/error shapes;
- terms and robots review timestamps, acquisition class, rate, cache, session requirement,
  privacy ceiling, and kill switch; and
- source-specific deterministic, replay, stale-page, injection, and layout-change tests.

Search, fetch, render, interact, session, and credential grants remain different even when one
adapter describes all their possible shapes. A generated extractor cannot upgrade itself from a
public PDF to a logged-in application, bypass access control, or keep crawling after its source
profile is disabled.

### Smith-assisted geographic bootstrap

The future Smith can make the default onboarding feel intelligent without turning probabilistic
guessing into runtime authority:

1. Lifestyle emits a minimized `MarketPortBrief`: declared country/language, optional coarse
   region, installed providers, desired merchants or use cases, and missing capabilities.
2. Smith reads the routed Composition/ADR scopes and the smallest relevant examples—such as Tech
   Scavenger for bazaar acquisition and this page for retail—rather than loading unrelated lore
   or private household records.
3. It inspects attributable target-market sources as hostile evidence and separates reusable
   Pattern law from locale, merchant, consumer-term, and page-shape assumptions.
4. It first tries to parameterize a verified generic Scout adapter. Only a genuine mismatch
   justifies a new typed adapter or market-pack contribution.
5. It fabricates schemas, registrations, fixtures, tests, provenance, documentation, and a
   preview in the Lab.
6. The Forge and focused trials verify the candidate. The Magus reviews exact origins,
   permissions, data disclosure, schedules, and effects before promotion.

This is in-context transfer from worked examples, not silent model-weight training. A Slovak
Bazoš adapter can teach the Smith the shape of a classified-market campaign; it cannot prove the
target bazaar's terms, messaging behavior, identity fields, or checkout law. Failed ports remain
attributable evidence for repair, never hidden fallback behavior.

## Store topology and the worthwhile-detour rule

The exact home address or private coordinate belongs behind a narrow location boundary. Merchant
queries, prompts, and ordinary traces receive only what they need: selected store ids, coarse
region, or derived walking distance/time.

A store record may contain:

- merchant/store id, public address, store type, opening-hour observation, and source;
- route duration/distance from an opaque private anchor for configured walking/driving profiles;
- user-stated familiarity, effort, range, queue, layout, and accessibility preferences;
- loyalty membership state as a boolean or opaque reference, never card credentials in prompts;
- observed catalogue scope and price conditions; and
- visit evidence only when the Magus records it.

The planner evaluates hard eligibility first, then a transparent utility vector:

```text
useful basket value
- extra travel/time friction
- additional-stop penalty
- stock and price uncertainty
- likely waste
+ explicit taste, convenience, movement, or novelty preference
```

It does not secretly convert health, time, or pleasure into euros. The Magus configures whether
the dimensions are ranked lexicographically, bounded by thresholds, or combined with visible
weights.

[OSRM](https://project-osrm.org/docs/) is one candidate for locally computing route and duration
matrices from OpenStreetMap data. A route remains an observation from a dated map/profile; it does
not prove current pavement, safety, accessibility, weather, closures, or opening hours.

## Catalogues, loyalty conditions, and stock

Research snapshot: **2026-07-29**.

Each merchant is a separate Scout origin profile with its own terms, robots decision, selectors,
rate, locale, store scope, credential/session policy, and kill switch. Official feeds, product
pages, downloadable catalogues, or manually admitted documents are preferred over rendered
crawling.

Current official Slovak examples demonstrate why conditions matter:

- [Kaufland publishes current and forward-looking store
  leaflets](https://predajne.kaufland.sk/aktualna-ponuka/letak.html), while also stating that
  promoted goods are available only while stocks last and that some prices require Kaufland Card.
- [Tesco publishes current and future catalogues scoped by store
  type/location](https://www.tesco.sk/akciove-ponuky/letaky-a-katalogy), and exposes separate
  Clubcard and online-shopping conditions.
- Lidl public pages, its application, and Lidl Plus are separate surfaces. Access to one does not
  grant a credential, session, loyalty profile, or automation right on another.

An offer observation records merchant surface, store scope, product identity, package, displayed
and previous price when present, unit price, multibuy, loyalty requirement, validity interval,
quantity limit, online/offline scope, image/text provenance, extraction revision, and stock
disclaimer. “Akcia,” “mimoriadna ponuka,” a crossed-out number, or a social post is not normalized
into a genuine discount without the required terms.

## Restaurant and public-social menu boundary

The least powerful menu source wins: structured official menu, restaurant website, current PDF,
then a separately admitted public social post. Each observation keeps restaurant, source URL,
publication and acquisition time, validity dates, meal text, price, declared allergens, and
uncertainty.

Public Facebook or another social post remains behind a site-specific Scout profile. Lifestyle
Steward does not log in without a separately authorized session, scrape private groups, collect
commenter profiles, evade access controls, infer availability from engagement, or treat an old
post as this week's menu. If compliant acquisition cannot be established, the restaurant is
manual-only.

Menu prose and photographs are hostile external claims. Missing ingredient closure or allergen
information remains unresolved. A restaurant suggestion can optimize taste, budget, route, and
declared options; it cannot certify preparation, cross-contact, stock, portion, nutrition, or
medical suitability.

## Online exploration, carts, and checkout

Search, product fetch, cart mutation, address disclosure, order submission, and payment are
different effects. No product page, CAPTCHA, login challenge, expiring discount, countdown, low
stock badge, model recommendation, or merchant redirect can authorize the next one.

For a discretionary AliExpress search such as figurines:

1. the Magus declares category, style, budget, exclusions, delivery horizon, and acceptable seller
   or material risk;
2. Scout acquires only permitted pages under a maintained AliExpress origin/session profile;
3. the local Mind groups exact seller, listing, variant, material/size, images, delivery, taxes or
   customs uncertainty, return terms, and reviews as claims;
4. the Altar presents a small candidate set with total-cost bounds;
5. the Magus selects one exact variant at HitL; and
6. checkout revalidates every consequential field before submitting once.

[AliExpress's current general terms](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202204182115_66077.html)
and [EU/EEA consumer transaction
terms](https://cdn.contract.alibaba.com/terms/EU_EE_UK_platform_service_agreement/20250514112355975/20250514112355975.html)
are adapter inputs, not permanent permission. Their current versions, effective dates, seller
identity, and checkout terms must be pinned and rechecked.

The model never receives card data, unrestricted merchant credentials, one-time codes, or the raw
delivery profile. A deterministic checkout handler resolves opaque secret references only after
effect-time Ward and consent checks. Novel discretionary items, seller changes, substitutions,
subscriptions, and cross-border uncertainty require live HitL.

A later standing authority may cover exact repeat grocery replenishment with maximum unit/total
price, merchant, SKU, quantity, delivery window, approved substitutions, rolling spend, and expiry.
It cannot cover “anything healthy,” “whatever is discounted,” figurines, or a changed seller.

## Capabilities and researched candidates

The Composition requests independently selectable capabilities:

| Need | Capability or tool shape |
| --- | --- |
| Receipt pixels | Reliquary materialization plus Prism decode, orientation, crop, unwarp, and enhancement |
| OCR | Local `ocr` with polygons, text, confidence, language, and provider revision |
| Semantic schema proposal | Local `vision` or `chat` with image/text input and strict structured output |
| Money and units | Exact decimal/minor-unit arithmetic, currency, unit normalization, and merchant grammar |
| Product identity | GTIN/SKU and reviewed alias catalogue with provenance |
| Food metadata | HFM's pinned food sources and optional Open Food Facts bridge; never sole allergen truth |
| Catalogue and menu acquisition | Scout `search`/`fetch`/`extract`; later separately granted render/session/interact |
| Route matrices | Private-anchor adapter plus selected local or explicitly consented route provider |
| Checkout | Merchant-specific cart/order effects, Ward, HitL, Toll, and delivery-profile references |

Research snapshot: **2026-07-29**.

| Role | Candidate | Fit and caveat |
| --- | --- | --- |
| Lightweight first-pass OCR | [PaddleOCR PP-OCRv6](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 toolkit with tiny/small/medium recognition tiers and Latin-script coverage; receipt accuracy, Slovak abbreviations, polygons, CPU latency, and exact model artifacts still require local fixtures |
| Document parser alternative | [PaddleOCR-VL 1.6](https://github.com/PaddlePaddle/PaddleOCR) | Compact `0.9B` document VLM and structured output candidate; it is an alternative measured profile, not permission to discard raw OCR geometry |
| Local schema and visual reviewer | [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | Candidate for image-plus-OCR reconciliation and strict JSON; may hallucinate lines, aliases, totals, or confidence and therefore remains upstream of deterministic checks |
| Local route engine | [OSRM](https://github.com/Project-OSRM/osrm-backend) | BSD-2-Clause route/table engine over a pinned OpenStreetMap extract; geocoding, map freshness, pedestrian profile quality, and hosting remain separate responsibilities |

The first reliable receipt path is deliberately layered:

```text
PaddleOCR observation → Qwen schema proposal
→ deterministic money/unit reconciliation → Magus correction
```

Running Qwen end-to-end without retained OCR evidence is a different candidate profile and must
beat the layered pipeline on Slovak fixture accuracy, uncertainty calibration, arithmetic
integrity, latency, and resource use before promotion.

## Priority, schedules, overlap, and budgets

| Work | Target priority | Overlap and residency |
| --- | ---: | --- |
| Receipt correction, trip planning, cart review, or checkout consent | `70` | Interactive; local OCR/Mind warm preferred only for the active turn |
| Merchant order mismatch, cancellation, delivery, or recall alert | `100` | Deterministic notification/hold; no model authority escalation |
| Restaurant or same-day shopping choice | `50` | Interactive/ordinary; one fresh result replaces stale menu work |
| Catalogue, price, and menu refresh | `20` | Coalesce by merchant and validity period; warm-only preference |
| Inventory projection and weekly trend review | `20` | Coalesce; no ambient camera, location, or forced model swap |

No schedule watches the operator, microphone, camera, location, bank, email, or fridge. A timer may
refresh enabled public sources or derive from already consented records. It cannot create a receipt,
consumption event, store visit, cart, or order.

Budgets include retained image bytes, OCR pages, merchants, catalogue pages, menu sources, product
candidates, model calls, route pairs, extra stops, cart mutations, checkout attempts, money,
delivery exposure, schedules, and retries. An expired flyer or menu normally coalesces away rather
than accumulating as a backlog.

## Durable data, migration, and recovery

Candidate application-owned records include:

- receipt artifact, transform, OCR observation, schema proposal, accepted receipt, line, printed
  discount/tax/deposit, reconciliation, and correction;
- merchant, merchant surface, public store, private route anchor reference, route observation,
  loyalty-condition reference, and store preference;
- product, GTIN/SKU, merchant alias, package, unit basis, identity decision, source, and
  supersession;
- price and offer observation, catalogue/menu release, validity, stock disclaimer, restaurant,
  dish candidate, and unresolved ingredient state;
- inventory item, storage zone, acquisition, confirmation, open, consumption link, disposal,
  transfer, correction, and expiry observation;
- shopping intent, HFM constraint reference, trip plan, cart draft, substitution rule, approval,
  order attempt, payment/settlement reference, order, shipment, delivery, refund, and dispute.

Graph checkpoints own one Invocation cursor, not the receipt ledger, pantry, cart, merchant session,
or payment truth. Each parked run pins Pattern, image pipeline, OCR, schema, parser, product
catalogue, merchant adapter, selectors, route profile, policy, and tool revisions.

An unknown checkout or payment result closes retry until merchant and rail reconciliation. A
catalogue parser upgrade imports beside prior observations. A product alias change does not rewrite
historical receipt text. A route-map update does not rewrite why an old shopping plan was chosen.

## Privacy, consent, retention, export, and deletion

Receipts reveal time, location, habits, health-adjacent purchases, alcohol, medication-like goods,
loyalty identity, payment fragments, household composition, and routines. They are `restricted`
even when every line item looks mundane.

- Local OCR and inference are defaults. Remote OCR, vision, route, or catalogue services require
  named provider, purpose, field set, retention, and duration consent.
- Payment fragments, loyalty ids, receipt numbers, addresses, barcodes, faces, backgrounds, and
  unrelated screen/photo content are minimized and redacted from ordinary traces.
- Exact home/delivery anchors, merchant credentials, payment material, and one-time codes never
  enter prompts.
- HFM restrictions remain in their namespace. Lifestyle stores only the purpose-bound constraint
  reference and fields its own decision actually used.
- Restaurant and seller data remains attributable third-party data and is not promoted into
  general memory or training.
- Corrections preserve original OCR evidence and reviewer identity; deletion inventories both.

An export contains accepted receipts and lines, original/canonical units, product identities,
price and inventory histories, preferences, sources, derivations, orders, approvals, and checksums.
Raw images, location anchors, health constraints, merchant sessions, and delivery data are
separate opt-in encrypted export compartments.

Deletion first disables schedules and checkout authority, closes or surfaces unresolved orders,
revokes merchant and delivery-profile access, drains atomic effects, removes personal rows,
derivations, indexes, caches, and admitted artifacts, and writes a content-free receipt. It cannot
erase merchant orders, messages, payments, deliveries, or public posts already held elsewhere.

## Riddle and adversarial proof

The trial set must include skew, blur, folds, shadows, long receipts, Slovak diacritics, dot-matrix
print, duplicate lines, weighted goods, negative coupons, loyalty prices, multipacks, deposits,
voids, ambiguous decimal separators, cropped totals, multiple VAT bases, foreign currencies, and
receipts whose arithmetic deliberately fails.

Mandatory invariants include:

- OCR and Qwen outputs never become accepted records without deterministic validation and the
  configured review threshold;
- a model cannot repair a discrepancy by changing evidence;
- purchase never becomes consumption;
- a catalogue offer never becomes stock;
- missing ingredient closure never becomes allergen-safe;
- a loyalty price never applies without its condition;
- a cheaper item never bypasses an HFM hard restriction;
- exact location, health, genetic, loyalty, address, and payment data never leak into public
  queries or prompts;
- a stale page, redirect, CAPTCHA, session failure, or discount never escalates authority;
- checkout submits at most once and unknown outcome blocks replay; and
- deletion during OCR, catalogue refresh, or parked checkout cannot resurrect personal content.

## Smallest proving slice

Using synthetic Slovak receipt images and a tiny local product fixture:

1. admit one straight and one deliberately skewed receipt through a fake in-memory artifact port;
2. run one pinned local PaddleOCR profile with network disabled and retain text, polygons, and
   confidence;
3. map merchant, date, currency, five line items, one discount, one deposit, and total into the
   typed candidate schema;
4. reconcile exact arithmetic and force one seeded mismatch to remain unresolved;
5. compare deterministic parsing with and without a local Qwen schema proposal;
6. display source crops for uncertain fields and accept an explicit correction;
7. compute product/store unit-price trends from several accepted fixtures;
8. create inventory acquisition candidates without any consumption event;
9. export the complete lineage, delete it, and verify rows, derivatives, checkpoints, and images
   are absent; and
10. restart between OCR and acceptance without duplicating a committed receipt.

No real receipt, health profile, catalogue, restaurant, merchant login, address, order, payment,
route service, remote provider, or personal data belongs in this slice.

## Staged roadmap

1. **Locale-neutral receipt law and first pack:** typed core schema, money/units, privacy,
   retention, corrections, migration, export, deletion, adversarial trials, and synthetic Slovak
   fixtures kept in a distinct first market pack.
2. **Paddle-first local ingestion:** Prism transforms, OCR evidence, merchant grammars, review
   table, deterministic reconciliation, and restart safety.
3. **Qwen reconciliation:** local schema proposal, source-bound confidence, product aliases, and
   measured benefit over deterministic parsing.
4. **Market bootstrap and Smith port:** optional minimized geo onboarding, market/source profile
   selection, generic adapter conformance, one non-Slovak synthetic port, Lab generation, review,
   promotion, disable, and repair behavior.
5. **Price memory:** exact product identities, package/unit normalization, store-conditioned
   trends, discounts, deposits, and neutral reviews.
6. **Inventory projection:** acquisition events, confirmations, zones, consumption/disposal links,
   expiry evidence, corrections, and visible uncertainty.
7. **HFM bridge:** approved shopping list plus minimal `ProvisionConstraintSet`; no raw health or
   genetic data crossing.
8. **Local trip planner:** private anchors, public stores, local route matrix, store friction,
   one/multi-store plans, and worthwhile-detour explanation.
9. **Catalogue and menu watch:** independently governed merchant, restaurant-site, PDF, and
   public-social adapters with the Slovak Kaufland, Lidl, and Tesco profiles as first examples,
   plus validity and stock uncertainty.
10. **Cart concierge:** read-only product search, exact variants, substitutions, total-cost and
   delivery review without checkout.
11. **One checkout:** one allowlisted merchant sandbox, fresh HitL, deterministic address/payment
    boundaries, submit-once, reconciliation, expected delivery, cancellation, and refund receipt.
12. **Discretionary marketplace:** AliExpress figurine search and one exact human-selected variant
    only after origin/session/consumer-term and cross-border trials pass.
13. **Repeat replenishment:** optional standing authority for exact low-risk SKUs only after spend,
    substitution, delivery, revocation, crash, and replay boundaries are proved.

## Current delivery gaps

Current LychD can carry immutable artifact metadata and image-modality declarations, but it cannot
store or materialize receipt bytes through a complete Reliquary, run a Prism OCR/Vision pipeline,
register this Composition, schedule catalogue Occurrences, own lifestyle migrations, or expose the
described Altar projections. Scout, Toll, mature Ward, route/location custody, merchant sessions,
MarketPack/Composition registries, Smith fabrication, checkout, and delivery reconciliation remain
absent or Designed.

HFM is itself an architecture-only reference. Its proposed shopping list, source catalogue, and
constraint solver do not deliver this receipt, inventory, retail, restaurant, or order workflow.

## Continue

- Read [Health, Food & Movement](health-food-and-movement.md) for the wellness and restriction
  owner.
- Read [Prism](../sepulcher/extensions/prism.md) and [Vision](../adr/36-vision.md) before receipt
  image ingestion.
- Read [Scout](../sepulcher/extensions/scout.md) before any catalogue, menu, merchant, or
  marketplace acquisition.
- Read [Sovereign Consent](../adr/25-hitl.md), [Ward](../sepulcher/extensions/ward.md), and
  [Toll](../sepulcher/extensions/toll.md) before cart mutation, checkout, address disclosure, or
  payment.
- Read [Tech Scavenger](tech-scavenger.md) before reusing used-market evidence or cash-on-delivery
  law.
- Return to the [Composition Portfolio](index.md).
