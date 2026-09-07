---
title: Deployment profiles
icon: material/tune-variant
---

# :material-tune-variant: Deployment profiles

When home loses power, should Reach go quiet, retain bounded incoming messages elsewhere, or continue as an independent restricted body? That availability choice determines where authority and credentials must live.

These profiles are **Designed, not deployable**. [State of Work](../../../state-of-the-work.md#composition-portfolio-delivery) records Reach’s delivery boundary. [Configuration](../../../adr/12-configuration.md) will select one exact immutable profile, not combine loose topology switches.

## Choose the body

| Profile | Sole application authority | Roads and trade-off |
| --- | --- | --- |
| [`reach.home.public@1`](home-public.md) | Home Ward, Vessel, Workers, corpus, effect ledger, Phylactery. | All outbound; no Tether/Veil. Durable truth stays home and Reach is unavailable with that host. |
| [`reach.edge-home.public@1`](vps-edge-home-core.md) | The same home authority; VPS has only bounded Discord transport/effect custody. | Exact Tether and private home Veil. Bounded offline intake adds a security-critical two-host protocol. |
| [`reach.vps.public@1`](vps-public.md) | Independent VPS-local Ward, Vessel, Workers, corpus, ledger, Phylactery. | Outbound baseline without Tether/Veil. VPS compromise exposes this entire restricted public body. |

The [one-question E2E contract](vps-public.md#first-e2e-contract-one-public-discord-question) is shared by all three profiles; its standalone VPS page also explains that profile's particular custody and recovery. Home-only is the default for home durability unless bounded offline intake justifies the edge. A backup elsewhere is recovery material, never a second authority. These are mutually exclusive profiles, not security levels or independent `use_vps`, `trusted`, `tether`, `veil`, or `local_db` options.

Tether grants an exact private road, not application power. Veil constrains an admitted HTTP entrance and need not be public. The split profile needs both because VPS initiates private HTTP to home. Later callbacks or A2A serving need a different profile revision. Compare authority location, data exposure, home dependency, compromise consequences, complexity, and recovery; no public label, guild membership, tunnel, or VPS ownership proves identity or egress permission.

## Invariants across every profile

For each `(Discord application, Habitat partition)`, one deployment generation binds one profile revision, `ReachAuthorityEpoch`, active Phylactery, `ReachEdgeEpoch`, Gateway/delivery credential owner, corpus authority, and provider/A2A gate. Pin per-host manifest digests, service Principals, credentials/routes, and both epochs in every event, attempt, settlement, backup, and migration receipt.

Unknown combinations, simultaneous activation, and stale epochs fail before Bind/admission. PostgreSQL is never WAN-exposed, shared, live-replicated, dual-written, or failed over. A transport journal witnesses bytes/effects without owning Run, Context, Ward, Sigil, corpus judgment, turn, or terminal truth. Service separation remains mandatory locally too. Every remote attempt needs exact destination/task policy, required Cut, and fresh payload-bound egress decision.

## Selection and migration

Changing profile is a quiesced Evolution effect:

1. Close admission and freeze the target generation.
2. Drain or classify all provider/A2A attempts, delivery intents, `UNKNOWN` effects, Gateway cursors, and spool rows.
3. Fence authority/edge epochs, stop the old Gateway owner, and revoke its routes/credentials.
4. When authority moves, export only the admitted public Reach partition with schema/profile/corpus/source/retention/dedupe/external-effect identity closure; restore transactionally into an inactive body. Never copy the whole home Phylactery or live-replicate it.
5. Attest new host manifests, rotate custody-changing bot/provider/Tether/Veil credentials, and enroll service Principals.
6. Activate the new authority last; reopen admission while rejecting old-generation messages.

Home-only/edge-home retain the home database but still transfer the Discord edge. Standalone transitions refuse when nonterminal or indeterminate effects cannot be safely preserved. After new admission begins, rollback is another quiesced migration and the old database remains fenced/read-only.

## Administrative separation

Application peers, routes, and service credentials cannot authorize SSH, Podman, systemd, deployment, rotation, provider consoles, or `magus:*`. Infrastructure administration and any later operator VPN peer require separate keys, routes, identity, and authorization.

[Home-only](home-public.md) · [VPS edge + home core](vps-edge-home-core.md) · [Standalone VPS](vps-public.md)
