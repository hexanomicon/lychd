---
title: VPS edge + home core
icon: material/home-switch-outline
---

# :material-home-switch-outline: VPS edge + home core

A mention arrives while home is offline. The VPS can preserve it within exact limits, but it cannot choose evidence, think, or author a reply. `reach.edge-home.public@1` leaves Ward, Vessel, Workers, corpus, provider/A2A gate, effect ledger, and Phylactery solely at home.

The edge is bounded Discord transport/effect custody, not a Vessel, replica, Legionnaire, sovereign peer, or fallback cognition service. Its relayed Gateway identities can be fabricated if it is compromised, so the profile is guest/public-only. Private enrollment would require separate human proof directly to home Ward; roles, fluency, tunnel membership, and edge assertions cannot supply it.

## Two sealed host manifests

The generation pins both manifests, service Principals, schema range, Tether peer generation, private Veil route, and `ReachAuthorityEpoch`/`ReachEdgeEpoch` in a compatibility/enrollment receipt.

The VPS needs enough custody to receive and relay Discord work: the bot token, encrypted spool key, exact Tether key, relay mTLS/service credential, Gateway/delivery adapter, bounded journals, and relay. It has no PostgreSQL road or home Codex.

Home retains database credentials, Ward/task Sigils, corpus/index, private Context, provider/A2A credentials and the application ledger. It also runs core/Workers/refresher/gates/isolated edge adapter/private Veil. On both hosts, distinct rootless services have exact mounts, secrets, networks, budgets, and local authentication.

```text
home Tether peer -- outbound UDP/keepalive --> public VPS WireGuard endpoint
VPS Discord edge -- outbound WSS/HTTPS --> Discord
VPS relay -- HTTPS/mTLS over Tether --> private home Veil --> isolated Reach edge adapter
home provider/A2A gate -- outbound HTTPS --> exact admitted destination
```

Veil binds only its Tether address and exact event-admission, delivery-claim, settlement, and unauthoritative-health operations. It never routes to database, core, corpus writer, provider gate, Altar, model API, host control, or public listener. VPS initiates application HTTP, so home needs no public application entrance.

## Ingress custody

The edge commits `EdgeIngressEnvelope@1` before forwarding:

```text
BUFFERED → FORWARDING → HOME_ADMITTED | HOME_REFUSED
BUFFERED | FORWARDING → EXPIRED | QUARANTINED
RECEIVED → EDGE_REFUSED_SIZE
```

The envelope binds the epochs, edge Principal, adapter, platform application/Habitat/event identity, canonical digest, bounded encrypted payload, receipt/expiry times, forwarding generation, and eventual admission identity. Home uses that binding to recheck credentials/epochs, freshness, guild/channel/subject, digest, quotas, and guest policy before atomically committing or deduplicating `DiscordEventAdmission@1`. Reusing an identity with changed bytes is a security fault.

Forwarding alone does not establish home custody. Retire a successfully forwarded raw payload only after receiving an authenticated commit receipt. Local expiry or refusal instead follows the limits below and must never claim home admission.

Ingress custody and delivery custody have separate ceilings:

| Material | Ceiling | Action at the boundary |
| --- | --- | --- |
| Ingress payload | 32 KiB encoded; 64 KiB expanded | Enforce while streaming, before canonical allocation/encryption. Overflow retains bounded identity/digest/observed-size and `EDGE_REFUSED_SIZE`, never body or home admission. |
| Encrypted ingress spool | 5,000 rows; 128 MiB; 24 hours | At any limit, visibly expire/refuse oldest unadmitted custody and stop new work before heartbeat/reconciliation suffers. |
| Delivery payload | 16 KiB canonical; 32 KiB projected | Home returns `KNOWN_REJECTED(size_limit)` before committing `SUBMITTING` or releasing oversize bytes. |
| Delivery journal | 2,000 rows; 64 MiB | Stop new claims at 80% pressure; exact retry/settlement outranks new work. |
| Delivery terminal evidence | Seven days | Keep the terminal record for this bounded retention. |

Offline home permits no edge cognition, corpus selection, provider/A2A calls, Sigils, judgment, or synthesized reply. Offline slash commands expire without edge response and never later become turns. Even static operational replies would need a separate delegated-effect profile and home-committed payload, scope, expiry, budgets, deterministic nonce/effect, revocation, and reconciliation.

## Discord effect custody

Home commits `ReachTurn@1` and `DiscordDeliveryIntent@1`. The edge's `EdgeDeliveryAttempt@1` binds epochs/Principal, intent/effect, payload digest, deterministic nonce, attempt, claim generation, observation, and settlement:

1. Persist `CLAIM_REQUESTED` with one attempt identity, then request that claim.
2. Home atomically binds the intent and commits `SUBMITTING` before returning bytes.
3. Edge persists `PREPARED`, then `SUBMITTING`, before Discord REST.
4. Record known/unknown result and retry only authenticated settlement to home.
5. Home idempotently adopts evidence and alone settles `ReachDelivery@1`.

A network partition can hide whether the edge sent, so elapsed time cannot reassign cross-host `SUBMITTING`. Only the same durable attempt may resume or reconcile. If its journal is lost, retain `UNKNOWN`; refuse a changed payload or attempt.

## Failure, compromise, and acceptance

When Tether is lost, enforce the spool limits and use no alternate route. A compromised VPS requires revoking the bot, edge Principal/mTLS, spool key, Tether peer, and edge epoch. Close the route, quarantine the spool, treat public queries as exposed, and reconcile Discord before rebuilding. Rotate provider keys only if evidence shows they crossed to the edge.

Home compromise has a different scope. Stop claims, revoke home/provider/A2A/Veil/Tether credentials, and mark issued work as tainted. Preserve edge journals without allowing new execution, then restore fresh home authority.

Qualification must show that hostile, replayed and old-epoch relay cannot obtain admission or upgrade the profile to private access, and that no WAN database route exists. Exercise every spool limit, offline slash expiry with zero reply, dedupe, and every partition between claim, send and settlement. Prove that submission cannot be reassigned and that journal loss preserves uncertainty. Finally, verify isolation, both compromise drills, and migration without duplicate Gateway owners or authorities.

[Deployment matrix](index.md) · [Tether](../../../sepulcher/extensions/tether.md) · [Veil](../../../sepulcher/extensions/veil.md)
