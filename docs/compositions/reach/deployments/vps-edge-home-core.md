---
title: VPS edge + home core
icon: material/home-switch-outline
---

# :material-home-switch-outline: VPS edge + home core

A mention arrives while home is offline. The VPS can preserve it within exact limits, but it cannot choose evidence, think, or author a reply. `reach.edge-home.public@1` leaves Ward, Vessel, Workers, corpus, provider/A2A gate, effect ledger, and Phylactery solely at home.

The edge is bounded Discord transport/effect custody, not a Vessel, replica, Legionnaire, sovereign peer, or fallback cognition service. Its relayed Gateway identities can be fabricated if it is compromised, so the profile is guest/public-only. Private enrollment would require separate human proof directly to home Ward; roles, fluency, tunnel membership, and edge assertions cannot supply it.

## Two sealed host manifests

The generation pins both manifests, service Principals, schema range, Tether peer generation, private Veil route, and `ReachAuthorityEpoch`/`ReachEdgeEpoch` in a compatibility/enrollment receipt.

VPS holds the bot token, encrypted spool key, exact Tether key, relay mTLS/service credential, Gateway/delivery adapter, bounded journals, and relay. Home holds database credentials, Ward/task Sigils, corpus/index, private Context, provider/A2A credentials and application ledger, plus core/Workers/refresher/gates/isolated edge adapter/private Veil. Distinct rootless services have exact mounts, secrets, networks, budgets, and local authentication. VPS has no PostgreSQL road or home Codex.

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

Bind epochs, edge Principal, adapter, platform application/Habitat/event identity, canonical digest, bounded encrypted payload, receipt/expiry times, forwarding generation, and eventual admission identity. Home rechecks credentials/epochs, freshness, guild/channel/subject, digest, quotas, and guest policy, atomically committing or deduplicating `DiscordEventAdmission@1`. Same identity with changed bytes is a security fault. Successful forwarding permits raw-payload retirement only after an authenticated commit receipt; local expiry or refusal follows the bounded custody limits below and never claims home admission.

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

Time cannot reassign cross-host `SUBMITTING`; a partition hides whether the edge sent. Only the durable same attempt may resume/reconcile. Journal loss leaves `UNKNOWN`; changed payload/attempt refuses.

## Failure, compromise, and acceptance

Tether loss invokes spool limits without alternate route. VPS compromise revokes bot, edge Principal/mTLS, spool key, Tether peer, and edge epoch; closes the route, quarantines spool, treats public queries as exposed, and reconciles Discord before rebuild. Provider keys rotate only if evidence shows they crossed. Home compromise stops claims, revokes home/provider/A2A/Veil/Tether credentials, taints issued work, preserves edge journals without new execution, and restores fresh home authority.

Acceptance covers hostile/replayed/old-epoch relay, no WAN database/private upgrade, every spool limit, offline slash expiry with zero reply, dedupe, every claim/send/settle partition, unreassignable submission, journal-loss uncertainty, isolation, both compromise drills, and migration without duplicate Gateway owners or authorities.

[Deployment matrix](index.md) · [Tether](../../../sepulcher/extensions/tether.md) · [Veil](../../../sepulcher/extensions/veil.md)
