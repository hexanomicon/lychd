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
- Host Reactor / host-authoritative user-service intent consumer
- Podman secret storage
- Explicitly trusted database roles and control-plane credentials
- The Pod-level `keep-id` mapping for the invoking, unprivileged host user

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
- Direct acquisition of host `root` through the ordinary rootless container identity
- Cross-identity memory contamination
- Replay of unsafe results without re-approval

### Explicitly Not Claimed

- Protection against all kernel 0-days
- Protection against malicious host administrators
- Protection after compromise of the trusted Magus host account or another process with that UID
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

!!! failure "Option 5: MicroVM Execution Substrate"
    Run untrusted Tomb jobs inside per-job microVMs such as Firecracker, Cloud Hypervisor, or QEMU/KVM guests.

    - **Pros:** Provides a stronger kernel boundary than containers or process sandboxes. A guest kernel compromise remains inside the guest unless the attacker also escapes the VMM/KVM boundary.
    - **Cons:** **Requires privileged host cooperation.** A production posture needs host-managed KVM access, jailer/chroot or equivalent process isolation, cgroups, rootfs/kernel image preparation, and network/vsock setup. This would either grant too much substrate authority to the Vessel or require a separate host-side microVM supervisor that has not yet been specified.
    - **Verdict:** Rejected for V1. MicroVM-backed Tomb execution is a valid future hardening path only after a dedicated host-mediated supervisor contract is defined.

!!! success "Option 6: Two-Plane Trust Model with Sandboxed Worker Subprocesses (The Golden Mean)"
    Use a separate worker/shadow execution plane as the primary boundary, but explicitly treat it as **Semi-Trusted**. All actual untrusted execution runs inside a kernel-enforced subprocess sandbox (`nono`).

    - **Pros:**
        - **Defense in Depth:** The container boundary protects the host, while the sandbox protects the container's high-value environment variables (DB credentials).
        - **Clear Topology:** The Semi-Trusted worker loop acts as a built-in proxy for the sandbox, removing the need for complex network routing.
        - **V1 Pragmatism:** Allows the system to share one network Pod for easy bootstrapping while retaining explicit mount boundaries and a separate no-network subprocess sandbox for untrusted code.
    - **Verdict:** Selected target architecture. The trusted core boundary is implemented first;
      the separate Tomb/nono execution plane is still pending.

## Decision Outcome

LychD adopts a layered **Defense in Depth** model built around a hard trust split:

- **Vessel** is the trusted control plane.
- **The Tomb** is the **Semi-Trusted** execution plane.

!!! warning "Foundation status: do not submit untrusted code yet"
    The current generated topology contains the trusted Vessel/core, narrow validated mounts,
    rootless identity, loopback-only host publication, and the typed Host Reactor boundary. It does
    **not** yet contain a Tomb Quadlet, Tomb SAQ queue/profile, narrow Tomb database role, executor
    loop, or `nono` invocation path. Every Tomb and `nono` rule below is normative design for that
    future plane, not a claim that arbitrary code execution is safe in the current Vessel. Until
    the whole boundary lands and is tested, untrusted tool execution is unavailable.

The architecture relies on the **"Golden Mean"** for its Initial Phase (V1). Joined containers
share one Pod and therefore one `localhost` network namespace and internet route; they can see each
other's listening ports. Host-published core and extension ports are generated on `127.0.0.1` only.
The practical boundaries are therefore layered rather than absolute:

1. **Service credentials:** services such as Postgres require their own scoped credentials. A shared
   network never implies shared database authority.
2. **Mount isolation:** a process cannot directly read a secret or control file that is not mounted
   into its unit.
3. **The Nono Sandbox (planned):** untrusted execution is intended to run inside `nono`, which uses Linux
   Landlock to enforce zero network access and strict file isolation inside the Tomb plane.

Loopback is not authentication. The current LychD web Ward stamps requests with the single
settings-derived Sigil and applies scope guards; it does not authenticate distinct callers. The
Altar/API is therefore a single-user, local-only foundation surface. Publishing it remotely requires
a separately configured authenticated, authorized, TLS-terminating front door; changing the bind
address alone is not a supported security posture.

