# Tumbleweed host-floor and bounded application candidate

Use the canonical [Tumbleweed runbook](../../docs/deployments/tumbleweed/index.md) for controller
setup, private inventory and variables, check/apply commands, limitations and host acceptance.

| Playbook | Authority | Effect |
| --- | --- | --- |
| `host.yml` / `verify.yml` | administrator + sudo | Converge / observe the installed host floor. |
| `source.yml` | direct `lychd` SSH | Stage one exact source CLI while the body is inactive. |
| `app-verify.yml` | direct `lychd` SSH | Read-only application acceptance of a running body. |
| `deploy.yml` | both, one `--limit`ed host | Classify, then provision a fresh host or only verify a healthy one. |

`deploy.yml` drives the installed LychD CLI (`init`, `bind`, `start`); it generates no units or
configuration of its own, never stops, restarts, updates or kills a running body, and edits
exactly one settings line whose relation to the init receipt it proves first. `start` also
requires `lychd_app_start_authorized=true` once the host's recovery plan is approved. The
application image comes from one admitted OCI archive (`roles/lychd_image/files/admit_oci_archive.py`).
