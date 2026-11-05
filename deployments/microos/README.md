# MicroOS first-boot assets

Follow the canonical [MicroOS VPS host runbook](../../docs/sepulcher/deployments.md) before using
these assets. It owns the AlphaVPS installation, storage, recovery, and qualification procedure.

The bootstrap is an unqualified first-boot candidate. The pinned DVD-to-Combustion initrd and
first-boot handoff has not been observed; do not treat an ISO swap as a working installer.

| Asset | Purpose |
| --- | --- |
| [`combustion/script`](combustion/script) | First-boot Combustion entrypoint. |
| [`host_bootstrap.py`](combustion/host_bootstrap.py) | Validated first-boot host setup; no disk partitioning or application deployment. |
| [`host.example.json`](combustion/host.example.json) | Configuration schema example; copy outside the checkout as `host.json`. |
| [`build_config_iso.py`](build_config_iso.py) | Build private first-boot media with xorriso or mkisofs and explicit configuration/output. |
| [`verify_host.py`](verify_host.py) | Read-only runtime-account checks, with an optional explicit local container image probe. |

Keep real host configuration, key files and observations outside the repository. The bootstrap
requires a fresh host and an installer-prepared mounted Btrfs `/home` with sufficient free space.
Runtime and infrastructure recovery keys are separate. A verifier pass establishes its reported
host mechanisms; application lifecycle and restore acceptance require their own observations.

The standalone host utilities use Python's standard library and their own correctness/import
Ruff profile, inheriting the repository's Python target and formatting. Core's application
policy remains unchanged. Run their checks with Python 3.12 or newer and `ruff 0.16.6`:

```bash
python3 -m unittest discover -s deployments/microos/tests -v
ruff check deployments/microos
ruff format --check deployments/microos
bash -n deployments/microos/combustion/script
```

The media round-trip test requires `xorriso`, or `mkisofs` plus `isoinfo`; CI installs xorriso
on its disposable runner. The tests use public fixture keys and never run host provisioning.
