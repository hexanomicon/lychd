---
title: Tumbleweed snapshot upgrade qualification
icon: material/test-tube
---

# Qualify one disposable snapshot upgrade

`deployments/qualification/qualify.py` boots one prepared baseline image in an owned QEMU
guest, observes its existing LychD deployment, upgrades only that guest to an explicitly pinned
Tumbleweed snapshot, reboots it and repeats the observations. It uses rootless QEMU TCG and
user networking with one SSH forward bound to `127.0.0.1`. It changes no controller networking,
desktop configuration or production host. A missing VM, repository, tool or input fails the run.
Offline contract tests and `--check` validate tooling; they are not VM qualification.

This is a candidate qualification procedure. No successful snapshot transition is claimed by
its presence. A passing receipt covers the exact baseline image, snapshots, controller source,
application revision and OCI image recorded there. It establishes neither fresh installation,
another snapshot transition, workstation hardware/browser behavior nor application-code upgrade.
The same application source and image remain in use before and after the OS upgrade.

## Prepare the private baseline

On an explicitly disposable builder, authenticate an official openSUSE image using its signed
checksum and independently authenticated signing-key fingerprint. The
[official download page](https://get.opensuse.org/tumbleweed/) provides cloud images and
verification instructions. Retain the original image, signed checksum, public key and their
SHA-256 identities; moving aliases and old-image retention are not permanent contracts.
The original signed image and prepared baseline have separate identities. An operator may
separately prepare an older baseline from a newer authenticated image, recording that explicit
builder transition; the harness still requires the prepared guest's actual release and packages
to match its baseline pin. The qualification run itself admits only a strictly later candidate.

Prepare the baseline using the [Server procedure](index.md), including a model-free running
body, exact source and admitted OCI image, root and runtime SSH public keys, required native
deployment protocol version 1 and any deliberately selected access profile. This preparation
is a separate effectful operation: the harness does not construct a working baseline from an
unconfigured cloud image. Keep private material outside every checkout. Use a baseline with
passwordless root SSH restricted to its disposable test key; no production key belongs here.

Create `/etc/lychd-qualification.json` as a root-owned regular file, mode `0600`, containing
exactly `{"schema":1,"disposable":true,"baseline_id":"<a recorded UUID>"}`. Record its
`/etc/machine-id`, snapshot `VERSION_ID`, source SHA and OCI image ID. Shut down the builder
cleanly and retain a standalone qcow2 image with no backing file. Never use a production disk
or a writable live image. The baseline marker is an additional guard; ownership of the actual
QEMU process, pinned image and localhost-only connection establish the harness target.
The prepared artifact must boot with BIOS firmware and virtio disk/network devices under QEMU
`q35`; this first lane does not select UEFI firmware or qualify Secure Boot.

## Pin one transition

Copy the [plan example](https://github.com/hexanomicon/lychd/blob/main/deployments/qualification/plan.example.json)
outside the checkout, replace every placeholder and restrict it and referenced private files
to the current operator. The closed schema admits one baseline, one strictly later candidate,
one prepared image, one application revision/image and one exact SSH host key. Host keys are
pinned before the first connection; `ssh-keyscan` is not an admission step. The private root
and runtime keys must match keys already installed in the baseline. The harness generates its
own one-host inventory and SSH configuration; it accepts no arbitrary command hooks.

Pin both snapshots' exact official repositories and each `repodata/repomd.xml` SHA-256.
[openSUSE's history repositories](https://doc.opensuse.org/documentation/tumbleweed/updating_upgrading_reverting/)
use `https://download.opensuse.org/history/<snapshot>/tumbleweed/repo/oss/`; admit non-OSS only
when that exact dated repository actually exists and is needed. There is no assumed retention
guarantee. Preserve required artifacts before they disappear or stop. For each repository,
admit the exact public signing-key file, SHA-256 and fingerprint. This explicit trust decision
is distinct from trusting a key offered during an upgrade.

The harness verifies signed checksum provenance with `gpgv`, verifies all file hashes, and
checks public-key fingerprints before launch. The controller-source digest covers the exact
Ansible and qualification implementation; obtain it with `qualify.py --source-digest` after
all candidate changes are settled. Private Ansible variables are JSON, individually hashed,
and must pin the same application revision and image as the plan. Existing role parsers remain
the owners of their detailed host and application input validation.

## Run and retain evidence

Run as an ordinary unprivileged controller identity; real runs refuse effective UID 0.
Use a private, absent work directory on a controller with Python 3.13+, QEMU (`qemu-img` and
`qemu-system-x86_64`), OpenSSH, GnuPG and the isolated deployment controller already available.
This procedure installs no local tools. Resource ceilings are fixed at two virtual CPUs,
3072 MiB RAM, a 24 GiB maximum overlay file and a 60-minute execution budget, with bounded
command/boot waits and at most 25 additional seconds for owned-process/output cleanup.
Each stage log and combined QEMU/serial output is capped at 32 MiB; exceeding a cap fails the run.
The prepared image must have a virtual disk no larger than 64 GiB. Allow sufficient free disk.

```bash
python3 deployments/qualification/qualify.py --source-digest
python3 deployments/qualification/qualify.py --plan /private/plan.json \
  --controller /private/controller --work-dir /private/new-run --check
python3 deployments/qualification/qualify.py --plan /private/plan.json \
  --controller /private/controller --work-dir /private/new-run \
  --authorize-upgrade RUN_UUID:BASELINE_SNAPSHOT:CANDIDATE_SNAPSHOT
```

The exact authorization token is mandatory for a real run. `--check` never starts a VM or
performs an upgrade. Ordinary Ansible host apply continues to exclude `zypper dup` and reboot.
The harness selects isolated repository and service directories, verifies pinned metadata
before and after refresh, keeps signature checks enabled, imports only admitted public keys,
then runs `zypper dup --no-allow-vendor-change` with automatic refresh disabled. It never uses
`--releasever` as a substitute for an explicitly dated repository. The
[zypper manual](https://manpages.opensuse.org/Tumbleweed/zypper/zypper.8.en.html)
owns these option semantics.

Before and after the upgrade, require the exact snapshot, baseline identity, machine identity,
rootless runtime login, responding user manager, host verification, native application acceptance
and a no-change Server observation. Native acceptance uses
`lychd status --json --deployment-revision SHA --deployment-image-id ID --deployment-verify`
through the existing Ansible entrypoints. The optional access lane additionally runs the existing
access verifier; an omitted lane provides no private-road qualification. Installed endpoint,
browser and two-device acceptance still follows its owning guide.

The reboot must change the kernel boot ID and reach the exact candidate snapshot. Every required
stage and a final controlled guest shutdown must pass before `receipt.json` says `passed`.
A failure records the last stage and stops
only the QEMU process owned by this invocation, using bounded termination and then a kill if
necessary. It preserves the overlay, serial output and private per-stage logs; no automatic
effectful retry, rollback or image deletion follows. The same bounded shutdown runs on success.
Inspect failed evidence before preparing a new run.

`receipt.json` contains only a fixed set of public identities, stage results and log digests.
The directory also contains private paths, inventory and diagnostic output: keep the entire
directory private. Review the sanitized receipt before sharing it. Never upload raw logs, plans,
keys, SSH configuration, memory/disk images or private Ansible variables as public CI artifacts.
No manual CI workflow is supplied until the operator has an authenticated prepared-baseline
artifact distribution and disposable-key delivery contract; missing artifacts cannot produce
a green qualification job.
