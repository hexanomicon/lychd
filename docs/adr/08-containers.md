---
title: 8. Containers
icon: material/cube-outline
---

# :material-cube-outline: 8. Containers

!!! abstract "Context"
    LychD manifests its one-host service body as rootless Podman Quadlets and systemd user units.
    systemd and cgroup v2 supply supervision, dependency ordering, and observable physical state;
    rootless Podman supplies containers. There is no external control plane.

## Supported host policy

LychD is committed to developing and supporting free and open-source (FOSS) software on FOSS hosts
only. Every layer entrusted with host authority, isolation, lifecycle, or recovery must remain
operator-inspectable, modifiable, rebuildable, and replaceable. The operator must retain full
control over host integration and removal.

Linux with systemd, cgroup v2, and rootless Podman/Quadlet is the supported substrate. macOS,
Windows, and other non-FOSS host stacks are unsupported hosting platforms. Running LychD in a
Linux VM or container on a non-FOSS host does not change that support boundary: the outer host
still controls its execution and storage.

Private extensions and Portals retain their separate admission boundaries under
[Extensions](05-extensions.md). Admission does not bring their implementations or host platforms
into Core's support scope. Neither may become a required owner of LychD's continuity.

### Rationale: FOSS commitment and the agentic transition

LychD's architectural commitment is to an open host that its operator can inspect, rebuild,
replace, and reshape through authorized, recoverable changes. Agentic control over the body must
remain accountable to the operator across the software stack. A proprietary host places part of
that authority beyond the project's ability to maintain and replace it.

Supporting macOS or Windows would require separate integrations for service supervision,
networking, filesystem ownership, privilege boundaries, secrets, CLI control, and recovery. Each
would add an ongoing implementation and verification burden. We commit that effort to deep Linux
integration and the guarantees of one supported host architecture.

Our strategic forecast is that the approaching agentic revolution will converge on Linux and
displace proprietary operating systems. **We do not expect Windows or macOS to survive that
transition.** We will not spend LychD development time sustaining compatibility with platforms we
expect that transition to leave behind.

Linux-only hosting and FOSS support are permanent project commitments. We deliberately accept a
smaller reachable user base to strengthen operator freedom and create an incentive to adopt an
open host stack. Native macOS and Windows backends, compatibility shims, and degraded hosting
profiles are outside the project's scope. Independent ports or forks carry their own maintenance
and support obligations; they create none for LychD Core.

## Decision: the manifested body

The generated topology contains `lychd.pod`, one `lychd-animator-*.target` for each
lifecycle-managed Soulstone, compatible `lychd-coven-*.target` aggregates, the migration gate,
Phylactery and Vessel, and admitted extension units. A Portal is a logical remote connection; it
does not summon a local container.

### Current unit graph

A generated Quadlet manifest is a Bind/Scribe deployment artifact. A live Animator retains its
Rune identity, Connector, and typed runtime surfaces; it never owns the generated manifest.
`RuntimePlan` compilation is available through the bind planner, not through the live
`AnimatorRegistry` surface.

Joined containers set `StartWithPod=false`: creating the shared namespace must not awaken every
Soulstone. Core ordering starts Phylactery, then the migration gate, then the Vessel. Only
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

### Compiler input

Code names the reusable mechanism directly. `QuadletConfig` is a frozen non-Rune value object
embedded as the `quadlet` field of operator intent that an admitted owner compiles into a
Quadlet-backed service; current Soulstone and Phoenix Runes are its concrete consumers. It owns
only their common OCI image invariant.

Lifecycle, mounts, devices, secrets, ports, commands, placement, and policy remain explicit fields
of the receiving owner rather than generic raw-Quadlet authority. `QuadletContainer` is the later
physical manifest model. Embedding `quadlet` declares the requested body but does not bypass the
owner-specific contributor or compiler that admits those policies. There is no `Stone`,
`ServiceStone`, or `AmbientStone` base type:
**Soulstone** is the sole accepted service term using that suffix.

### Versioned application deployments

A future `ApplicationDeploymentManifest@1` admits a complete application-specific service body
without granting a Composition raw Quadlet or systemd authority. It binds one immutable application
profile and its exact Composition/Pattern revisions to registered service-role implementations;
images and commands; dependency/start/stop order; local IPC and service identities; migrations;
mounts and durable volumes; ingress, egress, and isolated networks; secret references; ports;
resource ceilings; readiness; backup/restore; reconciliation; and removal policy. Unknown,
unowned, cyclic, overlapping, or undeclared edges fail before unit generation.

Configuration selects and assembles one registered profile generation. A multi-host profile closes
separately compiled per-host manifests plus one compatibility/enrolment receipt binding profile
revision, deployment and authority epochs, manifest digests, service Principals, protocol/schema
ranges, and exact private-route generations. It does not create a distributed control plane:
each host compiles and attests only its own Codex, secrets, volumes, and units. Each Core or
Extension Domain owns its typed service contribution. The Containers compiler arbitrates each
whole physical manifest and Scribe alone emits the units and receipts. A profile may place a
hostile parser, credential edge, or browser outside `lychd.pod` in a dedicated rootless network
zone, but it cannot create a second application authority, raw unit fragment, Podman socket route,
or lifecycle channel.

