---
title: 5. Podman Quadlets
icon: material/cube-outline
---

# :material-cube-outline: 5. Podman Quadlets for Service Orchestration

!!! abstract "Context and Problem Statement"
    The LychD architecture is a "Sepulcher"—a pod of interconnected, containerized services including The Vessel (application), The Phylactery (database), The Oculus (tracing), and various Soulstones (LLM runtimes). These components require a robust orchestration system to manage their lifecycle on a single host.

    The system must be declarative, reliable, secure, and integrate natively with the host environment. It must enforce exclusive access to hardware resources (GPUs) and provide unified logging without introducing the overhead of a distributed orchestrator.

## Decision Drivers

- **Resource Exclusivity:** The system must strictly enforce singleton behavior via `Conflicts=` logic. Two Soulstones cannot attempt to claim the same GPU VRAM simultaneously; one must yield (die) for the other to live.
- **Native Host Integration:** Service management (`start`, `stop`, `status`) and log inspection must be handled by standard system tools (`systemctl`, `journalctl`), avoiding proprietary CLIs.
- **Daemonless Architecture:** The solution should utilize the existing OS supervisor (PID 1) rather than running a secondary, monolithic daemon (like Docker).
- **Security by Default:** The method must be optimized for Rootless Containers to minimize the blast radius of a compromised LLM runtime.

## Considered Options

!!! failure "Option 1: Docker Compose"
    The industry standard for multi-container definitions.

    - **Pros:** Familiar YAML syntax and massive adoption.
    - **Cons:** **Insufficient Control.** It lacks native support for `Conflicts=` logic, making it impossible to guarantee that "Soulstone A" is terminated before "Soulstone B" starts. This risks VRAM contention and OOM crashes. It also fragments the management experience (`docker logs` vs `journalctl`).

!!! failure "Option 2: Kubernetes (K3s/Minikube)"
    The standard for distributed orchestration.

    - **Pros:** Extremely powerful and resilient.
    - **Cons:** **Architecture Mismatch.** Kubernetes abstracts the hardware away, whereas LychD requires direct, high-performance access to host hardware (GPU/NPU). Running a K8s control plane for a single-node daemon is an unacceptable violation of the Simplicity principle.

!!! success "Option 3: Podman Quadlets"
    A Podman feature that compiles `.container` definitions directly into native `systemd` service units.

    - **Pros:** **Systemd Native.** It inherits the full power of the init system, including `Conflicts=` (for resource safety), `OnFailure=` (for resilience), and socket activation.
    - **Generated Runes:** It aligns perfectly with the architecture: The Application generates ephemeral config files, and the OS executes them.
    - **Rootless:** Designed from the ground up to run without root privileges.

## Decision Outcome

**Podman Quadlets** are adopted as the exclusive orchestration mechanism. This choice elevates `systemd` from a mere init system to the primary, low-level supervisor of the Sepulcher.

### The Mechanism of Binding

The workflow is strictly defined as **Generation**, not manual authoring:

1. **Source:** The User defines intent in abstract `TOML` (The Codex).
2. **Compilation:** The `lychd bind` command transmutes the Codex into ephemeral `.container` files (Runes) in `~/.config/containers/systemd/`.
3. **Execution:** Systemd generates the service units and enforces the state.

### Hardware Access via CDI

To strictly maintain the rootless security boundary while ensuring high-performance access to GPU hardware, the **Container Device Interface (CDI)** specification is utilized in lieu of legacy runtime hooks.

- **Abstraction:** Generated Quadlets must not rely on hardcoded device paths (e.g., `/dev/nvidia0`). Instead, they must request resources via the stable CDI syntax (e.g., `Device=nvidia.com/gpu=all` or specific UUIDs).
- **Stability:** This approach decouples the container orchestration from the host's driver updates, provided the host maintains an up-to-date CDI specification at `/etc/cdi/nvidia.yaml`.


### Consequences

!!! success "Positive"
    - **Hardware Safety:** The usage of `Conflicts=` ensures that GPU resources are never accidentally oversubscribed by competing models.
    - **Unified Interface:** Users manage LychD services exactly like they manage Apache or SSH: via `systemctl`.
    - **Security:** Services run as user processes, drastically reducing the attack surface compared to a root-owned Docker daemon.

!!! failure "Negative"
    - **Linux Lock-in:** This decision irrevocably binds LychD to the Linux ecosystem and the `systemd` init system. This is a deliberate trade-off; portability to Windows/MacOS is explicitly rejected in favor of deep system integration.
