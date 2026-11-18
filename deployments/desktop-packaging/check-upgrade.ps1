# Exercise a historical edition, an interrupted handoff, then the candidate against the same database.
#Requires -Version 7.4
param([Parameter(Mandatory)][string]$BuildDirectory,
      [Parameter(Mandatory)][string]$Revision,
      [Parameter(Mandatory)][string]$PreviousRevision)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
. "$PSScriptRoot/trial-edition.ps1"
if ($PreviousRevision -ceq $Revision) { throw 'Two distinct editions are required.' }
$old = Get-TrialEdition "$BuildDirectory/previous" $PreviousRevision
$new = Get-TrialEdition "$BuildDirectory/artifacts" $Revision
$rows = (Resolve-Path "$PSScriptRoot/../../scripts/check_desktop_package_rows.py").Path
Set-Location ([IO.Path]::GetTempPath())
Install-TrialEdition $old
$python = $old.Python
$profilePaths = & $python -I -B -m lychd platform | ConvertFrom-Json
if ($profilePaths.profile -cne 'personal-desktop' -or (Test-Path $profilePaths.config) -or (Test-Path $profilePaths.data)) {
    throw 'Upgrade qualification requires a fresh desktop profile.'
}
$backup = Join-Path ([IO.Path]::GetTempPath()) ("lychd-upgrade-" + [guid]::NewGuid().ToString('N'))
& $python -I -B -c 'import sys; from pathlib import Path; from lychd.system.desktop.private import private_directory; private_directory(Path(sys.argv[1]))' $backup
& $python -I -B -m lychd desktop install
try {
    & $python -I -B $rows seed
    & $python -I -B -m lychd desktop backup --destination $backup
} finally {
    & $python -I -B -m lychd desktop uninstall
}
Install-TrialEdition $new
$python = $new.Python
# Inject one missing server prerequisite at the handoff so the real candidate refuses provisioning.
$pgBin = $env:LYCHD_PG_BIN
try {
    $env:LYCHD_PG_BIN = "$backup/absent-bin"
    $PSNativeCommandUseErrorActionPreference = $false
    $failure = & $python -I -B -m lychd desktop install 2>&1
    if ($LASTEXITCODE -eq 0 -or "$failure" -notmatch 'initdb is unavailable') { throw "Unexpected missing-server result: $failure" }
} finally {
    $env:LYCHD_PG_BIN = $pgBin
    $PSNativeCommandUseErrorActionPreference = $true
}
# Boot only an independent copy of the pre-switch backup using the original edition.
$oldPython = $old.Python
& $oldPython -I -B $rows restore --backup $backup
& $python -I -B -m lychd desktop install
try {
    & $python -I -B $rows repair
    & $python -I -B $rows recover
} finally {
    & $python -I -B -m lychd desktop uninstall
}
Remove-TrialEdition $old
Remove-TrialEdition $new
Write-Output "Verified populated upgrade from $PreviousRevision to $Revision and separate pre-switch recovery."
