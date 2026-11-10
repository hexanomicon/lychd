# Tumbleweed host-floor and bounded application candidate

Use the canonical [Tumbleweed runbook](../../docs/deployments/tumbleweed/index.md) for controller
setup, private inventory and variables, check/apply commands, limitations and host acceptance.

The runtime no-sudo gate supports Tumbleweed's distro `sudo` package profile with
`/etc` administrator configuration overriding `/usr/etc`. It requires a standalone, root-owned,
non-symlink `/etc/sudoers` and trusted configuration directories and files. `visudo` validates
the complete policy; `cvtsudoers` JSON expands aliases and matches `lychd` with its actual Unix
groups. Every matching rule is refused. Includes, remote or unknown sudoers NSS sources,
netgroups, non-Unix groups and custom plugin configuration require administrator review.
The three tools must share the distro's source RPM. A narrowly parsed `sudo -V` build diagnostic
must confirm `/etc/sudoers:/usr/etc/sudoers`; this diagnostic never decides authorization.
Unknown build paths and JSON shapes fail closed, while package-version changes alone do not.

The host package floor includes `wireguard-tools` for native Tether's `wg` key factory;
OpenSSH supplies `ssh-keygen`. Verification requires both executables. Installing these OS
prerequisites creates no VPN keys, peers or units; native Tether owns its preparation and runtime.

| Playbook | Authority | Effect |
| --- | --- | --- |
| `host.yml` / `verify.yml` | administrator + sudo | Converge / observe the installed host floor. |
| `source.yml` | direct `lychd` SSH | Stage one exact source CLI while the body is inactive. |
| `app-verify.yml` | direct `lychd` SSH | Read-only application acceptance of a running body. |
| `deploy.yml` | both, one `--limit`ed host | Classify, then provision a fresh host or only verify a healthy one. |
| `server.yml` | same as `deploy.yml` | Explicit headless Server entry point. |
| `admin.yml` | administrator + sudo, explicit target | Replace only stock vendor sudo policy with a named administrator policy. |
| `workstation.yml` / `workstation-verify.yml` | explicit personal user; sudo only for packages/policy | Independent KDE workstation baseline and observation. |
| `access.yml` | administrator, explicit opt-in | Separate host WireGuard and restricted forwarding candidate. |
| `access-verify.yml` | administrator, exact private intent | Read-only active/revoked transport observation. |
| `access-revoke.yml` | administrator, exact private intent | Persist revocation, disable/stop both dedicated transports, verify closure. |

`deploy.yml` drives the installed LychD CLI (`init`, `bind`, `start`); it generates no units or
configuration of its own and never stops, restarts, updates or kills a running body. It consumes
native deployment protocol 1 from `status --json --deployment-revision SHA` and selects the exact
image during `init --web-image REF`, before its original creation digest is recorded. `start` also
requires `lychd_app_start_authorized=true` once the host's recovery plan is approved. The
application image comes from one admitted OCI archive (`roles/lychd_image/files/admit_oci_archive.py`).

The [deployment index](../../docs/deployments/index.md) routes installation, Server, Workstation,
private access and acceptance. Private inventories, password hashes, endpoint keys, generated
AutoYaST profiles and image archives belong outside the checkout, including ignored directories.

Controller and installed CLI must both implement deployment protocol 1. An older pilot whose
settings were edited after init is deliberately refused; retain its previous private controller
for read-only observation. No automated settings migration or receipt rewrite is provided.