If the `nono` sandbox is breached, the attacker reaches the Tomb container's authority, including
any narrow worker credential and shared-Pod endpoints. The mount boundary still prevents direct
filesystem reads of unmounted Vessel secrets, but service/API authorization must independently
protect every reachable endpoint. In particular, the current local-only LychD API must not be
treated as a hostile-network boundary.

!!! warning "Axiom: Identity vs. Mounts (The Badge vs. The Wall)"
    Do not confuse system-level authority with data-level authority.

    - **Identity (The Badge):** The rootless Pod maps the invoking unprivileged host identity with
      `keep-id`; it does not hardcode UID 1000. This avoids host-root authority and permits assigned
      user-owned mounts, but it does not distinguish trusted and untrusted planes.
    - **Mounts (The Wall):** Provide **data-level security**. Mounts are absolute and throw a "blanket" over internal container permissions. The wall between the Vessel and the Tomb is entirely Mount-Defined.

### 1. Defense in Depth Layers

#### Layer 1: Rootless User Geometry

The image creates a dedicated fallback unprivileged user:

```dockerfile
RUN groupadd --system --gid 1001 lich && \
    useradd --system --uid 1001 --gid 1001 --create-home lich

USER lich
```

The internal `lich` user (UID 1001) is a fallback image identity, not a filesystem authority.
Persistent runtime paths are governed by **[Layout (13)](13-layout.md)** and only the specific paths
assigned to a unit are mounted symmetrically. The Vessel does not receive a blanket
`~/.local/share/lychd` mount. The image may provide a writable home for process caches, but no
security rule may rely on the baked-in user home as the canonical data topology.

#### Layer 2: The Warden (External Rootless Runtime)

LychD uses rootless Podman as the baseline runtime posture.

If a container breakout occurs, the attacker inherits only the authority of the host user, not host `root`. This does not make compromise harmless, but it meaningfully reduces escalation potential compared to privileged or rootful execution.

#### Layer 3: Identity Symmetry (The "Badge")

The static image identity is not sufficient for real host interaction. The runtime therefore
applies the user-namespace bridge once at the Pod and selects the process user per container:

```ini
[Pod]
UserNS=keep-id

[Container]
User=%U
```

`UserNS=keep-id` belongs to `lychd.pod`. Joined containers inherit that namespace, so generated
container Quadlets do not repeat a per-container `UserNS=` directive. `User=%U` is emitted for the
Vessel, migration gate, and Soulstones, mapping the actual invoking host UID rather than assuming a
number. The Phylactery instead preserves the Postgres image user and uses `:U,Z` on its data bind.

This creates a **Double Non-Root** posture:

1. On the host, the process is a normal unprivileged user.
2. Inside the container, the process is also non-root.

Because an application unit's UID matches the invoking host user, it can interact with its assigned
user-owned volumes without unsafe permission broadening. Data-plane separation is still achieved
through exact mounts and modes, not by pretending the shared numerical identity is an authorization
boundary.

#### Layer 4: The Mount-Defined Boundary (The "Wall")

The boundary between the Vessel and the Tomb is Mount-Defined, not Identity-Defined.

- **The Vessel:** High-trust plane. Its generated mounts are the Codex read-only; the configured
  stasis directory and Lab read-write; Core and Extensions read-only; and, in `host-reactor` mode,
  the Reactor inbox read-write plus its host-owned terminal journal read-only. It receives no
  whole-Crypt mount. Agents live here: graph state, LLM calls, routing, validation, memory access, and
  promotion policy remain Vessel-side. Writable Codex mutation remains a host/Magus action or an
  explicitly authorized ritual, not arbitrary agent labor.
- **The Tomb:** Low-trust execution hand. Granted no Codex mount at all under the No-Codex Law ([ADR 13](13-layout.md)): every job-safe fact it needs travels in the job payload as a task-safe, secret-forbidden runtime envelope ([ADR 11](11-backend.md)). It receives RW access only to disposable, task-scoped workspaces and artifacts.
- **Soulstones:** Model/runtime data plane. They receive only explicitly configured model/runtime
  volumes and unit-scoped secrets. Global, rune, and adapter-contributed mounts are all rejected if
  either endpoint overlaps the Codex, Crypt, stasis, trigger/Reactor, or user-systemd control roots;
  existing host symlink aliases are resolved before this comparison, and a safe alias is rendered
  as the canonical checked target rather than retained in the generated unit.

