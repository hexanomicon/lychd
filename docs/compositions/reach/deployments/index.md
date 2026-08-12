---
title: Deployment profiles
icon: material/tune-variant
---

# :material-tune-variant: Deployment profiles

Reach can keep its durable body at home, split only the Discord edge onto a VPS, or live as a
restricted standalone VPS body. These are immutable, mutually exclusive reference profiles—not
security levels and not independent `use_vps`, `trusted`, `tether`, `veil`, or `local_db` toggles.
[Configuration](../../../adr/12-configuration.md) selects one exact profile revision.

!!! warning "Designed, not deployable"
    The profiles are acceptance targets. The application selector, deployment-manifest compiler,
    Reach adapters and records, Tether, Veil, remote Ward IAM, and general Egress Gate do not ship.
    [State of Work](../../../state-of-the-work.md) remains the delivery owner.

## Choose the body

| Profile | Sole application authority | Tether / Veil | Honest trade-off |
| --- | --- | --- | --- |
| [`reach.home.public@1`](home-public.md) | home Ward, Vessel, Workers, corpus, effect ledger, and Phylactery | neither; all platform and provider roads are outbound | simplest and keeps durable truth at home; Reach is unavailable when home is offline |
| [`reach.edge-home.public@1`](vps-edge-home-core.md) | the same home body; VPS owns only bounded Discord transport/effect custody | exact Tether plus a private Tether-only Veil on home | buffers within fixed limits while home is offline; adds a security-critical two-host protocol |
| [`reach.vps.public@1`](vps-public.md) | independent VPS-local Ward, Vessel, Workers, corpus, effect ledger, and Phylactery | neither in its outbound baseline | availability-first; VPS compromise exposes the complete restricted public body |

For home durability, choose `reach.home.public@1` unless bounded offline intake is worth the extra
VPS edge. A backup on another host is a recovery artifact, never a second live authority.

Tether and Veil are orthogonal mechanisms:

- **Tether** supplies an exact private network road; it grants no application authority.
- **Veil** terminates and constrains an admitted HTTP entrance; it need not be public.
- Home-only and standalone outbound VPS need neither.
- The split profile needs both because the VPS calls a private HTTP contract on home.
- A later public callback or A2A server is a different profile revision, not an ingress switch.

The profiles are not ordered low-to-high trust. Compare authority location, private-data blast
radius, home availability dependency, VPS compromise consequence, operational complexity, and
recovery. Tunnel possession, VPS ownership, Discord membership, and a `public` label prove none of
caller identity, consent, egress admission, or provider trust.

## Invariants across every profile

For one `(Discord application, Habitat partition)`, one immutable deployment generation binds:

- exactly one profile revision, `ReachAuthorityEpoch`, and active Phylactery;
- exactly one `ReachEdgeEpoch` and Discord Gateway/delivery credential owner;
- one corpus authority and one provider/A2A egress gate;
- exact per-host manifest digests, service Principals, credential references, and routes; and
- every event, attempt, delivery, settlement, backup, and migration receipt to both epochs.

Simultaneous activation, an unknown profile combination, or an old-epoch request fails before
Bind or admission. PostgreSQL is never exposed, shared, synchronously replicated, dual-written,
or failed over across the WAN. A transport journal can prove narrow custody of bytes and external
effect observations; it cannot own a Run, Context, Ward decision, Sigil, corpus judgment,
`ReachTurn`, or application terminal.

Every service keeps the split required by its profile manifest. Local placement does not erase
the blast radius: compromise of the home host can expose the home body, while compromise of the
standalone VPS can expose its whole restricted body. Every remote model/A2A attempt still requires
an exact destination/task policy, a Cut when required, and a fresh payload-bound `EgressDecision`.

## Selection and migration

A profile change is an Evolution effect, never hot reload:

1. close new admission and freeze the intended target generation;
2. drain or explicitly classify every provider/A2A attempt, delivery intent, `UNKNOWN` effect,
   Gateway cursor, and edge-spool row;
3. fence the old authority and edge epochs, stop the old Gateway owner, and revoke its routes and
   workload credentials;
4. if authority moves, export exactly the admitted public Reach partition with schema, profile,
   corpus/source, retention, dedupe, and external-effect identities; restore it transactionally
   into an inactive body—never copy a whole home Phylactery or use live replication;
5. compile and attest the new per-host manifests, rotate custody-changing bot/provider/Tether/Veil
   credentials, and enrol their new service Principals;
6. activate the new authority last, then reopen admission and reject every old-generation message.

Home-only ↔ edge/home retains the home Phylactery but still drains and transfers the Discord edge.
Any transition to or from standalone VPS transfers authority and refuses while a nonterminal or
indeterminate effect cannot be preserved safely. After the new authority admits work, rollback is
another quiesced migration; the old database remains fenced/read-only.

## Administrative separation

Application Tether peers, Veil routes, and service credentials never authorize SSH, Podman,
systemd, deployment, secret rotation, provider consoles, or `magus:*`. Host administration uses a
separately governed infrastructure path. A later operator VPN peer needs a different key, routes,
identity, and authorization contract.

Continue with the exact profile:
[home-only](home-public.md) ·
[VPS edge + home core](vps-edge-home-core.md) ·
[standalone VPS](vps-public.md)
