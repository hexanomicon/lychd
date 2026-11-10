# Reviewed AutoYaST profiles

Read the [installation contract](../../docs/deployments/tumbleweed/install.md) before use.
This standalone Python 3.12+ generator creates XML for a fresh **whole-disk** x86_64 install.
It never opens a disk, runs a command, contacts a host, writes USB media or starts installation.
The profile always requests YaST confirmation; matching-media tests must establish the actual
stop before disk changes. No unattended flag is available.

Copy `examples/server.json` or `examples/workstation.json` to a private directory outside the
checkout. Replace the placeholders after inspecting the target. Supply a private mode-0600
SHA-512 crypt administrator hash file. No password is accepted on the command line.

```bash
python3 deployments/autoyast/generate.py \
  --config /absolute/private/host.json \
  --password-hash-file /absolute/private/admin.hash \
  --output /absolute/private/autoinst.xml
python3 -m unittest discover -s deployments/autoyast/tests -v
```

Only the displayed JSON fields are supported; unknown fields and duplicate keys refuse.
`architecture` is `x86_64`; `role` is `server` or `workstation`; `firmware` is `bios` or `uefi`
(workstations require UEFI). `disk.erase_all` must be the JSON boolean `true`, and `device`
must identify a whole `/dev/sd*`, `/dev/vd*`, `/dev/nvme*n*` or `/dev/disk/by-id/*` disk.
The generator validates syntax, never physical identity. `swap_gib` is an integer 0–32;
hibernation is not configured. Keyboard choices are `us`, `uk`, `de`, `fr`, `cz`, `sk`.

An explicit wired `network.interface` is required. DHCP uses exactly the two example fields.
For static IPv4, replace the network object with this shape, using actual assigned values:

```json
{
  "interface": "ens3",
  "mode": "static",
  "address": "192.0.2.10/24",
  "gateway": "192.0.2.1",
  "nameservers": ["192.0.2.53"]
}
```

Those documentation-range addresses are examples, not a usable provider configuration.
Only /1–/30 with a distinct on-subnet gateway is supported. IPv6 static configuration,
off-subnet gateways, Wi-Fi, VLANs and custom routes require the interactive installer.
DHCP does not disable IPv6; this generator does not impose an IPv6 routing policy.

Root is locked. The named administrator gets public-key SSH, console password access and
sudo authenticated by their own password. The complete fresh-install sudoers and sshd files
are explicit; no broad targetpw grant or sudo access for `lychd` is generated. Both profiles
enable SSH, allowing subsequent Ansible control. Neither profile imports SSH host keys or
configuration from an existing installation; verify the new host fingerprint through the console.
Workstations must be deliberately accepted without disk encryption; use the interactive installer
when encryption is required.

Tests establish input refusals, private output handling and generated intent, **not** installer
schema compatibility, package resolution, hardware support or successful boot. Validate with
the selected medium's full AutoYaST schema and install in disposable BIOS/UEFI VMs before a
real target. Do not use `YAST_SKIP_XML_VALIDATION` to bypass failures. Observe `/home` and `/var`
as separate Btrfs subvolume mounts before continuing to the Ansible floor.
