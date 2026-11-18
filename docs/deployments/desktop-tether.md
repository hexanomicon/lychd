---
title: Desktop Tether
icon: material/lan-connect
---

# Offer a private desktop service

A desktop owner can offer one TCP service to a named WireGuard peer from an ordinary account.
The foreground `desktop-tether` helper uses a separate userspace WireGuard device and TCP/IP stack for
each grant. The only host listener it opens is the encrypted UDP port chosen for that peer.
The service address exists inside the helper. The operating system keeps its existing interfaces,
routes, DNS and firewall settings. Local Bridge continues to use loopback.

Use a dedicated local service that authenticates and authorizes **every remote application caller**,
including calls arriving from loopback. It must accept TLS 1.3 on `127.0.0.1` and present a certificate
whose public PEM you obtain from its owner. The helper verifies the exact leaf certificate, validity
and hostname on each connection. A different process inheriting the same port cannot receive
application bytes without the corresponding TLS key. The service sees the desktop helper as its
TCP peer. It cannot use source IP as application identity.

## Start and admit

1. Open a terminal in the installed desktop edition directory containing `desktop-tether` (macOS)
   or `desktop-tether.exe` (Windows). The operator tool runs separately from Vessel. For a source
   build, use Go 1.26 or later and run `go build -trimpath -mod=readonly .` in `clients/desktop-tether`.
2. Start the helper in a private terminal. Replace the addresses, ports and certificate with
   those selected by the local service owner. In PowerShell use `.\desktop-tether.exe`.

    ```text
    ./desktop-tether --service 10.93.0.1:8443 --loopback-port 18443 --backend-cert service.pem --backend-name localhost
    ```

3. Confirm the printed service coordinates and copy the fresh `session` value. The session begins
   with zero peers. Obtain the peer's WireGuard **public** key and confirm its identity and current
   authorization independently. For each device, enter a command at the running helper's stdin.

    ```text
    admit SESSION laptop 10.93.0.2 PEER_BASE64_PUBLIC_KEY 51821
    ```

    Each peer needs its own private IPv4 address, public key and unprivileged UDP port. The helper
    refuses a repeated identity, overlapping address, repeated key or occupied port. An active
    session supports up to eight peers and 32 simultaneous streams per peer. Each stream closes
   after one hour. The loopback TCP connection and TLS handshake have a five-second deadline.

4. Send the returned `server_public_key`, the admitted peer address, exact service address and
   the owner's reachable numeric UDP endpoint to the authenticated device. On that device, select
   its own private key, its assigned address as a `/32`, and a WireGuard peer with the returned
   server key, the chosen UDP endpoint, and **only the service address `/32`** as AllowedIPs.
   Use a client
   binding that stays closed when the selected tunnel disappears. Check for conflicting routes on
   the client before installing this exact route. Firewall permission
   and any public UDP port mapping belong to the owner. The helper requires no network administrator
   role and performs no firewall, NAT or client configuration.

    For example, this is the peer-side configuration for the laptop above. Replace the example
    outer address with the owner's reachable IPv4 address and the actual external UDP port.
    Generate the device key in its WireGuard client. Keep that private key on the device.

    ```ini
    [Interface]
    PrivateKey = <private-key-on-this-device>
    Address = 10.93.0.2/32

    [Peer]
    PublicKey = <server_public_key-from-this-grant>
    Endpoint = 192.0.2.10:51821
    AllowedIPs = 10.93.0.1/32
    ```

5. Use the application's normal authentication inside the tunnel and test an actual request.
   The TCP stream on the private service address carries the application protocol. The helper
   originates the TLS connection on the loopback leg. For example, an HTTP API receives HTTP
   inside WireGuard and HTTPS on loopback. An ordinary browser will treat a private HTTP origin
   accordingly. For a credential-free connectivity check against a service with a health endpoint,
   use `curl --noproxy "*" --connect-timeout 5 http://10.93.0.1:8443/health`. Confirm the service
   observes the request. Verify a different destination port fails and the same request stops
   reaching the service when the grant is revoked. Keep application credentials out of shell
   history and check the client binding's failure behavior before sending them.
   This profile excludes owner Bridge, client-certificate authentication, transparent
   end-to-end TLS and services that trust loopback callers.

The helper generates each grant's WireGuard private key in memory and reports only its public key.
The peer retains its own private key. The service retains its TLS private key. Keep general
application credentials outside Tether. The `status` console command reports admitted grants
and generations. A recorded active grant identifies local admission only. Observe the application's
authenticated response separately. If the tunnel or pinned service fails, the helper closes the
stream and selects no alternate route or destination.

## Revoke, stop and recover

Keep a connection open from each of two peers. In the terminal that owns the helper, enter
`revoke laptop GENERATION` with the generation returned for that peer. The result changes to
`active: false` after its listener, WireGuard device and relays close. Verify that the revoked
peer loses the original stream and cannot open another. Verify that the other peer can still use
its original stream. Revocation cannot recall delivered bytes, revoke a remote application session,
or undo a completed request.

Closing stdin or ending the process removes every grant it owns. A fresh process generates a new
session, starts closed and rejects saved admission commands. Each new grant generates a fresh
server key. A revoked name, key or address remains reserved for the rest of its session.
After restart or a disk restore, check current revocations with the independent owner before
**explicitly re-enrolling** a device and delivering its new server public key. The helper has no
persisted authority to automatically restore. End the helper before sleep, hibernation or live
snapshot. Resuming an old in-memory process needs separate revocation-authority qualification.

Run `go test -mod=readonly -v ./...` from the helper source directory to exercise disposable
encrypted peers against a local TLS service. The test observes application bytes on two peers,
denies other destinations and port takeover, checks live revocation and tests stale admission after
restart. Native-host execution, physical peer devices, cold boot and sleep/resume have distinct
evidence requirements. See the [VPN contract](../adr/39-vpn.md), [desktop profile](desktop.md) and
[desktop Tether qualification issue](https://github.com/hexanomicon/lychd/issues/183).
