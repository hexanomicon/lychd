---
title: Personal and administrator shells
---

# Personal and administrator shells

The workstation and headless Server profiles select **Zsh by default**, with Fish as an explicit
alternative. This applies to one existing ordinary personal or administrator account. The
`lychd` runtime account retains its separate identity, Bash shell and authority. Root, UIDs below 1000, accounts with `false`/`nologin` shells and the runtime UID are refused.
The operator must choose the intended ordinary account; a high UID alone does not establish its purpose. No shell framework or third-party plugin is installed.

The shared `tumbleweed_shell` role installs only the selected distribution shell package and
changes that account's login shell. The workstation also uses the selected shell in its named
Konsole profile. Existing desktop terminal defaults stay unchanged. The headless shell playbook
installs no KDE, fonts, Starship or other workstation packages.

| Variable | Default | Effect |
| --- | --- | --- |
| `lychd_shell` | `zsh` | Exactly `zsh` or `fish`; other values are refused before changes. |
| `lychd_shell_user` | Inventory SSH administrator | Explicit existing ordinary account; the workstation supplies `lychd_workstation_user`. |
| `lychd_shell_set_login` | `true` | Set the selected account's login shell; `false` prepares the shell for manual invocation only. |

Zsh receives native Tab completion and persistent history with a 10,000-entry save target (Zsh trims after roughly 20% growth),
with consecutive duplicates and commands beginning with a space excluded. Its new history lives
in `~/.local/state/lychd-shell/history`, with a private directory and mode `0600`; existing shell
histories are neither imported, truncated nor removed by Ansible. Zsh's completion security
checks remain enabled and insecure completion directories are ignored. Fish uses its native
persistent history, suggestions and completion without replacing `config.fish` or its history.
A leading space is a convenience, not a guarantee that a secret cannot reach another log.

The role writes a reserved Zsh fragment at `~/.config/lychd-shell/zshrc` and a minimal `~/.zshrc`
loader only if no personal startup file exists. A foreign `.zshrc` is preserved and causes an
early refusal unless its owner has deliberately added this exact standalone line:

```zsh
source "$HOME/.config/lychd-shell/zshrc"
```

Review the existing startup logic and place the hook where it will execute in an interactive
shell, before personal overrides. The playbook recognizes the line without executing personal
configuration, and leaves that file's bytes and permissions unchanged. Reserved files bearing
this role's marker can be updated; foreign reserved files, symlinks, hard links, unsafe write
permissions and changed account identity are refused. Personal home writes run as that user.
Custom `ZDOTDIR` or relocated XDG configuration requires a separate review; this profile uses
ordinary home-relative startup paths. Existing personal prompt configuration takes precedence;
on workstations the managed Starship configuration is used only when no personal choice exists.

## Run and verify

Keep inventory and variables outside the checkout. Workstation runs include this role already;
set `lychd_shell: fish` in the private workstation variables to select Fish. The guarded
`server.yml`/`deploy.yml` flow includes administrator shell preparation only when that exact
host has been authorized for provisioning. Its healthy-running verification branch stays read-only.
For shell preparation independent of application deployment, from `deployments/ansible` run:

```bash
ansible-playbook -i /private/inventory.yml playbooks/shell.yml --limit pilot --check --diff
ansible-playbook -i /private/inventory.yml playbooks/shell.yml --limit pilot
ansible-playbook -i /private/inventory.yml playbooks/shell.yml --limit pilot
ansible-playbook -i /private/inventory.yml playbooks/shell-verify.yml --limit pilot
```

Add `-K` when sudo needs a password. To select another existing account or Fish, pass
`-e lychd_shell_user=existing_person -e lychd_shell=fish`. Check mode validates destinations and
reports package, file, history and login-shell changes without writing. Verification checks
packages, configuration, history permissions and the selected shell executable without changing
them or executing user startup code. When login-shell selection is enabled, apply and verification
also require the executable in `/etc/shells`, even if the account already names it. Planning can
report a missing shell package before its executable is installed. A second unchanged apply should report zero changes.

Keep an existing administrator session and console recovery available until a fresh SSH login
works. Verify the actual shell, native completion and history across two fresh interactive
sessions; confirm `zsh -c 'printf ok'` or `fish -c 'printf ok'` prints only `ok`. On a workstation,
check `konsole --profile LychD-Workstation` and the prompt/font. Fixture and syntax checks do not
replace this live acceptance. Switching between supported shells preserves previous configuration,
packages and histories. To retire the role, explicitly restore the chosen account shell, remove
only its marked startup files or manually added source line, and retain histories as personal data.

Upstream contracts: [Zsh history options](https://zsh.sourceforge.io/Doc/Release/Options.html#History),
[Zsh completion](https://zsh.sourceforge.io/Doc/Release/Completion-System.html#Use-of-compinit),
[Fish interactive features](https://fishshell.com/docs/current/interactive.html), and
[Fish startup files](https://fishshell.com/docs/current/language.html#configuration-files).
