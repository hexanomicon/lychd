---
title: 7. Privilege Escalation
icon: material/transfer-up
---

# :material-transfer-up: 7. Systemd Path Units for Unprivileged Triggers

!!! abstract "Context and Problem Statement"
    The LychD "Vessel" container is, by design, unprivileged. It cannot directly perform actions on the host system, such as initiating a `podman build` or reloading `systemd` services. However, a core feature of the Autopoiesis ambition is for the agent to trigger these very actions after it has generated new code.

    We require a secure and efficient mechanism to bridge this privilege gap. The unprivileged container needs a way to signal a request to the host, which can then execute the privileged command on its behalf.

## Decision Drivers

- **Security:** The communication must be unidirectional. The container can only make a request; it must never gain the ability to directly execute arbitrary commands on the host.
- **Simplicity:** The solution should leverage standard, built-in system tools. Introducing new daemons, custom watcher scripts, or complex container patterns is to be avoided.
- **Efficiency:** The mechanism must be event-driven and consume zero CPU resources while idle. Polling-based solutions are unacceptable.
- **Reliability:** The trigger mechanism should be as robust and reliable as the host's init system itself.

## Considered Options

!!! failure "Option 1: Privileged Sidecar Container"
    Deploy a second, "helper" container that runs with elevated privileges (e.g., with the Podman socket mounted).

    - **Pros:** A common pattern in complex orchestration systems like Kubernetes.
    - **Cons:** Unnecessary bloat for our single-host architecture. It doubles the number of containers to manage and introduces significant complexity around securing the inter-container communication channel.

!!! failure "Option 2: Custom Watcher Script"
    Write a standalone daemon that uses a library like `watchdog` to monitor a directory for trigger files.

    - **Pros:** Can be flexible.
    - **Cons:** Reinventing the wheel. We would be responsible for daemonizing, managing, and ensuring the reliability of this custom script, a task already perfected by `systemd`.

!!! success "Option 3: Systemd Path Units"
    Use the host's native `systemd` capabilities. A `.path` unit, which uses the kernel's efficient `inotify` API, monitors a directory. When the Vessel container writes a "trigger file", the `.path` unit activates a corresponding `.service` unit.

    - **Pros:** Perfectly matches all decision drivers. Exceptionally simple, secure, and efficient (event-driven, not polling).
    - **Cons:** Further deepens the project's dependency on `systemd`.

## Decision Outcome

We will use **Systemd Path Units** as the exclusive mechanism for triggering host-level actions from the unprivileged Vessel container.

The workflow is simple and secure:

1. The agent decides to perform an action (e.g., "rebuild image").
2. It writes a structured trigger file (e.g., `rebuild.request`) to a shared volume.
3. A pre-configured `.path` unit on the host detects the new file.
4. The `.path` unit activates its associated `.service` unit, which executes the command.

### Consequences

!!! success "Positive"
    - **Efficiency:** The solution is incredibly lightweight and avoids any additional software or process overhead.
    - **Security:** The security boundary is clean and well-defined (unidirectional trigger).
    - **Reliability:** The mechanism is as reliable as `systemd` itself, inheriting its robust lifecycle and dependency management.

!!! failure "Negative"
    - **Ecosystem Lock-in:** This decision further solidifies the project's lock-in to the `systemd` ecosystem. This is a known and accepted trade-off.
