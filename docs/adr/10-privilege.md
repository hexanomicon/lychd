---
title: 10. Privilege
icon: material/transfer-up
---

# :material-transfer-up: 10. Privilege: The Signal Mechanism

!!! abstract "Context and Problem Statement"
    The LychD security model traps the Agent in an unprivileged, rootless container to contain the blast radius of any potential compromise. However, the machine requires the capability to perform infrastructure actions that exist outside the container's scope, such as starting and stopping generated user services for Coven swaps. Granting the container direct access to host sockets or the shell violates the principle of least privilege and provides a path for escape. A physical gap exists between the unprivileged reasoning engine and the host-authoritative user-service substrate that must be bridged without compromising the system's seal.

## Requirements

- **Deterministic Security Boundary:** The gap between the container and the host must be bridged without granting direct shell access, socket control, or root privileges to the application process.
- **Narrow Domain Port:** The Orchestrator must depend on one typed actuation operation rather than subprocess, filesystem, or Systemd APIs.
- **Unidirectional Intent Dispatch:** A caged Vessel may publish a state-change request, but it must
  never define *how* the host executes it and must receive no host-writable command channel. A
  read-only terminal receipt may close the admission fence without becoming execution authority.
- **Structured Intent Protocol:** A transition must be frozen, extra-forbidden structured data containing only canonical Animator identities and state digests—never a command, unit name, path, environment, or arbitrary payload.
- **Bootstrap-Owned Authority:** The Codex selects the trusted actuator implementation when the
  process is assembled. Graphs, requests, Reference Compositions, and extensions cannot select an
  effect backend per call.
- **Atomic No-Replace Publication:** File delivery must use a restricted temporary file, `fsync`, and an atomic no-overwrite publication step so the host never observes a partial JSON intent or silently replaces an existing transition identity.
- **Stale-World Defense:** An actuator must reject a transition whose assumed active set no longer matches observed host state over registry-owned units before it mutates the host.
- **Bounded Recovery:** Direct in-process actuation must compensate completed effects on failure.
  The host consumer must claim before execution and may resume a crash-surviving record only when
  observed Systemd state equals an exact prefix of its ordered action plan.
- **Signal Isolation:** The Host Reactor inbox is a privilege boundary writable only by the trusted
  Vessel. The sibling journal is mounted into that Vessel read-only for terminal receipts and must
  never be writable there or mounted into a Soulstone, Tomb, or untrusted extension process.

## Considered Options

!!! failure "Option 1: Privileged Sidecar"
    Deploying a secondary container with the Podman socket mounted to execute tasks.

    -   **Cons:** **Architectural Security Hole.** If the sidecar is compromised, the entire host is compromised. It adds significant bloat to the Pod for a simple signaling task.

!!! failure "Option 2: Watchdog Script (Polling)"
    A host-side script that loops periodically checking for a trigger file.

    -   **Cons:** **Resource Waste.** Consumes CPU cycles even when dormant. Polling introduces latency into state transitions, which is unacceptable for real-time sensory swaps.

!!! success "Option 3: Typed Runtime Actuator"
    Injecting one narrow `RuntimeActuator` whose trusted implementations either apply a validated
    transition through the user's Systemd bus or atomically publish it to a Host Reactor inbox and
    await a read-only terminal receipt.

    -   **Pros:**
        -   **Injection Resistance:** The domain object cannot carry a shell command, host path, environment, or arbitrary unit name.
        -   **Manifestation Choice:** Direct Systemd development and caged mediated delivery share
            one orchestration path and completion barrier.
        -   **Atomic Handoff:** A complete structured request survives process scheduling boundaries without a partial-file state.

## Decision Outcome

**Typed Runtime Actuation** is adopted as the "Nervous System" of the Lich. The stable domain
contract is `RuntimeActuator.apply(TransitionIntent)`. The Orchestrator plans, closes admission,
drains leases, and submits one complete transition; the actuator alone owns physical mutation or
the mediated publish/receipt handshake.

### 1. The Transition Word

`TransitionIntent` is a frozen Pydantic model with `extra="forbid"`. It contains exactly:

- `transition_id`: a 32-character hexadecimal delivery/correlation identity.
- `operation`: `forward` for a planned hard swap or `compensation` for its exact typed inverse.
- `rollback_of`: absent for forward work; the completed forward transition id for compensation.
- `config_generation`: a `sha256:` digest of the capability projection used to make the plan.
- `target_animator`: the canonical requested Animator identity.
- `evict_animators`: the complete ordered stop set.
- `launch_animators`: the complete ordered start set.
- `expected_active_animators`: the observed physically started local-runtime set against which
  stale-world checks are made. A running dynamic router in `ACTIVATABLE` is included even when no
  model capability is loaded yet, matching host user-unit truth.