Native code modification is protected by Git Branching, not by different UIDs. Unsafe execution may manipulate workspaces, but it must not rewrite the trusted running body of the control plane.

When a host volume is bound to a container path, it throws a "blanket" over the internal permissions. The host's UID, GID, and Mode are the only laws that matter on that mount point. The internal `777` of the Bootstrap Grease Trap is effectively erased and replaced by the host's strictness.

#### Layer 5: The Shield (SELinux)

Where supported, mounts use SELinux relabeling via `:Z`.

This adds a kernel-enforced MAC layer on top of UID-based posture. SELinux does not replace proper trust zoning, but it hardens file access boundaries and helps prevent accidental or malicious access across mislabeled paths.

#### Layer 6: The Host Reactor Boundary

The caged default does not mount the user Systemd bus into the Vessel. Instead, the Vessel can write
only typed `TransitionIntent` files into an owner-only Reactor inbox. `lychd-reactor.path` watches
new inbox files and crash-surviving journal processing records, waking the host-side
`lychd reactor consume` oneshot. It claims a pending entry out of the Vessel-writable
directory before parsing, then validates it through a no-follow descriptor: file type, bounded size,
owner, mode, schema/set invariants, filename/transition identity, configuration digest, configured
switch-policy plan, expected user-systemd state, and host-owned Animator-to-unit mappings all pass
before an effect.

The host moves each claimed intent into a journal before execution and retains processing,
completed, declined, or rejected records. Existing journal IDs suppress duplicate execution.
Configuration/policy/stale-state preconditions become a typed no-effect decline; uncertain effect
failures remain rejected. The journal is
read-only in the trusted Vessel; terminal filenames close the admission/cancellation fence but do
not carry writable host commands. This protects the local file handoff; it is not a signature or
remote-authentication protocol. Malformed or oversized input is discarded and reduced to a compact
rejection marker rather than retained as an attacker-sized journal payload. After consumer death,
recovery resumes only when observed user-unit state equals an exact ordered action prefix;
non-prefix states are rejected without mutation. See **[Privilege (10)](10-privilege.md)** for the
exact implemented boundary and remaining failed-compensation/general-repair limit.

#### Layer 7: Secret Scope & Secret Classes

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

#### Layer 8: The Two-Plane Trust Boundary

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

#### Layer 9: Planned Worker Process Sandboxing (`nono`)

When the Tomb plane is implemented, the architecture must enforce strict per-process sandboxing
using **`nono`**. It is not an optional layer for enabling untrusted execution in the shared-Pod
architecture; its absence means that execution surface must remain disabled.

- The `lychd-tomb` container itself may use controlled Pod connectivity and holds only the narrow SAQ/Postgres execution credential.
- The `lychd-tomb` Python worker loop (the execution hand) is **Semi-Trusted**.
- When the Tomb loop picks up a code-execution job from SAQ, it uses `uv` to fast-install any required dependencies into a **job-scoped temporary workspace** before handing it to `nono`. The Tomb loop may use approved network access for this step; `nono` does not.
- The Tomb loop then wraps the actual untrusted execution in `nono`.
- `nono` uses Landlock to restrict the process to the job workspace directory and completely **drops its network interface**.
- If the untrusted script needs to fetch a URL, it cannot do so directly. It must ask the Semi-Trusted Tomb loop (the proxy) to fetch the URL on its behalf.

This ensures **zero exfiltration** of mounted user files and prevents the untrusted script from reading the DB credentials stored in the container's environment variables.

The Tomb does not run agent logic, graph runners, or LLM provider calls. It is a brainless executor. The full doctrine is defined in **[Workers (14)](14-workers.md)**.

### 2. Egress Posture (Network Is Authority)

Outbound network is treated as authority, not convenience.

#### Core Rules

- The `lychd.pod` shares a network namespace, meaning containers inherently possess the Pod's internet route.
- Every generated Pod `PublishPort` binds the host side to `127.0.0.1`; no core or contributed
  service is exposed on all host interfaces by default.
- The Vessel and Semi-Trusted Tomb loop utilize this native egress.
- **Untrusted execution (inside `nono`) defaults to ZERO egress.**
- Wide-open outbound access from a sandbox is forbidden. Any sandbox requiring external data must route requests through the Tomb loop acting as its proxy.

