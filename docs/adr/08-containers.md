---
title: 8. Containers
icon: material/cube-outline
---

# :material-cube-outline: 8. Containers

!!! abstract "Context"
    LychD manifests its one-host service body as rootless Podman Quadlets and systemd user units.
    systemd and cgroup v2 supply supervision, dependency ordering, and observable physical state;
    rootless Podman supplies containers. There is no external control plane. The supported substrate
    is a free Linux host with systemd, cgroup v2, and rootless Podman/Quadlet.

Every layer entrusted with host authority, isolation, lifecycle, or recovery must remain
operator-inspectable, modifiable, rebuildable, and replaceable. Private extensions and Portals may
contribute at their boundaries; neither may become a required owner of LychD's continuity.

## Decision: the manifested body

The generated topology contains `lychd.pod`, one `lychd-animator-*.target` for each
lifecycle-managed Soulstone, compatible `lychd-coven-*.target` aggregates, the migration gate,
Phylactery and Vessel, and admitted extension units. A Portal is a logical remote connection; it
does not summon a local container.

Joined containers set `StartWithPod=false`: creating the shared namespace must not awaken every
Soulstone. Core ordering starts migration, Phylactery, and Vessel in sequence. Only
`persistent_resident` Animator targets join normal boot; dedicated non-residents require the
Orchestrator or explicit break-glass operator action.

`groups`, `concurrency.conflict_domains`, and `alliances` are different declarations. Groups make
an operator-facing Coven; conflict domains declare finite-hardware exclusion; alliances grant
neither. The compiler forms the exact conflict graph: an explicit empty set declares coexistence;
an omitted dedicated non-resident domain becomes compiler-owned `default-exclusive` and conflicts
with every non-empty effective domain; residents may not declare a non-empty conflict set. It emits
one Animator target per Soulstone, its target/service ordering and binding, and one lexically
ordered `Conflicts=`/`After=` edge for each conflicting pair. Friendly grouping never implies safe
coexistence.

Each Animator target `Requires=` and is `Before=` its service; the service `BindsTo=` and is
`After=` the target. A Coven only `Wants=` and is `After=` compatible targets, whose members are
`PartOf=` that Coven. A compiler rejects a Coven with an internal conflict before it writes units.

## Three authorities, one transition

The [Orchestrator](23-orchestrator.md) decides that a lifecycle transition is admissible; the
[Dispatcher](22-dispatcher.md) grants capability; systemd performs the physical unit transaction.
No office substitutes for another. Before asking systemd, the application closes relevant
admission, drains leases, revalidates configuration and observed world, attests the generated
target/service/Coven graph and its loaded sources against Scribe ownership, then submits the
transition. It observes settlement, readiness, and recovery under [Privilege](10-privilege.md).
Direct target start bypasses those gates and is break-glass only.

Every mount, device, secret, port, and network edge is declared per unit. Joined containers share
a Pod network and therefore need service authorization as well as mounts; generated host ports are
explicitly `127.0.0.1:`. `UserNS=keep-id` belongs at the Pod and application units use `User=%U`;
the Phylactery retains its PostgreSQL image user and its data mount uses `:U,Z`. These identities
allow assigned paths, not ambient Crypt access. The Tomb is a separate Security/Workers boundary,
not a safer Pod member.

## Scribe inscription

Scribe materializes one validated generation transactionally: render and validate in staging,
verify the prior ownership receipt and exact binding sites, make same-filesystem backups, replace
the declared files, remove only stale receipt-named files, publish the new receipt, and daemon
reload. A changed source, generation, site, secret, filename, mode, symlink, or foreign collision
refuses; a failed transaction restores the previous files and receipt. Ambiguity authorizes no
deletion. Filename resemblance never proves ownership.

The declared compilation/materialization path is available within its State boundary. It is not a
receipt that a real operator host started Podman, systemd, GPU, or a model:
[State of Work](../state-of-the-work.md#systemd-podman-embodiment) owns that distinction.

## Consequences

The generated graph is inspectable and rootless, but it is not authority to start arbitrary
services or to infer host execution from a rendered unit.