Animator identities match a bounded identifier grammar. There is no intent token plus open-ended
`payload`; adding an unknown field is a validation error. A transition cannot smuggle `../../bin/sh`,
`systemctl`, a unit name, or a host path through this model.

The model also rejects duplicate identities, overlap between evict and launch sets, a target absent
from the launch set, an evictee absent from the expected-active set, or a launch target already
claimed active. These are schema invariants before either actuator sees the intent.

```json
{
  "transition_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "operation": "forward",
  "rollback_of": null,
  "config_generation": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "target_animator": "vision",
  "evict_animators": ["chat"],
  "launch_animators": ["vision"],
  "expected_active_animators": ["chat"]
}
```

`transition_id` is locally minted correlation. The host journal uses it to suppress a replay once a
matching processing, completed, declined, or rejected record exists, but it is not a cryptographic
identity, nonce, or remote authorization credential. The consumer validates `config_generation`
against its own trusted capability projection before execution.

A forward intent cannot carry `rollback_of` and must include its target in `launch_animators`. A
compensation must name a different completed forward id and include the original target in its
eviction set. The manager constructs compensation with `build_compensation_intent`: expected
post-forward state becomes the inverse's expected state, and the original launch/evict sets swap.
In Host Reactor mode the consumer admits it only when it is the exact inverse of the referenced
completed forward record; the word `compensation` alone grants no authority.

### 2. The Two Trusted Actuators

The implementation is selected once from `[orchestration.switching]`:

```toml
[orchestration.switching]
actuator = "host-reactor" # caged default; use "systemd" explicitly when uncaged
```

#### Direct Systemd (`systemd`, explicit uncaged mode)

`SystemdRuntimeActuator` is the uncaged/local effect owner:

1. At the host composition boundary it derives the observed active Animator set from
   `systemctl --user is-active` over registry-owned local units and rejects a stale
   `expected_active_animators` set before the first effect. It does not try to probe Pod-internal
   model endpoints from the host. This no-effect outcome is a typed `RuntimePreconditionError`, so
   the manager reopens its forward barrier without latching mutation containment.
2. It resolves canonical Soulstone identities to registry-owned generated service names. Callers
   cannot supply a unit name.
3. It stops the complete evict set and starts the complete launch set. Host-state mode does not try
   to refresh Pod-internal model endpoints; final capability probing and `WARM` convergence remain
   the Orchestrator/registry path after physical actuation.
4. If an operation fails, it best-effort reverses completed work: newly started Animators are
   stopped in reverse order and stopped Animators are restarted in reverse order. Every
   compensation error is retained in the raised failure.

This rollback is process-local compensation. It is not transactional Systemd, does not survive a
Vessel crash mid-transition, and has no durable journal from which another process can resume.
Moreover, `RuntimeActuator.apply()` currently returns success or raises; it does not attest that a
raising call's best-effort rollback restored the original world. The manager therefore leaves queue
and lease admission closed after any hard-actuator error, even when rollback probably succeeded.
Operational recovery is preferred to an unsafe reopen.

#### Host Reactor Delivery and Terminal Receipt (`host-reactor`)

`HostReactorRuntimeActuator` is the caged delivery adapter. It requires a pre-provisioned inbox and
its read-only sibling journal, validates both as current-UID `0700` directories, and publishes
`<transition_id>.json` by:

1. creating a sibling temporary file with `O_EXCL` and mode `0600`;
2. writing canonical JSON, flushing it, and `fsync`ing the file;
3. atomically linking it to the final name without overwriting an existing transition ID, then
   removing the temporary name; and
4. `fsync`ing the containing directory.

Published intents are `0600`; publication failure removes the temporary file. The adapter never
executes Systemd. After publication it watches only transition-correlated terminal filenames in the
read-only journal. A completed marker returns control to the manager; a declined marker raises the
typed, no-effect `RuntimePreconditionError`; a rejected marker raises an ordinary actuator failure,
which provides no safe no-effect attestation and therefore stays fail-closed. Ordinary capability
probing still decides whether the launched service becomes `WARM`.

Configuration requires an absolute, normalized path whose final segment is `inbox`; the
host-owned, Vessel-read-only journal is its derived sibling. Systemd-unsafe `%`, backslash, and
non-printable characters are rejected. `lychd init` provisions these configured paths, including
valid custom layouts.

### 3. Read-Only Terminal Receipt and Late-Intent Fence

There is no writable reply file or generic host-to-Vessel payload. The Host Reactor renames the
claimed intent to a transition-correlated `.completed.json`, `.declined.json`, or `.rejected.json`
record in the host-owned journal, which the Vessel can see only through a read-only mount. The delivery actuator
uses the record's name as a terminal receipt; it does not parse host instructions from the journal.
Physical completion and readiness remain distinct: the receipt proves the ordered Systemd action
set reached a terminal host outcome, while ordinary capability probes and bounded `await_warm`
prove the target is actually usable.

