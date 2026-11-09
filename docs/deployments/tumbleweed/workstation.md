---
title: Tumbleweed KDE workstation
---

# Tumbleweed KDE workstation

This candidate prepares a small personal baseline on an **already installed openSUSE Tumbleweed
KDE Plasma 6 workstation**. It does not install an operating system or desktop, create an account,
change its login shell or groups, configure a runtime identity, or activate LychD. The separate
[host preparation](index.md) procedure owns the server floor. [State of Work](../../state-of-the-work.md)
owns delivery evidence; syntax and fixture checks are not a live-workstation receipt.

The workstation playbook installs selected packages from existing repositories and adds three
reserved files for one explicitly named existing non-root user: a fish `conf.d` fragment, a small
ASCII Starship configuration, and a named Konsole profile. It preserves existing fish and Starship
configuration, terminal defaults, desktop layout, history, credentials, and browser profiles.
The fragment selects its prompt only when no explicit `STARSHIP_CONFIG` and no ordinary
`starship.toml` exists, and initializes it again in child shells inheriting that managed choice.
Existing personal prompt choices win. Fish reads `config.fish` after
`conf.d`, so personal initialization there can override these defaults.

Root installs packages. Personal files are inspected and written **as the selected user**, never
by root. The user and home come from the target account database. The files use reserved names and
a management marker; existing unmarked files, symlinks, unsafe directory ownership or write modes,
and changed account identity are refused. Shared directories are not recursively owned or chmodded.
The managed files can be replaced on subsequent runs; put personal overrides in separate files.
This first profile uses the ordinary home-relative XDG defaults. Users with relocated
`XDG_CONFIG_HOME` or `XDG_DATA_HOME` need a separately reviewed profile; these files may not load
in their session, and no environment override is imposed.

No NVIDIA packages, drivers, repositories, initramfs, firewall, SSH, partition, Snapper, reboot,
login-shell, or full-distribution-upgrade operation belongs to this playbook. It does not pull in
the server role. Fira Code and Hack are ordinary packaged fonts, not Nerd Fonts; the supplied
prompt uses text symbols. The optional Konsole profile is selected manually with
`konsole --profile LychD-Workstation`; it does not become the desktop default.

## Run against a disposable KDE installation first

Keep real inventory and account choices outside the checkout. From `deployments/ansible`, copy
`inventory.workstation.example.yml` and `workstation.example.yml` to a private operator directory,
then replace the example address and existing user names. The connection administrator needs
sudo authority to install packages and become the selected personal user. On systems that require
it, use `--ask-become-pass`; do not put passwords in inventory.

```bash
ansible-playbook -i /private/inventory.yml playbooks/workstation.yml -e @/private/workstation.yml --check --diff
ansible-playbook -i /private/inventory.yml playbooks/workstation.yml -e @/private/workstation.yml
ansible-playbook -i /private/inventory.yml playbooks/workstation.yml -e @/private/workstation.yml
ansible-playbook -i /private/inventory.yml playbooks/workstation-verify.yml -e @/private/workstation.yml
```

Check mode observes package presence and validates all existing destinations without writing. It
reports missing packages and planned files; it cannot establish repository resolution, installation,
font rendering, shell behavior, or extension installation. Installation uses `zypper --no-refresh`
against the operator's existing repository metadata. Refresh repositories separately when needed;
no repository, signing-key, or vendor fallback is added. A second unchanged apply should report
zero changes. Provisioning does not perform `zypper dup`; a rolling-distribution update and reboot
need their own maintenance and recovery observation.

## Optional machine-wide Dark Reader policy

`lychd_workstation_dark_reader: false` is the default. Explicit `true` installs a **machine-wide**
RPM Firefox policy at `/etc/firefox/policies/policies.json`. It affects every user of that Firefox
installation. The policy uses `normal_installed`, so the user can disable Dark Reader. A foreign
policy, even one containing other useful policies, is refused rather than merged or overwritten;
an already identical policy is preserved. Flatpak Firefox is outside this operation.

Restart the RPM Firefox, inspect `about:policies` for active policy and errors, then inspect
`about:addons` for `addon@darkreader.org`. Extension download happens in Firefox, not Ansible;
offline operation remains pending. Check a normal web page and verify the extension can be disabled.
Privileged Firefox pages and browser chrome are not transformed by Dark Reader. No browser security
restriction is disabled. The AMO latest-version URL tracks extension releases and is not an artifact
pin. Setting the option back to false preserves the policy: removing it is a separate explicit
operator action after inspecting its contents; it does not uninstall a user extension.

## Acceptance and recovery boundary

Record source revision, controller version, inventory intent, Tumbleweed snapshot, repository list,
package versions, first and second apply results, and verification output. Verify in a fresh user
session that `fish -c 'printf ok'` produces only `ok`, interactive fish initializes the selected
prompt and zoxide, the named Konsole profile renders its font, and Firefox policy works when opted
in. Test pre-existing personal configuration, missing/root user, foreign reserved file, symlink,
wrong OS, missing KDE, conflicting policy, check-before-apply, and offline Firefox refusal/pending
cases. The read-only verification play checks configuration bytes and installed packages, not UI
behavior or application deployment.

A root Snapper rollback generally excludes home; retain a separate personal-data backup. Remove
only the three explicitly managed files to retire these defaults; preserve shared directories and
all unrelated user files. Installed packages are not automatically removed.

Upstream contracts: [fish configuration](https://fishshell.com/docs/current/language.html#configuration-files),
[Starship](https://starship.rs/guide/), [Konsole profiles](https://docs.kde.org/stable_kf6/en/konsole/konsole/profiles.html),
[Mozilla policy configuration](https://firefox-admin-docs.mozilla.org/guides/policies-configuration/),
[ExtensionSettings](https://firefox-admin-docs.mozilla.org/reference/policies/extensionsettings/),
and [Tumbleweed updates](https://doc.opensuse.org/documentation/tumbleweed/updating_upgrading_reverting/).
