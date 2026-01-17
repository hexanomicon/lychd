---
title: 5. Podman Quadlets
icon: material/cube-outline
---

# :material-cube-outline: 5. Podman Quadlets for Service Orchestration

The LychD architecture is a "Sepulcher"—a pod of interconnected, containerized services including The Vessel (application), The Phylactery (database), The Oculus (tracing), and various Soulstones (LLM runtimes). We require an orchestration system to manage the lifecycle of these services on a single host.

This system must be declarative, reliable, secure, and integrate natively with the host environment. It needs to handle complex dependencies, ensure services are automatically restarted on failure, and provide unified logging and management without introducing unnecessary complexity or external daemons.

## Decision Drivers

- **Advanced Lifecycle Management:** The system must support robust restart policies (`Restart=always`, `on-failure`) and sophisticated dependency definitions, including service conflicts (`Conflicts=`) to ensure singleton behavior.
- **Native Host Integration:** Service management (`start`, `stop`, `status`) and log inspection must be handled by standard, battle-tested system tools, not a proprietary CLI.
- **Security by Default:** The chosen method must be designed for and default to rootless containers, adhering to the principle of least privilege.
- **Simplicity and Declarative Syntax:** Service definitions should be simple, human-readable text files that can be version-controlled.
- **Daemonless Architecture:** The solution should not rely on a monolithic, privileged daemon running on the host.

## Considered Options

1. **Docker Compose:** A popular tool for defining and running multi-container applications.
    - Pros: Widely adopted and familiar YAML syntax.
    - Cons: Critically lacks support for advanced dependency management like `Conflicts=`, making it impossible to enforce certain service states. Its restart policies are less nuanced than systemd's. It operates as a separate ecosystem with its own CLI (`docker-compose`), leading to fragmented management and logging (`docker logs` vs. `journalctl`).
2. **Kubernetes (K3s/Minikube):** The industry standard for large-scale container orchestration, available in smaller distributions for local use.
    - Pros: Incredibly powerful, declarative, and resilient.
    - Cons: Drastic overkill for LychD's single-host deployment model. It introduces an enormous layer of complexity (CNI networking, storage classes, controllers) that is entirely unnecessary and violates the principle of simplicity.
3. **Podman Quadlets:** A modern Podman feature that translates `.container` files into native `systemd` service units.
    - Pros: Directly leverages the full power and maturity of `systemd`, inheriting its advanced dependency management (`Wants=`, `After=`, `Conflicts=`), robust restart policies, and socket activation features. Integrates seamlessly with the host's `systemctl` for management and `journalctl` for unified logging. It is inherently daemonless and designed for rootless containers.
    - Cons: Tightly couples the application to the `systemd` init system.

## Decision Outcome

**Chosen Option:** "Podman Quadlets".

We will use Podman Quadlets to define and manage all services within the LychD Sepulcher. This decision elevates `systemd` from a mere init system to our primary, low-level service orchestrator.

This choice directly aligns with our lore: the `lychd bind` command transmutes abstract `TOML` configurations into `.container` files (the "Runes"), which `systemd` then materializes into active services (the "Binding").

We explicitly reject Docker Compose because its feature set is insufficient for our reliability and integration needs. The inability to define service conflicts and the reliance on a separate, non-native toolchain are unacceptable compromises. Kubernetes is rejected due to its excessive complexity for our use case.

## Consequences

- **Positive:**
    - We gain access to the entire, battle-hardened `systemd` feature set for free, including robust lifecycle management, dependency control, and unified logging via `journalctl`.
    - The security posture is significantly improved by a rootless-by-default design.
    - The user experience is simplified to a single, consistent management interface (`systemctl`) for all system and application services.
- **Negative:**
    - This decision irrevocably binds LychD to the Linux ecosystem, specifically distributions utilizing `systemd`. This is an accepted and deliberate trade-off. LychD is an opinionated tool for serious practitioners on Linux systems; support for other operating systems is a non-goal.