`declined` is reserved for configuration-generation, host policy/authorization (including exact
compensation shape), and stale user-unit-state preconditions that fail before any new physical
effect. The Vessel maps it to
`RuntimePreconditionError`, and an initial forward transition safely reopens admission without
global containment. `rejected` covers malformed delivery and effect-path failures; it does not
attest that no effect occurred, so the manager contains rather than treating it as a harmless
refusal.

`reactor_ack_timeout_s` bounds **claim**, not an already claimed physical transition. If the host
does not move the file out of the inbox by that deadline, the actuator atomically removes the still
pending file, `fsync`s the inbox, and raises before manager admission reopens. If the host has
claimed it, the manager barrier stays closed until a terminal journal record exists—even past the
claim deadline. Caller cancellation follows the same law: retract an unclaimed file, otherwise
shield the terminal wait before propagating cancellation. Vessel startup also refuses to publish
the run substrate while pending or processing Reactor work remains. These fences remove the old
delayed post-timeout application window without inventing a TTL inside `TransitionIntent`.

### 4. The Host Consumer

`lychd bind` inscribes two host user units when `host-reactor` is selected:

- `lychd-reactor.path` watches complete `inbox/*.json` names and crash-surviving
  `journal/*.processing.json` records.
- `lychd-reactor.service` is a host-side oneshot that runs `lychd reactor consume` with a
  deterministic host environment. `Restart=on-failure` retries a failed invocation; once a terminal
  outcome has been journaled, the next empty invocation succeeds instead of creating a restart loop.

The consumer validates both directories as real, current-UID-owned `0700` directories. A pending
name must first match `<32-lowercase-hex>.json` and identify a regular entry. The host then moves it
out of the Vessel-writable inbox before parsing and opens the claimed path with `O_NOFOLLOW`, using
`fstat` and a bounded descriptor read. Only a regular, current-UID-owned `0600` file no larger than
64 KiB is admitted; the filename must match the typed intent's transition ID, and Pydantic rejects
extra or malformed fields.

Before any effect, the consumer verifies the capability-configuration digest and requires every
referenced identity to be a local Soulstone. For a forward operation it recomputes the configured
switch policy from the target and expected-state projection; the exact evict/launch sets must match
that host-side plan. For compensation it opens the referenced `.completed.json` through the same
bounded no-follow reader, requires a current-generation forward operation, computes its typed
inverse, and compares every effect field except the newly minted transition id. A forged inverse is
declined before effects while the original record remains. Finally, the Systemd actuator compares expected state
to host user-unit truth (or an exact legal prefix during recovery/compensation) and resolves unit
names only from host-loaded registry truth.

For a fresh intent, the consumer atomically moves the file out of the Vessel-visible inbox to
`<transition_id>.processing.json` in the host-owned journal and `fsync`s both directories before
execution. Success becomes `.completed.json`; a stale configuration/policy/active-set precondition
becomes `.declined.json`; an invalid delivery or uncertain actuation failure becomes
`.rejected.json`. A later inbox file whose transition ID already has a processing, completed,
declined, or rejected record is removed without executing the effect again. Malformed or oversized
raw input is
discarded and replaced by a compact owner-only `invalid-<id>.rejected.json` reason marker rather
than copied into the journal without a bound.

This is a durable delivery/outcome journal, not a per-effect transaction log. After a host process
dies, the path unit notices the surviving processing record and the consumer handles it first.
Recovery derives every physical state reachable after an ordered prefix of the intent's stop/start
actions. It resumes the uncompleted suffix only when current user-unit state equals one exact legal
prefix. If suffix application then fails, best-effort compensation covers the effects observed
before the crash plus those completed during recovery. An unrelated or ambiguous physical state is
rejected without guessing. Repeated process death remains recoverable from the surviving processing
record, but failed compensation, non-prefix external mutation, a missing terminal record, and
cryptographic signature/remote-authentication policy remain explicit limits; this is not
transactional Systemd.

The current authorization boundary is deliberately local: owner UID, exact modes, a non-symlink
filesystem path, typed intent validation, and host-owned configuration/registry truth. There is no
network submission surface and no request signature. Compromise of the trusted host user is outside
this mechanism's protection; exposing the inbox remotely would require a separate authenticated
protocol and is not supported by this contract.

### 5. Extension-Defined Escalations

The current `TransitionIntent` authorizes one class only: lifecycle transitions over canonical
Animator identities. Extensions cannot add arbitrary intent IDs or payload fields at runtime.

A new privileged action class requires an explicit typed schema, a trusted actuator/consumer
implementation, configuration ownership, security review, and tests on both sides of the boundary.
It must never be expressed as a generic command escape hatch. Future Forge synthesis may install
such paired trusted code, but extension import alone grants no host authority.

