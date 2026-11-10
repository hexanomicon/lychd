---
title: 10. Privilege
icon: material/transfer-up
---

# :material-transfer-up: 10. Privilege

!!! abstract "Context"
    The Vessel does not receive a shell, Podman socket, user-systemd bus, or general root authority.
    The managed Vessel crosses the Host Reactor boundary for privileged effects. The typed direct
    systemd adapter remains a host-side mechanism exercised by explicit OCI tests, not a
    host-native Vessel deployment. Both accept the same closed transition word; trusted
    construction selects the effect owner without granting the container host control authority.

## Decision: authority before effect

Effectful initialization refuses effective UID 0; root may inspect a zero-effect dry run but does
not acquire initialization authority. Host mutation belongs to the invoking user, its user manager,
and rootless Podman/Quadlet. Layout owns which paths may exist or be retired.

Host tools are never trusted from spelling alone. Discovery accepts only an executable regular
file that is UID-0-owned or lies on a kernel-reported read-only filesystem. Neither the file nor
any ancestor may be group/other-writable or writable by the caller; the resolved absolute path,
device, and inode remain in the authority token. The systemd user-generator search follows
directory priority: the first matching entry wins, and an unsafe, empty, non-executable, or
`/dev/null`-linked entry masks every lower-priority copy.

Binding sites are real non-symlink, invoking-user-owned safe directories. All real
initialization, binding, deletion, direct-systemd actuation, and Host Reactor consumption share one
non-blocking lifecycle lock under `/tmp`. It is opened without following symlinks and must be a
regular caller-owned `0600` file. Dry runs do not acquire or create it; contention is a no-effect
refusal.

Foundation, desired bytes, source and secret generation, tool/site identities, and live
configuration are revalidated under that lock immediately before mutation. A state mismatch is a no-effect
refusal.

`TransitionIntent` is frozen, `extra="forbid"` data: a 32-hex correlation ID, forward or exact
compensation operation, configuration digest, canonical Animator and capability, ordered
evict/launch sets, and exact expected active world. It carries no command, unit name, path,
environment, or arbitrary payload. A host consumer or extension escalation needs an equally closed
typed class, trusted producer and consumer, configuration owner, recovery states, and boundary
tests; extension import grants no host authority.

## The physical transaction

Physical truth comes from observed state. For an admissible transition, the actuator first
validates the word and policy, preflights and attests the loaded Scribe-owned topology, rejects
relevant pending jobs, and compares the exact observed pre-world. It records intent before
actuating generated Animator targets, then obtains terminal readback and attests the result.
Client exit status cannot supply that proof: a successful receipt requires the observed desired
state, making the effect accountable.

The direct `systemd` actuator uses only the injected, attested absolute `systemctl` under the
lifecycle lock. It submits only generated target identities and observes both target reservations
and services. Cancellation and partial failure obtain one bounded inverse transaction. The prior
world reopens admission only when exact readback proves it.

The caged `host-reactor` default gives the Vessel a write-only owner-mode inbox and a read-only
host journal. It publishes one bounded typed JSON intent; the host claims it before parsing through
a no-follow descriptor, independently rechecks schema, ownership, topology, policy, digest, and
world, then acts. The journal distinguishes no-effect decline, completed desired state, proved
restoration, malformed rejection, processing uncertainty, and containment. Claimed work and
containment keep admission closed; terminal filenames never form a writable reply command. This
local file boundary is not remote authentication.

Claim first moves producer bytes into `.acquiring.json`, which never authorizes an effect or
recovery. The host captures a bounded no-follow read into a new private `0600` inode and writes
a separate host-owned, versioned custody companion binding its exact content digest. Both are
durable before `.processing.json` can authorize actuation. A producer-held descriptor or hard
link therefore cannot rewrite admitted or completed evidence. Processing and compensation
reads require matching custody; a marker inside producer-supplied JSON is not custody proof.
Interrupted acquisition without processing is rejected without effect. Missing, legacy, or
mismatched processing custody remains fenced for operator reconciliation; old completed files
without proof cannot authorize compensation and are never automatically certified or replayed.

| Receipt | Meaning | Admission result |
| --- | --- | --- |
| `.acquiring.json` | producer bytes claimed, host custody not yet established | remain closed; reject interrupted acquisition without effect unless durable processing already exists |
| `.processing.json` | claimed work without a terminal physical observation | remain closed |
| `.completed.json` | exact desired world observed | proceed to separate readiness |
| `.declined.json` / `.rejected.json` | no-effect precondition refusal / invalid delivery | fail closed; only a decline may reopen the initial barrier |
| `.restored.json` | exact prior world observed after failure or cancellation | reopen with a typed restored result |
| `.contained.json` | neither desired nor prior world proved | latch containment |

