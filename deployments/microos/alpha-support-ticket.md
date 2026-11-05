# AlphaVPS C6G: request the pinned MicroOS installer

Replace the service ID and IPv4 below in a private copy outside the checkout. Do not put real
account identifiers, host configuration, configuration-media URLs, or credentials in this file.
The installation and acceptance procedure lives in [VPS host provisioning](../../docs/sepulcher/deployments.md).

**Subject: Custom openSUSE MicroOS ISO and first-boot configuration media for one C6G VPS**

Hello,

Please make the following official installer ISO available for our C6G KVM VPS in Sofia:

- Service ID: **[SELECTED PILOT SERVICE ID]**
- Main IPv4: **[SELECTED PILOT IPV4]**
- OS: **openSUSE MicroOS, snapshot 20261103, x86_64**
- Installer role: **MicroOS Container Host, without a desktop**
- ISO: https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Snapshot20261103-Media.iso
- Size: **2931818496 bytes**
- SHA-256: **91ea07d7d9463316a2f227655dfa2f0465daa2c022df0b0eeeda68e51538a0f8**

Official checksum and detached signature:

- https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Snapshot20261103-Media.iso.sha256
- https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Snapshot20261103-Media.iso.sha256.asc

We will perform the installation ourselves through noVNC. Before we erase the selected VPS disk,
please confirm:

1. Its BIOS/UEFI firmware mode, virtual disk/NIC controller models, and ability to boot this ISO.
2. Whether IPv4 and IPv6 use DHCP or require static configuration. For static networking, please
   provide the assigned addresses, prefixes/netmask, gateways, DNS servers, and any special
   on-link gateway or routing requirements.
3. How to access noVNC during installation, select CD-ROM-first boot order, unmount media, restore
   disk-first boot order, and use rescue mode.
4. Whether, after the installer finishes but **before the first boot from the installed disk**,
   we can replace the installer ISO in the **same virtual CD-ROM** with an operator-provided
   private configuration ISO labelled `combustion`, then boot from disk with that ISO attached.
   A second virtual CD-ROM is not required. Please explain the supported upload/attachment
   method, any size or retention limits, and whether that configuration ISO remains private to
   our account. It will contain public SSH keys and host settings, never private keys.

Please do not run a template reinstall or mount/reboot anything until we confirm the selected
service and installation window. Please leave our other four VPS services unchanged.

Thank you.
