---
title: 7. Privilege Escalation
icon: material/transfer-up
---

# :material-transfer-up: 7. Systemd Path Units for Unprivileged Triggers

!!! abstract "Context and Problem Statement"
    The LychD "Vessel" container operates, by design, as an unprivileged entity. It inherently lacks the permission to directly execute host-level actions such as `podman build` or `systemctl reload`.

## Decision Drivers

- **Autopoiesis Support:** The architecture must allow the agent to trigger infrastructure actions (such as rebuilding its own image) immediately following code generation.
- **Secure Privilege Bridging:** The gap between the unprivileged container and the privileged host must be bridged without breaking the container isolation boundary or granting direct shell access.
- **Unidirectional Control:** The communication must be strictly one-way. The container may signal a request, but it must never possess the ability to define or execute arbitrary commands on the host.
- **Operational Simplicity:** The solution should utilize standard, built-in system tools rather than introducing new daemons or complex sidecar patterns.
- **Resource Efficiency:** The mechanism must be event-driven (using kernel interrupts). Polling-based solutions that consume CPU cycles while idle are unacceptable.
- **Reliability:** The trigger mechanism must be as robust as the host's initialization system.

## Considered Options

!!! failure "Option 1: Privileged Sidecar Container"
    Deploy a secondary "helper" container running with elevated privileges (e.g., with the Podman socket mounted) to execute tasks on behalf of the main container.

    - **Pros:** A common pattern in complex orchestration systems like Kubernetes.
    - **Cons:** Introduces unnecessary architectural bloat for a single-host system. It doubles the container management overhead and introduces significant complexity regarding the security of the inter-container communication channel.

!!! failure "Option 2: Custom Watcher Script"
    Develop a standalone daemon (using Python's `watchdog` or similar) to monitor a shared directory for trigger files.

    - **Pros:** Offers high flexibility in logic implementation.
    - **Cons:** Constitutes "reinventing the wheel." This approach necessitates the maintenance of custom daemonization, error handling, logging, and restart logic—tasks already solved by the init system.

!!! success "Option 3: Systemd Path Units"
    Utilize the host's native `systemd` capabilities. A `.path` unit leverages the kernel's efficient `inotify` API to monitor a specific directory. When the container writes a specific file, the `.path` unit activates a corresponding `.service` unit on the host.

    - **Pros:** aligns perfectly with all decision drivers. It is exceptionally simple, cryptographically secure (by separation of concerns), and resource-efficient.
    - **Cons:** Deepens the project's architectural dependency on `systemd`.

## Decision Outcome

**Systemd Path Units** are selected as the exclusive mechanism for triggering host-level actions from the unprivileged Vessel container.

The architecture follows a strict "Signal and React" pattern:

1. **Signal:** The agent determines an action is required (e.g., "rebuild image") and writes a structured trigger file (e.g., `rebuild.request`) to a volume shared with the host.
2. **Detection:** A pre-configured `.path` unit on the host detects the filesystem event via kernel interrupts.
3. **Execution:** The `.path` unit activates its associated `.service` unit (e.g., `lychd-rebuild.service`). This service runs with host privileges and executes the pre-defined command.

### Consequences

!!! success "Positive"
    - **Zero-Cost Idling:** Because the solution uses `inotify` rather than polling, the mechanism consumes zero CPU resources while waiting for a trigger.
    - **Hardened Security Boundary:** The security model is declarative. The container can only "pull a lever" (touch a file); it cannot define what happens when the lever is pulled. The host retains full control over the execution logic.
    - **Native Reliability:** The trigger mechanism inherits the lifecycle management, logging, and dependency resolution of `systemd`.

!!! failure "Negative"
    - **Ecosystem Coupling:** This decision further solidifies the project's coupling to the `systemd` ecosystem. Porting LychD to systems using SysVinit, OpenRC, or s6 would require a complete reimplementation of the trigger logic.
