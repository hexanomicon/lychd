---
title: 9. Security
icon: material/shield-lock-outline
---

# :material-shield-lock-outline: 9. Security: Defense in Depth

!!! abstract "Context and Problem Statement"
    LychD executes powerful AI-driven workflows that can:

    - inspect files
    - generate code
    - call external services
    - trigger background labor

    This creates a multi-layer security problem: LychD must handle untrusted or partially trusted execution while preserving the integrity of the control plane.

## Requirements

- **Contained Compromise:** The model must minimize blast radius through layered controls rather than relying on a single boundary.
- **Separated Execution Authority:** Untrusted or partially trusted execution must be able to operate on real data and tools without inheriting control-plane authority.
- **Clear Authority Distribution:** The architecture must explicitly define which units may:
    - hold secrets
    - mutate durable state
    - reach the network
- **Rootless Identity Symmetry:** Rootless containers must interact with user-owned host volumes without requiring `root`, hardcoded host assumptions, or unsafe permission broadening.
- **Immutable Trusted Runtime:** Trusted runtime code and trusted mounts must be protected from self-modification during execution.
- **Default-Deny Egress:** Untrusted execution must have deny-by-default outbound network access, with tightly scoped exceptions when enabled.

## Threat Model

The security posture is designed around the following assumptions:

### Trusted

- The host operating system and user account of the Magus
- Rootless Podman / Quadlet runtime posture
- Vessel control-plane services
- Host Reactor / privileged intent executor
- Podman secret storage
- Explicitly trusted database roles and control-plane credentials
- The Identity Symmetry (UID 1000) mapping

### Untrusted or Potentially Compromised

- Arbitrary code execution
- Code generation outputs before verification
- Browser and crawler payloads
- Remote peer inputs
- Tool outputs from untrusted sources
- Tomb/worker execution by default

### Defended Against

- Secret exfiltration
- Unauthorized file reads from trusted regions
- Unauthorized durable state mutation
- Lateral movement from unsafe execution into the control plane
- Over-broad network egress from risky workloads
- Host escalation via container compromise
- Cross-identity memory contamination
- Replay of unsafe results without re-approval

### Explicitly Not Claimed

- Protection against all kernel 0-days
- Protection against malicious host administrators
- Protection against physical compromise of the machine
- Absolute safety from every parser, dependency, or database vulnerability

The model aims for strong practical containment, not magical invulnerability.

## Considered Options

!!! failure "Option 1: Single Shared Trust Domain"
    Run agents, arbitrary execution, durable state transitions, and secret-bearing provider calls inside one application/process boundary.

    - **Pros:** Lowest architectural complexity. No secondary service or security substrate required.
    - **Cons:** **Trust Collapse.** If arbitrary execution occurs in the same boundary as durable control-plane authority or mounted secrets, compromise of that process becomes compromise of the system's most sensitive functions.
    - **Verdict:** Rejected.

!!! failure "Option 2: Process Sandbox as the Primary Boundary"
    Rely on per-process sandboxing inside the main container as the dominant protection model.

    - **Pros:** Lower operational overhead than a dedicated execution plane. Fine-grained file and network controls are possible.
    - **Cons:** **Boundary Blur.** This turns one runtime into multiple overlapping trust zones and makes the main container simultaneously trusted and untrusted. The result is a harder-to-reason-about authority graph.
    - **Verdict:** Rejected as the primary model.

!!! failure "Option 3: Worker Container Only, No Fine-Grained Execution Hardening"
    Isolate unsafe execution into a separate worker container and rely exclusively on the container boundary, rootless posture, SELinux, and least-privilege mounts.

    - **Pros:** Clean trust separation. Simpler to reason about than in-process sandbox orchestration.
    - **Cons:** **Coarse Grain Only.** This gives a strong service boundary but does not distinguish between different risky subprocesses inside the same worker. It also leaves outbound egress policy less expressive unless additional controls are introduced.
    - **Verdict:** Insufficient as the ideal end-state, but acceptable as a minimal posture.

