# Disposable native runner only. Test the package at its installed location, outside the source tree.
#Requires -Version 7.4
param([Parameter(Mandatory)][string]$BuildDirectory, [Parameter(Mandatory)][string]$Revision)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$artifacts = Join-Path $BuildDirectory artifacts
$receipt = Get-Content "$artifacts/provenance.json" -Raw | ConvertFrom-Json
if ($receipt.revision -cne $Revision -or $Revision -cnotmatch '^[0-9a-f]{40}$') { throw 'Unexpected revision.' }
$target = if ($IsWindows) { 'windows-x64' } elseif ($IsMacOS) { 'macos-arm64' } else { throw 'Native target required.' }
$extension = if ($IsWindows) { 'exe' } else { 'pkg' }
if ($receipt.artifact -cne "LychD-$target-$Revision.$extension") { throw 'Unexpected installer name.' }
$artifact = Join-Path $artifacts $receipt.artifact
if ((Get-FileHash -LiteralPath $artifact).Hash -ne $receipt.sha256) { throw 'Installer digest mismatch.' }
if ($IsMacOS) {
    $edition = "$HOME/Applications/LychD Editions/$Revision"
    $python = "$edition/runtime/bin/python3"
} else {
    $edition = "$env:LOCALAPPDATA/Programs/LychD Editions/$Revision"
    $python = "$edition/runtime/python.exe"
}
if (Test-Path -LiteralPath $edition) { throw 'Package trial requires an unused edition directory.' }
Set-Location ([IO.Path]::GetTempPath())
function Invoke-Installation {
    if ($IsMacOS) { & /usr/sbin/installer -pkg $artifact -target CurrentUserHomeDirectory }
    else {
        $install = Start-Process -FilePath $artifact -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
        if ($install.ExitCode -ne 0) { throw "Installation returned $($install.ExitCode)." }
    }
}
Invoke-Installation
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
& $python -I -B -c 'import sys; from pathlib import Path; from lychd.app import create_app; from lychd.interface.web.altar import PATH_ALTAR_INDEX; from lychd.interface.server import run_native_server; import psycopg; assert sys.version_info[:3] == (3,14,8) and PATH_ALTAR_INDEX.is_relative_to(Path(sys.executable).resolve().parents[2]) and PATH_ALTAR_INDEX.is_file() and psycopg.pq.__impl__ == "binary"'
# Damage only a package-owned file created by this trial.
Remove-Item -LiteralPath "$edition/edition.json"
Invoke-Installation
if ((Get-Content "$edition/edition.json" -Raw | ConvertFrom-Json).revision -cne $Revision) { throw 'Edition repair failed.' }
if ($IsWindows) {
    $uninstall = Start-Process -FilePath "$edition/unins000.exe" -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
    if ($uninstall.ExitCode -ne 0 -or (Test-Path -LiteralPath $python)) { throw 'Edition removal failed.' }
} else {
    Remove-Item -LiteralPath $edition -Recurse
}
foreach ($marker in $markers) {
    if ((Get-Content -LiteralPath $marker -Raw) -cne $Revision) { throw 'Package lifecycle changed profile data.' }
}