Operator provisioning supplies the one non-root host account and platform floor; LychD services
receive no account-creation or cross-user authority.

#### Gateway placement

An exact profile may place Veil on a separate
[Gateway Host](../sepulcher/gateway.md). That host is a deployment trust role, not a Composition,
Extension Domain, second Vessel, or application authority. Its manifest closes the public
listeners, typed Veil routes, exact authenticated backend, firewall flows, management boundary,
edge-only secrets, optional Tether attachment, resources, readiness, reconciliation, and removal.
It also binds or attests the independently enforced network zone, its router/firewall, L3-switch,
or cloud-network policy, and the receiving Core-firewall policy. The Gateway workload cannot widen
those controls; its local firewall rules remain defense in depth. The Core manifest accepts only
that backend identity and flow. The reference
placements **Home** and **Remote** reuse this role with different physical and custody boundaries;
a hostname, RPi, VPS, or boolean toggle cannot synthesize either topology.

#### Profile delivery and transition

The first concrete consumers are the designed, mutually exclusive
[Reach deployment profiles](../compositions/reach/deployments/index.md). No application selector,
deployment-profile registry, service-role contribution store, manifest compiler, or effectful host
receipt ships; the current generated topology above remains authoritative delivery truth.

A profile transition closes admission, drains or classifies every external effect, fences the old
generation, stops and revokes its credential owner, and activates the replacement authority last.
Two manifests for one profile never license two Phylacteries or Gateway owners. Downgrade or
rollback refuses when it would erase live custody; after the new authority admits work, return to
the old body is another quiesced migration rather than process restart.

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
the Phylactery explicitly sets `User=postgres` and its data mount uses `:U,Z`. These identities
allow assigned paths, not ambient Crypt access. The Tomb is a separate Security/Workers boundary,
not a safer Pod member.

`keep-id` maps the invoking host UID/GID into the Pod; process `User=` and each mount's
ownership and access policy remain separate decisions. It does not nest a second rootless
runtime or make an arbitrary image user match the host. Initial host layout creation belongs
to the invoking non-root account. Explicit `User=postgres` prevents `keep-id` from replacing
the image account with the invoking UID; `:U` supplies that account's mapped datastore ownership
before the PostgreSQL entrypoint initializes it. This requires no host-root setup. `:U` may
recursively change host-visible ownership and therefore belongs only on that
dedicated datastore, never a shared model shelf, home directory, Codex, or Reactor journal.
Existing mapped datastore ownership is preserved under [Layout](13-layout.md).

Soulstone data mounts cannot request recursive ownership changes (`:U`), host credential or
configuration roots, container storage, kernel/control filesystems, or existing sockets,
devices, and FIFOs. Host aliases are resolved before this check. Read-only access still discloses
credentials and may allow use of a Unix socket, so `ro` does not exempt these sources. Ordinary
explicit model and runtime-data mounts retain their declared access. This compiler check is not
a scan of every file inside an operator-selected data directory or a runtime inode attestation;
the operator must keep that directory free of unrelated private data and control endpoints.

Trusted Vessel and migration code is image-root-owned and their root filesystems are read-only;
declared writable tmpfs and application mounts supply runtime scratch and state. This rule must
hold for different host UIDs, including the image's historical application UID. It does not
assert that third-party images support a read-only root or that a rendered manifest proves
working subordinate-ID maps, SELinux labels, or filesystem permissions on an operator host.

Current Soulstone compilation joins every service to `lychd.pod`. That topology is not admissible
for a browser-bearing Scout renderer. Such a Soulstone must compile into a dedicated rootless
containment and network zone with no route to Core peers, Phylactery, host control sockets, wallets,
or unrelated secrets; its target egress must cross the Scout-owned destination gate. Until the
Rune, `RuntimePlan`, compiler, and effectful containment tests can express and prove that topology,
the Crawl4AI renderer candidate remains Designed rather than deployable.

## Scribe inscription

Scribe materializes one validated generation transactionally: render and validate in staging,
verify the prior ownership receipt and exact binding sites, make same-filesystem backups, replace
the declared files, remove only stale receipt-named files, publish the new receipt, and daemon
reload. A changed source, generation, site, secret, filename, mode, symlink, or foreign collision
refuses; a failed transaction restores the previous files and receipt. Ambiguity authorizes no
deletion. Filename resemblance never proves ownership.

Before planning, the complete ownership manifest also requires a one-to-one mapping from every currently runtime-bearing `.container`,
`.pod`, and generated/plain systemd source to its resolved runtime unit; different source names
that systemd would collapse onto one unit refuse together.

The declared compilation/materialization path is available within its State boundary. It is not a
receipt that a real operator host started Podman, systemd, GPU, or a model:
[State of Work](../state-of-the-work.md#systemd-podman-embodiment) owns that distinction.

## Consequences

The generated graph is inspectable and rootless, but it is not authority to start arbitrary
services or to infer host execution from a rendered unit.
