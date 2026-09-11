---
title: Accounting Office
icon: material/book-check
---

# :material-book-check: Accounting Office

A business owner needs to know what arrived, what is owed, what has been paid, and what the books can honestly say. An invoice in mail and a matching bank movement are evidence to connect, not a finished accounting judgment. Accounting Office would preserve that connection through review, reconciliation, and an explainable period close.

This **candidate study**, prepared **2026-09-11**, proposes `accounting.office` revision `1`, outside the accepted Portfolio. It supplies no source implementation, registered Pattern, executable configuration, live mail/bank integration, or jurisdiction support claim. [Workflow](../../adr/28-workflow.md#composition-identity-revision-and-retirement) owns acceptance and revision law; [State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery evidence.

## One accounting lifecycle

The proposed owner is one entity's accounting lifecycle:

```text
source evidence → proposed classification/match → validated and reviewed journal
→ reconciliation → period close → accepted scope, exact partial, unresolved, or handoff
```

An `AccountingOfficeRequest@1` would bind the entity, period, purpose, source coverage, exact compliance profile, rule versions, reviewer authority, privacy policy, and effect ceilings. An `AccountingOfficeOutcome@1` would identify accepted records and reports, exceptions, unresolved balances, missing coverage, and required handoffs. Refusal and an indeterminate external action remain explicit outcomes. A plausible report cannot substitute for missing evidence.

During a pilot, the external accountant's books remain the reference. Accounting Office shadows them, records disagreements, and prepares evidence for resolution; it cannot silently replace their books or treat agreement on one period as general accounting acceptance. Acceptance names the reviewer, scope, rule versions, exceptions, and reconciliation evidence.

## Records that survive the conversation

The candidate would retain distinct, linked records for:

- **Evidence:** each source occurrence, custody and coverage observations, original bytes and their separate digest, extraction version, and attributed corrections. Identical bytes can arrive through several occurrences; a digest alone does not identify the business event.
- **Commercial obligations:** counterparty identity and evidence; invoices, accounts payable/receivable, credit notes, due dates, disputes, advance allocations, and supporting contracts.
- **Money and books:** bank observations, match proposals, journal entries and postings, transaction and functional currencies, FX source/date/rate, rounding, reconciliation exceptions, and period closure evidence.
- **Assets and recurring rights:** acquisition/disposal basis, separate book and tax schedules, impairment evidence where applicable, subscription rights, renewal dates, cancellation conditions, and future obligations.
- **Compliance outputs:** attributed tax positions, applicable rule versions, report and filing candidates, reviewer disposition, and separately observed submission/acceptance receipts.

The accounting kernel must use decimal arithmetic with deterministic balancing, rounding, currency precision, effective-date resolution, and rule selection. Model output proposes classification or explanation; it does not choose arithmetic or establish tax law. Posting requires validated accounts, dates, amounts, provenance, and applicable review. Posted corrections append reversals or adjustments rather than rewriting history. A closed period is locked; authorized reopening records a reason and produces a successor close while preserving its predecessor.

## Portable rules, isolated entities

The proposed Composition-owned `EntityComplianceProfile@1` binds legal form, tax residence, functional/reporting currency, accounting period, typed registrations and their effective dates. A versioned `JurisdictionPack@1` resolves accounting, company-law, income-tax, VAT/GST/withholding, and filing rules and schemas. Transaction facts and treaty overlays may change which rules apply. Provider dialect translates transport fields; it never decides law.

Neither a country string nor a successful import proves support. Missing, conflicting, expired, or inapplicable rules block the affected judgment with an exact reason. Portability requires a second wholly synthetic foreign profile with distinct rules, effective-time changes, calendar, and currency. Its fixture must demonstrate deliberate rule selection and refusal without fallback; this study makes no live foreign legal assertion.

Each admitted rule needs its authoritative source, source digest, publication and effective dates, applicability predicates, reviewer, executable revision, and expected fixtures. Research findings cannot activate themselves. A rule change identifies affected open cases; it cannot silently recompute a filed return or closed period. Interface language, bank country, tax residence, establishment, and transaction jurisdiction remain separate configuration facts.

Each entity keeps separate books, credential references, source coverage, grants, and acceptance authority. A counterparty buying services establishes a commercial relationship, not permission to operate that counterparty's books. Shared software and reusable profiles do not create shared financial authority.

## Proposed Patterns and configuration

These are proposed Pattern identities, separate from the Composition revision:

| Pattern | Bounded result |
| --- | --- |
| `accounting.admit_evidence@1` | Deduplicated evidence references, coverage gaps, quarantined items, or refusal. |
| `accounting.review_journal@1` | Validated/reviewed postings or exact unresolved proposals. |
| `accounting.reconcile_period@1` | Reconciled scope and explicit unmatched observations/obligations. |
| `accounting.close_period@1` | Accepted scoped close/report candidates, partial close, blocker, or accountant handoff. |
| `accounting.review_obligations@1` | Asset/subscription accounting updates and evidenced renewal obligations. |
| `accounting.prepare_invoice@1` | Validated invoice or correction candidate with exact customer, supply, tax position, and numbering scope. |
| `accounting.prepare_filing@1` | Frozen return/report candidate, applicable schema validation, open exceptions, and authorized handoff. |
| `accounting.assess_cash@1` | Assumption-bound cash scenarios and a separately authorized handoff candidate. |

The following is **non-loadable, nonbinding design notation**, not a Rune or accepted schema. Exact registrations and deployment syntax remain future work.

```text
composition: accounting.office / revision 1
entity_ref: synthetic-entity-a
compliance_profile: synthetic-a / revision 1
jurisdiction_pack: synthetic-rules-a / revision 1
mail: provider_ref, capability_revision, read_scope, history_coverage
bank: provider_ref, capability_revision, account_refs, read_scope
documents: intake_ref, accepted_media, quarantine_policy
effects: ingestion_policy_ref, review_policy_ref, payment_policy_ref
privacy: local_policy_ref, approved_target_refs, disclosure_budget
close: period_ref, reviewer_ref, exception_policy_ref
```

## Intake and effects have different authority

`MailAdapter`, `BankAdapter`, and `DocumentAdapter` name proposed application-facing ports, not existing global LychD classes or new Core offices or Extension Domains. Mail separates read, draft, send, and delivery observation. Bank separates read, payment preparation, submission, status observation, and reconciliation. Document intake retains original evidence and quarantines untrusted content. Any required registration must identify the receiving owner, typed Contribution, Provider, profile revision, and Registrant under [Extensions](../../adr/05-extensions.md); these names do not justify stuffing bank or mail operations into `ToolConnector`.

Provider capability declarations must expose supported operations, coverage, limits, and recovery semantics. Unsupported operations refuse or produce a manual handoff. Cursors track traversal, not document identity. At-least-once ingestion deduplicates without losing distinct arrivals; partial imports, unavailable attachments, and historical gaps remain visible. Refunds, fees, FX differences, and payments without invoices require their own evidence and classification. A bank movement alone never becomes an automatic expense.

Bounded standing policy may authorize low-impact ingestion and repeated exact actions. Fresh consent is required when the applicable HitL or effect policy requires it; there is no mandatory per-click doctrine. Approval binds the exact entity, operation, recipient/account, payload, amount/currency, policy, and expiry as applicable. Mutation invalidates it. Credentials stay in their owning custody and never enter model context.

Observed submission is not delivered mail, settled money, or an accepted filing. An unclear timeout stays indeterminate. Recovery observes and reconciles the original external identity before any retry; uncertain execution cannot silently create a duplicate payment or message.

Issuing an invoice reserves its number within the entity's declared series and preserves the issued revision; a correction links its predecessor. Preparing a document, issuing it, sending it, receiving payment, and recognizing revenue have distinct records. A filing candidate likewise freezes its source/period and rule/schema revisions before submission. Neither generation nor local validation manufactures an official acceptance receipt.

## Privacy before remote cognition

Here **Portal** means remote provider cognition. The candidate follows [Context](../../adr/21-context.md#privatization-and-the-privacy-cut) and [Security](../../adr/09-security.md#portal-privatization-and-egress):

```text
local minimization + classification + lineage
→ consumer-specific PrivacyCut + independent verification
→ Security EgressDecision for exact target, payload, purpose, and expiry
→ transmission → quarantined return → validation and local admission
```

Local processing removes unnecessary identities, metadata, quoted correspondence, attachment text, and embedded banking information before a remote candidate is considered. Amounts, dates, relationships, and unusual combinations can themselves identify a business. Pseudonyms, reversible identifiers, and hashes are not anonymity. Semantic abstraction must preserve the question's declared invariants; if that cannot be verified, the work remains local or refuses the remote road.

Any re-identification map remains separately controlled locally under Context's lease law. No map, raw history, credential, or local decision evidence accompanies the request. Related calls, retries, and derived summaries count toward cumulative disclosure. A failed local capability or privacy check creates no implicit cloud fallback. A returned recommendation remains untrusted and cannot directly post, pay, send, or file. [State](../../state-of-the-work.md#context-privatization-and-portal-egress) records that the shared privacy machinery is not delivered.

Statutory records retain their actual legally required contents. An accountant may need exact originals through a separately authorized, exact-recipient exchange; model anonymization cannot replace that channel or alter the books. Applicable Security disclosure law still governs that exchange.

## A wholly synthetic advance

A fictional entity receives **2,400 currency units** before providing services across two periods. The intake records the bank observation and contractual evidence separately, then proposes an advance allocation. Under an explicitly synthetic rule fixture, reviewed evidence of service completion supports allocation of 1,200 units in each period. The example asserts no real tax treatment; tax timing remains a separately resolved position.

A missing completion record leaves the affected allocation unresolved. An invoice mismatch retains both originals and the discrepancy. A cash scenario may compare retaining the remaining advance against future obligations without changing the journal. If remote reasoning is eligible, it receives only the abstract synthetic problem required for that task, never a private transaction pattern disguised by substituted names.

## Foreign owners and the stopping line

Asset/subscription inventory here concerns accounting value, rights, and renewal obligations. Physical warehouse custody, stock counting, and IoT remain with their actual owner. Accounting Office consumes exact settled count/valuation evidence and records its accounting interpretation. A Suite becomes necessary only when a promised result must coordinate several owners' live Invocations; [Choosing a Home](../choosing-a-home.md) retains that routing test.

Cash strategy and tactics produce scenarios with assumptions, liquidity constraints, and uncertainty. A Broker client handoff is separate: a report provides neither trading agency nor payment authority. An external accountant or filing system remains an unmanaged external precondition unless an exact admitted integration says otherwise. No foreign reference lends credentials, lifecycle control, or settlement authority.

## Fixtures that can defeat the proposal

| Falsifying fixture | Required evidence |
| --- | --- |
| Duplicate mail plus bank ingestion | Preserve occurrences; prevent duplicated obligations/postings without merging distinct events. |
| Crash at every durable transition and effect boundary | Resume from receipts; retain unresolved state without invented completion. |
| Mutation after approval | Reject stale authority before the changed effect. |
| Currency mismatch or missing rules | Block affected posting/report; never guess conversion or inherit another entity's pack. |
| Reopened period | Preserve locked predecessor, authorized correction, and successor close. |
| Payment timeout and repeated delivery | Reconcile original identity; prove no duplicate semantic payment. |
| Adversarial privacy leakage | Detect metadata, quotes, attachments, linkage and cumulative reconstruction; refuse uncertain disclosure. |
| Accountant discrepancy | Preserve both positions and attributable resolution; no silent overwrite. |

Composition ownership itself fails if these records, judgments, recovery, and finish already belong to an exact existing owner, or if regional variation requires incompatible lifecycles concealed in profiles. A mere report projection, provider wrapper, or Product label cannot establish the proposed office. Conversely, distinct deployment credentials alone do not justify another Composition.

Implementation would begin with local synthetic receipts and the deterministic accounting kernel, then an explicitly authorized read-only shadow against reference books. Accounting acceptance follows demonstrated reconciliation and reviewer judgment; optional external effects come later with their own evidence. Portfolio acceptance establishes a maintained design boundary, while executable delivery requires source contracts, focused verification, and maintained receipts. Until then this remains a candidate study.
