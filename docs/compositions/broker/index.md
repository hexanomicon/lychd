---
title: Broker
icon: material/briefcase-account-outline
---

# :material-briefcase-account-outline: Broker

Broker carries one client request through a regulated service firm. The reference vertical is a
Slovak non-life insurance intermediary beginning with PZP: somebody calls to check cover, the firm
looks through its governed product knowledge, and returns an attributable answer, prepared act,
human handoff, or exact blocker.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `broker.office` revision `1` |
| **Principal Pattern** | `broker.service_case@1` |
| **Begins with** | an admitted `ClientContact@1`, one requested action, business policy, product catalogue, and current staff authority |
| **Can return** | an attributable answer, reviewable act, human handoff, or exact blocker |
| **Stops before** | unlicensed advice, undisclosed automation, payment, signature, binding, or unsupported product claims |

A deployment pins the firm's legal role, jurisdictions, represented institutions, disclosures,
complaint route, record duties, and named human authority. Neither a configured product nor a
fluent model response expands that mandate.

## Open the office

- [Cases](cases.md) owns why the client contacted the firm, what action is requested, and how that work ends.
- [Products](products.md) owns the firm's dated product knowledge, eligibility, comparisons, quotes, and expiry.
- [Channels](channels.md) owns how contacts arrive and how reviewed results leave without becoming authority.

Broker is the application office, not LychD's internal queue broker.

Related: [Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md) ·
[IAM](../../adr/38-iam.md)
