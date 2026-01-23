---
title: Tether
icon: material/link-lock
---

# :material-link-lock: Tether: Archon of the Inner Circle

> _"The Veil protects the temple from the masses, but the Tether is the umbilical of light that binds the Magus to the Lych. Across any distance, through any forest, the Silver Tether ensures that the Master's voice is always heard as if they stood within the Crypt itself."_

**The Tether** is the VPN Archon of the LychD system. It is the implementation of **[ADR 31 (VPN)](../../adr/31-vpn.md)**—a specialized, high-performance tunnel based on **Wireguard**.

While the **[Veil](./veil.md)** secures the public face of the Daemon, the Tether creates a private, encrypted "Inner Circle." It allows the Magus to access privileged internal services—such as the raw cognitive traces of the **[Oculus](./oculus.md)** or the host's **[Cockpit](./oculus.md)**—from remote, untrusted networks without exposing them to the open internet.

## I. The Tunnel Digger (The Infrastructure)

The Tether resides within the **[Sepulcher](../index.md)** as a privileged container, tasked with manipulating the network fabric to create a secure bridge.

- **The Interface**: It creates the `wg0` virtual interface. As mandated by **[ADR 31](../../adr/31-vpn.md)**, it is granted `CAP_NET_ADMIN` to manage the host's routing tables.
- **The Stealth**: Wireguard is silent by design. The Tether does not respond to unauthenticated packets, making the VPN's UDP port (default: 51820) effectively invisible to port scanners.
- **The Routing**: Once connected, the Magus's device is treated as a local entity within the Pod's private network (`10.88.x.x`), bypassing the restrictions of the public proxy.

## II. The Ritual of Bonding (Management)

The Tether eliminates the complexity of manual key exchange through specialized rituals grafted onto the **[CLI](../../adr/18-cli.md)**.

- **The Inscription**: `lychd vpn add-peer <name>` generates a unique cryptographic keypair and assigns an internal coordinate.
- **The Vision**: `lychd vpn show-qr <name>` renders the configuration as a QR code directly in the terminal. The Magus simply scans this with a mobile device to "bond" it to the Lych.
- **The Codex**: All peer definitions and keys are persisted within the **[Codex](../codex.md)**, ensuring the "Inner Circle" survives system **[Snapshots](../../adr/07-snapshots.md)** and migrations.

## III. The Privileged Zone (Security)

The Tether enforces a fundamental distinction between types of ingress. It recognizes the "Silver Tether" as a signal of absolute authority.

- **The Public Forest**: Traffic from the **[Veil](./veil.md)** is limited to standard web endpoints and A2A interfaces.
- **The Inner Circle**: Traffic from the **Tether** is granted access to the "Sacred Organs." This includes the **[Oculus Trace UI](./oculus.md)**, the raw metrics of the **[Ghouls](../vessel/ghouls.md)**, and the ability to trigger a **[Rebirth](../../adr/17-packaging.md)**.

## IV. Absolute Sovereignty

Following the Iron Pact of Sovereignty, the Tether is strictly peer-to-peer.

- **No Third Parties**: Unlike managed mesh networks (Tailscale/ZeroTier), the Tether relies on no external "Control Plane." If the internet breaks, but the route between Magus and Lych remains, the Tether functions.
- **Kernel Efficiency**: By utilizing the Wireguard protocol, the Tether provides the lowest possible latency and battery drain for mobile devices, making it the ideal substrate for the **[Echo's](./echo.md)** real-time audio streams.

!!! danger "The Endpoint Paradox"
    For the Tether to find its anchor, the Lych must be reachable. If the host machine is behind a restrictive firewall or a dynamic IP, the Magus may need to employ a Dynamic DNS service or configure Port Forwarding on their gateway.
