---
title: 6. Rootless Security
icon: material/shield-lock-outline
---

# :material-shield-lock-outline: 6. Defense in Depth: Rootless Architecture

!!! abstract "Context and Problem Statement"
    The LychD system executes powerful AI agents. A critical security risk is an "agent jailbreak," where code execution escapes the application's intended logic.

    We cannot rely on a single security boundary. We require a **Defense in Depth** strategy. Even if the Agent breaks out of the application logic, it must find itself trapped in a restrictive OS environment. If it breaks out of the container, it must find itself powerless on the Host. We must achieve this layering without sacrificing portability or imposing strict OS requirements (like mandatory SELinux) on the user.

## Decision Drivers

- **Defense in Depth:** Security must rely on multiple independent layers failing, not just one.
- **Least Privilege:** The application process should hold absolutely no permissions it does not strictly need.
- **Portability:** The security model must work across different Linux distributions.
- **User Autonomy:** The system should inform the user of their security posture (SELinux status) but not refuse to run based on it.

## Considered Options

!!! failure "Option 1: Standard Root Container"
    Run the process as `root` inside the container (default Docker behavior).

    - **Pros:** Easiest to configure. No permission issues during build.
    - **Cons:** Violates "Defense in Depth." If the app is hacked, the attacker is `root` inside the container. They can install packages, modify the container OS, and have a significantly easier path to attacking the kernel.

!!! failure "Option 2: Hard Enforcement of SELinux"
    Refuse to start unless the host has SELinux in `enforcing` mode.

    - **Pros:** Guarantees a high-security baseline.
    - **Cons:** Fundamentally user-hostile. It severely limits adoption by excluding the vast majority of Linux users (Debian/Ubuntu/Arch) who do not use SELinux by default.

!!! success "Option 3: Double-Rootless with Adaptive SELinux"
    Combine an internal non-root user, an external rootless runtime, and optional SELinux labelling.

    - **Pros:** Maximizes security on capable systems while remaining fully functional on standard systems.
    - **Cons:** Requires explicit file permission handling in the `Containerfile`.

## Decision Outcome

We will implement a three-tiered **Defense in Depth** architecture.

### Layer 1: The Prisoner (Internal Non-Root)

The `Containerfile` must create a dedicated system user (e.g., `appuser`, UID 1001) and switch to it via `USER 1001` before execution.
**The application will never run as root inside the container.**

- **Implication:** If the code is compromised, the attacker cannot modify system files or install software inside the container.
- **Requirement:** All necessary mount points (e.g., `/app/data`) must be created and `chown`ed to `appuser` during the container build process, as the runtime user lacks permission to create them.

### Layer 2: The Warden (External Rootless)

We leverage the standard "Rootless Podman" configuration. The container engine runs as the unprivileged user on the host. If the attacker escapes the container, they merely become the user `1000` on the host, not `root`.

### Layer 3: The Shield (Optional SELinux)

SELinux acts as the final, optional barrier. LychD supports it transparently but does not mandate it.

- **Quadlet Generation:** All generated volume mounts will use the `:Z` flag. This correctly labels files for SELinux on supported systems and is ignored on others.
- **Startup Check:** On startup, LychD will check the host's SELinux status. If it is not `enforcing`, it will log an `INFO` message stating that this specific security layer is inactive, but it will proceed without error.

### Consequences

!!! success "Positive"
    - **Blast Radius Containment:** A compromised agent is trapped as a powerless user inside the container.
    - **Transparent Security:** Users on SELinux systems get the highest possible security automatically.
    - **Portability:** The system remains usable on any Linux distribution.

!!! failure "Negative"
    - **Build Complexity:** The `Containerfile` requires explicit `mkdir` and `chown` steps for all directories the app needs to write to, otherwise the container will crash with "Permission Denied."
