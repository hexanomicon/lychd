---
title: Tumbleweed Server
icon: material/server
---

# Tumbleweed Server on AlphaVPS

This experiment targets an **AlphaVPS C6G in Sofia: 3 shared vCPU, 6 GB RAM and 55 GB NVMe**.
Install openSUSE Tumbleweed using its **Server** role, without a desktop, then use
[`deployments/ansible/`](https://github.com/hexanomicon/lychd/tree/main/deployments/ansible)
to prepare the ordinary runtime account and observe the host floor. Tumbleweed Server is an
installation choice, not a separate distribution.

For a laptop, use the independent [KDE workstation profile](workstation.md).
[Personal and administrator shells](shells.md) selects Zsh by default or Fish for the existing
administrator, separately from the runtime account; the guarded provisioning branch includes it.
[AutoYaST](install.md) prepares explicit installation inputs for either class. Optional
[private access](access.md) has its own host lifecycle and one-owner acceptance boundary.

!!! warning "One pilot before a fleet"
    The playbooks and source checks are candidate tooling. No successful Tumbleweed
    installation, second converged host run, rootless container operation, or recovery cycle
    has been observed by this campaign. [PR #136](https://github.com/hexanomicon/lychd/pull/136)
    reports five VPS trials; those are contributor reports, not a reproduced receipt for this
    changed candidate. Reinstalling a VPS destroys its existing disk.
    Select one explicitly disposable pilot, retain recovery access, and inspect the installer
    proposal before permitting erasure. The playbooks never partition, format or reboot a host.

Host preparation and application readiness are separate. [Summoning](../../summoning.md)
owns the application rite; [State of Work](../../state-of-the-work.md#systemd-podman-embodiment)
owns its incomplete acceptance. An initial application without a model can test startup and
authenticated database/queue readback. It cannot answer chat. Active container lifecycle and
Portal inference remain blocked; see [Application acceptance](#application-acceptance).

## What each layer owns

| Layer | Responsibility |
| --- | --- |
| Provider and installer | Console, boot media, network, destructive OS installation, firmware-compatible boot and Btrfs layout. |
| Ansible host playbook | Already installed Tumbleweed, required packages, a dedicated non-root account, checked subordinate IDs, public keys, linger and modest existing Snapper retention. |
| Source preparation | One exact public source revision and its host CLI; no moving branch independently on each machine. |
| LychD CLI | Application layout, settings, secrets, generated units, datastore ownership, bind and guarded lifecycle. |
| Operator acceptance | Real host observations, recovery, application readback and the decision to repeat the experiment elsewhere. |

Ansible does not generate an independent application unit/configuration stack. It leaves
existing firewall rules, service enablement and SSH authentication policy unchanged; review
those explicitly before calling a host ready. It does not run rolling upgrades, prune images,
delete snapshots, or install a model. Private input belongs outside every application checkout.
The optional access playbook owns only its declared separate infrastructure services.

## Install one headless host

Record the selected service, its existing data disposition, firmware, disk/NIC models,
addresses/prefixes/gateways/DNS, console and rescue access in a private worksheet. A working
Ubuntu template does not prove DHCP will work in another installer. Do not reset a password
or change another person's SSH access merely to avoid resolving those inputs.

Prefer an authenticated official Offline or NET ISO with the [AutoYaST procedure](install.md).
PR #136 reports a corrupted installer driver image and missing NIC through netboot.xyz on the
provider, while its official NET ISO trial worked. Treat netboot.xyz as a fallback to test through
the console, not a guaranteed installation path. AlphaVPS documents
[ISO/boot controls](https://alphavps.com/clients/knowledgebase/4/Getting-started-with-KVM-VPS.html).
Its existing Netboot.xyz entry can reach the upstream
[openSUSE menu](https://boot.netboot.xyz/opensuse.ipxe):

1. Attach Netboot.xyz only to the selected pilot and open its verified noVNC console.
2. Select CD-ROM before disk and reboot only within the authorized interruption window.
3. In Netboot.xyz select **Linux Network Installs (64-bit) → openSUSE → Tumbleweed**.
4. Select the **Server** role. Review the package selection and omit desktop patterns.
5. Review networking, SELinux **Enforcing**, boot loader, administrator access and the complete
   storage proposal. Stop before destructive acceptance until the exact disk and data loss
   have been approved.
6. Complete installation, detach the ISO, restore disk-first boot, and observe an ordinary
   reboot and SSH/console recovery before using Ansible.

The [upstream installer control](https://github.com/yast/skelcd-control-openSUSE/blob/master/control/control.xml)
defines Server as a small package set with a text interface. Observe the actual installer;
upstream source is not a receipt for the provider's boot medium.

### Network installation trust

The Netboot.xyz openSUSE script normally uses an HTTP mirror for the installer kernel and
initrd; printing MD5 values does not authenticate them. After the loader has read its
configuration, its iPXE shell can set `opensuse_mirror` to
`https://download.opensuse.org`, then return to the menu. Verify the actual displayed retrieval
URLs and stop on certificate errors. Do not disable certificate validation to continue.
That transport check is not the same as verifying a publisher-signed, pinned ISO.

Alternatively, openSUSE publishes a [Network ISO with checksum and signature](https://get.opensuse.org/tumbleweed/).
Pin and authenticate the exact media before using a provider-assisted mount. Netboot.xyz's
[Secure Boot documentation](https://netboot.xyz/docs/kb/hardware/secureboot/) does not establish
end-to-end openSUSE Secure Boot installation. Confirm actual firmware and policy; do not
silently disable an existing protection. Record the installed snapshot/version and source route.

## Fit Btrfs and snapshots into 55 GB

Keep the installer-supported boot partitions and use **one main Btrfs capacity pool**, with
separately mounted subvolumes for `/`, `/home` and `/var`. Preserve its supported Snapper and
boot-loader integration. Do not allocate an arbitrary fixed 18 GiB root and 22 GiB home: that
can strand free space. Size the shared pool and reserve against the actual workload.

Btrfs snapshots initially share blocks. Changed or deleted extents retained by old snapshots,
and metadata, consume additional space; a snapshot is not another full copy of the 55 GB disk.
Subvolumes share free capacity unless quotas restrict them, and root snapshots are not
recursive. [Btrfs documents both properties](https://btrfs.readthedocs.io/en/latest/Subvolumes.html).

Keep models, the actual rootless Podman graph root, application state, database and caches
outside the root OS snapshot set. Verify their backing mounts/subvolumes, not just path names.
For this pilot preserve the installer's `/home` and `/var` exclusion boundaries. Retain only a
few useful OS recovery points and monitor free space before package changes. The host role
changes retention only when the installer already created `/etc/snapper/configs/root`:

- timeline creation off;
- number cleanup on;
- six normal snapshots and two important snapshots.

Those are counts, not hard byte caps. The role does not invoke cleanup, create a replacement
root config, or delete the active/default recovery point. Review installed cleanup timers and
quota behavior separately. Aim for roughly **10 GB free as an operating target**, then revise
the budget against actual installed packages, images and database growth. An OS snapshot is
neither a consistent PostgreSQL capture nor an off-host backup.

Inspect after installation and after one controlled update:

```bash
lsblk -f
findmnt -T /
findmnt -T /home
findmnt -T /var
df -h / /home /var
sudo btrfs filesystem usage /
sudo snapper -c root list
sudo snapper -c root get-config
```

## Prepare the controller and private inventory

Run Ansible on a separate Linux x86_64 controller with Python 3.13, its `venv` module and
pip available. Install those controller prerequisites using its distribution packages first.
From the source checkout, choose an absolute private directory outside it:

```bash
LYCHD_DEPLOY_WORK="$HOME/.local/state/lychd-operator"
mkdir -p "$LYCHD_DEPLOY_WORK"
chmod 700 "$LYCHD_DEPLOY_WORK"
python3.13 -m venv "$LYCHD_DEPLOY_WORK/controller"
"$LYCHD_DEPLOY_WORK/controller/bin/python" -m pip install \
  -r deployments/ansible/requirements-controller.txt
cp deployments/ansible/inventory.example.yml "$LYCHD_DEPLOY_WORK/inventory.yml"
cp deployments/ansible/vars.example.yml "$LYCHD_DEPLOY_WORK/host-vars.yml"
chmod 600 "$LYCHD_DEPLOY_WORK/inventory.yml" "$LYCHD_DEPLOY_WORK/host-vars.yml"
```

Edit those private copies. The inventory identifies an existing administrator and one alias
`pilot`; use its real address and a verified host key. The host variables require an ordinary
runtime UID/GID, unoccupied subordinate UID/GID ranges, and plain **public** SSH keys. Inspect
the actual host before choosing IDs. Never put private keys in Ansible variables, Git, a ticket
or a container. Keep runtime and infrastructure-recovery credentials separate.

Host-key checking stays enabled. After a deliberate reinstall, compare the new SSH public-key
fingerprint through the verified provider console before replacing the corresponding local
known-host entry. Do not use `StrictHostKeyChecking=no` as an installation shortcut.

## Apply and observe the host

### Resolve the stock sudo policy before creating the runtime UID

Tumbleweed's vendor default can grant every user sudo using the root password. The dedicated
`lychd` account must have no sudo grant, so the host role refuses that policy. AutoYaST's fresh
profile writes a named-administrator policy. For an already installed host still using the exact
vendor policy, the separate `admin.yml` operation can install a standalone policy granting only
root and the explicitly named administrator, authenticated with that administrator's own password.
It refuses custom sudoers and existing drop-ins rather than discarding their rules.

Keep the verified provider console open. Confirm the administrator already has a working own
password before changing sudo policy. From `deployments/ansible`, preview the exact one-host change:

```bash
ANSIBLE_HOME="$LYCHD_DEPLOY_WORK/ansible" \
  "$LYCHD_DEPLOY_WORK/controller/bin/ansible-playbook" \
  -i "$LYCHD_DEPLOY_WORK/inventory.yml" playbooks/admin.yml --limit pilot -K \
  -e lychd_admin_name=existing_admin -e lychd_admin_policy_target=pilot --check --diff
```

Replace `existing_admin` with the actual inventory login, then repeat without `--check`.
The first invocation's sudo prompt follows the old policy (often the root password). The playbook
ends after validated publication: Ansible retains one `-K` password and cannot switch it mid-run.
Use a separate new invocation/session with the administrator's own password. Verify fresh SSH and
sudo before closing the console. The target-local backup is recovery material. Custom policy
needs console reconciliation; do not delete files to bypass a refusal.

### Converge the runtime host floor

From `deployments/ansible`, run the controller with the private inventory and variables.
If the administrator requires a sudo password, add `--ask-become-pass` (`-K`) to the host
and verification commands; enter it interactively rather than storing it in the inventory:

```bash
cd deployments/ansible
ANSIBLE_HOME="$LYCHD_DEPLOY_WORK/ansible" \
  "$LYCHD_DEPLOY_WORK/controller/bin/ansible-playbook" \
  -i "$LYCHD_DEPLOY_WORK/inventory.yml" playbooks/host.yml \
  -e "@$LYCHD_DEPLOY_WORK/host-vars.yml" --limit pilot --check --diff
```

Inspect the predicted changes, then repeat without `--check`. Check mode does not create the
new runtime account: dependent home/key/mapping/linger work is skipped until that account
exists. It is not a successful target execution. Run the actual playbook a second time and
retain its result; the expected steady state is no persistent changes.

The role refuses a wrong distro, non-enforcing SELinux, unsuitable storage, identity collisions,
and an existing runtime account that lacks its own matching root-owned receipt. It never
remaps an existing container store or adopts arbitrary account state. Its package installation
uses existing repositories and installs only missing capabilities, without `zypper dup` or
GPG bypasses. Refresh trusted repository metadata explicitly if a stale cache prevents install.
Interrupted account creation needs explicit recovery; do not remove its receipt to force a retry.
Once the mapping stage has been recorded, both exact subordinate ranges must remain present.
Runtime home and SSH-file work uses the runtime user's authority, with no privileged fallback.

The floor also owns one UID-specific systemd drop-in,
`user@UID.service.d/80-lychd-delegate.conf`, requesting `Delegate=cpu memory pids`.
This overrides Tumbleweed's vendor delegation reset only for the runtime manager; it changes
no resource ceilings. New identities receive it after the actual UID and no-sudo assertion,
before the initialized-maps checkpoint and before linger starts their manager. Every post-map
receipt produced by this recipe therefore already has the artifact, and ordinary interrupted
post-map creation can resume. An existing identity missing this file requires explicit one-time
operator preparation before retrying, including identities created by an older recipe with a
valid `maps_initialized` or `configured` schema-1 receipt. The receipt remains valid; do not delete
or rewrite it to bypass this maintenance boundary. The role does not infer application inactivity,
inspect container storage, query Podman state, or automatically prepare legacy identities.
An exact existing artifact is left unchanged even when an application is active. Foreign local
controller policy (including `/usr/local/lib/systemd/system`) and custom manager placement are
refused. The manager and its standard ancestor slices must report `NeedDaemonReload=no` before
convergence or verification; stale or unknown unit policy requires operator review, not an
automatic preflight reload.
The floor reloads PID1 only after publishing the file. It never restarts or reexecutes a user
manager, reboots, or kills a workload. If the current manager still lacks controllers, verification
reports **activation pending**: stop provisioning, perform the separately authorized controlled
boot, then rerun verification and the second no-change apply. A successful reload is not proof
of effective delegation. Root controller support, the exact managed file, effective delegation
and available controllers at the user-manager boundary are required; a resource-limited build
or container remains a separate live acceptance check. `CPUAccounting=` does not enable CPU
control on current systemd. See [systemd's delegation contract](https://systemd.io/CGROUP_DELEGATION/).

Then run the observation playbook:

```bash
ANSIBLE_HOME="$LYCHD_DEPLOY_WORK/ansible" \
  "$LYCHD_DEPLOY_WORK/controller/bin/ansible-playbook" \
  -i "$LYCHD_DEPLOY_WORK/inventory.yml" playbooks/verify.yml \
  -e "@$LYCHD_DEPLOY_WORK/host-vars.yml" --limit pilot
```

This administrative observation does not replace a **direct SSH login as `lychd`**. From that
login, verify the responding user manager and actual rootless storage/network behavior:

```bash
id
loginctl show-user "$USER" --property=Linger
systemctl --user show --property=Version --value
podman --version
podman info --format '{{.Host.Security.Rootless}} {{.Store.GraphRoot}}'
podman unshare cat /proc/self/uid_map
podman unshare cat /proc/self/gid_map
```

Require effective Podman and user Quadlet at least 5.4, cgroup v2, correct maps, Enforcing
SELinux and the intended Btrfs graph-root placement. Current Tumbleweed mapping helpers can
come from `account-utils` and delegate to `newidmapd`; merely installing `shadow` does not
prove rootless mapping works. Observe failures before changing services or permissions.
The verification output reports the actual Landlock ABI; require at least 6 before accepting
that host capability. A separate actual-container-policy observation remains necessary;
neither probe implements Tomb/nono.

## Prepare one exact LychD source

Resolve the desired `main` revision once on the controller and record its full SHA. Reuse
that exact revision on every host in the campaign; independently resolving moving `main`
on five servers does not identify one deployment.

```bash
git ls-remote https://github.com/hexanomicon/lychd.git refs/heads/main
```

The source-preparation playbook stages a versioned checkout and host CLI through **direct SSH
as `lychd`**. It does not build or start the application, edit its settings, bind units or
generate credentials. An active or unknown current/retired Vessel blocks source changes;
an existing interpreter path must not be replaced beneath Host Reactor. A completed versioned
environment is preserved, while dirty, unreceipted or partially prepared workspaces refuse.

The controller requirements also install uv 0.13.4 from PyPI. Admit that Linux x86_64 executable
by its actual SHA-256 and copy it through the role; no remote installer is run. Substitute the
full source SHA observed above and the private key corresponding to the installed runtime key:

```bash
LYCHD_SOURCE_REV=FULL_40_CHARACTER_SHA
LYCHD_RUNTIME_KEY=/absolute/path/to/runtime-private-key
"$LYCHD_DEPLOY_WORK/controller/bin/python" - \
  "$LYCHD_DEPLOY_WORK/source-vars.json" \
  "$LYCHD_DEPLOY_WORK/controller/bin/uv" "$LYCHD_SOURCE_REV" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

destination, binary = Path(sys.argv[1]), Path(sys.argv[2]).resolve(strict=True)
revision = sys.argv[3]
if not re.fullmatch(r"[0-9a-f]{40}", revision):
    raise SystemExit("Supply the recorded full source SHA")
destination.write_text(json.dumps({
    "lychd_source_revision": revision,
    "lychd_source_uv_local_binary": str(binary),
    "lychd_source_uv_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "lychd_source_python": "3.14.8",
}, indent=2) + "\n")
destination.chmod(0o600)
PY
ANSIBLE_HOME="$LYCHD_DEPLOY_WORK/ansible" \
  "$LYCHD_DEPLOY_WORK/controller/bin/ansible-playbook" \
  -i "$LYCHD_DEPLOY_WORK/inventory.yml" playbooks/source.yml \
  -e "@$LYCHD_DEPLOY_WORK/source-vars.json" \
  --private-key "$LYCHD_RUNTIME_KEY" --limit pilot --check
```

The command assumes the shell remains in `deployments/ansible`. After reviewing the check,
repeat without `--check`. Source check mode observes current refusal conditions but does not
clone or install. The first actual preparation can download the explicit managed CPython lane
and locked project dependencies; this is network/package work, not a free-space guarantee.
Repeat it only while the body remains inactive and record the actual result. Keep all model,
credential and private host files outside the source tree, including ignored directories.

For the application image and CLI, follow the same-source build in
[Summoning](../../summoning.md#the-desecration). Prefer building once on a suitable Linux x86_64
workstation from the same recorded SHA, then transfer a verified image archive privately and
load it under each runtime account. Do not build a different moving branch on each VPS or copy
a host `.venv` between machines. The production build shape is:

```bash
podman build --file Containerfile --build-arg "VCS_REF=$LYCHD_SOURCE_REV" \
  --tag "localhost/lychd:$LYCHD_SOURCE_REV" .
podman image inspect "localhost/lychd:$LYCHD_SOURCE_REV" \
  --format '{{.Id}} {{index .Labels "org.opencontainers.image.revision"}}'
```

Execute the build in the exact source checkout and record its resolved base/output image IDs.
If transferring an archive, check its SHA-256 before `podman load`; retain it outside the source
checkout and inspect the loaded image identity. The committed Altar assets are already included;
no desktop or Node/npm installation is needed on the VPS for this path. Tags and source labels
do not prove byte-reproducible images. Do not run CPU benchmarks or continuous inference until
the provider clarifies permission for this shared-core plan.

## Application acceptance

After host and same-source image preparation, connect directly as the runtime user and use
the installed CLI in its stable versioned path:

```bash
# Set the same full SHA recorded on the controller.
LYCHD_SOURCE_REV=FULL_40_CHARACTER_SHA
LYCHD_SOURCE="$HOME/src/lychd-$LYCHD_SOURCE_REV"
LYCHD_CLI="$LYCHD_SOURCE/.venv/bin/lychd"
cd "$LYCHD_SOURCE"
"$LYCHD_CLI" init --dry-run
"$LYCHD_CLI" init
```

Inspect the generated private `lychd.toml` in the effective XDG config root. Preserve its
creation receipt, mode and other generated fields. Edit the existing `[server.web]` table's
`image` to `localhost/lychd:<the recorded full SHA>`; do not append duplicate tables. Keep
`[extensions]` `builtins=[]` and `crypt=[]`, with no model or Portal declarations for this
bounded body trial. Keep the generated PostgreSQL profile, Host Reactor actuator and disabled
raw SAQ admin UI. This is deliberate application configuration, outside the Ansible host role.

Then inspect and apply binding through the same CLI:

```bash
"$LYCHD_CLI" bind --dry-run
"$LYCHD_CLI" bind
"$LYCHD_CLI" status --json
```

Preserve existing settings, generated secrets and datastore ownership; do not rerun
initialization to erase an unclear state. Configuration and image identity still need deliberate
inspection; command exit success alone is not a health claim.

Before attempting `lychd start`, establish the separately authorized recovery plan required
by [Summoning](../../summoning.md#close-the-rite). Public active-container stop/start is still
incomplete. Do not install an Ansible `systemctl restart`, `podman kill`, native web process,
or fake database as a second application lifecycle.

A bounded model-free trial can observe the actual Vessel, PostgreSQL migration, Host Reactor
and queues. Use server-local authenticated reads of `/api/v1/altar/status`,
`/orchestrator/status` and `/orchestrator/queues`; require an unauthenticated protected request
to refuse, working database readback, empty capabilities and observed idle `runs`/`rites`.
Obtain the generated local access credential only in a private interactive terminal through
`lychd access`, never Ansible output or a URL. There is no invented generic `/health` route.

Do not publish or reverse-proxy the listener. The optional [one-owner access candidate](access.md)
preserves loopback publication and authentication through a restricted private road; it still
needs installed/browser qualification. General shared remote access remains unsupported.
A Portal row or supplied API key does not enable inference:
Portal grants refuse until egress admission is implemented. A running model-free body is
not a working chat deployment, a complete lifecycle, or a recovery proof.

## Automate one host end to end

The combined playbook connects as both the existing administrator and `lychd`. Select their
separate keys by host **and remote user** in a private OpenSSH configuration outside the checkout;
a single global Ansible `--private-key` or inventory `ansible_ssh_private_key_file` cannot select
both. For example, create `$LYCHD_DEPLOY_WORK/ssh_config` with mode 0600:

```sshconfig
Host 192.0.2.10
    IdentitiesOnly yes
    StrictHostKeyChecking yes

Match host 192.0.2.10 user existing_admin
    IdentityFile /absolute/private/administrator-key

Match host 192.0.2.10 user lychd
    IdentityFile /absolute/private/runtime-key
```

Replace the address with the exact `ansible_host` and the administrator with the inventory login.
[OpenSSH `Match user`](https://man.openbsd.org/ssh_config#Match) uses the remote username selected
by each play. Pass this file with `--ssh-common-args="-F $LYCHD_DEPLOY_WORK/ssh_config"` on the
combined command below. Do not also set a global private-key option. Inspect the effective key
selection without connecting:

```bash
ssh -G -F "$LYCHD_DEPLOY_WORK/ssh_config" -l existing_admin 192.0.2.10
ssh -G -F "$LYCHD_DEPLOY_WORK/ssh_config" -l lychd 192.0.2.10
```

The first runtime connection will fail on a fresh host; the administrator must then observe that
the account is absent before provisioning starts.
An existing runtime account with inaccessible SSH refuses before any host-floor change: resolve
its key, host-key or network failure instead of treating it as a fresh install.

`playbooks/server.yml` is the server entry point and imports `deploy.yml`, which composes
the steps above for exactly one `--limit`ed host. It first
classifies the runtime account read-only (`roles/lychd_app/files/app_probe.py`) and then admits
only one mode:

| Observed state | Mode |
| --- | --- |
| `running`: owned units active, settings equal to the init receipt except the `[server.web]` image line, Vessel and settings agree on an image labelled with the pinned SHA, Reactor bound to the pinned CLI | read-only verification |
| administrator confirms no `lychd` account, `absent`, `initialized` or `bound_inactive` | provisioning, only with `-e lychd_deploy_target=<host>` |
| `foreign_revision` or anything else (`unknown`) | stop and print the exact reasons |

Provisioning converges the floor, stages the source, loads the admitted image, then runs
`lychd init --dry-run`/`init`, replaces the single image line in place, and runs
`lychd bind --dry-run`/`bind`. It re-classifies after each step. Existing PostgreSQL data,
secrets and settings with any other change are never adopted, regenerated or overwritten.
`lychd start` runs only with `-e lychd_app_start_authorized=true`, after the recovery plan for that
host has been approved. Convergence is then observed read-only; nothing is restarted or killed.

Build or select the campaign image once. Then admit its archive on the controller, which verifies
every blob digest, the revision label and, when given, the expected image ID, and records the
archive SHA-256:

```bash
REV=FULL_40_CHARACTER_SHA
mkdir -p -m 700 "$LYCHD_DEPLOY_WORK/artifacts"
ssh lychd@BUILD_HOST "podman save --format oci-archive localhost/lychd:$REV" \
  > "$LYCHD_DEPLOY_WORK/artifacts/lychd-$REV.oci.tar"
"$LYCHD_DEPLOY_WORK/controller/bin/python" -I \
  roles/lychd_image/files/admit_oci_archive.py \
  "$LYCHD_DEPLOY_WORK/artifacts/lychd-$REV.oci.tar" "$REV" \
  "$LYCHD_DEPLOY_WORK/image-vars.json" EXPECTED_64_HEX_IMAGE_ID
```

Each host's image role refuses a different image under the campaign tag. It checks the transferred
SHA-256 before `podman load` and the exact image ID and label afterwards. Set
`lychd_floor_enable_network_online: true` in the host variables. On Tumbleweed Server nothing else
pulls `network-online.target` into boot, so rootless Podman's
`podman-user-wait-network-online.service` times out. The floor links the target into
`multi-user.target.wants` and starts it once; it changes no network configuration.

```bash
ANSIBLE_HOME="$LYCHD_DEPLOY_WORK/ansible" \
  "$LYCHD_DEPLOY_WORK/controller/bin/ansible-playbook" \
  -i "$LYCHD_DEPLOY_WORK/inventory.yml" playbooks/server.yml \
  -e "@$LYCHD_DEPLOY_WORK/host-vars.yml" -e "@$LYCHD_DEPLOY_WORK/source-vars.json" \
  -e "@$LYCHD_DEPLOY_WORK/image-vars.json" \
  --ssh-common-args="-F $LYCHD_DEPLOY_WORK/ssh_config" \
  --limit NEW_HOST -e lychd_deploy_target=NEW_HOST -K
```

Repeat the same command with `-e lychd_app_start_authorized=true` to start the bound body. Then
run it again without either authorization: a healthy host must report `mode=verify` with no
changes. When image variables are supplied, verification still requires their exact admitted image
ID; a matching source label alone is insufficient. `playbooks/app-verify.yml` runs the same
acceptance without sudo. It reads the local credential through `lychd access` into probe memory
and sends it only to the loopback Altar. It
requires 401 for anonymous and wrong-credential requests, authenticated status/orchestrator/queue
reads, empty capabilities, idle `runs`/`rites`, database tables and a non-superuser runtime role.
It also requires the receipted Phylactery subvolume identity (or an exact mountpoint) and a
loopback-only listener.

On Btrfs, `init` creates the PostgreSQL `data` directory as a subvolume and records its ID and
UUID in the version-2 lifecycle receipt. A subvolume is not a mountpoint, so `lychd status`
reports `not an exact mountpoint`. That is the expected unmounted-subvolume shape; acceptance
compares the live subvolume identity with the receipt instead.

## Repeat on another host

After the pilot passes its declared host and recovery observations, add each fresh Tumbleweed
host and its own IDs/keys to private inventory/host variables. Keep the same admitted source
SHA. Run `--check --diff` and apply with an explicit `--limit`; the playbook defaults to serial
one. The initial OS installation remains a separate destructive operation.

Record first apply, second apply, direct-runtime checks and a controlled OS recovery cycle
for each new host. A passing pilot is reusable procedure, not evidence that an untouched
server is ready. A developer or their coding assistant should read this page and run the same
bounded commands; sharing root credentials or private inventories in Discord is unnecessary.
