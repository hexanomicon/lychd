---
title: 10. Privilege
icon: material/transfer-up
---

# :material-transfer-up: 10. Privilege

!!! abstract "Context"
    The Vessel does not receive a shell, Podman socket, user-systemd bus, or general root authority.
    Privileged effects cross one of two non-interchangeable boundaries: the default caged Host
    Reactor, or explicit uncaged direct systemd development mode. Both accept the same closed
    transition word; only trusted bootstrap selects the effect owner.

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
configuration are revalidated under that lock immediately before mutation. Drift is a no-effect
refusal.

`TransitionIntent` is frozen, `extra="forbid"` data: a 32-hex correlation ID, forward or exact
compensation operation, configuration digest, canonical Animator and capability, ordered
evict/launch sets, and exact expected active world. It carries no command, unit name, path,
environment, or arbitrary payload. A host consumer or extension escalation needs an equally closed
typed class, trusted producer and consumer, configuration owner, recovery states, and boundary
tests; extension import grants no host authority.

## The physical transaction

An admissible transition proceeds in order: validate the word and policy, preflight and attest the
loaded Scribe-owned topology, reject relevant pending jobs, compare the exact observed pre-world,
record intent, actuate the generated Animator targets, obtain terminal readback, and attest the
result. Client exit status is not physical truth. Attestation is what makes an effect accountable;
there is no successful receipt without observed desired state.

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

| Receipt | Meaning | Admission result |
| --- | --- | --- |
| `.processing.json` | claimed work without a terminal physical observation | remain closed |
| `.completed.json` | exact desired world observed | proceed to separate readiness |
| `.declined.json` / `.rejected.json` | no-effect precondition refusal / invalid delivery | fail closed; only a decline may reopen the initial barrier |
| `.restored.json` | exact prior world observed after failure or cancellation | reopen with a typed restored result |
| `.contained.json` | neither desired nor prior world proved | latch containment |

## Manifestation and retirement

Binding writes only Scribe receipt-owned Quadlet/plain user-unit files under the lifecycle lock.
It stages and validates a full generation, rechecks foundation/sites/secrets/generations, replaces
the exact declared set, reloads systemd, and restores the previous set on failure. Foreign units,
ambiguous ownership, unsafe names, changed identities, and unknown files refuse rather than delete.

Deletion is a separately fingerprinted, revalidated sequence—quiesce, runtime, storage, unbind,
secrets, filesystem, package, verify. It stops only exact owned units and recursively retires only
init-attested dedicated roots through pinned no-follow descriptors. An exact, init-created
Phylactery Btrfs subvolume may need root; LychD proves mount/device/filesystem/subvolume identity,
prints a narrow trusted root handoff, writes a protected continuation receipt, and never invokes
`sudo` itself. Any ambiguous mount, replacement, interruption, or root outcome preserves evidence
and blocks continuation.

## Containment rule and delivery boundary

Compensation restores only an exactly proved prior world. An indeterminate physical result latches
containment and requires recovery; retry is not recovery. Signal authority follows the same line:
only the trusted Vessel may write the Reactor inbox, only the host consumer claims it, and Tombs,
Soulstones, and untrusted extensions receive neither inbox nor journal.

The mediated protocol and its isolated receipts are available within their stated boundary, but no
repository test proves an operator's Quadlet/Podman/GPU host. [State of Work](../state-of-the-work.md#host-reactor-protocol)
and [its systemd/Podman embodiment record](../state-of-the-work.md#systemd-podman-embodiment) own
that delivery distinction.

## Consequences

Host mutation remains attributable and recoverable, but an uncertain physical outcome deliberately
costs availability until an operator establishes a safe recovery boundary.
