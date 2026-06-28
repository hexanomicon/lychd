---
title: 10. Privilege
icon: material/transfer-up
---

# :material-transfer-up: 10. Privilege: The Signal Mechanism

!!! abstract "Context and Problem Statement"
    The LychD security model traps the Agent in an unprivileged, rootless container to contain the blast radius of any potential compromise. However, the machine requires the capability to perform infrastructure actions that exist outside the container's scope, such as restarting services, modifying Systemd units, and executing the state transitions required for Coven swaps. Granting the container direct access to host sockets or the shell violates the principle of least privilege and provides a path for escape. A physical gap exists between the unprivileged reasoning engine and the privileged host substrate that must be bridged without compromising the system's seal.

## Requirements

- **Deterministic Security Boundary:** The gap between the container and the host must be bridged without granting direct shell access, socket control, or root privileges to the application process.
- **Unidirectional Intent Dispatch:** The communication must be strictly one-way; the container may signal a request for a state change, but it must never define *how* that request is executed.
- **Structured Intent Protocol:** Requests from the container must be structured data (JSON) adhering to a strict schema, rather than raw command strings.
- **Hardcoded Host Registry:** The host-side executor must only possess the capability to run a pre-authorized "Allow-list" of functions.
- **Event-Driven Efficiency:** The mechanism must be event-driven (utilizing kernel APIs like `inotify`) to ensure zero CPU overhead while idle.
- **Persistence of Intent:** The signal must be file-based to ensure it can be audited and survives momentary process failures.

## Considered Options

!!! failure "Option 1: Privileged Sidecar"
    Deploying a secondary container with the Podman socket mounted to execute tasks.

    -   **Cons:** **Architectural Security Hole.** If the sidecar is compromised, the entire host is compromised. It adds significant bloat to the Pod for a simple signaling task.

!!! failure "Option 2: Watchdog Script (Polling)"
    A host-side script that loops periodically checking for a trigger file.

    -   **Cons:** **Resource Waste.** Consumes CPU cycles even when dormant. Polling introduces latency into state transitions, which is unacceptable for real-time sensory swaps.

!!! success "Option 3: Deterministic Intent Reactor"
    Utilizing host-native Systemd Path units to monitor a shared volume and trigger a strictly typed reactor process.

    -   **Pros:**
        -   **Zero-Trust Boundary:** Even a full compromise of the container does not allow for arbitrary command execution on the host.
        -   **Kernel Efficiency:** Uses `inotify` to wake the reactor only when a signal is written.
        -   **Auditability:** Every privileged action is recorded as a structured JSON artifact on the filesystem.

## Decision Outcome

**Deterministic Intent Dispatch** is adopted as the "Nervous System" of the Lich. This mechanism allows the unprivileged mind to trigger physical transitions in the body through a secure, air-gapped handshake.

### 1. The Intent Registry (The Allow-list)

The Host Reactor—a minimal process running on the host machine—does not possess the capability to execute arbitrary logic. It is a strictly typed state machine containing a hardcoded mapping of **Intent Tokens** to **Host Functions**:

- `INTENT_SWAP_COVEN`: Triggers the sequence of `systemctl --user` stop/start commands required for VRAM management.
- `INTENT_RESTART_VESSEL`: Issues a restart signal to the primary application service.
- `INTENT_RELOAD_QUADLETS`: Triggers a `daemon-reload` to apply newly forged infrastructure definitions.

### 2. The Structured Handshake

When a system component (such as the Orchestrator) requires a privileged transition, it does not issue a command. It writes a **Structured Intent File** (`.intent.json`) to a shared, read-write volume in the Crypt.

```json
{
  "intent_id": "INTENT_SWAP_COVEN",
  "nonce": "a1b2c3d4...",
  "payload": {
      "target_coven": "vision.coven"
  }
}
```

### 3. The Reactor Ritual (The Path Unit)

The host monitors this specific directory utilizing a **Systemd .path unit**.

