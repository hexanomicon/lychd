---
title: MicroOS VPS host
icon: material/server
---

# MicroOS on an AlphaVPS C6G

This runbook prepares **one AlphaVPS C6G in Sofia: 3 shared vCPU, 6 GB RAM,
55 GB NVMe and 6 TB transfer** ([provider specification](https://alphavps.com/clients/store/cheap-cloud-vps)).
It uses the headless **openSUSE MicroOS Container Host**,
an ordinary runtime account, SELinux, and rootless Podman/Quadlet. Ansible is not required.
The plan is for an explicitly selected empty pilot VM; reinstalling it destroys its disk.
No VPS has been installed or qualified by the repository checks for this guide.

!!! warning "First-boot automation is not yet qualified"
    The pinned DVD can be requested for interactive installation. The proposed automatic
    bootstrap below is candidate tooling, not a working DVD installation route. No observed
    target proves that this installer includes Combustion in its initrd and leaves the machine
    uninitialized for the first-boot bundle. **Do not erase a VPS in reliance on that automation.**
    First qualify the exact media, initrd, trigger and bundle in a disposable VM, and confirm
    AlphaVPS's private configuration-media attachment. Manual OS installation is a separate
    procedure; it does not create the bootstrap receipt required by this verifier.

Host preparation and application qualification are separate milestones. A working SSH login,
successful bootstrap, or healthy MicroOS boot does not prove a composed LychD installation.
[Summoning](../summoning.md) remains an unfinished acceptance rite, with no published matching
CLI/image pair and no qualified complete install/start/reply/stop sequence. Its current example
requires NVIDIA hardware; this VPS has no GPU and does not inherit that example's model path.
The [delivery ledger](../state-of-the-work.md#inscription-and-embodiment) owns those limits.

## Choose one pilot and preserve recovery

Use `lychd-pilot` as the **single** SSH alias throughout the campaign. Resolve it to the selected
VM in private workstation SSH configuration. Do not expand this procedure to a host group or all
servers. Keep its private worksheet, keys, provider correspondence, configuration bundle and
observations outside the checkout.

Before changing boot media or erasing the selected disk, record:

- the selected VM's panel identity and confirmation that it contains no data to preserve;
- current IPv4 address, prefix/netmask, gateway, DNS servers, interface MAC, IPv6 allocation and
  route, and any provider network restrictions;
- current disk layout, the provider's BIOS/UEFI setting and virtual disk/network device types;
- a working panel console, a separate recovery SSH key, and the provider's rescue procedure.

Ask AlphaVPS to confirm DHCP versus static configuration, required IPv6 setup, virtio support,
firmware compatibility, custom ISO availability for this service, and how to supply first-boot
configuration media. A stock template's networking is not evidence that DHCP will configure a
custom installation. Keep the console open until the new installation has survived a reboot and
both intended access paths have been checked. Credentials for infrastructure recovery remain
separate from the runtime account and are never mounted into an application container.

## Pin and verify the installer

Use the **x86_64 offline DVD installer**, selected from the official
[MicroOS download page](https://get.opensuse.org/microos/):

```text
https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Current.iso
https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Current.iso.sha256
https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Current.iso.sha256.asc
```

`Current` is a moving discovery URL. Before installation, record the resolved dated snapshot,
exact download URL and SHA-256 in the private campaign record; send that pin with the support
request. Fetch the ISO and both verification files together. Verify the signature using an
independently authenticated openSUSE signing-key fingerprint, then verify the downloaded ISO
against the authenticated checksum. Follow openSUSE's
[download verification instructions](https://en.opensuse.org/SDB:Download_help#Checksums).
A checksum fetched beside an image without authenticating its signer establishes corruption
detection, not provenance. Do not proceed with a missing or mismatched signature/checksum, or
silently substitute a later `Current` image when repeating the pilot.

On **5 November 2026**, the official alias resolved to this dated installer:

```text
https://download.opensuse.org/tumbleweed/iso/openSUSE-MicroOS-DVD-x86_64-Snapshot20261103-Media.iso
Size: 2931818496 bytes
SHA-256: 91ea07d7d9463316a2f227655dfa2f0465daa2c022df0b0eeeda68e51538a0f8
Signing fingerprint: AD48 5664 E901 B867 051A B15F 35A2 F86E 29B7 00A4
```

The dated URL's `.sha256` and `.sha256.asc` files were fetched and the checksum signature verified
against that fingerprint, independently listed on the official download page. The public key
is available from the official
[Tumbleweed repository](https://download.opensuse.org/tumbleweed/repo/oss/repodata/repomd.xml.key).
This check verified signed checksum metadata; the multi-gigabyte ISO was not downloaded or hashed
as part of preparing this guide. The installer operator must download and verify its actual bytes
before asking the provider to mount it. If this dated artifact is no longer available, explicitly
select and verify a new dated snapshot and update the campaign record.

This is the installer route, not a preinstalled raw disk image or a self-install image. The
operator selects networking, firmware-compatible boot setup, and storage through the installer.

## Request media and install through the console

AlphaVPS documents [custom ISO requests](https://alphavps.com/clients/knowledgebase/1/Available-ISOs.html)
and [VNC, media and boot order](https://alphavps.com/clients/knowledgebase/4/Getting-started-with-KVM-VPS.html).
Open a support ticket for the selected service if the required ISO is not offered;
account-specific controls must be confirmed
by the provider. A [ready-to-copy ticket](https://github.com/hexanomicon/lychd/blob/main/deployments/microos/alpha-support-ticket.md)
contains the pinned public ISO URL and checksum. Ask for the
supported ISO attachment and boot-order procedure, and request confirmation that support can
replace that ISO in the **same virtual CD/DVD drive** with an operator-supplied private
`LABEL=combustion` configuration ISO after installation and before the first disk boot. Ask for
the supported private transfer mechanism. This provider confirmation is a precondition; a custom
installer ISO does not establish support for an operator configuration ISO. Include no private
key or runtime secret. Confirm the console and rescue route before authorizing a disk replacement.

The following is the **proposed acceptance sequence**, gated by the unqualified first-boot
handoff above. It is not a supported installation recipe yet.

1. In the selected VM's panel, attach the confirmed installer ISO, select CD/DVD before the disk,
   and boot into its installer using the provider's VNC console.
2. Select **MicroOS Container Host**, without a desktop. Configure the provider-confirmed
   network, hostname, time synchronization and firmware-compatible boot setup. Do not assume
   GRUB: use the boot loader offered for the confirmed firmware by this installer.
3. Review the complete partition plan using the storage rules below. Verify that the target
   disk belongs to the selected empty VM before accepting the destructive installer summary.
4. Establish a console recovery method and prepare the first-boot configuration as described
   below. Confirm the installed target will execute Combustion on its first boot;
   an ISO installation and a preconfigured MicroOS image need not expose identical first-boot
   choices.
5. Finish installation but **stop before the first disk boot**. Have the confirmed provider
   procedure swap the installer ISO for the private configuration ISO in the same drive. Select
   the hard disk first, leaving the configuration ISO attached, then boot the installed target.
   No simultaneous second virtual drive is required. Remove the configuration ISO after a
   successful bootstrap, then test another ordinary disk boot.

If first-boot media or the required first-boot trigger is unavailable, stop at the installed-host
boundary and resolve it with the provider and the
[Combustion instructions](https://github.com/openSUSE/combustion/blob/master/README.md).
Do not run the first-boot helper as an undocumented live repair script.

For the disposable-VM qualification, inspect the installed package and `lsinitrd` output for the
Combustion module before first boot, and observe the first-boot detector and successful helper
completion. Upstream can omit the module from a host-only initrd when `/etc/machine-id` exists.
The helper deliberately requires that machine ID to be absent: adding a `combustion.firstboot`
kernel argument to an initialized machine does not make it eligible. Do not delete its machine
ID, bypass the guards, or invent installer-target paths to force the candidate through.

## Allocate the 55 GB disk deliberately

The current upstream [MicroOS installer control file](https://raw.githubusercontent.com/yast/skelcd-control-MicroOS/master/control/control.MicroOS.xml)
proposes a 20 GiB root and separate `/var`; `/home` can otherwise consume that small root.
Rootless Podman normally places image layers below the runtime user's home, as do LychD's XDG
data and cache roots. Accepting that proposal without checking home placement can put images,
PostgreSQL and caches into the root budget instead of the larger data area.

For this empty 55 GB pilot, propose **18 GiB Btrfs `/`, 22 GiB Btrfs `/home`, and Btrfs `/var`
using the remaining space after installer-required firmware/boot partitions**. Let the installer
select firmware-appropriate boot partitions; do not assume their names or sizes. Require at least
5 GiB for `/var`, and review the actual layout rather than deriving it from the advertised size.
Swap is optional only if this budget and the free-space gate still fit. If they do not fit, stop
and resolve the layout rather than weakening the checks.

Use a **Btrfs root and an explicitly mounted Btrfs `/home`** with at least the configured
`home_min_free_gib` free after installation; the bootstrap example requires 20 GiB. A separately
mounted Btrfs subvolume is acceptable. Its backing filesystem must actually have the planned
capacity. Merely mounting another subvolume of an already constrained 20 GiB root does not create
space. Choose the custom installer layout before erasure and account for firmware partitions,
root, `/var`, `/home`, system logs, image layers, database growth and free-space reserve together.
55 GB of advertised storage is not 55 GiB of usable capacity.

Keep application storage and caches outside the root OS snapshot set. Verify the actual mount and
snapshot layout rather than relying on names. If the installer's proposed layout cannot provide
the required Btrfs home within this disk, adjust it before installation; the bootstrap refuses
an unmounted or undersized `/home` and never partitions a disk or moves an existing account.
Do not compensate by placing private application data in the checkout.

After first boot, inspect both filesystem capacity and Btrfs allocation as infrastructure root:

```bash
lsblk -f
findmnt -T /
findmnt -T /home
findmnt -T /var
df -h / /home /var
btrfs filesystem usage /
btrfs filesystem usage /home
snapper list-configs
snapper -c root list
```

`/home` must be its own mounted Btrfs path, with the intended capacity and exclusion from root
rollback. Keep only a small, reviewed number of useful OS recovery points and monitor free space.
A snapshot count is not a byte cap; shared extents, changed data and pinned snapshots affect
reclamation. Do not delete the active/default snapshot or automate broad cleanup during this
pilot.

## Prepare a first-boot bundle

The source bundle is in
[`deployments/microos`](https://github.com/hexanomicon/lychd/tree/main/deployments/microos).
It configures the host floor only. Combustion is an initial provisioning mechanism; it is not
continuous reconciliation or Nix, and it does not deploy LychD.

On a Linux workstation, create the bundle **outside the repository**. From the checkout root:

```bash
umask 077
BOOTSTRAP_DIR="$HOME/lychd-private/lychd-pilot-bootstrap"
install -d -m 700 "$BOOTSTRAP_DIR" "$BOOTSTRAP_DIR/keys"
cp deployments/microos/combustion/host.example.json "$BOOTSTRAP_DIR/host.json"
```

Edit private `host.json` to select the hostname, runtime account name, UID/GID, nonoverlapping
subordinate UID/GID ranges, and free-space threshold. Supply two **distinct** public keys at
`keys/runtime.pub` and `keys/recovery.pub` beside that JSON, matching its relative key paths.
Keep both private keys on the workstation. The ordinary runtime account has no sudo authority;
the explicitly enabled root recovery SSH path has a separate key. Password SSH authentication
is disabled. Review this change against your console recovery plan before first boot.

With `xorriso` or `mkisofs` already installed on the workstation, build the configuration ISO:

```bash
python3 deployments/microos/build_config_iso.py \
  --config "$BOOTSTRAP_DIR/host.json" \
  --output "$BOOTSTRAP_DIR/combustion.iso"
```

The helper uses the upstream
[Combustion media format](https://github.com/openSUSE/combustion/blob/master/README.md), labels
the ISO `combustion`, and stages only the tracked script/helper, validated configuration and
referenced Ed25519 public keys. It does not recursively copy the private directory. Its output
must be absent, outside Git checkouts, with an invoking-user-owned `0700` parent. Repository
checks build and inspect fixture media, including long filenames and exclusion of unlisted
files. They do not build your private configuration media or establish AlphaVPS acceptance.

Present that ISO through the provider-confirmed private transfer and same-drive swap procedure.
Do not publish it or paste the configuration into a support ticket. The source example is a
schema example, not authorization to reuse an existing account, subordinate range or SSH key.

The first-boot host helper checks a fresh MicroOS host, Btrfs layout, identity/range collisions and selected
access configuration before host setup. It does not erase or repartition, import application
secrets, create a public application listener, enroll a peer, or qualify a model. Preserve failed
first-boot logs privately and repair the specific cause through the console. Replaying a
first-boot bundle against an established installation is outside its contract.

## Verify the host floor as the runtime user

After reboot, log in using only the runtime key through `lychd-pilot`. Keep the separate recovery
console/key available. Transfer this revision's verifier to the pilot without copying private
workstation state, and run it as the ordinary runtime account:

```bash
python3 deployments/microos/verify_host.py
```

The path above refers to the transferred source tree or script bundle on the VPS. Record the
source revision and verifier digest in the private trial record. Do not prefix the verifier,
Podman, LychD or `systemctl --user` with `sudo`.

Require the complete result, including:

- SELinux **Enforcing**, Btrfs root/data placement and adequate free capacity;
- rootless Podman and the **effective Quadlet user generator**, both at least 5.4;
- effective Podman `graphRoot` on the reviewed Btrfs `/home` mount, and XDG roots within that
  same runtime-home budget; environment or storage overrides must not silently escape it;
- cgroup v2, working subordinate UID/GID maps, a responding systemd user bus and linger;
- host Landlock ABI 6 or newer.

Once an exact reviewed image is already present locally, additionally probe inside the actual
container boundary:

```bash
python3 deployments/microos/verify_host.py --container-image sha256:REPLACE_WITH_64_LOWERCASE_HEX_DIGITS
```

Replace the placeholder with the already-local immutable image ID selected for the campaign. The
verifier uses `--pull=never`, no network, a read-only root, dropped capabilities, no-new-privileges,
and finite process/memory limits, retaining default seccomp. It does not fetch an arbitrary
image. Require the container Landlock probe to pass under that policy, and repeat under the
deployment policy if its seccomp/runtime settings differ. A host ABI number alone does not prove
the container can make the required syscalls. Do not disable SELinux
or use `seccomp=unconfined` to turn a failed floor into a pass.

Landlock availability is a prerequisite, not a delivered Tomb or Coffin. Installing `nono` does
not qualify its source, policy, advisory disposition, resource ceilings or cancellation. Those
boundaries remain [Designed](../state-of-the-work.md#delegated-agent-execution) under
[Security](../adr/09-security.md#the-coffin-delegated-agent-profile).

Keep only the management SSH flow required by the campaign in the host/provider firewall. There
are no public LychD, PostgreSQL, Podman socket or A2A ports to open for host qualification.
Generated loopback bindings do not establish remote access or authentication policy.

## Deliver the application separately

The intended delivery path is **local development → future CI build and verification → one
immutable application image plus matching host tools → the selected VPS**. Building off the
6 GB VPS is preferable to competing with its database and services for shared CPU, RAM and disk.
There is no measured application footprint or supported throughput claim for this machine.

Today, there is no implemented automatic deployment pipeline or published matching CLI/image
pair for this source. Do not invent a registry tag, unattended pull/restart job or CI release.
A future artifact set must bind the same source revision and lock inputs to:

- an immutable Vessel image digest and its provenance;
- matching CLI/host dependencies and a stable Host Reactor installation path;
- selected extensions, Rune/configuration schema and migration compatibility;
- observed lifecycle, readiness and recovery evidence for this host.

The host tools remain on the host; the Vessel remains containerized. MicroOS's root filesystem
policy does not move the application onto the host interpreter. Stage host tools under the
ordinary runtime account on durable storage and keep the stable path required by its generated
Reactor unit. The matching source build described by
[Summoning](../summoning.md#the-desecration) is an acceptance candidate, not a published release.
Do not blindly run its NVIDIA/GGUF instructions on this CPU-only VM. A remote-provider or other
CPU-capable application profile needs its own admitted configuration and end-to-end evidence;
opening a Portal or exposing a public listener is not part of host bootstrap.

Within a separately authorized application trial, preserve the order:

1. **Host ready:** complete the host and actual-container floor checks above.
2. **Initialize:** use the matching CLI's `lychd init --dry-run`; repair required `HOST` failures
   and require a safe plan before `lychd init`. Inspect Codex, Crypt and Forge placement.
3. **Bind:** supply the admitted configuration, secret references and exact image identity;
   inspect `lychd bind --dry-run` before `lychd bind`. Binding validates and materializes units;
   it does not prove they work.
4. **Start and qualify:** establish a separately authorized recovery plan before `lychd start`.
   Observe migration, database permissions, queue processing, useful dispatch, persisted reply,
   authenticated access and recovery according to the specific trial's acceptance criteria.

The public stop path currently refuses an active Vessel. Do not use a claimed graceful
`lychd stop`, direct systemd fallback, image watcher or automated reboot as a substitute for that
missing lifecycle contract. Read
[Close the rite](../summoning.md#close-the-rite) before starting anything. Mark the application
milestone blocked or unqualified until the missing application and recovery boundaries are
explicitly resolved; a host-floor pass remains a useful narrower result.

The runtime home holds default Podman storage and LychD XDG roots. Check their effective paths
and filesystem after initialization; [Layout](../adr/13-layout.md) owns the geography and receipt
rules. PostgreSQL's dedicated data leaf is special: `init` may create a Btrfs subvolume and
attempt no-COW only when the target is absent and trusted. Do not recursively chown or disable
copy-on-write across the home, an existing database or shared storage to imitate that behavior.

## Maintain the OS independently

MicroOS transactional OS updates and application delivery are different changes. A transactional
update prepares an OS snapshot that becomes active after reboot; it does not update the
application image, host tool environment, Codex or database schema. Read the upstream
[`transactional-update` manual](https://kubic.opensuse.org/documentation/man-pages/transactional-update.8.html)
before changing its schedule, package set or rollback selection.

For the first host, inspect the configured timers and reboot policy through the recovery/admin
path. Keep updates controlled while qualifying the pilot:

```bash
systemctl status transactional-update.timer
systemctl list-timers --all
systemctl status rebootmgr.service
```

Confirm the effective update/reboot schedule and its interaction with live application state.
Use one canary, preserve console access and a known bootable OS snapshot, perform one planned
update, reboot, then repeat host and application-specific checks before widening the campaign.
Do not schedule unattended reboots around an application whose safe active stop is unqualified.
Use transactional package operations for the immutable OS; do not treat live `zypper` mutations
as the normal update path.

An OS health check or successful automatic rollback proves only its checked OS conditions. It
does not establish PostgreSQL consistency, a complete LychD migration, useful dispatch or durable
Run health. OS rollback also does not roll back `/home`, separately retained `/var` data or remote
effects. Inspect `/etc` merge/rollback behavior before recovery rather than assuming configuration
and data returned to the same moment. Keep OS rollback and application/database restoration as
separately reviewed operations.

## Back up off host and prove a fresh restore

Snapper root snapshots are OS recovery points, **not database backups**. They neither capture
all application data nor coordinate PostgreSQL writers, queues, extensions and external effects.
The whole-body checkpoint and restore protocol in [Snapshots](../adr/07-snapshots.md) remains
[Designed](../state-of-the-work.md#whole-body-snapshot-restore).

[Restic](https://restic.net/) is an optional free backup transport with encrypted repositories;
its [documentation](https://restic.readthedocs.io/en/stable/) owns installation, keys, repository
checks and restore commands. This repository does not deliver a Restic timer, a coordinated
capture driver, automatic restore or a guaranteed backup schedule.

Before daily use, define an operator procedure that:

1. closes admission and brings application writers to a known consistency boundary;
2. obtains a PostgreSQL-supported consistent logical or physical capture, rather than copying
   live `PGDATA` as ordinary files;
3. seals that capture with a manifest naming the source revision, image digests, host-tool/lock
   identity, schema, configuration and extension provenance, and required durable files;
4. encrypts the sealed material to an off-host destination and verifies repository integrity;
5. records an actual restore to an inactive fresh VM before trusting recovery.

A workstation available over SSH can be the off-host destination. An operator-initiated pull
may fetch a completed, permission-restricted capture from the VPS, then back it up on the
workstation. Keep archive/repository passwords and backup credentials separate from runtime
service secrets, and never expose a Podman socket or unrestricted database access just to enable
the transfer. A stopped laptop is not an available scheduled destination; choose a schedule and
retention that match its real availability and the desired recovery point.

For the restore trial, verify the manifest and integrity first, supply matching artifacts, restore
PostgreSQL using the chosen driver's supported procedure into an inactive target, then verify
schema, ownership, configuration, services and retained application evidence. Reconcile effects
that happened outside the captured host before reopening admission. Never blindly unpack an old
capture over live `PGDATA` or auto-restore on an ordinary boot failure.

Acceptance of this pilot ends with two separately recorded results: a reproducible MicroOS host
floor, and—only after the relevant missing contracts are resolved—a qualified application and
fresh-host restore. Keep disk/free-space and memory observations with those results; the C6G's
advertised capacity alone establishes neither fit nor recoverability.
