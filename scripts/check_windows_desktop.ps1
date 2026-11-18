# The administrative runner installs dependencies. A separate standard account runs the personal profile.
param([string] $TrialSid, [switch] $BridgeChat, [switch] $TetherTrial, [switch] $VolumeTrial, [switch] $VolumeProbe, [string] $VolumeDrive,
      [string] $PackageBuild, [ValidatePattern('^[0-9a-f]{40}$')][string] $PackageRevision, [ValidatePattern('^[0-9a-f]{40}$')][string] $PreviousRevision, [switch] $PackageLoginOnly)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($TrialSid) {
    if ($elevated -or $identity.User.Value -ne $TrialSid) { throw 'Expected the isolated standard user.' }
    $root = Split-Path $PSScriptRoot
    Set-Location -LiteralPath $root
    $profileKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$TrialSid"
    $userHome = (Get-ItemProperty -LiteralPath $profileKey).ProfileImagePath
    if (-not $userHome -or -not (Test-Path -LiteralPath "$userHome\NTUSER.DAT")) { throw 'Missing user profile.' }
    $env:USERPROFILE = $userHome
    $env:APPDATA = [Environment]::GetFolderPath('ApplicationData')
    $env:LOCALAPPDATA = [Environment]::GetFolderPath('LocalApplicationData')
    if (-not $env:LOCALAPPDATA.StartsWith("$userHome\", [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Application data did not resolve inside the test account.'
    }
    # The runner image may grant packaged applications access to the default Temp tree.
    # Start from a fresh test-owned directory directly beneath this disposable account.
    $testTemp = Join-Path $userHome ('lychd-trial-' + [guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $testTemp)
    & icacls.exe $testTemp /inheritance:r /grant:r "*${TrialSid}:(OI)(CI)F"
    $env:TMP = $env:TEMP = $testTemp
    $env:HOME = $userHome
    $env:USERNAME = $identity.Name.Split('\')[-1]
    $env:LYCHD_PG_BIN = Join-Path $env:ProgramFiles 'PostgreSQL\18\bin'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONNOUSERSITE = '1'
    if ($TetherTrial) {
        & "$root/tether-trial.exe" '-test.v' '-test.timeout=2m'
        exit $LASTEXITCODE
    }
    if ($PreviousRevision) {
        & "$root/deployments/desktop-packaging/check-upgrade.ps1" -BuildDirectory $root -Revision $PackageRevision -PreviousRevision $PreviousRevision
        exit 0
    }
    if ($PackageRevision) {
        & "$root/deployments/desktop-packaging/check-install.ps1" -BuildDirectory $root -Revision $PackageRevision -LoginOnly:$PackageLoginOnly
        exit 0
    }
    $python = "$root\.venv\Scripts\python.exe"
    $cli = "$root\.venv\Scripts\lychd.exe"
    # Both child probes use the Vessel's standard account. This checks an ACL between accounts.
    $protectedFile = Join-Path $root 'administrator-canary.txt'
    try {
        [void][IO.File]::ReadAllText($protectedFile)
        throw 'The standard account read the administrator-only canary.'
    } catch [UnauthorizedAccessException] {
        # Expected denial from the Windows file open.
    }
    $ownFile = Join-Path $testTemp 'standard-user-canary.txt'
    $probe = @'
import errno
import sys
from pathlib import Path
from lychd.system.vessel_mode import require_native_user
require_native_user()
own, protected = map(Path, sys.argv[1:])
own.write_text("standard-user", encoding="ascii")
if own.read_text(encoding="ascii") != "standard-user":
    raise SystemExit("The native account could not read its private canary.")
try:
    protected.read_bytes()
except PermissionError as exc:
    # The CRT used by open() can report EACCES without retaining a Win32 error.
    if exc.errno != errno.EACCES or exc.winerror not in (None, 5):
        raise
else:
    raise SystemExit("The native account read the administrator-only canary.")
'@
    & $python -I -c $probe $ownFile $protectedFile
    if ($VolumeTrial) {
        if ($VolumeProbe) { & $python scripts/check_volume_trial.py --root $VolumeDrive --probe-exposure }
        else { & $python scripts/check_volume_trial.py --root $VolumeDrive }
        exit $LASTEXITCODE
    }
    & $cli --help
    & $cli platform
    & $cli desktop --help
    & $python -m pytest -q -o addopts= -p no:cacheprovider tests/unit/cli/test_native_entry.py tests/unit/domain/web/test_vessel_owner.py tests/unit/system/desktop tests/unit/system/services/test_native_runtime.py tests/integration/test_native_pg_backup.py
    $env:PGHOSTADDR = '127.0.0.2'
    if ($BridgeChat) {
        & $python scripts/check_desktop_bridge.py --browser msedge --engine "$root\engine\llama-server.exe" --model "$root\model.gguf" --output "$root\artifacts\bridge-evidence"
    } else {
        & $python scripts/check_desktop_startup.py
    }
    exit 0
}

if (-not $elevated -or $env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'This account-provisioning trial requires a disposable GitHub-hosted Windows runner.'
}
if (-not $TetherTrial -and -not $PackageRevision) {
    # Exercise the checked-out policy before provisioning the trial account or installing LychD.
    $sourceRoot = Join-Path (Split-Path $PSScriptRoot) 'src'
    $probe = @'
import sys
sys.path.insert(0, sys.argv[1])
from lychd.system.vessel_mode import require_native_user
try:
    require_native_user()
except ValueError as exc:
    if str(exc) != "Run native Vessel as the ordinary installation user.":
        raise
else:
    raise SystemExit("The elevated runner was admitted to native Vessel.")
'@
    & python -I -c $probe $sourceRoot
}
$id = [guid]::NewGuid().ToString('N')
$name = 'LychDCI' + $id.Substring(0, 10)
$stage = Join-Path $env:ProgramData "LychD-CI-$id"
$password = 'aA9!' + [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
Write-Output "::add-mask::$password"
$secure = ConvertTo-SecureString $password -AsPlainText -Force
$user = New-LocalUser -Name $name -Password $secure
try {
    $sid = $user.SID.Value
    $users = Get-LocalGroup -SID 'S-1-5-32-545'
    if ($sid -notin (Get-LocalGroupMember -Group $users).SID.Value) { Add-LocalGroupMember -Group $users -Member $user }
    $credential = [PSCredential]::new("$env:COMPUTERNAME\$name", $secure)
    [void](New-Item -ItemType Directory -Path $stage)
    & icacls.exe $stage /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "*${sid}:(OI)(CI)RX"
    # Populate a read-only checkout and build an installed environment at its final path.
    & git archive --format=tar "--output=$stage\source.tar" HEAD
    & tar.exe -xf "$stage\source.tar" -C $stage
    Remove-Item -LiteralPath "$stage\source.tar"
    if ($TetherTrial) {
        # Compile the exact checked-out revision from the read-only archive above.
        # The standard account only executes this fixed, staged test binary.
        Push-Location -LiteralPath "$stage/clients/desktop-tether"
        try { & go test -mod=readonly -c -o "$stage/tether-trial.exe" . }
        finally { Pop-Location }
    } elseif ($PackageRevision) {
        Copy-Item -LiteralPath "$PackageBuild/artifacts" -Destination "$stage/artifacts" -Recurse
        if ($PreviousRevision) { Copy-Item -LiteralPath "$PackageBuild/previous" -Destination "$stage/previous" -Recurse }
    } else {
        $protectedFile = Join-Path $stage 'administrator-canary.txt'
        [IO.File]::WriteAllText($protectedFile, 'administrator-only')
        & icacls.exe $protectedFile /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F'
        if ([IO.File]::ReadAllText($protectedFile) -ne 'administrator-only') {
            throw 'The administrative control could not read its protected canary.'
        }
        $env:UV_PYTHON_INSTALL_DIR = "$stage\runtime"
        & uv python install --no-bin 3.14.8
        $python = @(Get-ChildItem -Path "$stage\runtime\cpython-3.14.8-*\python.exe")
        if ($python.Count -ne 1) { throw 'Expected one staged CPython 3.14.8 interpreter.' }
        $env:UV_PROJECT_ENVIRONMENT = "$stage\.venv"
        & uv sync --project $stage --python $python[0].FullName --locked --no-default-groups --extra postgres-binary --group test --group desktop-browser --no-editable --link-mode copy
    }
    if ($env:BRIDGE_CHAT -eq 'true') {
        Copy-Item -LiteralPath (Split-Path -Parent $env:BRIDGE_ENGINE) -Destination "$stage\engine" -Recurse
        Copy-Item -LiteralPath $env:BRIDGE_MODEL -Destination "$stage\model.gguf"
        [void](New-Item -ItemType Directory -Path "$stage\artifacts")
        & icacls.exe "$stage\artifacts" /grant:r "*${sid}:(OI)(CI)M"
    }
    Start-Service seclogon
    $argsLine = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$stage\scripts\check_windows_desktop.ps1`" -TrialSid $sid"
    if ($TetherTrial) { $argsLine += ' -TetherTrial' }
    if ($PackageRevision) { $argsLine += " -PackageRevision $PackageRevision" }
    if ($PackageLoginOnly) { $argsLine += ' -PackageLoginOnly' }
    if ($PreviousRevision) { $argsLine += " -PreviousRevision $PreviousRevision" }
    if ($VolumeTrial) {
        . "$stage\scripts\check_volume_vhd.ps1"
        $drive = New-TrialDatabaseVolume $stage $sid
        $argsLine += " -VolumeTrial -VolumeDrive $drive"
        if ($VolumeProbe) { $argsLine += " -VolumeProbe" }
    }
    if ($env:BRIDGE_CHAT -eq 'true') { $argsLine += ' -BridgeChat' }
    $stdout = Join-Path $env:RUNNER_TEMP "lychd-$id.out"
    $stderr = Join-Path $env:RUNNER_TEMP "lychd-$id.err"
    $options = @{
        FilePath = Join-Path $PSHOME 'pwsh.exe'
        ArgumentList = $argsLine
        Credential = $credential
        LoadUserProfile = $true
        UseNewEnvironment = $true
        Environment = @{ SystemRoot = $env:SystemRoot; WINDIR = $env:WINDIR; ProgramFiles = $env:ProgramFiles; ComSpec = $env:ComSpec }
        WorkingDirectory = $stage
        RedirectStandardOutput = $stdout
        RedirectStandardError = $stderr
    }
    $process = Start-Process @options -PassThru
    if ($VolumeTrial) { Invoke-TrialVolumeRequest $drive $process $stage $stdout $stderr }
    if (-not $process.WaitForExit(1200000)) {
        $process.Kill($true)
        throw 'The Windows desktop trial exceeded 20 minutes.'
    }
    $process.WaitForExit()
    Get-Content -LiteralPath $stdout
    Get-Content -LiteralPath $stderr
    if ($env:BRIDGE_CHAT -eq 'true' -and $process.ExitCode -eq 0) {
        $source = "$stage\artifacts\bridge-evidence"
        $destination = Join-Path $env:GITHUB_WORKSPACE 'bridge-evidence'
        [void](New-Item -ItemType Directory -Path $destination)
        foreach ($item in @("$stage\artifacts", $source)) {
            if ((Get-Item -LiteralPath $item).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Redirected evidence directory.' }
        }
        foreach ($file in @('01-bridge.png', '02-answer.png', '03-restarted.png', '04-nexus.png', 'receipt.json')) {
            $item = Get-Item -LiteralPath (Join-Path $source $file)
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint -or $item.PSIsContainer) { throw 'Invalid evidence file.' }
            Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $destination $file)
        }
    }
    if ($process.ExitCode -ne 0) { throw "Desktop account exited with code $($process.ExitCode)." }
}
finally {
    if ($VolumeTrial -and $process -and !$process.HasExited) { $process.Kill($true); $process.WaitForExit() }
    if ($VolumeTrial -and (Get-Command Stop-TrialVolumeProcesses -ErrorAction SilentlyContinue)) {
        if ($stdout -and (Test-Path -LiteralPath $stdout)) { Get-Content -LiteralPath $stdout -Tail 35 -ErrorAction Continue }
        if ($stderr -and (Test-Path -LiteralPath $stderr)) { Get-Content -LiteralPath $stderr -Tail 35 -ErrorAction Continue }
        Stop-TrialVolumeProcesses $sid
    }
    if ($VolumeTrial -and (Test-Path -LiteralPath "$stage\volume.vhdx")) {
        Dismount-DiskImage -ImagePath "$stage\volume.vhdx" -ErrorAction Continue
    }
    Get-CimInstance Win32_UserProfile -Filter "SID='$($user.SID.Value)' AND Loaded=FALSE" | Remove-CimInstance
    Remove-LocalUser -SID $user.SID
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Continue }
}