The loopback bind limits which hosts can connect; it does not identify which same-host process or
user made a request. Until real caller authentication exists, the LychD web/API surface remains
local single-user infrastructure. Remote ingress requires an authenticated and authorized front
door with TLS and an explicit trusted-proxy policy.

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
- Tomb/worker units may receive a narrow queue-only SAQ/Postgres credential for execution-plane job claiming, acknowledgement, and retry bookkeeping
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

#### Return Quarantine

The Untrusted Returns warning names the risk; **Return Quarantine** is the doctrine that answers it. Tomb returns are data, never instruction.

- Stdout and artifacts returning from the Tomb enter agent context only as **fenced, provenance-tagged blocks** within the volatile layers (5–6) of the Stable Floor (**[Context (21)](21-context.md)**).
- They are never concatenated into instruction layers.
- Any structured interpretation of a return passes through a typed boundary (**[Agents (20)](20-agents.md)**).

The same law governs every input crossing into cognition from a lower-trust plane: assimilated external material (**[Assimilation (35)](35-assimilation.md)**) and A2A peer returns (**[A2A (26)](26-a2a.md)**) are quarantined identically. A return is admitted as fenced data; it is never spoken as command.

### 5. Authority Matrix

| Dimension          | Vessel (Trusted Control Plane)                                 | The Tomb (Untrusted Execution Plane)                                   |
| :-------------------| :---------------------------------------------------------------| :-----------------------------------------------------------------------|
| **Identity**       | Invoking unprivileged host UID through Pod-level `keep-id`; `User=%U` for the Vessel. | Same Pod user-namespace geometry where manifested; identity alone is not the plane boundary. |
| **Secrets**        | Accesses control-plane database credentials and high-value API keys. | Narrow queue-only SAQ/Postgres execution credential when required; no provider keys, signing keys, Codex secrets, or control-plane credentials. |
| **Mounts**         | Codex RO; stasis and Lab RW; Core/Extensions RO; Reactor inbox RW plus terminal journal RO only in Host Reactor mode; no whole Crypt. | No Codex mount (the No-Codex Law); the runtime envelope travels in the job payload. RW access only to disposable workspaces and artifacts. |
| **Network**        | Shared Pod network and egress; host publication is loopback-only and not caller authentication. | Tomb loop may use shared Pod connectivity for queueing and approved proxy work; sandboxed `nono` subprocesses have zero network. |
| **Queue Control**  | Owns enqueue policy, durable scheduling, and control-plane retries. | Claims, acks, and retries execution-plane SAQ jobs only.               |
| **Agent / LLM**    | All cognitive labor runs here exclusively.                     | Forbidden. The Tomb is a brainless executor.                           |
| **Context Egress** | Applies privatization and anonymization gates.                 | Cannot bypass egress policy.                                           |
| **Host Authority** | May emit typed intents into the inbox; the host validates and journals them before acting. | Cannot mount the inbox, emit host intents, or mutate infrastructure.   |
| **Arbitrary Code** | Forbidden.                                                     | Allowed only in constrained execution contexts (`nono` sandbox).       |
| **Mutation**       | Forbidden. Protected by Git Branching and RO Mounts.           | Allowed only in disposable/task-scoped areas.                          |

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

The implemented foundation (shared Pod, narrow mounts, loopback-only host publication, and service
credentials) is deliberately pragmatic. It does not include remote caller authentication or the
Tomb/`nono` untrusted-execution plane.

However, the architecture explicitly acknowledges possible future sovereign security milestones for later versions (V2+):

- **Total Network Separation:** Abandoning the shared `lychd.pod` in favor of strict, isolated Podman networks (`lychd-core`, `lychd-tomb`).
- **Authenticated External Ingress:** Place remote access behind an explicitly trusted TLS front
  door with real caller authentication, authorization, and proxy-header policy.
- **Dedicated Worker API Plane:** Tomb workers communicating with the Vessel purely over a restricted internal API, removing direct database access from the worker completely.
- **Sovereign Egress Proxy:** Moving the egress routing into a dedicated Vessel service, potentially dropping the reliance on `nono`'s internal Rust proxy in favor of a pure-Python boundary.

These are valid long-term directions. The Tomb/`nono` boundary is, however, an immediate
prerequisite for exposing any untrusted code-execution feature; the current Vessel container must
not be substituted for it.

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
