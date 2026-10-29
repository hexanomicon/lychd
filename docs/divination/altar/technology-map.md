---
title: Owned Technology Map
icon: material/graph-outline
---

# :material-graph-outline: Owned Technology Map

Start with a device or application you own and a question about maintaining it. A useful map
should let you trace its components, dependencies, data, interfaces, current state, available
source, and ways to change or recover it. The same inquiry applies to a PC, phone, router,
appliance, or application. Prefer more FOSS, better documentation, and greater replaceability,
while recording where closed components limit that understanding and control.

This candidate undertaking, developed **2026-10-09**, uses [Atlas](atlas.md) to keep its brief,
questions, evidence, and judgments together. The direction is independent of Companion or the
phone's operating system. The current Project surface can hold the undertaking; a dedicated
component graph, automatic inventory, and agent access to its dossiers would need their own
implementation. [State of Work](../../state-of-the-work.md#atlas-projects) retains Atlas's delivery
boundary.

## What the map should retain

Start from one actual device or system and identify its parts. A GPU's silicon, firmware, kernel
driver, userspace driver, compute runtime, libraries, and calling application are distinct
components. Record relationships such as contains, runs on, initializes, depends on, exposes an
interface to, and can replace. Each relation needs its own meaning and evidence.

The following is proposed dossier content, not a new LychD record family:

| Account | Material to retain |
| --- | --- |
| Identity and state | Exact model, hardware revision, installed versions, configuration, relevant limits, and dated observations. |
| Knowledge | Source revisions, manuals, schematics, programming references, protocol/format schemas, and the claims each supports. |
| Dependencies | Hardware, firmware, drivers, runtimes, libraries, services, required accounts, and compatibility constraints. |
| Control | Actual read/write operations, privilege and signing boundaries, modification/install paths, and independent local operation. |
| Recovery | Backups, export/restore, replacement options, failure detection, reconciliation, and tested recovery procedures. |
| Uncertainty | Missing source, undocumented behavior, unavailable observations, inferred interfaces, disputed claims, and tests that could resolve them. |

Aim to account for every identified component within the declared scope. Unknown internals remain
part of that account. A list of nodes does not prove that hidden components are absent or that
their behavior is fully understood.

## Knowledge and control have different coverage

Ask separately what you can inspect, what is documented, what you have observed, what you can
modify or install, whether it works independently of a vendor, and how you could recover it.
These dimensions often diverge. Public source may be readable while installation is restricted.
An opaque firmware image may have a documented interface and a verified update path. You may
understand a hardware design without having a practical way to manufacture it. Keeping each fact
separate makes the map useful for an actual decision.

FOSS increases the material available for inspection, testing, maintenance, and replacement. An
open layer should improve its own entry in the map without making its dependencies open by
association. Procurement compares these dimensions alongside the required capability: prefer
greater openness and fewer opaque dependencies, and retain the limits of the selected equipment.
Manufacturing every component is not a prerequisite for this undertaking.

Reverse engineering can target a missing format, protocol, or replaceable implementation.
Recovered behavior remains tied to tested versions and cases. An inferred schema is a hypothesis
until verified; passing one case does not establish all hidden behavior or a working replacement.

## CPU firmware as a worked distinction

AGESA supplies AMD platform/silicon initialization in the host firmware stack.
[AMD openSIL](https://www.amd.com/en/blogs/2023/empowering-the-industry-with-open-system-firmware-.html)
opens a particular host initialization layer; AMD also describes substantial initialization by
embedded microcontrollers before the x86 cores begin. Its presence therefore does not establish
source coverage of every underlying firmware component, nor compatibility with an arbitrary
motherboard.

CPU microcode patches have a separate loading path. The open
[Linux microcode loader](https://docs.kernel.org/arch/x86/microcode.html) consumes vendor patch
binaries and applies matching updates to CPU cores. Record the patch identity, loading path,
applicability, and observed version separately from AGESA and the surrounding BIOS.

Public interface schemas can still explain closed parts. The
[coreboot PSP integration guide](https://doc.coreboot.org/soc/amd/psp_integration.html) documents
firmware table structures and component types while leaving further firmware details to other,
sometimes NDA-bound publications. Such a guide can support a precise structural map without
claiming access to the implementation inside each image.

## NVIDIA software as a worked distinction

[NVIDIA's open GPU kernel modules](https://github.com/NVIDIA/open-gpu-kernel-modules) publish a
kernel-driver layer. The repository requires corresponding NVIDIA userspace components and GSP
firmware. Its [firmware integration documentation](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/nouveau/extract-firmware-nouveau.txt)
describes GSP-RM binaries obtained from the proprietary driver package. Kernel source, userspace
implementation, and GPU firmware therefore need separate entries.

CUDA is a collection of interfaces, tools, runtimes, and libraries with different source and
license coverage. Its [SDK terms](https://docs.nvidia.com/cuda/eula/index.html) cover proprietary
components and recognize separately licensed components; [CCCL](https://github.com/NVIDIA/cccl)
publishes source for Thrust, CUB, and libcu++. Inspect the actual components a workload uses rather
than giving the entire ecosystem one openness label.

[Mesa NVK](https://docs.mesa3d.org/drivers/nvk.html) implements Vulkan for NVIDIA GPUs. That is a
different interface from CUDA's runtime and libraries. A workload could use an alternative
compute backend only where its implementation, device support, and behavior are established;
choosing an open driver alone supplies no application-portability evidence.

## Make an agent's questions answerable

An agent examining a component should be able to answer a connected set of questions: what is it,
what depends on it, which exact documentation applies, what has been observed, and which operations
are available? The remaining gaps determine how far a proposed task can responsibly proceed.
Keep every claim's versions, evidence, and conditions attached, and identify whether it is
source-supported, experimentally established, inferred, disputed, or unknown.

Schemas describe shape; tests and observations establish particular behavior. An action contract
also needs effects, current authority, limits, outcomes, and recovery. Reading a map grants no
device access or authority to change firmware. Linking a dossier in Atlas does not automatically
put it in model Context; [Context](../../adr/21-context.md) owns that admission.

The first useful case is one system with a finite scope: identify its layers, trace one dependency
from application to device, retain one opaque component, and answer one maintenance question from
exact references. Change a version and verify that affected claims need review. A later agent
integration should refuse to treat a missing reference as knowledge or an unverified operation as
available control.

## Keep each owner in place

Atlas keeps the undertaking and its judgments. [Homestead](../../compositions/homestead/index.md)
may supply asset identity, custody, and maintenance facts while their owners retain them. Actual
personal inventories, configuration, credentials, and device dossiers live outside the repository
checkout; this guide retains only the reusable example.

[Containers](../../adr/08-containers.md#supported-host-policy) governs LychD's FOSS host support.
A device's presence in a knowledge map does not make it a supported LychD host.
[Packaging](../../adr/17-packaging.md) owns source/build evidence, and
[Assimilation](../../adr/35-assimilation.md) owns the separate study and promotion of foreign craft.
The undertaking creates no new Composition, device authority, or automatic execution path.

[Atlas](atlas.md) · [Concerns before a Project](atlas.md#concerns-before-a-project)
