---
title: Toll
icon: material/cash-register
---

# :material-cash-register: The Toll

**Purpose:** The Toll is the intended economic boundary for priced remote labor. It separates
finding and accounting for a price from the isolated authority that can make value leave the
Sepulcher.

**Delivery boundary:** LychD has no Toll package, quote or budget ledger, signer, settlement path,
or safe response to a payment challenge. There is nothing to enable or invoke on this page.
[State of the Work owns the exact x402 boundary](../../state-of-the-work.md#x402-payments), while
[ADR 41](../../adr/41-x402.md) owns the accepted commitment, signer, and reconciliation law.

**Extension form:** Toll is an optional economic Domain manifested as governed middleware and
isolated effect handlers, not as a mandatory wallet service. Quote parsers, settlement rails,
signers, and paid Portal connectors are adapters around one commitment and reconciliation law.
Currency-neutral Tithe accounting remains useful when every payment adapter is disabled.

> _A price may enter the gate as a whisper. Only bounded Will may let it leave as consequence._

The Toll's promise is not that the Lich becomes a wallet with opinions. Its promise is stricter:
economic consequence becomes visible, attributable, bounded, and interruptible before it becomes
irreversible.

!!! danger "A challenge is not authority"
    An HTTP `402` response is controlled by a remote server. It may propose a price; it may never
    authorize payment. LychD must not implement a generic interceptor that pays a challenge and
    retries from a system wallet. Merchant substitution, quote drift, redirects, loops, and
    concurrent requests would otherwise turn untrusted HTTP into spending authority.

## I. The Two Courts

The future Toll has two deliberately unequal planes.

### The Counting House — quote and accounting

The Counting House may parse a versioned payment challenge, normalize integer monetary units,
compare candidate costs, reserve a bounded budget, and reconcile receipts. It must bind every
proposal to an authenticated principal and budget owner, a trusted service or merchant, the exact
method and canonical destination, a request-body digest, the purchased resource, asset and network,
the maximum amount including fees, expiry, redirect policy, and idempotency key.

It holds no spend key and cannot settle. The **Dispatcher** may use its quotes as one planning input,
after capability, privacy, and resource feasibility; neither the Dispatcher nor an Agent receives
wallet authority.

### The Irreversible Gate — authorization and signing

Signing belongs behind a narrow effect boundary with no model or tool surface and no broad Vessel
authority. The signer must independently verify the pinned authorization, atomically consume its
reservation, enforce per-effect and rolling caps, and permit at most the one settlement operation
named by that authorization. Unknown versions, schemes, networks, destinations, amounts, or quote
changes fail closed.

The Magus may administer policy but is not exempt from wallet safety. Significant or novel spend
remains live [Human-in-the-Loop consent](../../adr/25-hitl.md); only explicitly bounded low-risk
classes may ever use preauthorization. Approval means _these exact maximum terms_, never “whatever
the next challenge asks.”

## II. The Rite of a Paid Request

The intended sequence is explicit:

1. A destination-pinned connector produces a candidate request and asks for a quote.
2. The Counting House validates the quote against merchant identity, request digest, resource,
   amount, fees, asset, network, expiry, redirect policy, and budget.
3. Policy rejects it, admits a bounded standing authority, or parks the run for the Magus to review
   the exact terms.
4. Accounting reserves the worst-case total before any key is used.
5. The isolated signer revalidates the same facts, signs once, submits once, and records the
   external-effect identity.
6. After independently authorized settlement, the original connector may make at most one
   proof-bearing replay to the same pinned destination. It does not initiate another payment.
7. The ledger reconciles settlement and useful delivery. An uncertain settlement is investigated;
   it is never answered by signing again.

Payment and delivery are not atomic. A settled payment may still yield no useful artifact, and a
successful response does not make its content true. Refund, credit, dispute, expiry, and
paid-but-undelivered outcomes therefore belong in the receipt chain rather than being hidden behind
an HTTP retry.

## III. The Tithe Is Not the Wallet

The **Tithe** is currency-neutral resource accounting: token or image budgets, concurrency, queue
weight, and bounded hardware time associated with a stable principal or service grant. It must work
when every payment adapter is disabled.

A payment may purchase a precisely defined quota grant, but money cannot mint a Sigil, widen an IAM
scope, expose memory, reveal a tool, bypass consent, or displace protected local work. The effective
resource grant is always the intersection of payment receipt, Ward policy, capability policy, and
available resources.

Owned Legion nodes may be configured for currency-free delegation—the Magus need not pay the Magus
over a settlement rail—but they still require quotas, reservations, attribution, and evidence.
“No payment” never means “no accounting” or “no safety cap.”

## IV. Protocols Are Adapters, Not Synonyms

The first implementation must pin one explicit x402 profile and conformance corpus. x402, L402,
Lightning invoices, Wallet Connect, and Nostr Zaps are distinct protocols or settlement adapters;
none should be documented as an alias for another. Each later adapter carries its own identities,
replay rules, custody model, finality, privacy, failure behavior, and receipts.

Extensions may contribute bounded protocol or facilitator adapters and declarative paid products.
They may not install arbitrary global spending middleware, hold unrestricted keys, define a second
ledger truth, or bypass the host-owned authorization and signer gates.

## V. The Receipt Outlives the Trace

Money does not rewind when the Phylactery is restored. Every quote, reservation, authorization,
submission, settlement, delivery, refund, and uncertain outcome therefore needs a durable,
idempotent receipt chain and post-restore reconciliation before spending reopens.

Native **[Oculus](./oculus.md)** may observe redacted transitions and reconciliation lag, but a trace
is not a financial ledger. Keys, signatures, bearer proofs, preimages, invoices, and unrestricted
wallet credentials must not enter prompts, Codex values, ordinary logs, traces, or artifacts.

## VI. The Road to the Gate

The safe build order is: define immutable financial identities and integer money types; build quote,
budget, reservation, and receipt accounting without money movement; establish the isolated signer
and hard caps; prove one allowlisted test connector through crash and replay tests; then add seller
routes, metering, and optional settlement adapters. A peer marketplace comes later still—it needs
its own product, reservation, delivery, refund, abuse, and dispute law beyond x402.

> _Next act: read the [x402 delivery boundary](../../state-of-the-work.md#x402-payments), then
> prove quote and receipt accounting without money movement before opening the signer gate._
