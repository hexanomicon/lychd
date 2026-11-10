---
title: 39. VPN
icon: material/lan-connect
---

# :material-lan-connect: 39. VPN

!!! abstract "Context"
    A Magus may need a private road to the host without making administrative surfaces public or
    mistaking membership of that road for authority inside the Vessel.

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

## First managed profile: single operator {#single-operator-profile}

The first native profile is `single-operator-forward@1`: one instance owner, one active peer,
IPv4, and one exact route to a restricted OpenSSH forwarder. It remains **Designed**, conditional
on the installed qualification below. It supplies neither remote IAM nor the Reach gateway
profile. No mesh, relay, exit route, DNS change, or client-device configuration is implicit.

The Rune owns the static deployment envelope: profile revision, stable service identity,
interface, server tunnel address, exact host UDP bind address/port, advertised endpoint,
single-peer limit, image, and server tunnel-secret reference. A separate Tether-owned public peer
record in the Codex owns peer identity, public key, exact tunnel `/32`, keepalive policy,
enabled/revoked state and generation. This record is not a Rune or a second copy of Settings;
peer operations do not change shared configuration or Scribe generations. The forwarding role
owns its distinct SSH authorized public key, host-key reference, tunnel listener and fixed local
Altar destination. [Layout](13-layout.md#tether-custody-designed) owns these paths.

Validation refuses unknown fields, invalid keys or interface names, overlapping addresses,
default/LAN routes, ambiguous endpoints, and address/protocol/port collisions. Client routes
contain only the server tunnel `/32`. The client generates and retains its WireGuard and SSH
private keys; enrollment accepts public keys only. Server generation or export of client private
keys, preshared-key distribution, QR projection and overlapping rotation are outside this first
profile. A public configuration projection is not proof of client installation.

The managed body is a dedicated rootless Pod containing standard kernel WireGuard and standard
OpenSSH in separate containers. Only WireGuard receives namespaced `CAP_NET_ADMIN`; no container
joins Core or receives host networking. Tether custody contains only tunnel material. The
forwarder owns its SSH host key separately and receives no application password. Compilation
selects fixed programs and closed WireGuard, address, nftables and sshd configuration: no
operator command, `wg-quick` hook, `SaveConfig`, generic capability list, or raw unit text.

Pasta supplies one explicit container-loopback to host-loopback TCP mapping for the configured
Altar port. Automatic mappings and broad host-address/loopback mappings are disabled explicitly.
The namespace uses default-deny input, output and forwarding policies. It admits only WireGuard
UDP on the declared listener, the exact peer-to-SSH flow and its replies, and the Altar loopback
TCP flow and its replies. Output permits WireGuard ciphertext from its declared UDP socket to
its learned peer endpoint, not arbitrary container egress. No DNS resolver/forwarder or IPv6
flow is admitted; the first profile uses a literal IPv4 advertised endpoint. The fixed startup
helper installs and verifies these policies before raising the tunnel and declaring WireGuard
ready. OpenSSH starts only after that readiness, binds only the tunnel address, and admits only
local TCP forwarding to the exact loopback Altar destination, with no shell/session, reverse,
agent or Unix-socket forwarding.
The client listener, browser URL and application publication remain literal loopback. The
[Security forwarding boundary](09-security.md#single-operator-forwarding-candidate) still owns
Basic authentication, Host, Origin, CORS, CSRF and browser-profile requirements.

### Native peer operations and closure {#native-peer-operations}

The first closed host-owned operation namespace admits `prepare`, `enroll`, `inspect` and `revoke`
under the grammar designed in [CLI](19-cli.md#admit-work-without-ceding-the-language). Before bind,
`prepare` creates only the exact server WireGuard and forwarding SSH host-key secrets through
fixed trusted native factories and records immutable creation identity receipts. Both remain
typed `Secret` references in their respective container contributions; bind validates their
presence and admitted identity. A missing or foreign secret cannot be deferred to enrollment.
Preparation neither starts transport nor creates client keys; partial creation remains recorded
or fenced for reconciliation, never adopted or deleted merely by name.

Enrollment is idempotent for the same operation identity and intent; a key or generation mismatch
refuses. It requires prepared secrets, persists pending/public intent, and activates only the
exact Scribe-owned Tether body after locked revalidation. Enrollment cannot rewrite units or
adopt a foreign/older application generation. Initially adding Tether is not an exception to
existing bind or active-Vessel restrictions.

The first profile admits one bounded maintenance transition: cold replacement of the transport
image through `prepare`, followed by ordinary complete-fileset bind and explicit enrollment.
Only the image reference may differ between the selected and proposed typed envelopes. Existing
server secret identities are reattested, never recreated or adopted; their immutable creation
authority is separate from each deployment envelope's preparation attestation. Before first
peer enrollment the road must be proven cold; after enrollment its exact current generation must
also have retained revocation evidence and the active closure latch. Preparation preserves peer
generation, the latch and all historical ownership and revocation records. It does not bind,
stop Core or start transport. [Privilege](10-privilege.md#tether-host-operations-designed) owns the
atomic transition and interruption rules; [Layout](13-layout.md#tether-custody-designed) owns its
retained evidence. Other envelope changes, including interface, endpoint, forwarding destination
and secret references, have no admitted migration in this profile. Ordinary bind alone cannot
migrate their preparation authority.

Inspection separates desired peer state, loaded generation, unit state and bounded transport
observations. A running unit or recent handshake alone is not end-to-end readiness. Secret-bearing
WireGuard dump output never becomes a public result or log.

Revocation first durably fences the current generation, then stops the whole Tether Pod and
forwarding process tree. It succeeds only after exact terminal observations establish closure;
an interrupted or unknown stop stays fenced and incomplete. A separately supervised host guard
closes the live road after a fence even if the CLI dies before submitting stop, as specified by
[Privilege](10-privilege.md#tether-host-operations-designed). A boot-only fence is insufficient.
The fixed closure latch is distinct from immutable generation-specific revocation evidence.
The first profile does not hot-reload peers. Repeating revoke reconciles the same generation;
re-enrollment requires the cold, ordered sequence in Privilege, preserves old revocation evidence,
and clears only the active latch after new intent is durable. A post-fence recovery path can
stop or observe transport, never restart or compensate back to the revoked world.

Tunnel loss has no public fallback. Reboot requires typed startup checks of current public intent and
retained generation evidence, the exact [persistent Scribe binding identity](13-layout.md#persistent-binding-identity),
and an active path guard, before either container starts. Device-number changes alone do not alter
that identity; changed source objects or content do. Legacy live-generation records confer no
reboot authority and are not automatically converted. A whole-state
rollback can restore both old intent and its old fence: a counter on that same disk cannot detect
it. Restore therefore requires independently retained revocation evidence or fresh server identity and client
re-enrollment; uncertainty refuses activation.

### Qualification and ownership transfer

The implementation must first prove rootless kernel WireGuard creation, real UDP handshake,
the exact pasta loopback mapping and denied alternate host routes, restricted OpenSSH forwarding,
established-session teardown, crash after fence persistence, guard failure, stale-state refusal,
loss and reboot on the selected host/runtime versions. Browser/SSE and hostile-origin acceptance
remain separate. Repository rendering tests establish none of these installed properties.

Ansible retains platform preparation and the explicit external UDP firewall opening. Native
Tether owns its tunnel, peers, keys, units and revocation. Qualify a replacement under a distinct
identity and endpoint before fencing and retiring the old infrastructure-owned road through its
own ownership procedure. Never run two controllers for one interface or adopt old units/secrets
by name. Qualification uses an isolated rootless installation; it does not mutate an existing
active Vessel, its data, source/image identity or receipts.

The alternative is a native-owned host `wg-quick` service with a restricted privileged helper.
It reduces network indirection but adds host-root mutation authority. It is not an automatic
fallback if this rootless profile fails: that authority needs a separate accepted amendment.

The mechanisms are documented by [WireGuard's namespace guide](https://www.wireguard.com/netns/),
[Podman's Pod unit reference](https://docs.podman.io/en/latest/markdown/podman-pod.unit.5.html),
the [pasta manual](https://passt.top/builds/latest/web/passt.1.html), and
[OpenSSH's configuration reference](https://man.openbsd.org/sshd_config). Their documentation
does not qualify this generated combination or replace exact-version live evidence.

## Peer custody and exact routes

The Codex may retain stable peer identity, public key, allowed addresses/routes, endpoint and
keepalive policy, enabled/revoked state, and creation/rotation metadata. Private and preshared keys
are hydrated through the secret boundary and never rendered into ordinary documentation, logs, QR
history, or public peer records.

Each route must be explicit. Host firewall policy determines which listeners the interface can
reach, Veil may apply ingress policy, and Ward and Vessel still authenticate and authorize.
Database administration, lifecycle mutation, Oculus, audio, model APIs, and A2A stay closed until
their own policy admits the peer. A tunnel address, interface, peer key, or forwarded metadata
can contribute credential evidence but cannot mint `magus:*`, widen a Sigil, or create an
administrator.

## Lifecycle, failure, and recovery

Binding validates peer-address overlap, route conflict, key reference, port collision, and the
generated service contribution before inscription. Revocation removes the peer from the active
interface and persists revised intent. Rotation overlaps old and new credentials only with explicit
operator authorization. Versioned public intent and retained revocation evidence fence stale
reconciliation; whole-state restore requires the independent evidence or fresh identity described
above. Failure stays visible and privileged traffic never falls back to a public route.

Dynamic addressing needs an operator-supplied reachable endpoint, whether through DNS, fixed
addressing, or a separately accepted rendezvous mechanism. Carrier NAT, blocked UDP, changing
endpoints, roaming, endpoint metadata, and traffic analysis remain concerns. Relay and NAT
traversal require separate trust decisions; recovery cannot introduce them invisibly.

## Delivery and consequences

This Covenant remains **Designed** pending installed qualification. The source candidate
implements the bounded native profile, including its exact UDP compiler contribution, server-secret
and peer custody, and closed operations under the [CLI grammar](19-cli.md). Core remains
loopback-published; the general Extension port grammar still rejects UDP. Source implementation
does not qualify live interface, enrollment, route policy, health, revocation, browser or reboot
behavior, and supplies no general key-rotation path. The optional infrastructure-owned
[single-operator forwarding candidate](09-security.md#single-operator-forwarding-candidate)
is separate from Tether and has no installed qualification. General tunnelling and shared-user
access remain unsupported. [State of
Work](../state-of-the-work.md#vpn-tether) owns that boundary.

Independent revocation is Tether's practical return. Operating that private road requires
security-sensitive peer and route management, backup, rotation, recovery, and an account of
uncertain direct reachability.