!!! failure "Option 4: Zerobox for Process Sandboxing"
    Use the Zerobox framework to isolate worker processes.

    - **Pros:** Provides a developer-friendly wrapper and built-in secret proxying.
    - **Cons:** **Requires `CAP_NET_ADMIN`.** Zerobox relies on creating custom network namespaces, which requires the `CAP_NET_ADMIN` Linux capability. Because `CAP_NET_ADMIN` cannot be safely granted in a purely rootless environment, it breaks the requirement for strict, rootless Podman containers.
    - **Verdict:** Rejected. It is too heavy for the current architecture.

!!! success "Option 5: Two-Plane Trust Model with Sandboxed Worker Subprocesses (The Golden Mean)"
    Use a separate worker/shadow execution plane as the primary boundary, but explicitly treat it as **Semi-Trusted**. All actual untrusted execution runs inside a kernel-enforced subprocess sandbox (`nono`).

    - **Pros:**
        - **Defense in Depth:** The container boundary protects the host, while the sandbox protects the container's high-value environment variables (DB credentials).
        - **Clear Topology:** The Semi-Trusted worker loop acts as a built-in proxy for the sandbox, removing the need for complex network routing.
        - **V1 Pragmatism:** Allows the entire system to share a single network Pod for easy bootstrapping, while retaining absolute file and network isolation for untrusted code.
    - **Verdict:** Selected for the Initial Phase (V1).

## Decision Outcome

LychD adopts a layered **Defense in Depth** model built around a hard trust split:

- **Vessel** is the trusted control plane.
- **The Tomb** is the **Semi-Trusted** execution plane.

The architecture relies on the **"Golden Mean"** for its Initial Phase (V1):
All containers (`vessel`, `lychd-tomb`, `phylactery`) share a single Pod and therefore share a `localhost` network namespace. Because they share a network, they all have internet access and can "see" each other's ports.
Security is guaranteed by two independent layers:

1. **Layer 7 Authentication:** Containers can see the Database and Phoenix, but they cannot access them without the proper passwords. The Tomb is given only a strictly-scoped least-privilege role.
2. **The Nono Sandbox:** Untrusted execution never runs directly in the Tomb container. It is spawned inside `nono`, which uses Linux Landlock to enforce **zero network access** and strict file isolation.

If the `nono` sandbox is breached (e.g., via a Kernel 0-day), the attacker escapes into the Tomb container. They gain internet access and the queue password, but they hit the titanium wall of the container boundary. They cannot steal the Vessel's master DB passwords, API keys, or signing keys.

!!! warning "Axiom: Identity vs. Mounts (The Badge vs. The Wall)"
    Do not confuse system-level authority with data-level authority.

    - **Identity (The Badge):** Provides **system-level security**. Symmetric Identity (UID 1000) prevents Root escalation while allowing native file editing. The boundary between planes is *not* defined by different UIDs.
    - **Mounts (The Wall):** Provide **data-level security**. Mounts are absolute and throw a "blanket" over internal container permissions. The wall between the Vessel and the Tomb is entirely Mount-Defined.

### 1. Defense in Depth Layers

#### Layer 1: The Static Alias (Pre-carved Geometry)

The image creates a dedicated fallback unprivileged user:

```dockerfile
RUN groupadd --system --gid 1001 lich && \
    useradd --system --uid 1001 --gid 1001 --create-home lich

RUN mkdir -p /home/lich/.local/share/lychd && chmod -R 777 /home/lich

USER lich
```

The internal `lich` user (UID 1001) exists only to pre-carve the container's geometry (home directories and shells). It is a Static Alias ensuring consistent internal paths (`/home/lich`) regardless of who the host user is.

The `chmod 777` on `/home/lich` acts as a Bootstrap Grease Trap. It allows any mapped host UID to immediately write internal caches (e.g., `.cache/uv`) upon booting, avoiding permission conflicts with the "baked-in" UID 1001.

#### Layer 2: The Warden (External Rootless Runtime)

LychD uses rootless Podman as the baseline runtime posture.

If a container breakout occurs, the attacker inherits only the authority of the host user, not host `root`. This does not make compromise harmless, but it meaningfully reduces escalation potential compared to privileged or rootful execution.

#### Layer 3: Identity Symmetry (The "Badge")

The static image identity is not sufficient for real host interaction. The runtime therefore applies a dynamic host/container identity bridge through Quadlets:

```ini
[Container]
User=%U
UserNS=keep-id
```

The `keep-id` flag acts as a Runtime Identity Mapping. It performs a "Hot Swap" that maps the Host user (UID 1000) directly into the container, overriding the `USER` instruction from the Containerfile.

