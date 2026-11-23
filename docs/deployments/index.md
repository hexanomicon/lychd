---
title: Deployments
icon: material/server
---

# Deployment profiles

Choose the role of this computer before installing anything. To see how the same job works
on each host, read [Platform differences across Linux, macOS and Windows](platform-differences.md).

| What you want | Where to start |
| --- | --- |
| Host on Linux (primary) | [Summoning](../summoning.md) takes one installation through configuration, model selection, Altar and Bridge. |
| Run Vessel natively on Linux, macOS or Windows | [Personal native hosts](desktop.md) covers installation, a foreground session, local browser chat and PostgreSQL recovery. |
| Run Vessel in a container on a Mac or Windows PC | [Portable container deployment](container-desktop.md) covers the local Compose stack, its database and fixed CPU model or host-managed Animators. |
| Use an existing installation | Use its operator-approved [Altar access](../divination/altar/index.md). The client needs a browser and the access arrangements for that host. |

## Personal desktop operations

- [Desktop editions](desktop-packages.md) covers installation, repair, signing and removal.
- [Dedicated volume snapshots](volume-snapshots.md) covers APFS and Windows VSS storage selection, cold capture and recovery.
- [Offer a private desktop service](desktop-tether.md) covers a WireGuard peer, an exact TLS service and live revocation.

## Linux host preparation

- [Tumbleweed Server](tumbleweed/index.md): headless AlphaVPS, one exact source and OCI image,
  guarded CLI activation and read-only acceptance; qualify one pilot before adding hosts.
- [KDE workstation](tumbleweed/workstation.md): a separate personal-user baseline with configurable Zsh or Fish,
  Starship, CLI tools, packaged fonts and optional Firefox Dark Reader policy. NVIDIA is excluded.
- [Personal and administrator shells](tumbleweed/shells.md): shared Zsh default or Fish,
  with native history and completion; runtime identity remains separate.
- [AutoYaST installation](tumbleweed/install.md): explicit server/workstation inputs and a
  reviewed whole-disk installation proposal, using official media or a network installer.
- For a LychD-managed private road, select the [native Tether profile](tumbleweed/index.md#native-tether-profile-protocol-2)
  during original initialization. Its [delivery record](../state-of-the-work.md#vpn-tether)
  identifies the installed transport and browser checks still needed.
- The [legacy single-owner access profile](tumbleweed/access.md) gives the administrator separate
  custody of host WireGuard and a restricted SSH forward to one VPS.
- [Snapshot upgrade qualification](tumbleweed/qualification.md): a real disposable QEMU
  baseline-to-candidate OS transition with exact artifacts, a controlled reboot and retained evidence.

| Stage | Owner | Verification |
| --- | --- | --- |
| OS installation | AutoYaST and the selected installer | Matching-media schema and disposable-VM installation, then actual console/boot/storage/network checks. |
| Server | Ansible host floor and pinned source/image | Check, apply, second no-change apply, direct runtime SSH and `app-verify.yml`. |
| Workstation | Ansible package baseline and selected existing user | Check, apply, second no-change apply, workstation verification and hardware/browser checks. |
| Native Tether | LychD CLI, managed Pods and [native key custody](../sepulcher/aspects/tether.md#managed-path-and-peer-custody) | Protocol 2 inspection, exact attachment and generation, active-stream revocation, restart and reboot on the selected host. |
| Legacy single-owner access | Host administrator and systemd | Exact listeners, wrong-peer/key/destination refusal, tunnel loss and live revocation. |
| LychD body | Installed LychD CLI and generated rootless units | Initialization/binding receipts, application readback and separately admitted recovery. |

The workstation does not need a runtime account to receive personal tools. To run LychD there,
check the [model host requirements](../summoning.md#the-grounds) and read the
[recovery conditions](../summoning.md#close-the-rite) before starting services. Keep the
runtime UID separate from the personal user's sudo and browser state.
Provisioning installs missing packages against selected repositories. It does
not run `zypper dup`, reboot, install GPU drivers, or promise immutable reconstruction from
moving Tumbleweed repositories. DVD installation and fully offline provisioning are distinct:
the latter also needs the selected RPM/Python/image artifacts retained locally.

[State of Work](../state-of-the-work.md#systemd-podman-embodiment) owns the delivery boundary.
The [candidate verification record](https://github.com/hexanomicon/lychd/blob/main/deployments/VALIDATION.md)
separates passed source checks, unavailable Core gates and required target observations.
Keep private inventories, keys, host settings, backup repositories and observations outside
the checkout.
