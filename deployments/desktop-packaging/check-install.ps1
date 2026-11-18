# Disposable native runner only. Test the package at its installed location, outside the source tree.
#Requires -Version 7.4
param([Parameter(Mandatory)][string]$BuildDirectory, [Parameter(Mandatory)][string]$Revision)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
. "$PSScriptRoot/trial-edition.ps1"
$package = Get-TrialEdition "$BuildDirectory/artifacts" $Revision
$edition = $package.Path
$python = $package.Python
$receipt = $package.Receipt
Set-Location ([IO.Path]::GetTempPath())

function Test-EditionLogin {
    if ($IsWindows) {
        if ($env:USERNAME -cnotmatch '^LychDCI[0-9a-f]{10}$' -or $BuildDirectory -notlike "$env:ProgramData\LychD-CI-*") {
            throw 'Login qualification requires the disposable standard user from the Windows trial harness.'
        }
    } elseif ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
        throw 'Login qualification requires the disposable hosted macOS runner.'
    }
    & $python -I -B -m lychd desktop enable-login
    try {
        if ($IsWindows) {
            $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
            $task = Get-ScheduledTask -TaskPath '\' -TaskName "LychD-Vessel-$sid"
            if ($task.Principal.RunLevel -ne 'Limited' -or $task.Actions[0].Arguments -cne '-I -B -m lychd.system.desktop session') {
                throw 'Expected a limited task launching the isolated interpreter.'
            }
        } else {
            $service = "gui/$(/usr/bin/id -u)/org.lychd.vessel"
            $deadline = [datetime]::UtcNow.AddSeconds(120)
            $ready = $false
            while ([datetime]::UtcNow -lt $deadline) {
                try {
                    $reply = Invoke-WebRequest -Uri 'http://127.0.0.1:7134/api/v1/altar/status' -TimeoutSec 2 -SkipHttpErrorCheck
                    if ($reply.StatusCode -eq 401) { $ready = $true; break }
                } catch [System.Net.Http.HttpRequestException] {}
                Start-Sleep -Seconds 1
            }
            if (-not $ready) { throw 'The LaunchAgent did not present the authenticated local API.' }
            & $python -I -B -m lychd stop
            $deadline = [datetime]::UtcNow.AddSeconds(30)
            while ((& /bin/launchctl print $service) -match '^\s*state = running$') {
                if ([datetime]::UtcNow -gt $deadline) { throw 'The LaunchAgent did not exit.' }
                Start-Sleep -Seconds 1
            }
        }
    } finally {
        & $python -I -B -m lychd desktop disable-login
    }
}
Install-TrialEdition $package
$tether = if ($IsWindows) { "$edition/desktop-tether.exe" } else { "$edition/desktop-tether" }
& $tether -help
if (!(Test-Path -LiteralPath "$edition/TETHER_THIRD_PARTY_NOTICES.txt" -PathType Leaf)) { throw 'Missing Tether notices.' }
$installed = Get-Content "$edition/edition.json" -Raw | ConvertFrom-Json
if ($installed.revision -cne $Revision -or $installed.wheel_sha256 -cne $receipt.wheel_sha256) { throw 'Wrong installed edition.' }
$profilePaths = & $python -I -B -m lychd platform | ConvertFrom-Json
if ($profilePaths.profile -ne 'personal-desktop') { throw 'Expected the personal host profile.' }
# Place synthetic content in the real data/config locations of this disposable account.
$markers = foreach ($directory in $profilePaths.config, $profilePaths.data) {
    if (Test-Path -LiteralPath $directory) { throw "Refusing to use an existing desktop profile at $directory." }
    $null = New-Item -ItemType Directory -Path $directory -Force
    $marker = Join-Path $directory 'installer-smoke-marker'
    Set-Content -LiteralPath $marker -Value $Revision -NoNewline
    $marker
}
& $python -I -B -m lychd desktop --help
& $python -I -B -c 'import sys; from pathlib import Path; from lychd.app import create_app; from lychd.interface.web.altar import PATH_ALTAR_INDEX; from lychd.interface.server import run_native_server; import psycopg; assert sys.version_info[:3] == (3,14,8) and PATH_ALTAR_INDEX.is_relative_to(Path(sys.executable).resolve().parents[2]) and PATH_ALTAR_INDEX.is_file() and psycopg.pq.__impl__ == "binary"; import lychd.system.desktop as desktop; assert Path(desktop.__file__).with_name("volume_vss.ps1").is_file()'
$rowCheck = (Resolve-Path "$PSScriptRoot/../../scripts/check_desktop_package_rows.py").Path
& $python -I -B -m lychd desktop install
try {
    Test-EditionLogin
    & $python -I -B $rowCheck seed
}
finally { & $python -I -B -m lychd desktop stop }
# Damage only a package-owned file created by this trial.
Remove-Item -LiteralPath "$edition/edition.json"
Install-TrialEdition $package
if ((Get-Content "$edition/edition.json" -Raw | ConvertFrom-Json).revision -cne $Revision) { throw 'Edition repair failed.' }
& $python -I -B -m lychd desktop install
try { & $python -I -B $rowCheck repair }
finally { & $python -I -B -m lychd desktop uninstall }
Remove-TrialEdition $package
foreach ($marker in $markers) {
    if ((Get-Content -LiteralPath $marker -Raw) -cne $Revision) { throw 'Package lifecycle changed profile data.' }
}
# Reinstall from the same artifact without restoring any data or supplying old secrets.
Install-TrialEdition $package
& $python -I -B -m lychd desktop install
try { & $python -I -B $rowCheck recover }
finally { & $python -I -B -m lychd desktop uninstall }
Remove-TrialEdition $package