This creates a **Double Non-Root** posture:

1. On the host, the process is a normal unprivileged user.
2. Inside the container, the process is also non-root.

Because the UID matches the invoking host user, the process can interact with user-owned volumes without unsafe permission broadening. The architecture explicitly rejects a separate Tomb UID (1001) for runtime execution, as mismatched UIDs prevent the AI from natively editing the Magus's files. System security is instead achieved via the Non-Root status of UID 1000—which inherently protects the container's internal `/etc` and `/usr`—combined with strict Read-Only Mounts for trusted paths.

#### Layer 4: The Mount-Defined Boundary (The "Wall")

The boundary between the Vessel and the Tomb is Mount-Defined, not Identity-Defined. 

- **The Vessel:** High-trust plane. Granted Read-Write (RW) mounts to the Codex, Crypt, and Projects.
- **The Tomb:** Low-trust plane. Restricted by Read-Only (RO) mounts for system files and the Codex. It receives RW access only to disposable Workspaces (The Lab).

Native code modification is protected by Git Branching, not by different UIDs. Unsafe execution may manipulate workspaces, but it must not rewrite the trusted running body of the control plane.

When a host volume is bound to a container path, it throws a "blanket" over the internal permissions. The host's UID, GID, and Mode are the only laws that matter on that mount point. The internal `777` of the Bootstrap Grease Trap is effectively erased and replaced by the host's strictness.

#### Layer 5: The Shield (SELinux)

Where supported, mounts use SELinux relabeling via `:Z`.

This adds a kernel-enforced MAC layer on top of UID-based posture. SELinux does not replace proper trust zoning, but it hardens file access boundaries and helps prevent accidental or malicious access across mislabeled paths.

#### Layer 6: Secret Scope & Secret Classes

Secrets are stored by reference in configuration and materialized through Podman secret storage only into units that require them.

#### Secret Materialization Contract

- Codex and rune schemas store secret references, not inline runtime values.
- Quadlet generation emits `Secret=` directives only for the units that require them.
- The bind process fails closed if required runtime secrets are missing.
- File-based config containing sensitive references must be Magus-owned and `0600`.

Operational example:

```bash
printf '%s' "$OPENAI_API_KEY" | podman secret create --replace portal_openai_main -
podman secret ls
podman secret inspect portal_openai_main
```

#### Secret Classes

The architecture distinguishes multiple secret classes:

- **Control-plane secrets:** database credentials, internal signing keys, privileged provider credentials
- **Provider secrets:** API keys for remote portals and external services
- **Identity-scoped secrets:** secrets tied to a user, Sigil, or delegated identity
- **Ephemeral execution tokens:** temporary tokens or envelopes derived for bounded workflows

Policy:

- Control-plane secrets belong only in trusted units.
- Untrusted execution planes do not receive durable secrets by default.
- If a secret must be hidden from agent-level execution, it must be moved to a separate service boundary.
- Secret safety is boundary-defined, never obfuscation-defined.

#### In-Process Reality

Permissions at rest protect secrets from other host users and less-privileged host processes. They do **not** protect secrets from code executing inside the same privilege boundary.

If a unit can use a secret, that unit must be assumed capable of reading it.

#### Layer 7: The Two-Plane Trust Boundary

Security is built around a hard split between trusted and untrusted roles:

- **Vessel**: trusted control plane, durable authority, queue ownership, secret-bearing provider operations
- **The Tomb**: untrusted execution plane, arbitrary code, risky tools, disposable workspaces, constrained output return

Invariant:

> Arbitrary execution and high-value secrets do not coexist in the same unit.

#### The "Ask the Brain" Protocol (LLM Proxying)

To enforce the central law, the Tomb execution plane (and its internal `nono` sandboxes) is strictly forbidden from communicating directly with any LLM provider, including local instances.

- If AI reasoning is required by untrusted code executing within the Tomb plane (e.g., to debug a generated script), a structured intent must be emitted to the Tomb proxy loop.
- This request is then routed back to the Vessel via an internal HTTP endpoint or a fast-lane queue.
- The intent is received by the **[Dispatcher (22)](22-dispatcher.md)**, where Ward policies and the Privatization Gate are applied. The provider call is then executed by the Vessel utilizing its secured secrets.
- Only the resulting string is returned to the Tomb plane.

