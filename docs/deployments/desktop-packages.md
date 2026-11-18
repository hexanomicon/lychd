---
title: Native desktop installers
icon: material/package-variant
---

# Native desktop installers

The desktop packaging workflow builds a macOS Apple Silicon `.pkg` and a Windows x64
`.exe`. Each installer contains CPython 3.14.8, the locked application dependencies, the
LychD wheel, its compiled Altar and the native Desktop Tether executable. Installation works offline under a personal account.
Git, uv, Node and a compiler are build-host tools.

Have PostgreSQL **18** and its matching server-side **pgvector** extension available before
provisioning. The bundled Psycopg client connects to that server. For Bridge chat, also
supply a trusted native llama.cpp server and a local GGUF. Follow the platform-specific
preparation and model steps in [Personal desktop hosts](desktop.md#choose-the-installation).

## Verify and install an edition

Choose the operating system and full source revision. The **Desktop installers (no
publication)** workflow retains unsigned candidates for qualified testing. Its downloadable
artifact contains the installer, `SHA256SUMS` and `provenance.json`. The latter records the
revision, target, Python, uv and Go versions, wheel and lockfile digests, signing mode and final
installer digest. Compare the source revision and digest with the independently trusted
build or release record. A checksum copied alongside a download only detects corruption.

For ordinary distribution, use an installer signed by the expected publisher. On macOS run
`pkgutil --check-signature "<installer>.pkg"` and `spctl --assess --type install --verbose=4 "<installer>.pkg"`.
Check the Developer ID Installer team against the release custodian's independently supplied
team ID. Match `shasum -a 256 "<installer>.pkg"` to the trusted digest. On Windows check
`Get-FileHash -Algorithm SHA256 -LiteralPath $installer` and
`Get-AuthenticodeSignature -LiteralPath $installer` in PowerShell. Require a valid signature,
the expected signer certificate thumbprint and a timestamp certificate. Obtain the expected
identity and digest before installing. A public signed release requires these actual identities
and successful platform verification.

Open the verified installer as the account that will own the database. It places program
files in a directory named for that exact revision. Substitute the full revision below
and keep the terminal open. These functions run the bundled interpreter in isolated mode.

```bash title="macOS"
edition="$HOME/Applications/LychD Editions/<full-revision>"
lychd() { "$edition/runtime/bin/python3" -I -B -m lychd "$@"; }
export LYCHD_PG_BIN="/absolute/path/to/postgresql-18/bin"
lychd platform
lychd desktop install
```

```powershell title="Windows"
$edition = "$env:LOCALAPPDATA\Programs\LychD Editions\<full-revision>"
function lychd { & "$edition\runtime\python.exe" -I -B -m lychd @args }
$env:LYCHD_PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'
lychd platform
lychd desktop install
```

The edition root also contains `desktop-tether` on macOS or `desktop-tether.exe` on Windows.
It has its own setup and consent flow. Run the executable with `-help` to inspect its options.

Use this `lychd` function wherever the source installation uses `uv run --no-sync lychd`.
Configure the model, start `lychd desktop session`, and confirm that the same Bridge
conversation opens after restarting. The deployment guide covers login access, vault
credentials, cold login and backup. [Personal desktop operation](desktop.md)

## Repair, upgrade, recover or remove

- **Repair this edition.** Stop the active session and use `lychd desktop stop`. Re-run the
  same verified installer to replace damaged or missing program files. For a suspected
  modified installation, remove its program directory first using the procedure below.
  Run `lychd platform`, then `lychd desktop install` to check the provisioned host.
- **Upgrade.** Back up the database, settings and credentials through the
  [desktop recovery procedure](desktop.md). Stop the running Vessel with `lychd stop`,
  then use the **old** edition's `lychd desktop uninstall` to retire its login registration
  and stop the dedicated database. Install the new edition alongside it. Select the new
  edition in the terminal function, run `lychd desktop install` and qualify the persisted
  chat. Re-enable login through the new edition if required.
- **Recover.** Keep the old verified installer with its matching pre-upgrade backup and
  credential recovery materials. A program downgrade cannot undo a database migration.
  To recover an earlier database, use the matching version and the desktop recovery drill
  in a separate destination. Confirm the known conversation and credential access before
  retiring the original data or program files.
- **Remove.** From the edition that owns the active login registration, stop Vessel and run
  `lychd desktop uninstall`. On Windows, remove the matching revision under **Installed
  apps**. On macOS, move just that revision's folder under **Applications → LychD Editions**
  in your home directory to the Trash. Program removal preserves the paths printed by
  `lychd platform`, database backups, credentials and model files. An old inactive edition
  whose registration was already retired only needs program-file removal.

## Build and sign

Use a clean checkout of the intended commit on the matching architecture. Builders need
Git, Go 1.26.11, PowerShell 7.4 or later, uv 0.13.0, Node as pinned in `.nvmrc` and npm 12.0.2.
macOS requires the Apple packaging tools. Windows requires the [Inno Setup 7.1.1 compiler](https://jrsoftware.org/inno-setup/downloads) with
`ISCC.exe` on PATH. CI pins the compiler installer by digest. The build downloads the
uv catalogue's managed CPython and installs runtime wheels under `--require-hashes`
from the lock export. It rejects an unavailable wheel on either target, builds the exact-source
Altar, audits both Python archives and retains distribution metadata and license material.

```powershell
$revision = git rev-parse HEAD
$build = Join-Path ([IO.Path]::GetTempPath()) "lychd-edition-$revision"
./deployments/desktop-packaging/build.ps1 -Revision $revision -BuildDirectory $build
```

Use a fresh output directory outside the checkout. The `artifacts` directory contains the
installer and verification records. The build also keeps the exact-source wheel and sdist
under `distributions`. Build once per clean checkout because the Altar build regenerates its
tracked output. Only the custodian of the signing identities should add `-Sign` on a trusted
release machine.

| Host | Credentials and operations for `-Sign` |
| --- | --- |
| macOS | Set `LYCHD_APPLE_TEAM`, the full `LYCHD_APPLE_APPLICATION` and `LYCHD_APPLE_INSTALLER` Developer ID names, and the existing `LYCHD_NOTARY_PROFILE` keychain profile. The script signs nested native code with the application identity, signs the product archive with the installer identity, submits it to Apple's notary service, staples the ticket and checks Gatekeeper. |
| Windows | Make the code-signing private key available to SignTool through the current user's Personal certificate store. Set `LYCHD_SIGNER_THUMBPRINT` and the custodian-approved HTTPS RFC 3161 `LYCHD_TIMESTAMP_URL`. Put the Windows SDK `signtool.exe` on PATH. The script signs the bundled Tether executable and final installer, checks the Authenticode trust chain, matches the exact certificate and requires a timestamp. |

The native CI trial installs, imports the application and bundled Altar from the relocated
interpreter, repairs a missing program file, removes the edition and checks synthetic
configuration and data markers. The separate desktop-host CI exercises PostgreSQL and
authenticated Vessel startup. Windows Server CI, macOS CI and credentialed signing each have
distinct evidence. Physical workstation, clean-account Gatekeeper/SmartScreen acceptance
and cold login require target observations. [Platform qualification](desktop.md)