### 6. The Signal Boundary Invariant

The intent drop directory is itself a privilege boundary, and this ADR is its sole owner:

!!! important "The Signal Boundary Invariant"
    Among caged application units, the Host Reactor intent directory SHALL be writable only by the
    trusted Vessel; the host consumer retains the authority required to claim/remove entries. The
    inbox SHALL never be mounted into the Tomb, a Soulstone, or an untrusted extension process. The
    journal may be mounted only read-only into the trusted Vessel for terminal receipts.

The generated deployment mounts the configured Reactor inbox read-write and its sibling journal
read-only into the trusted Vessel. The broader Crypt is not mounted through that channel.
Soulstones receive only explicitly configured model/runtime volumes after host/container
protected-root validation; Codex, Crypt, trigger/Reactor, and user-systemd overlaps fail
binding. The writer and consumer additionally enforce exact owner, mode, file type, and
no-overwrite publication rules at the filesystem boundary.

**[Layout (13)](13-layout.md)** and **[Evolution (18)](18-evolution.md)** restate this boundary from
their own vantage. They cross-reference this invariant rather than defining a second authority.

### 7. Manifestation Modes

Actuation mode is explicit configuration, not an automatic guess based on whether the process seems
caged:

- `host-reactor` is the caged default. It publishes a typed file for the generated host path/service
  consumer, waits for a read-only terminal receipt, then relies on ordinary readiness observation
  for `WARM` convergence.
- `systemd` directly addresses the user Systemd bus and is an explicit trusted uncaged/development
  choice.

The Orchestrator, Dispatcher, Graph, and switch policy do not branch on the selected mode. Only the
trusted bootstrap root chooses the effect owner.

### 8. Implementation Boundary

| Capability | Foundation status |
| :--- | :--- |
| Frozen, extra-forbidden `TransitionIntent` | Implemented |
| Bootstrap-selected `systemd` / `host-reactor` actuator | Implemented |
| Direct stale-active-set rejection | Implemented for the Systemd actuator |
| Direct best-effort in-process compensation | Implemented for the Systemd actuator |
| Restricted atomic JSON publication | Implemented for the Host Reactor actuator |
| Host path/service consumer and `lychd reactor consume` | Implemented |
| Host schema/set invariants, fd-safe ownership/size checks, config generation, policy recomputation, and stale user-unit-state validation | Implemented |
| Durable processing/completed/declined/rejected records and transition-ID replay suppression | Implemented |
| Read-only terminal receipt, unclaimed-timeout retraction, cancellation fence, and startup idle fence | Implemented |
| Inbox RW + sibling journal RO in the caged Vessel; no Soulstone control mounts | Implemented |
| Crash recovery from an exact ordered physical-action prefix | Implemented |
| Typed hard-readiness inverse tied to an exact completed forward record | Implemented |
| Writable/generic reply channel | Forbidden |
| TTL and cryptographic signature / remote authentication policy | Later; no network intake exists |
| Per-effect transaction log and automatic repair of non-prefix/failed-compensation states | Later |

### Consequences

!!! success "Positive"
    - **Narrow Authority:** The Orchestrator can express only canonical Animator lifecycle intent, never generic host execution.
    - **One Runtime Physical Will:** Direct and mediated application paths share the same
      plan/drain/actuate/converge path; explicit operator break-glass actions remain outside it.
    - **Honest Completion:** Atomic publication, read-only terminal receipts, and probe-based WARM
      observation keep delivery, physical completion, and readiness as distinct truths.

!!! failure "Negative"
    - **No General Physical Transaction:** Exact-prefix crash recovery is bounded and deterministic,
      but non-prefix external mutation or failed compensation still requires operator repair.
    - **Uncertain Actuator Failure Stays Closed:** A raising actuator call has no typed proof that
      its internal best-effort rollback succeeded, so manager admission remains closed.
    - **Safe Decline Is Not Automatic Reconciliation:** The manager projects expected activity from
      capability readiness, while the host checks user-Systemd activity. A hung-but-active unit can
      therefore cause a no-effect `.declined.json` repeatedly; the operator must reconcile or stop
      that unit before retrying.
    - **Fail-Closed Claimed Wait:** Once the host claims an intent, cancellation and the claim
      deadline do not reopen admission; a permanently stuck processing record can therefore block
      the transition/startup until the consumer reaches a terminal record or an operator repairs it.
    - **Operational Friction:** Every new privileged action requires an explicit schema and trusted implementation on both sides. This "Double Implementation" is an intentional security tax.
    - **Linux Substrate:** Both direct user-systemd actuation and the implemented event-driven Host Reactor cement the Linux requirement.