This mechanism ensures that while cognitive labor can be requested by the execution plane, the system's economic limits cannot be bypassed, API keys cannot be stolen, and the underlying model hardware cannot be accessed directly.

#### Layer 8: Worker Process Sandboxing (`nono`)

Inside the Tomb plane, the architecture enforces strict per-process sandboxing using **`nono`**. This is not an optional layer; it is the fundamental mechanism that enables the shared Pod architecture.

- The `lychd-tomb` container itself has internet access and holds the DB queue credentials.
- The `lychd-tomb` Python worker loop (the Ghoul) is **Semi-Trusted**.
- When the Ghoul picks up a code-execution job from SAQ, it uses `uv` to fast-install any required dependencies into a **job-scoped temporary workspace** before handing it to `nono`. The Ghoul has internet access for this step; `nono` does not.
- The Ghoul then wraps the actual untrusted execution in `nono`.
- `nono` uses Landlock to restrict the process to the job workspace directory and completely **drops its network interface**.
- If the untrusted script needs to fetch a URL, it cannot do so directly. It must ask the Semi-Trusted Tomb loop (the proxy) to fetch the URL on its behalf.

This ensures **zero exfiltration** of mounted user files and prevents the untrusted script from reading the DB credentials stored in the container's environment variables.

The Tomb does not run agent logic, graph runners, or LLM provider calls. It is a brainless executor. The full doctrine is defined in **[Workers (14)](14-workers.md)**.

### 2. Egress Posture (Network Is Authority)

Outbound network is treated as authority, not convenience.

#### Core Rules

- The `lychd.pod` shares a network namespace, meaning containers inherently possess the Pod's internet route.
- The Vessel and Semi-Trusted Tomb loop utilize this native egress.
- **Untrusted execution (inside `nono`) defaults to ZERO egress.**
- Wide-open outbound access from a sandbox is forbidden. Any sandbox requiring external data must route requests through the Tomb loop acting as its proxy.

    - no secrets
    - no broad durable mounts
    - no broad database role
    - lower trust classification

#### Worker Egress Modes

The system allows multiple worker postures depending on need:

- **No-network execution**
- **Brokered or allowlisted egress**
- **Broader egress with reduced authority elsewhere**

This keeps security practical without pretending all workloads are equal.

#### Portal Egress Gate

Outbound context is weighted before dispatch:

- `0.0` = public-safe
- `1.0` = strictly private

Policy:

- below `portal_threshold`: portal egress allowed
- at/above `portal_threshold`: anonymization required
- at/above `forbidden_threshold`: raw portal egress forbidden

If anonymization cannot satisfy policy, the request fails closed.

### 3. Database Least Privilege

The worker boundary is only meaningful if its database authority is narrow.

Rules:

- Tomb/worker units do not receive broad database credentials
- no superuser
- no migration authority
- no schema ownership outside explicitly assigned surfaces
- no durable queue/database ownership for untrusted execution
- if database access is granted, it must be:

    - role-scoped
    - schema-scoped
    - operation-scoped
    - identity-scoped where applicable

The database must never become the accidental bridge that nullifies all other boundaries.

### 4. Subprocess & Runtime Mutation Policy

Unsafe execution is permitted only under bounded conditions.

#### Vessel

- no arbitrary shell execution
- no arbitrary Python execution
- no runtime package installation
- no mutation of trusted runtime body

#### Tomb

- may execute arbitrary code only in scoped workspaces
- may run risky tools only under constrained mount/network policy
- does not run agent logic, graph runners, or LLM calls — it is a brainless executor
- runtime package installs should prefer:

  1. build-time inclusion
  2. disposable execution-local workspace installs (via `uv` into job-scoped directories)
  3. never mutation of the trusted control-plane environment

This keeps experimentation and codegen possible without normalizing mutation of trusted infrastructure.

!!! warning "Untrusted Returns"
    The Tomb `stdout` returned to the Vessel is **untrusted**. If the executed code processed data fetched from the internet, the output may contain adversarial content including indirect prompt injection attempts. Tool outputs returning from the Tomb must be treated as untrusted when injected into agent context.

### 5. Authority Matrix

