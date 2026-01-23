---
title: Veil
icon: material/security
---

# :material-security: The Veil: Archon of the Threshold

> _"The Sepulcher is a sanctuary of silence. To speak with the Swarm without inviting the rot of the Forest, one must draw a Veil—a shimmering wall of cryptographic trust that blinds the malicious and guides the faithful."_

**The Veil** is the Proxy Archon of the LychD system. It is the implementation of **[ADR 30 (Proxy)](../../adr/30-proxy.md)**—a specialized gatekeeper based on **Caddy** that stands between the raw **[Vessel](../vessel/index.md)** and the chaotic public network.

While the Vessel handles the internal logic of the machine, the Veil handles the external reality of the "Forest" (the Internet). It provides the high-performance TLS termination, DDoS protection, and routing required to safely expose the **[Intercom (A2A)](../../adr/23-a2a.md)** and the **[Altar](../../divination/altar.md)** to the world.

## I. The Gatekeeper (The Infrastructure)

The Veil resides within the **[Sepulcher](../index.md)** as a standard container, acting as the primary point of ingress for all incoming traffic.

- **The Watch:** It claims Host Ports 80 and 443.
- **The internal NAT:** It shares the `localhost` namespace with the Vessel. Traffic arriving at the Veil is forwarded instantly to the internal port 8000, ensuring the application itself is never directly exposed to the wire.
- **The Persistence:** It maintains its own cryptographic keys and certificates within a dedicated volume in the **[Crypt](../crypt.md)**, ensuring that its identity remains stable across reanimations.

## II. The Scribe's Protocol (Composite Configuration)

To maintain the **[Federation Protocol](../../adr/05-extensions.md)**, the Veil does not possess a monolithic configuration. Instead, it utilizes the **Scribe's Protocol** for assembly.

- **The Fragments:** As mandated by **[ADR 30](../../adr/30-proxy.md)**, any extension can register its own `.caddy` fragments.
- **The Assembly:** During the **[Packaging Forge](../../adr/17-packaging.md)**, the system scans all active Archons and Extensions, concatenating their routing rules into a single, cohesive Caddyfile.
- **Example:** When the **[Intercom](../../adr/23-a2a.md)** is active, it injects a rule to expose `/a2a/*` while the rest of the system remains hidden behind authentication.

## III. Zero-Config Trust (Automatic TLS)

The Veil is a memory-safe entity written in Go, chosen specifically for its ability to automate the acquisition of cryptographic trust.

- **Automatic HTTPS:** The Veil contains a native ACME client. It negotiates, obtains, and renews SSL/TLS certificates (e.g., Let's Encrypt) without manual intervention from the Magus.
- **Hardened Headers:** By default, the Veil applies a set of protective runes—HSTS, X-Content-Type-Options, and Frame-Options—to prevent standard web-based exploits from reaching the Vessel.

## IV. The Shield of the Swarm

The Veil is the physical substrate upon which the **[Necropolis Protocol (A2A)](../../adr/23-a2a.md)** is built. It ensures that when two Liches communicate, the exchange is encrypted and authenticated.

- **Peer Verification:** It can be configured to require Mutual TLS (mTLS) for high-security A2A links, ensuring that only trusted peers can even initiate a handshake.
- **Rate Limiting:** It acts as a shield against "Exhaustion Attacks," preventing remote agents from flooding the **[Orchestrator](../../adr/21-orchestrator.md)** with malicious intents.

!!! danger "The Port Conflict"
    The Veil requires absolute sovereignty over ports 80 and 443. If the host machine is already running a mundane web server (e.g., Nginx or Apache), the Veil will fail to manifest. The Magus must either disable the rival service or modify the **[Codex](../codex.md)** to assign alternative coordinates.
