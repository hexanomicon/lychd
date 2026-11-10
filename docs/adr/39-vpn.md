---
title: 39. VPN
icon: material/lan-connect
---

# :material-lan-connect: 39. VPN

!!! abstract "Context"
    A Lich may offer a private road to admitted peers while holding separate private roads to
    other Liches. Neither reachability nor membership of any road grants application authority.

## Decision

The **Tether** extension uses **WireGuard** for an operator-controlled, encrypted, self-hosted
private road. This layer supplies reachability only. Tunnel membership grants no application
role, Sigil, capability, or permission to a named object or effect.

Private reachability is not anonymous browsing. A tunnel can conceal destination traffic from
the access network while moving visibility and trust to its endpoint; traffic timing and volume,
endpoint addresses, browser fingerprints, accounts, and provider-held request content remain
separate disclosure surfaces. Tether does not currently define a consumer VPN exit, browser
anonymity profile, or Tor transport. An accepted future outbound privacy profile must name the
observer it protects against and prove DNS, IPv4/IPv6, direct-route and reconnect failure closure,
browser-origin isolation, and egress custody. It must never silently bypass a failed private route.
Remote model/CLI requests still disclose their transmitted content to the receiving provider,
irrespective of the road carrying it; [Security](09-security.md#portal-privatization-and-egress)
owns that disclosure decision.

The Tether may manifest a rootless service with only the network capability it needs and explicit
UDP publication. Interface name, listen port, address space, DNS behaviour, routes, and peer limits
are Rune-owned configuration, not hard-coded topology. Typed operations under a future host-owned
run-operation verb may generate a keypair, admit, inspect, revoke, rotate, or export a short-lived
client configuration or QR projection; it adds no root CLI verb.

If that service is projected through Quadlet, its future Rune may embed the code-level
`QuadletConfig` value under `quadlet`. That does not rename Tether to a kind of Stone, make it an
Animator, or grant generic unit-text authority; Tether keeps ownership of its exact network fields
and compilation policy.

The Tether service remains outside the shared application Pod. It receives no broad mounts,
application secrets, database credentials, or host-mutation channel; granting `CAP_NET_ADMIN`
inside that Pod is not an acceptable shortcut.

## Offered network and imported attachments {#offered-and-imported-roads}

A Lich may offer one locally governed VPN network to many admitted peers and simultaneously hold
many independent attachments to other Liches' private networks. These are configuration ownership
and consent roles; WireGuard traffic is bidirectional and the roles confer no asymmetric trust.
Publicly reachable peers need no VPN merely to participate in A2A.

An offered network may share one WireGuard interface among peers with distinct admitted addresses
when its local key identity and policy permit. An imported attachment binds its own local identity,
remote Lich and tunnel-peer identity, key references, outer UDP endpoint, inner service coordinates,
DNS policy, allowed callers, and versioned route intent. The outer endpoint carries encrypted
packets; it is distinct from the inner address, port, and protocol of the admitted service.
Tunnel identity does not replace the remote application's independently enrolled identity.

Independent attachments may use the same private addresses. Bind refuses ambiguous overlap within
a shared routing domain; it does not reject equal prefixes in properly isolated domains. Where
addresses overlap or trust policies conflict, each attachment needs a distinct routing and
enforcement context. Independent imported networks have separate routing and name-resolution
contexts by default. Sharing requires an explicitly admitted profile proving deterministic
selection, compatible address and DNS policy, no unauthorized forwarding, and independent lifecycle
fencing. Two interfaces alone do not establish that boundary. Network namespaces are one mechanism;
one peer, interface, namespace, and container are not interchangeable units.

Every application connection using an imported attachment selects the remote Lich, attachment
identity and current generation, and admitted service before opening a socket. An IP address or
hostname alone is insufficient.
Keep that selection through name resolution, connection pooling, reconnects, and redirects or
retries where the selected application profile permits them. Changed intent or authority requires
fresh admission. [A2A](26-a2a.md) retains its narrower protocol rules, egress decisions, and
settlement of uncertain submissions.

Imported configuration is untrusted input, not installation authority. Locally admit the needed
keys, endpoint, address scope, exact services, and DNS behavior; do not execute imported hooks or
silently install default routes, host DNS changes, forwarding rules, or other host mutations.
The local operator's typed intent admits the proposal, Tether validates its network contribution,
the deployment compiler validates the declared topology, and the authorized materializer inscribes
it. Import supplies no arbitrary unit text or new privilege.
WireGuard `AllowedIPs` selects peers and validates source addresses; service ports, protocols,
callers, and application effects require their own enforcement.

Only the admitted service interactions and corresponding return traffic cross an attachment.
Neither imported attachments nor peers on the offered network receive implicit access to one
another, unrelated host listeners, or the application Pod. A receiving endpoint is an exact
admitted service, not ambient Pod reachability. IP transit between these networks, peer-to-peer
forwarding, and exit-node behavior require a separately accepted profile; possession of several
VPN accesses creates no full mesh.

### Isolation and service packaging

Routing isolation is required independently of packaging. A dedicated rootless service may hold
one or more compatible attachments only when their identity, route, key, and enforcement boundaries
remain explicit. Neither a container per peer nor one shared VPN container is mandated.
[WireGuard namespaces](https://www.wireguard.com/netns/) also make native systemd-managed namespace
services a technical alternative. This does not admit a privileged native Tether profile: any such
profile needs an accepted owner, closed operations, recovery, and verification under
[Containers](08-containers.md) and [Privilege](10-privilege.md). The Vessel receives no general
root, shell, network-administration, or service-launch authority and runs no tunnel subprocess.
Attaching to infrastructure-owned VPNs retains that infrastructure's separate custody.

Container packaging does not imply userspace WireGuard, and Quadlet services are themselves
systemd-managed. Performance qualification must name the actual kernel or userspace implementation,
forwarding path, simultaneous attachments and traffic, and incremental process and kernel memory.
Image size is not resident-memory overhead; no portable per-container RAM or throughput figure
selects this architecture. Rootless networking and per-attachment helpers require measured evidence
before a deployment claims its capacity or isolation.

The optional [Gateway Host](../sepulcher/gateway.md) uses Tether only when placement requires a
private routed road. **Remote** may admit one exact peer and backend route from the off-site Veil to
Core; it receives no default route or ambient home reachability. **Home** needs no Tether merely
because Veil runs on a separate local machine: an exact directly routed private segment may supply
reachability while firewall and service authorization retain their separate duties.

## Reach deployment roads

The [Reach deployment matrix](../compositions/reach/deployments/index.md) selects Tether by exact
profile, not a trust toggle. Home-only and standalone outbound VPS use no Tether. Only
`reach.edge-home.public@1` requires one named VPS peer and the smallest route to a Tether-only
private Veil backend for typed event admission, delivery claim, settlement, and health. It receives
no default route or path to the home Phylactery, Reach core, Altar, model/provider API, Podman
socket, Reactor, or host administration. Tether custody contains tunnel keys only; the edge relay
keeps its disjoint workload credential and revoking one class never repairs another.

## Peer custody and exact routes

The Codex may retain stable peer identity, public key, allowed addresses/routes, endpoint and
keepalive policy, enabled/revoked state, and creation/rotation metadata. Private and preshared keys
are hydrated through the secret boundary and never rendered into ordinary documentation, logs, QR
history, or public peer records.

The offered network holds its interface private key and admitted peers' public keys. Each imported
attachment holds its own local private-key reference and the remote public key, with a separate
preshared-key reference when used. Short-lived client export does not make retaining every peer's
private key normal server custody. Application, operator, and SSH credentials remain separate.

Each route must be explicit. Host firewall policy determines which listeners the interface can
reach, Veil may apply ingress policy, and Ward and Vessel still authenticate and authorize.
Database administration, lifecycle mutation, Oculus, audio, model APIs, and A2A stay closed until
their own policy admits the peer. A tunnel address, interface, peer key, or forwarded metadata
can contribute credential evidence but cannot mint `magus:*`, widen a Sigil, or create an
administrator.

## Lifecycle, failure, and recovery

Binding validates peer-address overlap and route conflicts within each routing domain, key
references, port collisions, and the generated service contribution before inscription.
Revocation removes the peer from the active interface and persists revised intent.
Rotation overlaps old and new credentials only with explicit
operator authorization. Versioned public peer/routing intent prevents restore or reconciliation
from reviving revoked or stale access; failure stays visible and privileged traffic never falls
back to a public route.

Readiness is observed per attachment generation and service binding: Tether supplies route health,
while the consumer verifies its remote service under that service's authentication owner. A tunnel
handshake alone proves neither. Unavailable or revoked attachments, failed permitted resolution,
missing routes, or service-authentication failure close that selection; they never select another attachment with
the same address or direct/public application transport. Ordinary outer WireGuard UDP traffic is
not such a fallback. Revocation fences active pooled connections and future sends for the affected
generation; it cannot recall bytes or undo remote effects already admitted. Independent attachments
keep separate revocation and recovery intent, so restoring one cannot resurrect another's access.
Tunnel revocation does not revoke independent application sessions or credentials. Restore must
check current authoritative route and revocation generations, not infer freshness from records
restored together in the same snapshot. If that authority cannot be established, the affected
attachment stays closed for reconciliation.

Dynamic addressing needs an operator-supplied reachable endpoint, whether through DNS, fixed
addressing, or a separately accepted rendezvous mechanism. Carrier NAT, blocked UDP, changing
endpoints, roaming, endpoint metadata, and traffic analysis remain concerns. Relay and NAT
traversal require separate trust decisions; recovery cannot introduce them invisibly.

## Delivery and consequences

This Covenant is **Designed**. No VPN provider, interface, enrollment, peer registry, key
rotation, route policy, health, or revocation path ships; generated deployment remains
IPv4-loopback-only and rejects UDP. The optional infrastructure-owned
[single-operator forwarding candidate](09-security.md#single-operator-forwarding-candidate)
is separate from Tether and has no installed qualification. General tunnelling and shared-user
access remain unsupported. [State of
Work](../state-of-the-work.md#vpn-tether) owns that boundary.

Independent revocation is Tether's practical return. Operating that private road requires
security-sensitive peer and route management, backup, rotation, recovery, and an account of
uncertain direct reachability.
