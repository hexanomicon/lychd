---
title: Tether
icon: material/shield-link-variant-outline
---

# :material-shield-link-variant-outline: The Tether

> _A private road shortens distance. It does not widen the gate._

**Tether** is the private-reachability Extension Domain, with WireGuard as its accepted transport.
It may eventually appear as a LychD-managed WireGuard service or as an attachment to an externally
managed private network.

Its state is **Partial, inert foundation**. Immutable public interface/peer intent,
secret-reference validation, bounded endpoint and route validation, revision fencing, and retained
revocation tombstones now exist as pure Domain code. No Rune, VPN provider, live interface,
enrollment, peer registry, key generation or rotation effect, network health, reconciliation
adapter, or revocation effect ships. Generated deployment remains IPv4-loopback-only; the
Extension port grammar accepts only
`127.0.0.1:<host>:<container>` and rejects UDP. Remote, proxied, tunneled, and untrusted-browser
use is unsupported. Keep the Vessel on the same host, and do not tunnel or port-forward the
current Altar. [State of Work](../../state-of-the-work.md#vpn-tether) owns that boundary.

## Managed path and peer custody

[ADR 39](../../adr/39-vpn.md) permits a managed Tether to manifest as a rootless service with
narrow network capability and explicit UDP publication. Interface, listen port, address space,
DNS behavior, routes, and peer limits remain Rune-owned intent.

The gateway stays outside the shared application Pod and receives no broad mounts, application
secrets, database credentials, or host-mutation authority. `CAP_NET_ADMIN` inside that Pod is not
an acceptable shortcut.

The Codex may retain stable peer identity, public key, allowed addresses and routes, endpoint and
keepalive policy, enabled or revoked state, and creation or rotation metadata. Private and
preshared keys stay within the secret boundary; they never enter ordinary documentation, logs, QR
history, or public peer records. Future typed operations beneath `lychd run` may generate, admit,
inspect, revoke, rotate, or export a short-lived client configuration or QR projection without
adding a root CLI verb.

## Tunnel identity and exact routes

WireGuard proves possession of a tunnel key and encrypts packets. Human or process identity,
object or effect authorization, consent, and device trust remain outside that proof. The host
firewall selects each reachable listener; [Veil](veil.md) may constrain route or transport policy,
while [Ward](ward.md) and the Vessel authenticate and authorize.

A tunnel address, interface, peer key, or forwarded metadata contributes at most credential
evidence. It cannot mint `magus:*`, widen a Sigil, or create an administrator. Bootstrap
`magus:*` stays same-host only. Routes default to exact destinations; PostgreSQL, model APIs,
container and Host lifecycle control, Oculus, audio, and
[Intercom](../../adr/26-a2a.md) remain closed unless their own policies admit them.

## Revocation, rotation, and recovery

Binding validates peer-address overlap, route conflicts, key references, port collisions, and the
generated service contribution. Revocation removes the peer from the live interface and persists
revised intent. Rotation overlaps old and new credentials only with explicit operator
authorization. Public peer and routing intent is versioned so restore or reconciliation cannot
resurrect revoked or stale access. Failure is visible; privileged traffic never falls back to a
public route.

Direct WireGuard avoids a mandatory hosted control plane, but CGNAT, blocked UDP, changing
endpoints, roaming, endpoint metadata, and traffic analysis remain. Reachability may require fixed
addressing, DNS, or a separately accepted rendezvous or relay. ADR 39 owns transport law;
[Security](../../adr/09-security.md) and the Ward own the trust boundary.
