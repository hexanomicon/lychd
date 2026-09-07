---
title: Toll
icon: material/cash-register
---

# :material-cash-register: The Toll

> _A price may enter the gate as a whisper. Only bounded Will may let it leave as consequence._

**Toll** is LychD's optional economics Extension Domain for priced remote labor. It is
**Designed**: no payment machinery or safe HTTP `402` handler ships.
[State of Work](../../state-of-the-work.md#x402-payments) owns delivery;
[ADR 41](../../adr/41-x402.md) owns the law.

An HTTP `402`, invoice, or quote is an untrusted proposal. It carries no authority to
sign, settle, retry, identify a caller, grant access, or enlarge a budget. Toll admits no global
system-wallet middleware that pays the challenge and retries. Neither Agent nor Dispatcher
receives wallet or signing authority.

## First road, later rails

Initial Toll delivery is issuer-local. An operator may manually grant **MANA** service credits,
then optionally fund an exact balance through one conventional payment processor or charge one
bounded request as pay-as-you-go. MANA is an issuer-qualified, account-bound balance in that
issuer's Counting House. It is not cash or cryptocurrency; the initial profile cannot be spent
with or accepted by another issuer and carries no peer transfer, cash redemption, or cross-issuer
conversion.

Tithe meters model-token and resource consumption; the Counting House separately reserves, debits,
credits, releases, refunds, and reconciles MANA. A purchased balance remains the issuing operator's
service obligation. Spending it still requires the same authenticated Principal, eligible task,
budget authority, idempotency, and delivery accounting as an external payment.

Only the authorized issuer boundary may issue, expire, or correct MANA; an Agent, model, or ordinary
tool cannot. The ledger appends the authority and grant reason or independently verified funding
identity for every entry, uses compensating corrections instead of rewriting history, and prevents
reservation from making available balance negative. A webhook, client-supplied receipt, pending
authorization, or ambiguous settlement cannot fund spendable MANA.

The two practical flows remain distinct:

```text
MANA → quote → reserve local balance → execute → debit / release / refund → reconcile
PAYG → quote → reserve budget → authorize → Irreversible Gate → settle → execute → reconcile
```

Conventional pay-as-you-go, x402, and any later crypto scheme are distinct settlement adapters over
the same quote, reservation, authorization, delivery, refund, and reconciliation law. x402 is not
a currency. The first delivered adapter need not use it, and selecting it later does not imply a
project-native token or chain.

## One external paid request

A destination-pinned connector produces a candidate request and quote.
Execution-road policy considers quotes among roads that satisfy capability, privacy, policy, and
resource eligibility. Toll judges their economic terms and reserves the exposure;
[Dispatcher](../../adr/22-dispatcher.md) binds an already eligible capability without ranking prices. Two unequal planes then carry the same request.

For Intercom, casting work and teaching a missing Spell are different purchased resources. Each
needs its own exact quote, content identity, budget reservation, consent or standing authority,
idempotency key, delivery condition, and reconciliation. Payment for one never buys or retries the
other.

The **Counting House** parses one supported, versioned quote in integer units, accounts its cost,
reserves worst-case exposure, and reconciles receipts. It holds no spend key. The reservation binds
an authenticated Principal and budget owner; trusted merchant or service; exact method and
canonical destination; request-body digest and purchased resource; asset and network; maximum
amount including fees; expiry; redirect policy; and idempotency key. Unknown versions, schemes,
networks, merchants, destinations, amounts, fee bounds, changed terms, or expired authority fail
closed.

Policy rejects the request, applies one explicitly bounded low-risk standing authority, or parks
the Run for live consent to the exact terms. Significant or novel spend requires
[HitL](../../adr/25-hitl.md). Approval covers the stated maximum, never a later challenge. The
Magus administers policy without exemption from signer or key safety.

The **Irreversible Gate** has no model or general tool surface. It revalidates the pinned
authorization, live reservation, and caps; atomically consumes the reservation; signs and submits
the one named settlement at most once; and records the external-effect identity. After independently
authorized settlement, the original connector may make at most one proof-bearing replay to the
same destination. That replay cannot initiate another payment. Reconciliation then joins
settlement to useful delivery.

## What settlement cannot buy

**Tithe** accounts currency-neutral model-token usage, generated media, concurrency, queue weight,
and hardware time against a stable Principal or service grant, including when every payment
adapter is disabled. Money or a receipt cannot mint or widen a Sigil or [Ward](ward.md) authority,
expose memory or tools, bypass consent, or displace protected local work. A purchased grant exists
only at the intersection of settlement evidence, Ward policy, capability policy, and available
resources. Currency-free [Legion](legion.md) work still needs quotas, reservations, attribution,
and evidence.

Settlement cannot authenticate a peer, make an unknown Spell compatible, admit a teaching bundle,
publish an implementation, activate a catalogue generation, or resume the refused Invocation. It
may satisfy only the economic condition of an otherwise eligible act.

Payment and delivery are not atomic. Settlement may yield no useful artifact; apparent success may
be false or unusable. Refund, credit, dispute, expiry, paid-but-undelivered, and ambiguous outcomes
remain explicit durable states.

## What survives uncertainty and restore

Quote, reservation, authorization, submission, settlement, delivery, refund, expiry, and
uncertainty form a durable idempotent chain. An unknown settlement triggers investigation and
reconciliation, never another signature. Local rollback or a database restore cannot rewind
money; spending stays closed until external state is reconciled.

[Oculus](oculus.md) receives redacted observations, never ledger authority. Keys, signatures,
bearer proofs, preimages, invoices, and unrestricted wallet credentials stay outside prompts,
Codex values, logs, traces, and artifacts.

Protocols and settlement rails are adapters around this law, never rival ledgers. The first
implementation may remain local; every external adapter must pin one exact provider or protocol
profile and conformance corpus. x402 and crypto rails are later options, not first-delivery
requirements. A shared asset, validator network, or sovereign chain requires a later
amendment to [ADR 41](../../adr/41-x402.md#deferred-shared-and-sovereign-settlement) and every
affected Covenant rather than silently entering as an adapter.
