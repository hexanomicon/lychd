---
title: Tether
icon: material/shield-link-variant-outline
---

# :material-shield-link-variant-outline: The Tether: Extension of the Inner Circle

**Purpose:** The Tether is LychD's private-network transport jurisdiction. It is the intended
silver path by which an enrolled device may reach a deliberately narrow set of services across an
untrusted network.

**Current boundary:** The `vpn` package contains no working organ and is absent from the built-in
catalog. There is no WireGuard unit or interface, external UDP listener, peer registry, key
lifecycle, route or firewall policy, enrollment surface, health model, revocation path, or VPN
test. The existing extension port seam forces host publication onto IPv4 loopback and rejects UDP
shapes. [State records the local browser boundary](../../state-of-the-work.md#local-browser-bind-boundary)
and the [Tether boundary](../../state-of-the-work.md#vpn-tether).

**Law:** [ADR 39 — VPN](../../adr/39-vpn.md), constrained by
[ADR 09 — Security](../../adr/09-security.md) and the future [Ward](./ward.md).

**Extension form:** Tether is an infrastructure Extension Domain, not a synonym for one VPN
package. The sole planned LychD-managed pre-v1 manifestation is Linux WireGuard operated through
the official `wireguard-tools` on the host. An existing Tailscale, Headscale, or other private
network may remain an externally managed attachment, while a private coupled Crypt package may
attempt its own lifecycle integration without a compatibility promise. Exactly one manager owns
each concrete listener, interface, route, and firewall rule.

> _"Across distance, the Silver Tether may carry the Magus's voice toward the Lich. It is a road
> through the Forest, not proof that every hand upon that road belongs to the Magus."_

WireGuard can authenticate possession of an enrolled device key and encrypt packets between
peers. It cannot identify the current human or process, express an application scope, bind a
request to an object, record consent, or make a compromised device trustworthy. The Tether narrows
reachability; it never creates authority.

## I. The Silver Path

The mature Tether must own a bounded transport lifecycle:

- **Topology:** one explicit packet path from external UDP ingress through an isolated gateway or
  operator-owned host unit to exact allowlisted service destinations. The private route must not
  reveal the whole pod or host.
- **Device enrollment:** unique peer and device identities, public keys, constrained addresses and
  routes, owner, expiry, status, rotation, compromise, and immediate revocation. Device identity
  remains separate from human, service, peer, and Lych identities.
- **Secret custody:** private material lives in an owner-only secret boundary. Runes may hold public
  peer metadata and secret references, never reusable private keys. Device-generated keys are
  preferred; any one-time handoff or QR revelation must be local, explicit, redacted, and
  disposable.
- **Route policy:** default-deny forwarding to a small service allowlist. Databases, model APIs,
  container control, Host Reactor handoff, unrelated pod services, and raw administrative surfaces
  remain unreachable.
- **Reanimation:** generation-stamped interface, route, firewall, and peer state with atomic
  reconciliation, health, rollback, stale-rule cleanup, and revocation history that a restored
  snapshot cannot silently undo.
- **Honest sovereignty:** direct peer-to-peer operation avoids a mandatory hosted control plane,
  but it does not solve CGNAT, blocked UDP, dynamic endpoints, DNS metadata, roaming, or traffic
  analysis. Failure is explicit; privileged traffic never downgrades automatically to a public
  path.

The internet-facing network parser must not receive broad mounts, application secrets, database
credentials, or host mutation authority. A container with `CAP_NET_ADMIN` inside the shared
application pod is not an acceptable default topology: compromise there could rewrite the network
around every organ.

## II. The Inner Circle Is a Route, Not a Rank

Every application request arriving through the Tether must still cross the [Ward](./ward.md).
Source interface, peer address, tunnel key, and forwarded metadata may constrain reachable routes
or contribute authentication evidence; none may mint `magus:*`, bypass a login, widen an Authority
Grant, or authorize an effect.

The same separation governs [Intercom](../../adr/26-a2a.md) and future owned-node traffic. A
WireGuard peer key is not a Lych or node identity, not a request signature, and not replay
protection. Logical node credentials, audience, expiry, idempotency, revocation, resource leases,
and node-local admission remain independent.

!!! danger "A Stolen Thread Still Reaches the Door"
    A stolen phone, copied tunnel configuration, or compromised enrolled device can possess a
    valid WireGuard key. The Ward must still reject that device when it presents no valid
    application credential or asks for an unauthorized object or effect. There is no trusted
    Tether bypass.

## III. Gates Before the Tether Is Cast

No tunnel carries LychD traffic until all of these gates agree:

1. Credential-backed Ward authentication and object/effect authorization are mandatory for every
   tunneled HTTP, SSE, WebSocket, A2A, telemetry, and administrative request. Bootstrap `magus:*`
   is unreachable from the tunnel.
2. One isolated gateway or host-unit topology has an exact IPv4/IPv6 packet-flow and threat model;
   it requires no network-admin capability in the shared application pod.
3. Core owns a typed, operator-approved external UDP listener and firewall contribution with exact
   address, protocol, port, owner, exposure class, prerequisites, collision handling, and rollback.
4. Typed peer records enforce unique keys and addresses, bounded `AllowedIPs`, no raw hook commands,
   one-time or device-generated enrollment, secret-safe custody, rotation, and live revocation.
5. Firewall tests prove least reachability: an enrolled peer cannot reach the Phylactery, model
   services, Host Reactor, container control, or any route outside its allowlist.
6. Application tests deny a stolen VPN key without a valid credential, a wrong or revoked
   principal, spoofed source metadata, object-id guessing, and replayed Intercom traffic.
7. Crash, partial apply, restore, key compromise, stale firewall, DNS, NAT, roaming, and blocked-UDP
   failures close the private route without falling back to a weaker public security profile.
8. Tether telemetry proves configuration generation, peer lifecycle, route convergence, and
   denials while redacting private keys, QR payloads, full configurations, and unbounded endpoint
   metadata.

**Safe next act:** keep the Vessel on the same host and follow
[The Awakening](../../summoning.md#the-awakening). Do not tunnel or port-forward its current HTTP
surface.
