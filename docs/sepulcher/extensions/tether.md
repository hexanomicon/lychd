---
title: Tether
icon: material/shield-link-variant-outline
---

# :material-shield-link-variant-outline: The Tether

> _A thread drawn taut between two distant thresholds._

**Tether** is the private-reachability Extension Domain, with WireGuard as its accepted transport.
It may eventually appear as a LychD-managed WireGuard service or as an attachment to an externally
managed private network.

Tether is **Designed**; no managed VPN or peer-operation path ships. [State of
Work](../../state-of-the-work.md#vpn-tether) records that delivery boundary. The public peer intent,
secret references, endpoint and route checks, revision fences, and retained revocation tombstones
below are accepted design.

Generated deployment remains IPv4-loopback-only: the Extension port grammar accepts only
`127.0.0.1:<host>:<container>` and rejects UDP. Remote, proxied, tunneled, and untrusted-browser
use is unsupported. Keep the Vessel on the same host, and do not tunnel or port-forward the
current Altar.

## Managed path and peer custody

[ADR 39](../../adr/39-vpn.md) permits a managed Tether to manifest as a rootless service with
narrow network capability and explicit UDP publication. Interface, listen port, address space,
DNS behavior, routes, and peer limits remain Rune-owned intent.

The Tether service stays outside the shared application Pod and receives no broad mounts,
application secrets, database credentials, or host-mutation authority. `CAP_NET_ADMIN` inside that
Pod is not an acceptable shortcut.

An optional [Gateway Host](../gateway.md) composes Tether only for a placement that needs a private
routed road. **Remote** may bind one exact peer and route from the off-site Veil to one Core
backend. **Home** does not require Tether when an exact local segment already supplies
reachability. In neither placement does a tunnel grant authority or a default route into the home
network.

Keep the public account of a peer in the Codex: stable identity, public key, allowed addresses
and routes, endpoint and keepalive policy, enabled or revoked state, and creation or rotation
metadata. Keep private and preshared keys with the secret owner, outside ordinary documentation,
logs, QR history, and public peer records.

Future typed operations under a host-owned run-operation verb may generate, admit, inspect,
revoke, rotate, or export short-lived client configuration or QR projections. They would use
that governed operation path without adding a root CLI verb.

## Reach attachment

The [Reach deployment matrix](../../compositions/reach/deployments/index.md) gives Tether one exact
consumer: [`reach.edge-home.public@1`](../../compositions/reach/deployments/vps-edge-home-core.md).
Home-only and standalone outbound VPS use none. The split profile admits one named VPS peer, one
exact address and route, explicit expiry and revocation generation, and one Tether-only private
Veil backend for event admission, delivery claim, settlement, and health. It never uses
`0.0.0.0/0`, exposes the home Phylactery, Reach core, Altar, model API, Podman socket, Reactor, or
forwards arbitrary VPS traffic through the sovereign host.

Tether holds only tunnel material. Root/VPS compromise still requires revoking that peer,
separately rotating every resident application and operator credential, reconciling uncertain
effects, and rebuilding the host; tunnel revocation alone is not containment.

## Tunnel identity and exact routes

WireGuard proves possession of a tunnel key and encrypts packets. Human or process identity,
object or effect authorization, consent, and device trust remain outside that proof. The host
firewall selects each reachable listener; [Veil](veil.md) may constrain route or transport policy,
while [Ward](ward.md) and the Vessel authenticate and authorize.

For Intercom, the conservative first designed road is a Veil-compiled HTTP route exposed only
through Tether. Tether supplies private reachability; Veil canonicalizes ingress; Ward admits the
peer; Intercom verifies and replay-fences the A2A envelope. None may impersonate the next layer or
turn an advertised Spell or Scroll into authority.

A tunnel address, interface, peer key, or forwarded metadata contributes at most credential
evidence. It cannot mint `magus:*`, widen a Sigil, or create an administrator. Bootstrap
`magus:*` stays same-host only. Routes default to exact destinations; PostgreSQL, model APIs,
container and Host lifecycle control, Oculus, audio, and
[Intercom](../../adr/26-a2a.md) remain closed unless their own policies admit them.

## Revocation, rotation, and recovery

Before changing the service, binding validates peer-address overlap, route conflicts, key
references, port collisions, and the generated contribution. Revocation then removes a peer from
the live interface and persists the revised intent. Rotation may overlap old and new credentials
only with explicit operator authorization.

Version the public peer and routing intent so restore or reconciliation cannot revive stale or
revoked access. Keep failures visible; privileged traffic must never escape through a public
fallback.

Direct WireGuard avoids a mandatory hosted control plane, but CGNAT, blocked UDP, changing
endpoints, roaming, endpoint metadata, and traffic analysis remain. Reachability may require fixed
addressing, DNS, or a separately accepted rendezvous or relay. ADR 39 owns transport law;
[Security](../../adr/09-security.md) and the Ward own the trust boundary.