1. **Detection:** The kernel detects a file write and triggers the associated **Reactor Service**.
2. **Validation:** The Reactor reads the `intent_id` and validates it against the internal Registry.
3. **Parsing:** The `payload` is parsed using a strict schema associated with that specific intent. (e.g., The `target_coven` must match a known Systemd target).
4. **Execution:** The Reactor executes the hardcoded host function associated with the token.
5. **Purge:** The intent file is deleted, signaling the completion of the ritual.

### 4. Extension-Defined Escalations

To maintain the Federation's flexibility, Extensions may propose new Intent IDs. However, these intents are not active until their corresponding host-side logic is synthesized into the Host Reactor during the assembly phase. This ensures the Magus remains the ultimate arbiter of which privileged actions the machine is permitted to perform.

### 5. The Nonce Ledger

The `nonce` carried in every `.intent.json` protects the channel only if its consumption is remembered. The Reactor maintains a **persistent ledger of consumed nonces**, scoped per Intent Token. A nonce is single-use: an intent whose nonce already appears in the ledger, or whose file mtime exceeds the intent TTL, is a replay or a stale signal. The Reactor purges it without execution and journals it as rejected. The ledger survives Reactor restarts, so a replayed intent cannot be re-executed by bouncing the reactor. Without the ledger the nonce protects nothing.

### 6. The Observation Doctrine

The channel remains strictly unidirectional; **no reply file exists**. The Reactor reports only to the journal—the systemd journal, structured—recording each intent as executed or rejected. The Vessel confirms an intent solely by observing its effects: unit states and the Orchestrator's Awakening poll. It MAY read the journal read-only, but the return path is never a file the Reactor writes back into the shared volume, which would itself become an escalation surface. A rejected intent (bad token, bad nonce, malformed payload, stale mtime) is purged and journaled; the Vessel distinguishes "reactor refused" from "reactor slow" by reading that journal, never by a reply.

### 7. The Signal Boundary Invariant

The intent drop directory is itself a privilege boundary, and this ADR is its sole owner:

!!! important "The Signal Boundary Invariant"
    The intent directory is mounted **writable into the Vessel alone**. It SHALL never be mounted into the Tomb or any Soulstone.

**[Layout (13)](13-layout.md)** (the Tomb must not mount host trigger/signaling paths) and **[Evolution (18)](18-evolution.md)** (the Tomb cannot trigger host intents) restate this boundary from their own vantage. They cross-reference this invariant rather than defining it; the canonical statement lives here.

### 8. Manifestation Modes

The actuation channel is not always the Reactor. While the Vessel runs **uncaged** on the host—the development manifestation of the pre-alpha—the Orchestrator addresses the user Systemd bus directly (`systemctl --user` stop/start), because no cage yet separates it from the host substrate.

Upon **caging**, every `systemctl` verb in the Orchestrator's swap ritual is replaced by its corresponding intent: `INTENT_SWAP_COVEN`, `INTENT_RELOAD_QUADLETS`, `INTENT_RESTART_VESSEL`. The Orchestrator's strategy code SHALL treat the actuation channel as pluggable, so the swap logic is identical in both modes and only the final actuator differs. This ADR is the canonical home of the transition condition; the **[Orchestrator (23)](23-orchestrator.md)** may note it from its own vantage.

### Consequences

!!! success "Positive"
    - **Total Containment:** The application is trapped in its container, yet it can effectively command its own hardware through a secure gateway.

    - **Physical Synchronicity:** This mechanism provides the physical link required for the Orchestrator to manifest different operational states.

    - **Forensic Trail:** Every privileged action requested by the machine leaves a permanent, structured record in the system logs.

!!! failure "Negative"
    - **Operational Friction:** Adding a new type of host interaction requires updating both the internal reasoning logic and the Host Reactor code. This "Double Implementation" is an intentional security tax.

    - **Path Unit Dependency:** The mechanism relies on host-level Systemd features, further cementing the Linux system requirement.