| Dimension        | Vessel (Trusted Control Plane)                                 | The Tomb (Un-trusted Execution Plane)                                  |
| :--------------- | :------------------------------------------------------------- | :------------------------------------------------------------------ |
| **Identity**     | UID 1000 (Symmetric Identity).                                 | UID 1000 (Symmetric Identity).                                      |
| **Secrets**      | Accesses queue/database credentials and high-value API keys.   | Accesses queue/database credentials only (Least Privilege Role).    |
| **Mounts**       | Read-Write access to Codex, Crypt, and Projects.               | Read-Only access to Codex; Read-Write access to disposable Workspaces. |
| **Network**      | Shared Pod network (Internet + Localhost).                     | Shared Pod network. (Sandboxed `nono` subprocesses have zero network). |
| **Queue Control**| Owns enqueue/dequeue/retry lifecycle for core tasks.           | Owns enqueue/dequeue/retry for untrusted tasks via the worker loop. |
| **Agent / LLM**  | All cognitive labor runs here exclusively.                     | Forbidden. The Tomb is a brainless executor.                        |
| **Context Egress**| Applies privatization and anonymization gates.                | Cannot bypass egress policy.                                        |
| **Host Authority**| May emit validated host intents via the Host Reactor contract.| Cannot emit host intents or mutate infrastructure.                  |
| **Arbitrary Code**| Forbidden.                                                     | Allowed only in constrained execution contexts (`nono` sandbox).    |
| **Mutation**     | Forbidden. Protected by Git Branching and RO Mounts.           | Allowed only in disposable/task-scoped areas.                       |

### 6. Compromise Response

Detection of a Tomb or worker compromise triggers deterministic containment.

Minimum expected actions:

- revoke active lease
- kill or quarantine the affected worker unit
- invalidate runtime envelopes or task grants
- quarantine workspaces and produced artifacts
- mark related queue jobs as tainted
- rotate any credentials that may have been exposed
- require manual consecration before replay or promotion
- preserve audit evidence for later analysis

The goal is not merely to stop the process. It is to prevent silent continuation of contaminated state.

### 7. Auditability

The system must produce structured security-relevant events for at least:

- privileged host intents
- secret materialization and secret-binding failures
- shadow dispatches
- policy denies
- portal egress denials or anonymization requirements
- compromise-triggered quarantine or revocation flows

Security posture is only real if it is inspectable after the fact.

### 8. Future Hardening (The Remaster)

The V1 "Golden Mean" (Shared Pod + Nono + Layer 7 Auth) is deliberately pragmatic. It allows LychD to bootstrap and self-host safely today without writing complex custom network routers.

However, the architecture explicitly acknowledges possible future sovereign security milestones for later versions (V2+):

- **Total Network Separation:** Abandoning the shared `lychd.pod` in favor of strict, isolated Podman networks (`lychd-core`, `lychd-tomb`).
- **Dedicated Worker API Plane:** Tomb workers communicating with the Vessel purely over a restricted internal API, removing direct database access from the worker completely.
- **Sovereign Egress Proxy:** Moving the egress routing into a dedicated Vessel service, potentially dropping the reliance on `nono`'s internal Rust proxy in favor of a pure-Python boundary.

These are valid long-term directions. They are **not** immediate prerequisites. The current container boundary combined with `nono` provides sufficient blast-radius containment while the system matures.

## Consequences

!!! success "Positive"
    - **Legible Trust Topology:** The system cleanly distinguishes trusted control-plane duties from untrusted execution.
    - **Defense in Depth:** Host, container, process, network, and data boundaries all contribute independent resistance.
    - **Deterministic Identity Posture:** UID symmetry solves the permission dilemma without granting root.
    - **Secret Honesty:** The architecture explicitly rejects fake in-process secrecy claims and treats boundaries as the real protection mechanism.
    - **Practical Evolution:** The design allows current hardening with room for future sovereign replacements.

!!! failure "Negative"
    - **Operational Discipline Required:** Bad mounts, over-broad roles, or wide-open egress can still collapse an otherwise good design.
    - **Shared Kernel Reality:** Rootless containers and process sandboxes remain stronger practical containment, not perfect isolation.
    - **Complexity Tax:** Separate trust planes, narrow roles, and quarantine flows impose real implementation and maintenance cost.
    - **Platform Coupling:** The model remains deeply tied to Podman, Quadlets, Systemd, and Linux security semantics.
