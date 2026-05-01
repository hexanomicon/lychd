---
title: 38. IAM
icon: material/account-check-outline
---

# :material-account-check-outline: 38. IAM: The Ward

!!! abstract "Context and Problem Statement"
    The LychD is a sovereign daemon, but it must be capable of interacting with multiple external entities—human "Apprentices" (Family) or automated "Peers" (API/SaaS)—without compromising the Master's total control. A mechanism is required to authenticate diverse identities and enforce granular access boundaries (**Wards**) over routes and capabilities, ensuring that the machine's "Inner Sanctum" remains air-gapped from restricted users.

## Requirements

- **Identity Plurality:** Support for multiple concurrent identities (Sigils) within the system's trust model.
- **Granular Scoping:** The ability to bind specific identities to limited functional scopes (e.g., `chat-only`, `api-only`, `system-admin`).
- **Symmetric Authentication:** Enforcement of identity checks at the **[Proxy (ADR 40)](./40-proxy.md)** and the **[Backend (ADR 11)](./11-backend.md)**.
- **Least Privilege:** By default, any new identity is granted zero access until explicitly endowed with a "Ward" by the Master.
- **Local Persistence:** Identity and permission records must reside within the **[Phylactery (ADR 06)](./06-persistence.md)**, rejecting external third-party auth providers.
- **Memory Namespace Discipline:** Identity must bound semantic recall/write paths using Sigil-derived `entity_id` unless an explicit shared-memory policy is granted.

## Considered Options

!!! failure "Option 1: Physical Data Isolation (Postgres Schemas)"
    Giving every user a separate database schema.
    - **Pros:** Maximum security; impossible for users to see each other's data.
    - **Cons:** **Architectural Bloat.** Unnecessarily complex for a system where users are sharing a single "Mind" (Agent). It complicates cross-user collaboration and system-wide memory retrieval.

!!! failure "Option 2: Single-User Sovereignty (No IAM)"
    Hardcoding the system to only accept one Master identity.
    - **Pros:** Absolute simplicity; zero overhead.
    - **Cons:** **Functional Rigidity.** Prevents the Magus from safely sharing the Lych's capabilities with family or integrating it with external webhooks (e.g., FB/SaaS) without exposing the entire system.

!!! success "Option 3: Scoped Sovereignty (RBAC + Sigils)"
    Using a Role-Based Access Control (RBAC) model where identities (Sigils) are assigned functional "Scopes."
    - **Pros:**
        - **Flexibility:** Allows the Master to hand one "Sigil" (Key) to a family member and another to an API, with different permissions for each.
        - **Efficiency:** Uses standard Litestar `Guards` to check scopes at the route level with near-zero latency.
        - **Centralized Mind:** All users interact with the same "Soul," but their perception of the system is filtered by their scope.

## Decision Outcome

**The Scoped Ward** is adopted as the IAM extension. It functions as a filter that determines which parts of the machine are visible to which identity.

### 1. The Sigil Registry

Identities are stored in a `cabal.identities` table.

- **Master Sigil:** The primary key created at Initialization via **[(CLI ADR 19)](./19-cli.md)**. Possesses the `*` (Universal) scope. Can be bound to a **Nostr Keypair** for global identity.
- **Guest Sigils:** Created by the Master for external entities. Each is bound to a specific list of **Scopes** (e.g., `echo.read`, `altar.interact`, `a2a.execute`). Can be represented by a **Nostr npub**.

### 1.1 The Nostr Identity Graft

The Ward integrates with the Nostr network to provide decentralized identity:
- **Cryptographic Auth:** The Proxy and Backend support Nostr-signed authentication, allowing the Magus to authenticate using their keys without traditional passwords.
- **Global Peerage:** A Sigil can be defined by a public key. When a remote Lich contacts the machine via Nostr, the machine automatically maps the identity to a Guest Sigil and applies the configured Wards.



### 2. Scoped Enforcement (The Ward)

The Ward is implemented as a set of **Litestar Guards** and **Middleware**:

- **Authentication:** Validates the incoming credential (JWT, API Key, or Passkey) and identifies the associated Sigil.
- **The Ward Check:** Before a route is executed, the Guard compares the route's required scope against the Sigil's granted scopes.
- **Capability Gating:** The **[Dispatcher (ADR 22)](./22-dispatcher.md)** can utilize the Sigil's scope to determine which tools are "visible" to the Agent during that specific user's session.
- **Skill Gating:** Maps A2A skills to internal Scopes. For example, an incoming A2A request for the code-gen skill is only permitted if the peer's Sigil possesses the skill.code-gen scope
- **Archive Gating:** Memory tools must query only the active Sigil namespace by default; this is the primary barrier against cross-soul contamination.

### 3. Proxy-Level Symmetry

The **[Veil (ADR 40)](./40-proxy.md)** acts as the first Ward. It can be configured to require a valid Sigil for any traffic originating from the public network, while allowing open access for traffic originating from the **[Tether (ADR 39)](./39-vpn.md)** (The Inner Circle).

## Consequences

!!! success "Positive"
    - **Safe Sharing:** The Magus can safely expose parts of the system to the public internet or family members without risking the core substrate.
    - **Operational Leaness:** Avoids the complexity of multi-database or multi-schema management.
    - **Sovereign Control:** The Master remains the sole arbiter of who can speak to the Lych and what they can say.

!!! failure "Negative"
    - **Internal Data Leakage:** Because data is not physically partitioned, the developer must be disciplined in ensuring that sensitive "Master-only" memories are not tagged with scopes that make them visible to "Guest" agents.
