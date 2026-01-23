---
title: 9. Security
icon: material/shield-lock-outline
---
# :material-shield-lock-outline: 9. Security: Defense in Depth

!!! abstract "Context and Problem Statement"
    The LychD system executes powerful AI agents capable of writing code and executing tools. This capability introduces the critical risk of "Agent Jailbreak," where code execution escapes the application's intended logic boundaries. However, strict isolation creates a **Permission Paradox**: a mechanism is required to facilitate interaction with host files ("Working with the outside world") without granting privileged access to the host system ("Keys to the prison").

## Requirements

- **Blast Radius Containment:** A compromise of the Agent process must not result in a compromise of the Host System. The damage must be mathematically limited to the container.
- **Defense in Depth:** Security must rely on multiple, independent layers failing, rather than a single point of failure.
- **Least Privilege:** The application process should hold absolutely no permissions not strictly required for operation.
- **Identity Symmetry:** The unprivileged container identity must be able to interact with host volumes owned by the User dynamically, for any user, without requiring `root` or insecure `chmod 777` workarounds.
- **Immutability:** The Agent must be physically prevented from modifying its own runtime code or installing malicious packages.

## Considered Options

!!! failure "Option 1: Standard Root Container"
    Run the process as `root` inside the container (default Docker behavior).
    -   **Pros:** Configuration is trivial.
    -   **Cons:** **Unacceptable Risk.** If the application is compromised, the attacker possesses `root` privileges within the container's namespace, significantly lowering the bar for kernel exploitation and breakout.

!!! failure "Option 2: Hard Enforcement of SELinux"
    Refuse to start unless the host has SELinux in `enforcing` mode.
    -   **Pros:** Guarantees a high-security baseline.
    -   **Cons:** **Limits Adoption.** Excludes Debian/Ubuntu/Arch users who do not use SELinux by default, violating the principle of broad Linux compatibility.

!!! success "Option 3: Rootless Architecture with User Namespaces"
    Combine an internal non-root user, an external rootless runtime, read-only mounts, and a precise User Namespace mapping to solve the Permission Paradox.

## Decision Outcome

A five-tiered **Defense in Depth** architecture is adopted. Each layer provides an independent security boundary.

### Layer 1: The Prisoner (Internal Non-Root Identity)

The `Containerfile` creates a dedicated, unprivileged system user named **`lich`** (e.g., with UID/GID 1001). This serves as a **fallback identity**. The application process *never* runs as `root` inside the image's filesystem.

### Layer 2: The Warden (External Rootless Runtime)

The standard "Rootless Podman" configuration is leveraged. The entire container engine executes as the unprivileged user on the host. This is the primary containment layer. In the event of a full container escape, the attacker gains only the limited privileges of the host user, never `root` on the host machine.

### Layer 3: Identity Symmetry (The Bridge via `UserNS=keep-id`)

This is the definitive solution to the **Permission Paradox** and the core of LychD's user identity model. It is a feature specific to Podman Quadlets.

- **The Problem:** A host user with UID 1000 owns a file at `~/Projects/my-app`. Inside the container, the process runs as the `lich` user with UID 1001. When the container mounts `~/Projects/my-app`, the `lich` user (1001) cannot write to a file owned by the host user (1000), resulting in "Permission Denied" errors.
- **The Naive (and insecure) Solution:** `chmod 777` the host directory. This is an unacceptable security practice.
- **The LychD Solution:** The generated **[Systemd Runes (08)](08-containers.md)** utilize the `UserNS=keep-id` directive.
- **The Mechanism:** This instructs Podman to create a user namespace but to **map the host user's UID/GID directly to the same UID/GID inside the container**. It effectively ignores the `lich` (1001) user defined in the `Containerfile` and instead runs the container's entrypoint process with the *exact same identity* as the user who started the `systemd` service.
- **The Result:** If the host user is `lucy` (UID 1000), the process inside the container runs as UID 1000. It can seamlessly read and write to any file `lucy` owns on the mounted host volumes. This works for any user on any Linux machine, regardless of their specific UID, without any manual configuration.

### Layer 4: The Immutable Body (Read-Only Mounts)

To prevent the Agent from modifying its own logic at runtime or persisting an infection, the application directory is sealed.

- **Mechanism:** `chmod -R a-w /app` is executed in the final build stage of the `Containerfile`. The **[Systemd Runes (08)](08-containers.md)** then mount the Core and Extension source code with the `:ro` (read-only) flag.
- **Effect:** The Agent cannot `pip install`, modify `.py` files, or tamper with its own source code. To change itself, it must follow the formal **[Creation (16)](16-creation.md)** workflow.

### Layer 5: The Shield (Optional SELinux)

On supported systems, all generated volume mounts utilize the `:Z` flag. This instructs Podman to automatically relabel the files for SELinux, adding a kernel-level mandatory access control (MAC) layer as a final, powerful defense.

### Consequences

!!! success "Positive"
    - **Dynamic Portability:** The system works for any user on any Linux machine, regardless of their specific UID, without manual configuration. This is a direct result of the `keep-id` strategy.
    - **Blast Radius Containment:** A compromised agent is trapped as a non-root user in a read-only filesystem, running inside a rootless container.
    - **Operational Fluidity:** The `keep-id` mapping solves the Host/Container permission paradox elegantly and securely.

!!! failure "Negative"
    - **Conceptual Complexity:** Understanding the interplay between the build-time image UID (`lich`) and the runtime UID provided by `keep-id` is non-trivial for contributors.
    - **Quadlet Dependency:** The system's elegant permission model relies entirely on a Podman-specific feature, cementing the Linux and Systemd requirement.
