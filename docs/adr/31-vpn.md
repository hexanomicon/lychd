---
title: 31. VPN
icon: material/lan-connect
---

# :material-lan-connect: 31. VPN: The Tether

!!! abstract "Context and Problem Statement"
    The **[Proxy (30)](30-proxy.md)** secures the public face of the Daemon, but administrative tasks—such as scrying traces in **[The Oculus (28)](28-observability.md)**, inspecting the database, or managing system lifecycles—require access to internal ports that must remain air-gapped from the public internet. A mechanism is required to extend the "Trust Boundary" of the localhost to authorized remote devices, creating a private, encrypted tunnel directly into the Sepulcher without relying on third-party relay servers or centralized coordination.

## Requirements

- **Absolute Sovereignty:** The tunnel must be strictly peer-to-peer; reliance on managed mesh networks requiring external authentication servers or third-party "Control Planes" is forbidden.
- **Stealth and Silence:** The service must remain silent to unauthenticated probes to minimize the attack surface on the host.
- **Kernel-Level Efficiency:** Utilization of a lightweight, high-performance protocol suitable for low-power mobile devices.
- **Privileged Zone Mapping:** Mandatory recognition of traffic originating from the VPN interface as "Internal," granting it access to dashboards physically blocked on the public proxy.
- **Automated Ritual of Bonding:** Integration with the **[CLI (18)](18-cli.md)** to facilitate the generation of keys and QR codes for frictionless mobile setup.
- **Persistence of Trust:** Mandatory storage of peer definitions within the **[Codex (12)](12-configuration.md)** to ensure the private network survives snapshots and upgrades.

## Considered Options

!!! failure "Option 1: Legacy OpenVPN"
    The traditional industry standard for secure tunnels.
    - **Cons:** **Architectural Bloat.** Possesses a massive, complex codebase prone to vulnerabilities. Slow cryptographic handshakes and high overhead result in poor performance on mobile devices.

!!! failure "Option 2: Managed Mesh Networks"
    Proprietary or open-core overlays that automate NAT traversal.
    - **Cons:** **The Breach of Autonomy.** These solutions require trusting a "Control Plane" hosted by a third party. If the provider's server is unreachable, the Magus is locked out of their own Daemon.

!!! success "Option 3: Wireguard"
    A modern, high-performance, kernel-level VPN protocol.
    - **Pros:**
        - **Minimalism:** Less than 4,000 lines of code, enabling easy security audits.
        - **Performance:** State-of-the-art cryptography providing the lowest latency and battery drain.
        - **Stealth:** Silent by design; it sends no response to invalid packets, effectively hiding the UDP port from scanners.
        - **Sovereign:** Operates purely on public/private key pairs without external introduction servers.

## Decision Outcome

**Wireguard** is adopted as the **VPN Extension**, serving as the "Silver Tether" that binds the Magus to the Lych.

### 1. The High-Trust Tunnel (The Infrastructure)

The extension registers `lychd-vpn.container` within the pod, claiming Host UDP Port 51820. The container is granted `CAP_NET_ADMIN` to manage the `wg0` interface. Wireguard ensures that remote devices are treated as local entities within the pod's private network (`10.88.x.x`), bypassing the restrictions of the public proxy.

### 2. Sovereign Identity and Bonding

To eliminate the complexity of manual key exchange, the extension grafts management subcommands onto the **[CLI (18)](18-cli.md)**. These rituals generate unique keypairs and assign internal IP coordinates, rendering the configuration as a QR code for instantaneous mobile bonding. All peer definitions are persisted in the **[Codex (12)](12-configuration.md)**.

### 3. Transport Tiering (The Inner Circle)

The architecture implements a firewall policy that differentiates between the public "Forest" and the private "Tether":

- **Administrative Access:** Traffic arriving via `wg0` is granted exclusive access to **[Oculus (28)](28-observability.md)** telemetry, **[Worker (14)](14-workers.md)** metrics, and system **[Rebirth (17)](17-packaging.md)** hooks.
- **Biometric Isolation:** Real-time audio streams (biometric data) defined in **[Echo (32)](../sepulcher/extensions/echo.md)** are physically restricted to the VPN interface to prevent voice-pattern leakage.
- **Sovereign Intercom:** High-trust **[A2A (23)](23-a2a.md)** endpoints (e.g., `/a2a/smith`) are physically pinned to the VPN interface, allowing nodes to collaborate on sensitive source code with the same security posture as `localhost`.

### Consequences

!!! success "Positive"
    - **Total Privacy:** Cryptographic keys remain only on the Magus's device and the Lych's iron. No third party possesses metadata regarding system access.
    - **Physical Stealth:** The Daemon is effectively invisible to internet scanning; only those who possess the "Silver Tether" can detect the VPN's existence.
    - **Sensory Performance:** The low-latency transport is the ideal substrate for real-time data, such as high-fidelity audio streams.

!!! failure "Negative"
    - **UDP Blocking:** Restrictive firewalls often block UDP traffic. In these environments, the VPN may fail, requiring fallback to the public Proxy.
    - **Dynamic IP Complexity:** If the host connection uses a changing public IP, the remote client requires a Dynamic DNS service to maintain the connection.
