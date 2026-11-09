---
title: Install Tumbleweed
icon: material/disc
---

# Prepare a reviewed Tumbleweed installation

The [AutoYaST generator](https://github.com/hexanomicon/lychd/tree/main/deployments/autoyast)
renders a private installation profile for an x86_64 Server or KDE workstation. It does not
install an OS, inspect hardware, write USB media, or authorize erasing a disk. The profile
requests confirmation of the YaST proposal; a negative test with the matching installation
medium must establish that it stops before disk changes. This is candidate tooling: generated XML and
unit tests do not establish a successful installation or recovery on AlphaVPS or a laptop.

The supported contract is a **fresh, whole-disk replacement**: one explicitly named disk,
GPT, a firmware-specific boot partition, and one Btrfs capacity pool with `/home` and `/var`
subvolumes outside root snapshots. BIOS uses GRUB2 with a BIOS boot partition. UEFI uses
classic GRUB2 EFI with a 1 GiB ESP and Secure Boot support requested. This deliberate choice
avoids depending on changing boot-loader defaults; it must still be checked against the
selected installation medium. There is no encryption, dual boot, preserved partition,
hibernation, automatic disk selection, custom script, or unattended mode in this generator.
For an encrypted laptop use the interactive installer's supported encryption workflow instead.

Networking supports one explicitly named wired interface: DHCP or static IPv4 with a gateway
inside its subnet. Static IPv6, off-subnet gateways, VLANs, bridges and Wi-Fi credentials are
refused rather than guessed. Use an interactive network configuration for those cases.
NetworkManager is selected for both roles. The installer network needed to retrieve a profile
or packages must already work; target network configuration cannot bootstrap that retrieval.

Both profiles require an ordinary administrator's public Ed25519 key and a private SHA-512
crypt password hash. The password permits console recovery and authenticates sudo as that
administrator. Root is locked, root SSH and SSH password authentication are disabled, and
the complete sudo policy grants only root and that named administrator. The future `lychd`
runtime account is not an administrator. No application secrets or private keys belong in
these inputs. The profile itself contains a password hash and is private material.

## Generate outside the checkout

Use Python 3.12 or later; the generator uses only the standard library. Copy the server or
workstation JSON example into a private directory outside every checkout and edit its explicit
disk, firmware, hostname, interface and administrator. Placeholder keys are intentionally
rejected. Keep the administrator password hash in a separate mode-0600 regular file in that
directory, using a trusted local password-hashing tool with interactive password input.
Never put the password or hash in a shell command argument or public example.

From the checkout, with existing absolute private paths:

```bash
python3 deployments/autoyast/generate.py \
  --config "$LYCHD_INSTALL_WORK/host.json" \
  --password-hash-file "$LYCHD_INSTALL_WORK/admin.hash" \
  --output "$LYCHD_INSTALL_WORK/autoinst.xml"
```

The output is created exclusively with mode 0600; an existing file or symbolic link refuses.
Input and output paths must be absolute, outside checkout/worktree ancestors identified by a
`.git` marker. This check does not identify repositories whose marker has been removed.
The generator reads no inventory or credential other than those two explicit input files.
JSON unknown fields, duplicate keys, unsupported values and malformed keys/hashes refuse.
It never opens the named target disk. Inspect the XML privately; do not paste it into a ticket.

## Choose and authenticate the medium

Use the official [Tumbleweed installation images](https://get.opensuse.org/tumbleweed/),
not a Live image. Record the exact filename, snapshot, checksum and publisher-signature
verification. Retain that medium with the profile identity and installed package manifest.
The Offline image can install its included package set without a network; the Network image
requires working installer networking and downloads packages from a moving repository.

For AlphaVPS, establish the service's actual firmware, disk, NIC, address/prefix, gateway,
DNS and working console/rescue route first. The provider documents
[ISO and boot controls](https://alphavps.com/clients/knowledgebase/4/Getting-started-with-KVM-VPS.html).
Its [high-performance service](https://alphavps.com/high-performance-vps/) advertises custom
ISO upload; these pages do not prove the controls or DHCP behavior of a particular service.
Prefer the authenticated official ISO. If using netboot.xyz, its
[openSUSE menu](https://raw.githubusercontent.com/netbootxyz/netboot.xyz/master/roles/netbootxyz/templates/menu/opensuse.ipxe.j2)
loads the upstream kernel/initrd and forwards installer parameters; record and inspect the
actual retrieval route. Printed MD5 values are not publisher authentication.

## USB and offline profile delivery

A DVD hybrid image written to a USB stick retains its ISO9660 image layout. Do not assume it
is a writable filesystem into which `autoinst.xml` can be copied. This workflow does not
repartition, rewrite or append data to an existing installer stick. Use a **separate already
writable profile medium**, or a deliberately prepared custom medium validated separately.
Copy the private profile to that medium and select it with an explicit boot parameter such as
`autoyast=usb:///autoinst.xml`; remove other profile media to avoid ambiguous discovery.
FAT/exFAT media do not enforce Unix mode 0600: retain physical custody and remove private
profiles after installation. Follow the official
[profile retrieval documentation](https://doc.opensuse.org/projects/autoyast/).

An offline bundle consists of the authenticated Offline installer, the private rendered
profile, its input/receipt kept privately, and every additional package/input needed for the
chosen profile. The generator adds no remote scripts, add-on repositories or online update.
Verify the selected patterns and packages are present on that exact medium, then test with
networking disconnected. A complete OS install does not include later Ansible dependencies,
application images or models. Those are a separate transfer/provisioning stage.

## Review, install and hand over

Before confirming YaST's proposal, compare the physical/provider disk identity and capacity,
actual boot firmware, complete destructive partition list, package selection, SELinux
Enforcing, network and administrator access with the private worksheet. A syntactically
valid device path is not evidence it identifies the right disk. There is no runtime guard
claim: AutoYaST pre-script failures can be warnings, so this generator contains no pre-scripts
and never sets `confirm=false`.

After installation, detach installer media and restore disk-first boot. Verify a normal cold
boot, administrator SSH key and console login, `sudo -v` using that administrator's password,
rejection of root/password SSH, effective firewall and `getenforce`. Check `findmnt -T /`,
`findmnt -T /home`, `findmnt -T /var`, `lsblk -f`, and Snapper's root configuration. KDE also
needs physical laptop checks for graphics, input, Wi-Fi and suspend/resume. This layout does
not configure hibernation or protect data at rest with encryption.

Then follow the [Ansible controller and host preparation](index.md#prepare-the-controller-and-private-inventory)
and [application deployment](index.md#automate-one-host-end-to-end). Use the new administrator
as the inventory connection user and `--ask-become-pass`; the runtime account remains separate.

## Qualification and upstream contracts

Run the generator tests with `python3 -m unittest discover -s deployments/autoyast/tests -v`.
Validate each rendered profile with the **matching installer's** AutoYaST schema and
`yast2 autoyast check-profile` in a disposable environment. The
[upstream validation guide](https://documentation.suse.com/sles/15-SP4/html/SLES-all/cha-autoyast-create-control-file.html)
warns that YaST versions affect results. No full schema validation or VM/hardware installation
receipt is supplied by the generator tests.

Qualify BIOS Server, UEFI Server and UEFI KDE separately. Test wrong/absent disks, firmware
mismatch, missing NIC, unavailable packages and interrupted installation, and verify no disk
changes occur before confirmation. Retain sanitized logs and observe two boots plus remote
and console recovery. Recheck on every newly admitted installer snapshot.

The [product control source](https://github.com/yast/skelcd-control-openSUSE/blob/master/control/control.xml)
owns the current Server/KDE pattern proposals. The
[AutoYaST configuration reference](https://doc.opensuse.org/documentation/leap/autoyast/html/book-autoyast/cha-configuration-installation-options.html)
documents partitioning, users, files, networking and services; its Leap version is not a
Tumbleweed acceptance receipt. Tumbleweed separately documents
[NetworkManager for servers](https://news.opensuse.org/2022/01/28/bash-systemd-libvirt-update-in-tw/),
[SELinux Enforcing](https://news.opensuse.org/2025/02/13/tw-plans-to-adopt-selinux-as-default/)
and [changing boot defaults](https://news.opensuse.org/2025/11/13/tw-grub2-bls/).
