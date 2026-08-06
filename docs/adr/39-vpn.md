---
title: 39. VPN
icon: material/lan-connect
---

# :material-lan-connect: 39. VPN

!!! abstract "Context"
    A Magus may need a private road to the host without making administrative surfaces public or
    mistaking membership of that road for authority inside the Vessel.

## Decision

**WireGuard** is the transport of the **Tether** extension: an operator-controlled, encrypted,
self-hosted private-reachability layer. It is transport only. Tunnel membership grants neither an
application role, Sigil, capability, nor permission to a named object or effect.

The Tether may manifest a rootless service with only the network capability it needs and explicit
UDP publication. Interface name, listen port, address space, DNS behaviour, routes, and peer limits
are Rune-owned configuration, not hard-coded topology. Typed operations beneath `lychd run` may
generate a keypair, admit, inspect, revoke, rotate, or export a short-lived client configuration
or QR projection; it adds no root CLI verb.

If that service is projected through Quadlet, its future Rune may embed the code-level
`QuadletConfig` value under `quadlet`. That does not rename Tether to a kind of Stone, make it an
Animator, or grant generic unit-text authority; Tether keeps ownership of its exact network fields
and compilation policy.

The gateway remains outside the shared application Pod. It receives no broad mounts, application
secrets, database credentials, or host-mutation channel; granting `CAP_NET_ADMIN` inside that Pod
is not an acceptable shortcut.

## Peer custody and exact routes

The Codex may retain stable peer identity, public key, allowed addresses/routes, endpoint and
keepalive policy, enabled/revoked state, and creation/rotation metadata. Private and preshared keys
are hydrated through the secret boundary and never rendered into ordinary documentation, logs, QR
history, or public peer records.

Routes are explicit. Host firewall policy decides listeners reachable through the interface; Veil
may apply ingress policy; Ward and Vessel still authenticate and authorize. Database
administration, lifecycle mutation, Oculus, audio, model APIs, and A2A remain closed unless their
own policy admits the peer. A tunnel address, interface, peer key, or forwarded metadata can
contribute credential evidence; it cannot mint `magus:*`, widen a Sigil, or create an administrator.

## Lifecycle, failure, and recovery

Binding validates peer-address overlap, route conflict, key reference, port collision, and the
generated service contribution before inscription. Revocation removes the peer from the active
interface and persists revised intent. Rotation overlaps old and new credentials only with explicit
operator authorization. Versioned public peer/routing intent prevents restore or reconciliation
from reviving revoked or stale access; failure stays visible and privileged traffic never falls
back to a public route.

Dynamic addressing still needs an operator-supplied reachable endpoint through DNS, fixed
addressing, or a separately accepted rendezvous mechanism. Carrier NAT, blocked UDP, changing
endpoints, roaming, endpoint metadata, and traffic analysis remain. Relay and NAT traversal are
separate trust decisions, never an invisible recovery route.

## Delivery and consequences

This Covenant is **Designed**. No VPN provider, interface, enrollment, peer registry, key
rotation, route policy, health, or revocation path ships; generated deployment remains
IPv4-loopback-only, rejects UDP, and must not be tunnelled or port-forwarded. [State of
Work](../state-of-the-work.md#vpn-tether) owns that boundary.

Tether makes private transport independently revocable, at the cost of security-sensitive peer and
route management, backup, rotation, recovery, and uncertain direct reachability. It never changes
the separate application-authority requirement.
