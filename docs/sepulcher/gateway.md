---
title: Gateway
icon: material/gate
---

# :material-gate: Gateway

A public request need not land on the host that keeps the Lich's durable body. A **Gateway Host**
is an optional, separate deployment trust role that carries hostile ingress while the Core host
retains data and application authority. It is neither a Composition nor an Extension Domain:
[Veil](extensions/veil.md) still owns TLS and route admission, optional
[Tether](extensions/tether.md) supplies private reachability, and the selected deployment profile
closes the physical hosts and flows.

A same-host Veil is not a Gateway Host. The extra role exists only when the operator deliberately
spends another machine to separate the exposed surface. Gateway is **Designed**;
[State of Work](../state-of-the-work.md#proxy-veil) owns the delivery boundary.

## Boundary

| Gateway may hold | Gateway must not hold |
| --- | --- |
| edge certificates, compiled Veil routes, firewall intent, one backend service credential, optional Tether key, bounded transport evidence | Phylactery or database authority, private Context, provider or application credentials, Sigils, corpus, Podman or systemd control, a general LAN route |

The public road is exact:

```text
client -> admitted listener -> Veil -> authenticated exact backend -> Ward and application
```

Every route closes host, port, path, method, protocol, limits, backend identity, and authentication
precondition. The Core firewall accepts the backend path only from the admitted Gateway identity;
the Gateway cannot initiate arbitrary LAN or Internet traffic. IPv4 and IPv6 obey the same policy,
and host administration uses a separate route and credential. Forwarded bytes remain hostile:
possession or compromise of the Gateway cannot mint caller identity, a Sigil, consent, or effect
authority behind the route.

## Home

**Home** places the Gateway on operator-controlled iron, such as a Raspberry Pi, between the home
router and one exact Core backend. The router forwards only the admitted public listener to Home;
Home may reach only the named Core address and port; the Core accepts that port only from Home.
All other Home-to-LAN forwarding and non-required egress are denied, and management is admitted
separately.

Home keeps edge custody local and adds no rented control plane. It shares the household's power,
uplink, public-address exposure, and upstream denial-of-service limit. Tether is unnecessary when
an exact directly routed private segment already connects Home to Core. The backend still
authenticates the Gateway independently of network location; the selected profile also closes any
required transport encryption.

## Remote

**Remote** places the same role on rented or otherwise off-site iron, such as a VPS. Public DNS and
listeners terminate there. The Core exposes no public application port; an exact Tether route may
carry authenticated backend traffic from Remote to the one admitted Core listener without giving
Remote a default route into the home network.

Remote moves scans and link-level abuse away from the household and can supply stable public
reachability. It adds a provider account, remote control plane, tunnel custody, and another rebuild
and revocation boundary. It does not become a standalone Vessel, replica, administrator, or
application authority merely because it is off-site.

## Selection and recovery

`Home` and `Remote` are reference topology names, not free configuration switches. An exact
deployment profile either omits the separate Gateway role or binds one placement together with its
per-host manifest, Veil routes, optional Tether generation, service Principals, credentials,
firewall boundary, management path, and recovery contract. `gateway=true`, `rpi`, `vps`, or an
arbitrary proxy target cannot assemble a partial edge.

Suspected Gateway compromise closes the public route, revokes its certificates, backend
credential, optional Tether peer, and deployment generation, quarantines bounded evidence, and
rebuilds the host from admitted inputs. Core credentials and data remain unchanged only when
boundary evidence proves they never crossed.

[Security](../adr/09-security.md) owns the trust zone ·
[Containers](../adr/08-containers.md#versioned-application-deployments) owns the host manifests ·
[Proxy](../adr/40-proxy.md) owns Veil
