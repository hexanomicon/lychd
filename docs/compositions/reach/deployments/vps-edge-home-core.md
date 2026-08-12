---
title: VPS edge + home core
icon: material/home-switch-outline
---

# :material-home-switch-outline: VPS edge + home core

`reach.edge-home.public@1` keeps the home Ward, Vessel, Workers, corpus, provider/A2A gate, effect
ledger, and Phylactery as the only application authority. The VPS is an application-specific
Discord transport/effect edge with bounded durable custody. It is not a Vessel, Phylactery,
Legionnaire, A2A peer, policy engine, cognition fallback, or replica.

The profile is guest/public-only. Discord Gateway events are not independently signed evidence
that home can verify: a compromised edge can fabricate a Discord subject. Therefore an edge-
relayed identity can never unlock enrolled/private Context, tools, consent, or effects. A future
private profile needs independent human proof presented directly to home Ward, such as an admitted
step-up credential; guild roles, account fluency, tunnel membership, and edge assertions do not
qualify.

## Two sealed host manifests

One profile generation closes two separately compiled manifests and one compatibility/enrolment
receipt binding their digests, service Principals, schema range, Tether peer generation, private
Veil route revision, `ReachAuthorityEpoch`, and `ReachEdgeEpoch`.

| VPS edge may hold | Home alone may hold |
| --- | --- |
| Discord bot token, encrypted spool key, exact Tether peer key, relay mTLS/service credential | Phylactery/database credential, Ward and task Sigils, corpus/index, private Context, provider/A2A credentials and application effect ledger |
| Discord Gateway/delivery adapter, bounded ingress and delivery-attempt journals, relay | Reach core, Workers, corpus refresher, Portal/A2A gate, isolated edge-admission/claim/settle adapter, private Veil |

The roles are separate rootless services with exact mounts, secrets, networks, budgets, and local
service authentication. The VPS has no PostgreSQL route or home Codex. The application road is:

```text
home Tether peer -- outbound UDP/keepalive --> public VPS WireGuard endpoint
VPS Discord edge -- outbound WSS/HTTPS --> Discord
VPS relay -- HTTPS/mTLS over Tether --> private home Veil --> isolated Reach edge adapter
home provider/A2A gate -- outbound HTTPS --> exact admitted destination
```

Private Veil binds only its Tether address and admits exact bounded event-admission, delivery-
claim, delivery-settlement, and unauthoritative-health operations. It never routes to PostgreSQL,
Reach core, corpus writer, provider gate, Altar, model API, host control, or a public listener.
All application HTTP is VPS-initiated, so NAT at home needs no public application entrance.

## Ingress custody

The VPS commits `EdgeIngressEnvelope@1` before forwarding:

```text
BUFFERED → FORWARDING → HOME_ADMITTED | HOME_REFUSED
BUFFERED | FORWARDING → EXPIRED | QUARANTINED
RECEIVED → EDGE_REFUSED_SIZE
```

The record binds both epochs, edge Principal, adapter revision, Discord application/Habitat/event
identity, canonical payload digest, bounded encrypted payload, receipt/expiry times, forwarding
generation, and eventual home admission identity. Home revalidates current credential and epochs,
freshness, guild/channel/subject bounds, digest, quotas, and public/guest policy, then atomically
commits or deduplicates `DiscordEventAdmission@1`. Same identity with changed digest is a security
fault. Only that authenticated commit receipt permits raw-payload retirement.

One ingress envelope admits at most 32 KiB encoded and 64 KiB after decoding/decompression. The
adapter enforces both while streaming, before canonical-body allocation or encryption; overflow
persists only bounded event identity, digest/observed-size evidence, and `EDGE_REFUSED_SIZE`, never
the body or a home admission. The ingress spool admits at most 5,000 rows, 128 MiB of encrypted
payload, and 24 hours of age;
reaching any limit expires/refuses oldest-unadmitted custody visibly and stops accepting new work
before Gateway heartbeat or reconciliation capacity is threatened. The delivery-attempt journal
admits at most 2,000 rows and 64 MiB; each immutable delivery payload is at most 16 KiB canonical
encoded and 32 KiB after platform projection. Home rejects oversize as `KNOWN_REJECTED(size_limit)`
before committing `SUBMITTING` or returning bytes to the edge. The journal retains terminal
evidence for seven days and stops new claims at 80% pressure. Exact retries and settlements take
priority over new work. When home is offline
the edge performs no cognition, corpus choice, provider/A2A call, Sigil minting, turn judgment, or
synthesized reply. The first profile excludes offline slash-command work: the interaction expires
without an edge-authored bot response and never later becomes a Reach turn. A preauthorized static
operational reply would require a separate delegated-effect profile and home-committed payload,
scope, expiry, budget, deterministic effect/nonce, revocation, and reconciliation contract.

## Discord effect custody

Home alone commits `ReachTurn@1` and `DiscordDeliveryIntent@1`. The edge polls home and persists
`EdgeDeliveryAttempt@1`, binding epochs, Principal, home intent/effect identity, immutable payload
digest, deterministic Discord nonce, attempt identity, claim generation, Discord observation, and
settlement status.

1. The edge persists `CLAIM_REQUESTED` with one attempt identity and asks home with that identity.
2. Home atomically binds one intent to it and commits `SUBMITTING` before returning the payload.
3. The edge persists `PREPARED`, then `SUBMITTING`, before Discord REST.
4. It records the known or unknown Discord result and retries only authenticated settlement to home.
5. Home idempotently adopts that evidence and alone settles `ReachDelivery@1`.

Time never reassigns a cross-host `SUBMITTING` intent: home cannot know whether the edge crossed
the external boundary during a partition. Only the same durable attempt may resume/reconcile.
Loss of the edge journal leaves delivery `UNKNOWN`; a changed payload or attempt refuses.

## Failure, compromise, and acceptance

Tether failure applies the bounded spool rules and creates no alternate route or edge claim. VPS
compromise revokes the bot token, edge Principal/mTLS credential, spool key, Tether peer, and edge
epoch; closes the exact route; quarantines the spool; assumes buffered public queries exposed; and
reconciles Discord identities before rebuild. It does not require provider-key rotation unless
boundary evidence says those keys crossed. Home compromise stops new claims, revokes home service,
provider/A2A, Veil, and Tether credentials, treats issued delivery work as tainted, preserves the
edge journals without executing new instructions, and restores one fresh home authority epoch.

Acceptance proves hostile/replayed/old-epoch relay refusal; no WAN database path; no private caller
upgrade; spool TTL/item/byte overflow; offline slash-command expiry with zero edge reply; exact admission dedupe;
partition at every claim/send/settle boundary; unreassignable `SUBMITTING`; loss-to-`UNKNOWN`;
credential isolation; both compromise drills; and home-only ↔ edge/home migration without two
Gateway owners or two application authorities.

[Deployment matrix](index.md) · [Tether](../../../sepulcher/extensions/tether.md) ·
[Veil](../../../sepulcher/extensions/veil.md)
