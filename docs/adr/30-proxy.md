---
title: 30. Proxy
icon: material/shield-home
---

# :material-shield-home: 30. Proxy: The Veil

!!! abstract "Context and Problem Statement"
    Exposing a raw Python ASGI application server directly to the public internet presents a critical security liability. Standard application servers lack robust DDoS mitigation, high-performance static asset handling, and automated TLS lifecycle management required for production-grade sovereignty. A barrier is required to stand as the **Veil** between the internal Sepulcher and the public network—shielding the Daemon from malformed traffic while managing the acquisition of cryptographic trust for the decentralized swarm.

## Requirements

- **Automated TLS (ACME):** Mandatory zero-config negotiation and renewal of HTTPS certificates (e.g., Let's Encrypt) without external sidecars or manual scripts.
- **Container Cohesion:** Integration as a standard container within the pod, sharing the `localhost` namespace to route traffic to internal service ports.
- **Composable Ingress Ritual:** Provision for "Configuration Fragments" where Extensions register their own routing rules (e.g., specific subpaths) without modifying a monolithic core file.
- **Extension Sovereignty:** Implementation as a pluggable Archon, allowing the proxy engine to be swapped for alternative solutions without modification of internal application logic.
- **Protocol Agnosticism:** Native support for modern transport protocols, including HTTP/2, HTTP/3, and WebSockets, to facilitate high-performance scrying.
- **A2A Shielding:** Mandatory provision of the first layer of defense for the **[Intercom (23)](23-a2a.md)**, enforcing path-based routing and encryption for peer-to-peer traffic.

## Considered Options

!!! failure "Option 1: Nginx"
    The industry standard for high-concurrency proxies.
    - **Pros:** Unmatched performance and a massive community ecosystem.
    - **Cons:** **High Manual Overhead.** Nginx lacks native ACME (SSL) handling, requiring external `certbot` processes and brittle shell scripting to manage certificates, violating the "Self-Contained Daemon" philosophy.

!!! failure "Option 2: Traefik"
    A modern, cloud-native edge router.
    - **Pros:** Native label discovery and automated SSL.
    - **Cons:** **Architectural Overkill.** Designed for dynamic, distributed clusters. Its internal state management and configuration logic introduce unnecessary complexity for a static, single-pod architecture.

!!! success "Option 3: Caddy"
    A modern, memory-safe web server written in Go.
    - **Pros:**
        - **Automatic HTTPS:** Native, robust ACME client built directly into the binary.
        - **Simplicity:** Uses the "Caddyfile"—a human-readable, highly composable configuration format.
        - **Security:** Memory-safe execution and hardened default headers.
        - **Composability:** Perfectly suited for the "Composite Caddyfile" pattern where extensions inject config snippets into a shared directory.

## Decision Outcome

**Caddy** is adopted as the **Proxy Extension**, serving as the primary gatekeeper for the Sepulcher.

### 1. The Edge Gatekeeper

The extension registers `lychd-proxy.container` within the Pod, claiming Host Ports 80 and 443. It acts as the internal NAT gateway, forwarding public traffic to the internal **[Vessel (11)](11-backend.md)** on port 8000. Caddy was selected specifically for its ability to automate the acquisition of cryptographic trust without human intervention, ensuring the Daemon is "Secure by Default."

### 2. Composite Configuration (The Scribe's Protocol)

To maintain the federation of logic, the Proxy utilizes a dynamic assembly mechanism. Extensions register specific `.caddy` fragments during their registration hook. During the **[Packaging (17)](17-packaging.md)** ritual, the system concatenates these fragments into a single manifest. This allows an extension to register a rule like `reverse_proxy /a2a/* localhost:8000` to expose the Intercom without requiring manual edits to the Proxy source.

### 3. The Outer Intercom Ward

The Veil provides the first layer of shielding for the swarm. By enforcing mandatory TLS and path-based routing, it ensures that the agentic communion defined in **[A2A (23)](23-a2a.md)** is encrypted and hidden from unauthorized discovery. Traffic reaching the application kernel is thus pre-filtered, allowing internal logic to focus exclusively on higher-order authentication and resource prioritization.

### Consequences

!!! success "Positive"
    - **Privacy by Default:** The machine automatically achieves a "Grade A" security posture with encrypted traffic the moment it is bound to a domain.
    - **Zero-Maintenance SSL:** The Magus no longer manages renewals; the Lych handles its own cryptographic hygiene.
    - **Static Performance:** Caddy handles the serving of frontend assets significantly faster and more securely than the Python runtime.

!!! failure "Negative"
    - **Port Conflict:** Caddy requires ports 80/443. If the host machine is already running a web server, the LychD will fail to bind unless the user manually modifies the **[Codex (12)](12-configuration.md)**.
    - **DNS Dependency:** Automated SSL requires a valid DNS record pointing to the host; without it, the Proxy will fail to initialize the "Veil," leaving the system in a limited local-only state.
