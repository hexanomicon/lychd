---
title: Broker
icon: material/briefcase-account-outline
---

# :material-briefcase-account-outline: Broker

Broker carries one client request through a regulated service firm. It finishes with an
attributable answer, a prepared act, a human handoff, or a precise blocker; it never hides missing
authority behind a fluent reply.

The reference vertical is a Slovak non-life insurance intermediary beginning with PZP. That choice
pressures identity, private records, product evidence, deadlines, human review, and external effects
without claiming that LychD is itself a broker or adviser.

!!! note "Current material"
    No Broker Pattern, business or client surface, mail or telephone intake, case ledger,
    insurer adapter, or regulated effect is registered or executable. The Altar, local Sigil, and
    Run engine are common substrate, not this application.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `broker.office` revision `1` |
| **Principal Pattern** | `broker.service_case@1` |
| **Application begins with** | an admitted `ClientContact@1`, business policy, and current staff authority |
| **Application can return** | an answer, reviewable act, human handoff, or exact blocker |
| **Application stops before** | unlicensed advice, undisclosed automation, payment, signature, binding, or unsupported product claims |

A deployment pins the firm's legal role, jurisdictions, represented institutions, disclosures,
complaint route, record duties, and named human authority. Stale or missing authority stops the
affected case. Neither a configured product list nor a model response expands that mandate.

## Contact to case outcome

1. An email, form, call, or future peer envelope is preserved with its native identity, time,
   attachments, provenance, and deduplication evidence.
2. The office resolves the sender only to the assurance the channel actually proves. An address,
   caller ID, familiar voice, or Discord identity can suggest a relationship; none authorizes a
   protected read or effect.
3. A `ServiceCase` is opened or matched, then pinned to business policy, product releases, staff
   assignment, deadlines, consent, and one declared purpose.
4. Deterministic tools validate identifiers, dates, money, required fields, eligibility, ranking,
   payload closure, and effect identity. A Mind may extract, explain, or draft; it cannot invent a
   premium, exclusion, client need, provider decision, or completed act.
5. For PZP, the comparison names the represented universe, retrieval time, hard eligibility,
   criteria, fees or relationships, gaps, and expiry. “Best” is replaced by an attributable claim
   such as “lowest price among these eligible offers under these criteria.”
6. The broker reviews the exact proposal. Preparation does not authorize sending, signing, buying,
   or binding; a changed payload receives a new revision and review.
7. An admitted adapter submits once and records the result. An unknown acknowledgement parks the
   case for reconciliation instead of creating a second application or contract.

Narrow supporting Patterns may enrol a client, admit a contact, prepare an effect, hand work to a
human, schedule one expiring follow-up, or export and delete a client's records. They remain finite
scores with separate authority; the service-case Pattern does not inherit every child effect.

## Business records and surfaces

Broker keeps distinct records for the firm and its authority, Principals and relationships,
contacts and source artifacts, cases and waits, product releases and live quote observations,
comparisons and explanations, prepared effects and receipts, consent and disclosures, corrections,
complaints, exports, and deletion fences. Records identify whether a fact was imported, stated by
the client, confirmed by staff, proposed by a model, derived deterministically, or observed from a
provider. A summary never replaces the original evidence.

| Surface | Office |
| --- | --- |
| **Business Console** | staff manage cases, facts, products, drafts, approvals, deadlines, and corrections in business language |
| **Client Web** | a client submits bounded material and sees only records and choices authorized for that Principal |
| **Altar** | the technical operator inspects Runs, evidence, readiness, consent, and recovery |

The Business Console and Client Web are separate typed projections, not recoloured Altar screens.
Neither talks directly to PostgreSQL, a model server, or an insurer. Their projection and packaging
boundary is still designed.

## Authority, privacy, and case recovery

Inbound prose, documents, quoted mail, audio, provider pages, and peer material remain hostile data.
Credentials and raw client secrets stay outside model Context. Local inference is preferred, but
“local” does not waive access, retention, backup, export, or deletion rules. A future remote-model
route must use the exact privacy and egress decision owned by
[Context](../adr/21-context.md) and [Security](../adr/09-security.md); transformation alone grants
nothing.

The first vertical admits no medical record, credit judgment, affordability decision, payment,
signature, or policy binding. Consent to converse, store records, record a call, disclose fields,
and perform a financial effect are separate decisions. Every privileged read and effect rechecks
current authority after a queue, wait, restart, or revocation.

Cases name their current owner, wait, deadline, pinned revisions, and terminal or partial outcome.
Silence is unknown. Product refresh never rewrites an in-flight comparison. After restart, stale
authority, an expired quote, an unavailable Pattern, or an uncertain provider effect parks for
review rather than replaying conversation. Deletion first fences new admission, then drains or
contains atomic work and removes governed derivatives; legal holds and third-party custody remain
explicit.

## Proving office

Use one synthetic Slovak firm, one staff Principal, ten synthetic clients, one reviewed PZP product
release, a fake provider, local inference, PostgreSQL, and email intake only. Prove unauthenticated
and known-client handling, duplicate and hostile-message containment, one complete renewal, one
missing fact, one ineligible case, one provider timeout, attributable comparison, draft-review-send,
unknown-send reconciliation, restart during a wait, human handoff, scoped export, and deletion.
No public route, live insurer, medical data, telephone, Portal, payment, binding, training, or
autonomous promotion enters this slice.

Continue with [Workflow](../adr/28-workflow.md), [IAM](../adr/38-iam.md), or the
[Composition Portfolio](index.md).
