# Tumbleweed deployments

Start with the [deployment guide](../docs/deployments/index.md). Installation, host provisioning,
application lifecycle and private access have distinct owners and acceptance checks.

| Target | Installation input | Ansible entry | Read-only acceptance |
| --- | --- | --- | --- |
| AlphaVPS Server | `autoyast/examples/server.json` | `ansible/playbooks/server.yml` | `app-verify.yml` and host `verify.yml` |
| KDE workstation | `autoyast/examples/workstation.json` | `ansible/playbooks/workstation.yml` | `workstation-verify.yml` plus actual laptop/session checks |
| Personal/admin shell | Existing ordinary account; default Zsh or optional Fish | `ansible/playbooks/shell.yml` | `shell-verify.yml`, then fresh login/history/completion |
| Optional private road | Existing installed Server | `ansible/playbooks/access.yml` | `access-verify.yml`, then two-device/browser trial; `access-revoke.yml` closes transport |

Keep real inventories, password hashes, private keys, rendered AutoYaST XML and image archives
outside every checkout. Public examples intentionally cannot install a real host unchanged.
NVIDIA provisioning is excluded. The workstation baseline does not install or activate LychD.
The shared [shell profile](../docs/deployments/tumbleweed/shells.md) changes only the selected
personal/administrator login shell; the runtime identity remains separate.
The access profile is for one trusted owner per instance; it is not a shared multiuser Altar.
The [access guide](../docs/deployments/tumbleweed/access.md) covers local key preparation,
`access/client.py` rendering and the pinned `access/forward.py --profile ...` browser road.
The separate [snapshot upgrade qualification](../docs/deployments/tumbleweed/qualification.md)
boots an admitted prepared baseline in one disposable QEMU guest; fixture tests do not establish
a successful OS transition.

For offline source checks, create a separate controller environment with Python 3.13+ and install
`ansible/requirements-checks.txt`, then run from this checkout:

```bash
bash deployments/check.sh /absolute/path/to/controller
```

This runs fixture tests, Ruff, playbook syntax and example-host selection. It contacts no target.
It does not validate AutoYaST against the selected installer or qualify a real VPS, laptop, VPN
or browser. Follow each guide's acceptance procedure before calling that target ready.
