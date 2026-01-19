---
title: 6. Rootless Security
icon: material/shield-lock-outline
---

# :material-shield-lock-outline: 6. Defense in Depth: Rootless Architecture

!!! abstract "Context and Problem Statement"
    The LychD system executes powerful AI agents. A critical security risk is an "agent jailbreak," where code execution escapes the application's intended logic.

## Decision Drivers

- **Defense in Depth:** Security must rely on multiple independent layers failing, rather than a single point of failure.
- **Least Privilege:** The application process should hold absolutely no permissions not strictly required for operation.
- **Portability:** The security model must function across different Linux distributions without manual user configuration.
- **User Autonomy:** The system should inform the user of their security posture (e.g., SELinux status) but must not refuse execution based on environment hardening.

## Considered Options

!!! failure "Option 1: Standard Root Container"
    Run the process as `root` inside the container (default Docker behavior).

    - **Pros:** Configuration is trivial; permissions issues during build or runtime are non-existent.
    - **Cons:** Violates "Defense in Depth." If the application is compromised, the attacker possesses `root` privileges within the container, allowing package installation, OS modification, and a significantly easier path to kernel exploitation.

!!! failure "Option 2: Hard Enforcement of SELinux"
    Refuse to start unless the host has SELinux in `enforcing` mode.

    - **Pros:** Guarantees a high-security baseline for all deployments.
    - **Cons:** Fundamentally limits adoption. Excludes the majority of Linux users (Debian/Ubuntu/Arch) who do not use SELinux by default or use AppArmor instead.

!!! failure "Option 3: Mandated AppArmor Profiles"
    Rely on AppArmor profiles (common on Debian/Ubuntu) to restrict container capabilities.

    - **Pros:** Native security layer for Debian-based systems; allows granular file path restrictions.
    - **Cons:** High maintenance burden. Creating and maintaining a generic AppArmor profile that works for all user configurations is complex. Unlike Podman's automatic SELinux handling, AppArmor often requires manual profile loading on the host, reducing the "plug-and-play" nature of the deployment.

!!! success "Option 4: Double-Rootless with Adaptive SELinux"
    Combine an internal non-root user, an external rootless runtime, and optional SELinux labelling.

    - **Pros:** Maximizes security on capable systems (Fedora/RHEL/CentOS) while remaining fully functional on standard systems (Ubuntu/Debian). Leverages Podman's native ability to automate SELinux context handling.
    - **Cons:** Requires explicit file permission handling in the `Containerfile` and creates complexity in volume management.

## Decision Outcome

A three-tiered **Defense in Depth** architecture is adopted.

### Layer 1: The Prisoner (Internal Non-Root)

The `Containerfile` is mandated to create a dedicated system user (e.g., `appuser`, UID 1001) and switch context via `USER 1001` before the entrypoint. **The application is prohibited from running as root inside the container.**

- **Implication:** Upon code compromise, the attacker is unable to modify system files or install software within the container image.
- **Requirement:** All necessary mount points (e.g., `/app/data`) must be created and assigned ownership to `appuser` during the container build process, as the runtime user lacks permissions to create directories at the root level.

### Layer 2: The Warden (External Rootless)

The standard "Rootless Podman" configuration is leveraged. The container engine executes as the unprivileged user on the host. In the event of a container escape, the attacker gains only the privileges of the standard user (e.g., UID `1000`) on the host, rather than `root`.

### Layer 3: The Shield (Optional SELinux)

SELinux acts as the final, optional barrier. LychD supports it transparently but does not mandate it.

- **Quadlet Generation:** All generated volume mounts utilize the `:Z` flag. This correctly labels files for SELinux on supported systems and is silently ignored on non-SELinux systems.
- **Startup Check:** During initialization, the host's SELinux status is queried. If not `enforcing`, an `INFO` log is emitted stating that this specific security layer is inactive, but execution proceeds without error.

### Consequences

!!! success "Positive"
     - **Blast Radius Containment:** A compromised agent is trapped as a powerless user inside the container. Even if the container is breached, the host system remains protected by standard user permissions.
     - **Transparent Security:** Users on SELinux-enabled systems receive maximum isolation automatically via the `:Z` flag without manual configuration.
     - **Universal Portability:** The system remains functionally identical on any Linux distribution, regardless of the underlying security module (SELinux, AppArmor, or none).

!!! failure "Negative"
     - **Build Complexity:** The `Containerfile` requires explicit `mkdir` and `chown` steps for every directory the application needs to write to. Failure to do so results in immediate "Permission Denied" crashes, increasing the friction of adding new persistence features.
