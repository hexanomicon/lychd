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
use is unsupported. The separate infrastructure-owned
[single-owner access candidate](../../deployments/tumbleweed/access.md) permits an explicit
qualification experiment while keeping loopback publication. It is not a native Tether
implementation or a shared remote Altar.

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

## First native operator profile (Designed) {#first-native-operator-profile}

`single-operator-forward@1` is the first bounded implementation target: one trusted instance
owner and one active WireGuard peer. The profile uses standard kernel WireGuard and OpenSSH in
separate containers of a dedicated rootless Pod outside Core. It is not an installed capability,
a shared Altar, remote IAM, a mesh, or a VPN exit. The [owning decision](../../adr/39-vpn.md#single-operator-profile)
defines its exact boundary.

The browser continues using `http://127.0.0.1:7134` through an ordinary SSH local forward. The
server SSH destination is the configured loopback Altar port, reached through one exact pasta
mapping. Only WireGuard UDP is publicly published. The peer receives only the server tunnel
`/32`; it receives no DNS, default or LAN route. The existing Basic credential, Host, Origin,
CORS and CSRF requirements remain unchanged. Keep a dedicated browser profile for this instance.

The static Rune declares the tunnel/deployment envelope. Tether's separate public peer record
contains the enrolled public key and generation; the forwarding role separately records the SSH
authorized public key. The client creates and retains both private keys locally. Tether owns only
server tunnel material; the forwarding role owns its server SSH host key, which the client pins.
Neither container receives the application password. The server does not export client private
keys or modify the operator's device.

For this source candidate, discover the public declaration before the first preparation:

```bash
lychd run tether inspect --declared
```

Use the returned `envelope.installation_id` and `envelope_digest` for preparation's
`--installation-id` and `--envelope-digest`, with `--expected-generation 0` and a fresh
`--operation-id` UUID. This read-only query works before prepared secrets, Tether custody or
bindings exist. It reports declared intent; installed readiness still requires qualification.

The designed operator sequence is:

1. Prepare the Linux/rootless substrate and explicit UDP firewall opening. Qualify the exact
   kernel, Podman, pasta and OpenSSH combination under an isolated installation first.
2. Initialize the owned Tether custody leaves. Use the designed `lychd run tether prepare` to
   create the exact server WireGuard and SSH host-key secrets and their creation receipts. Then
   install the static service envelope through ordinary complete-fileset bind, which validates
   both typed secret references. Existing active-Vessel and foreign-revision refusals still apply.
3. Generate client keys locally. Use the designed `lychd run tether enroll` operation with public
   keys and exact peer intent. The operation may activate only the already owned Tether units;
   it cannot change the compiled topology or shared binding generation.
4. Inspect desired, loaded and observed state through the designed `lychd run tether inspect`.
   Establish the client WireGuard route and pinned SSH forward separately, then qualify the browser
   and its refusal boundaries. Unit state alone cannot establish this result.
5. Use the designed `lychd run tether revoke` to fence the generation and stop the complete private
   road. Confirm terminal settlement. An incomplete result stays fenced and needs reconciliation;
   it is not permission to clear the fence or repeat enrollment blindly.

The source candidate implements these closed CLI operations. Follow the
[fresh Tumbleweed pilot](../../deployments/tumbleweed/tether.md) for the concrete sequence,
including Core startup before peer enrollment. Installed qualification remains incomplete and
the profile remains Designed.
Preparation creates server secrets before bind; later peer operations change only Tether's public
intent and operation evidence, leaving prepared secret identities and compiled units unchanged.
Changing the image, interface, UDP endpoint binding or forwarding destination requires normal bind.
They cannot update or restart a separately running older Vessel.

An independent host systemd path guard watches the durable closure latch and invokes the exact
owned stop handler. Its conflict/ordering edges stop transport before the handler takes the
lifecycle lock; watcher loss also requests stop. Closure still requires observed settlement,
including established sessions, even if the revoking CLI crashes after writing the latch. A
boot-only check cannot provide that property. The successful handler stays active/exited while
the fixed latch persists. Re-enrollment first proves transport cold, stops the watcher, preserves
old revocation evidence, stops/resets the handler and watcher, publishes the new generation,
clears only the active latch durably, then starts the watcher before transport. Recovery after a
fence never restarts the revoked generation.
Boot requests require public peer intent and an absent closure latch, followed by the same native
preflight as explicit activation. A completed, exactly correlated enrollment permits a new boot
incarnation. An incomplete enrollment admits only its native first-start request in the same
kernel boot; merely publishing peer intent never grants reboot authority. An unmatched retained
Pod activation attempt blocks automatic recovery across boots. Reconciliation may advance only to
a fresh generation after exact retained revocation evidence and cold proof; it preserves the old
attempt and generation evidence.

Reboot cannot restart a fenced generation. Whole-state rollback can also roll back its fence,
so restoration needs independent revocation evidence or fresh server identity and client
re-enrollment; a generation number alone is not rollback protection.

Live qualification must include denied unrelated host/loopback/LAN destinations, unauthorized SSH
channels, browser/SSE and hostile origins, established-session revocation, process/guard failure,
interruption after fence persistence, tunnel loss and reboot. Keep their exact versions and observed
results with delivery evidence. Do not infer these properties from generated configuration.

When replacing the infrastructure access candidate, use a distinct endpoint and identity until
the new road passes qualification. Then fence and retire the old road using its owner. Ansible
retains substrate/firewall preparation; it must not remain a second controller for native peers,
keys or units. Existing application data and receipts remain subject to their normal owners.

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