## Tether host operations (Designed) {#tether-host-operations-designed}

The first [native Tether profile](39-vpn.md#native-peer-operations) uses closed host-owned
`prepare`, `enroll`, `inspect` and `revoke` requests. Each mutation binds installation and operation identity,
expected peer generation, static Rune/binding digest and exact public intent. Inputs carry no
command, arbitrary path, unit name or capability. The native host service resolves its fixed
units from Scribe ownership, uses trusted adapters, and revalidates under the existing lifecycle
lock. It does not expose a Reactor channel to either transport container or dispatch extension
callbacks with host authority.

Before ordinary bind, `prepare` uses fixed native WireGuard and Ed25519 SSH host-key factories
and the trusted secret adapter to create only the two exact referenced server secrets. No
extension supplies a factory callback or command. The preparation record binds installation,
operation, purpose, secret source name, observed immutable Podman secret identity and public-key
fingerprint. Existing names require matching creation authority; a crash between creation and
receipt is an uncertain outcome to preserve and reconcile, not permission to adopt or overwrite.
Secrets never appear in argv, public intent, logs or receipts. Bind validates both typed references
and their prepared identities before writing units.

Cold image replacement uses a distinct typed preparation request naming the exact prior
preparation-selection digest and proposed envelope, together with installation, operation and
expected peer generation. The native owner rechecks under the lifecycle lock that only the image
changed, both existing secret identities still attest, and the old road is physically cold.
An existing peer additionally requires its exact immutable revocation and matching active latch.
Before any peer, an existing binding requires ordinary owned-unit cold observations; a never-bound
installation requires positive absence of the fixed units, jobs and Podman objects, with no
activation/runtime history. A missing unit or failed observation alone is not cold proof.

The owner writes an immutable transition bundle with the exact request digest, parent selection,
new compiled plan and preparation attestation, then durably replaces one typed current-preparation
selector. That replacement is the commit point. A bundle written before it is inert; retry must
revalidate the same parent selection, secrets, generation and fresh cold observations before
commit. After commit, the same operation reconciles its completion without selecting the parent
again; a superseded operation cannot select itself anew. Request identity conflicts refuse.
Initial secret creation and its existing request serialization remain unchanged. Image replacement
never invokes a key factory, alters units, clears the latch or advances the peer generation.

Closure, retained runtime checks and cold re-enrollment resolve each old latch, activation attempt
and incarnation against its own retained envelope and binding. A selected replacement cannot
relabel old evidence. Crossing to the new envelope requires the exact retained image-only
transition authority as well as existing closure and startup proofs. After normal full bind,
explicit enrollment advances the peer generation and clears only the active latch through the
existing cold sequence. Any interruption before that enrollment leaves no authority to restart
the revoked generation. This transition grants no exception to active-Vessel or foreign-revision
refusals and makes no claim to detect whole-state rollback.

After initial binding, peer operations preserve the complete compiled unit fileset and its
generation. Enrollment may change only the Tether public peer record, separate forwarding public
authorization and operation evidence; it requires the prepared server secrets. Initial unit
installation or envelope changes use normal bind and its existing refusals. Reconciliation cannot treat a newer CLI as authority over a foreign
or older live body. Pending operations retain confirmed stages; a retry reconciles their exact
identity before another effect. Unknown activation stays fenced rather than reporting success.

Revocation durably publishes the fixed active closure latch before any stop effect; it then
retains separate immutable generation-specific revocation evidence. If the CLI dies between
those writes, the latch already closes the road and reconciliation completes the record. A fixed
Scribe-owned systemd user `.path` guard uses `PathExists=` on that same pathname for every
generation and activates a fixed native host handler. The latch is not a consumed queue item.
The handler has `Conflicts=` and `After=` on the exact owned Pod, WireGuard and SSH services;
it has no `Requires=` or `BindsTo=` edge pulling those conflicting services in. systemd orders
the conflicting transport stops before starting the handler, so physical closure does not wait
for the handler to obtain the lifecycle lock.

The handler accepts no payload-selected command or unit. After those stops it acquires the
existing lifecycle lock, revalidates ownership and reads the exact settled world. The native
Tether-specific stop adapter shares trusted bounded process execution and lock infrastructure,
but does not reuse Animator compensation: after a durable fence it can only stop, observe or
record uncertainty. No error, cancellation or retry may restart the previous transport. Neither
container receives host sockets, Podman, systemd authority or the private operation journal.

The handler is `Type=oneshot` with `RemainAfterExit=yes`, finite `TimeoutStartSec` and
`TimeoutStopSec`, and `StartLimitIntervalSec=infinity` with `StartLimitBurst=3`. It reaches
active/exited only after full closure is observed and recorded. That retained state prevents a
persistent latch from starting an endless successful handler loop. On failure or timeout,
`PathExists=` rechecks the still-present latch; exhausted starts fail the path unit. The Pod and
both containers have `BindsTo=` and `After=` edges to that path, so watcher inactivity/failure also
requests their stop. A failed watcher or failed stop is not a successful closure receipt.

Startup performs a fixed typed preflight of current intent, prepared secret identities,
generation evidence, absent closure latch and active path guard before UDP activation. A marker
condition alone cannot validate generation. Re-enrollment first proves the old Pod, services and
sessions quiescent; while the latch remains present it stops the path, preserves the old immutable
revocation evidence, stops/resets the active/exited or failed handler and resets path failure.
It then durably publishes the new generation and intent, durably clears only the active latch,
starts/attests the path guard, and finally starts the transport through its normal readiness
order. Every stage is journaled under the lifecycle lock. Interruption leaves transport cold or
fenced for reconciliation; restarting a watcher cannot erase old revocation evidence.

A change-only watch is insufficient: after handler failure or coalesced notifications there may
be no second file change. The persistent latch, bounded handler and cumulative three-start limit
close that gap. Qualification must exercise lock contention, notification coalescing, handler
death/timeout, exhausted starts, watcher failure, successful-handler latching, cold re-enrollment,
restart races and crash immediately after latch durability. A live receipt records the measured
closure bound; a frozen host/user manager cannot be certified closed by unit declarations.

The CLI also requests and observes exact stop settlement. Successful revocation requires the
exact peer generation, fence digest/durability, Scribe generation, guard/handler outcome, terminal
container/service identities, terminated forwarding process trees and absence of the owned Pod
namespace. The same correlated record retains confirmed stages for incomplete outcomes. An
inactive configuring process alone is insufficient, and a watcher marked failed is not itself
proof that dependent teardown completed.

Ordinary retirement must include these exact Scribe-owned units in its existing inventory and
attest their closure before removing their intent/fence evidence. Revocation is not deletion or
secret destruction. Existing deletion rules preserve Podman secrets without immutable creation
authority. Preparation receipts do not by themselves extend generic deletion to consume that
authority; this first profile preserves its secrets on revoke and never deletes them by name.

## Materialization and retirement

Scribe's ownership receipt bounds every Quadlet/plain user-unit file that binding may write.
Under the lifecycle lock, binding stages and validates the full generation, rechecks
foundation/sites/secrets/generations, replaces exactly the declared set, and reloads systemd.
Failure restores the previous set. Foreign units, ambiguous ownership, unsafe names, changed
identities, and unknown files cause refusal rather than deletion.

Deletion is a separately fingerprinted, revalidated sequence—quiesce, runtime, storage, unbind,
secrets, filesystem, package, verify. It stops only exact owned units and recursively retires only
init-attested dedicated roots through pinned no-follow descriptors. An exact, init-created
Phylactery Btrfs subvolume may need root; LychD proves mount/device/filesystem/subvolume identity,
prints a narrow trusted root handoff, writes a protected continuation receipt, and never invokes
`sudo` itself. Any ambiguous mount, replacement, interruption, or root outcome preserves evidence
and blocks continuation.

## Containment rule and delivery boundary

Compensation can reopen the prior world only after exact proof of its restoration. When the
physical result remains indeterminate, containment latches and recovery is required; another retry
cannot supply that recovery. Signal authority stays equally narrow: the trusted Vessel alone
writes the Reactor inbox, and the host consumer alone claims it. Tombs, Soulstones, and untrusted
extensions receive neither inbox nor journal.

The mediated protocol and its isolated receipts are available within their stated boundary, but no
repository test proves an operator's Quadlet/Podman/GPU host. [State of Work](../state-of-the-work.md#host-reactor-protocol)
and [its systemd/Podman embodiment record](../state-of-the-work.md#systemd-podman-embodiment) own
that delivery distinction.

## Consequences

Host mutation remains attributable and recoverable, but an uncertain physical outcome deliberately
costs availability until an operator establishes a safe recovery boundary.
