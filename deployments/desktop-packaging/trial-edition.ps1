# Common operations for disposable native installer trials.
function Get-TrialEdition([string]$Artifacts, [string]$Revision) {
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
    [pscustomobject]@{ Path = $edition; Python = $python; Artifact = $artifact; Receipt = $receipt }
}

function Install-TrialEdition($Package) {
    $artifact = $Package.Artifact
    if ($IsMacOS) { & /usr/sbin/installer -pkg $artifact -target CurrentUserHomeDirectory }
    else {
        $install = Start-Process -FilePath $artifact -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
        if ($install.ExitCode -ne 0) { throw "Installation returned $($install.ExitCode)." }
    }
}
function Remove-TrialEdition($Package) {
    $edition = $Package.Path
    $python = $Package.Python
    if ($IsWindows) {
        $uninstall = Start-Process -FilePath "$edition/unins000.exe" -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
        if ($uninstall.ExitCode -ne 0 -or (Test-Path -LiteralPath $python)) { throw 'Edition removal failed.' }
    } else {
        Remove-Item -LiteralPath $edition -Recurse -Force
    }
}
