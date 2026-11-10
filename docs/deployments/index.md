---
title: Deployments
icon: material/server
---

# Deployment experiments

These guides prepare an operator-controlled Linux host and separate that work from LychD's
application initialization, generated service body, and recovery. They do not establish a
working application merely because a playbook finishes.

- [Tumbleweed Server](tumbleweed/index.md): headless AlphaVPS, one exact source and OCI image,
  guarded CLI activation and read-only acceptance; qualify one pilot before adding hosts.
- [KDE workstation](tumbleweed/workstation.md): a separate personal-user baseline with configurable Zsh or Fish,
  Starship, CLI tools, packaged fonts and optional Firefox Dark Reader policy. NVIDIA is excluded.
- [Personal and administrator shells](tumbleweed/shells.md): shared Zsh default or Fish,
  with native history and completion; runtime identity remains separate.
- [AutoYaST installation](tumbleweed/install.md): explicit server/workstation inputs and a
  reviewed whole-disk installation proposal, using official media or a network installer.
- [Private access](tumbleweed/access.md): optional infrastructure-owned WireGuard and a restricted
  forwarding service for one trusted owner of one VPS; native Tether remains Designed.

| Stage | Owner | Verification |
| --- | --- | --- |
| OS installation | AutoYaST and the selected installer | Matching-media schema and disposable-VM installation, then actual console/boot/storage/network checks. |
| Server | Ansible host floor and pinned source/image | Check, apply, second no-change apply, direct runtime SSH and `app-verify.yml`. |
| Workstation | Ansible package baseline and selected existing user | Check, apply, second no-change apply, workstation verification and hardware/browser checks. |
| Private road | Host administrator and systemd | Exact listeners, wrong-peer/key/destination refusal, tunnel loss and live revocation. |
| LychD body | Installed LychD CLI and generated rootless units | Initialization/binding receipts, application readback and separately admitted recovery. |

The workstation does not need a runtime account to receive personal tools. To run LychD there,
perform the separate host/application rite; never give its runtime UID the personal user's sudo
or browser state. Provisioning installs missing packages against selected repositories. It does
not run `zypper dup`, reboot, install GPU drivers, or promise immutable reconstruction from
moving Tumbleweed repositories. DVD installation and fully offline provisioning are distinct:
the latter also needs the selected RPM/Python/image artifacts retained locally.

[State of Work](../state-of-the-work.md#systemd-podman-embodiment) owns the delivery boundary.
The [candidate verification record](https://github.com/hexanomicon/lychd/blob/main/deployments/VALIDATION.md)
separates passed source checks, unavailable Core gates and required target observations.
Keep private inventories, keys, host settings, backup repositories and observations outside
the checkout.
