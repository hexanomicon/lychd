# One-shot native requestor. Install this reviewed script in an administrator-controlled
# directory and invoke it from an already elevated Windows PowerShell console.
[CmdletBinding()]
param([Parameter(Mandatory)][guid]$Volume, [Parameter(Mandatory)][guid]$Cut)
$ErrorActionPreference = 'Stop'
$volumeName = '\\?\Volume{' + $Volume.ToString() + '}\'
$target = Get-Volume -Path $volumeName
$partition = Get-Partition -DriveLetter $target.DriveLetter
if (!$target.DriveLetter -or $target.FileSystem -ne 'NTFS' -or $target.DriveType -ne 'Fixed' -or $partition.IsBoot -or $partition.IsSystem) {
    throw 'Expected a dedicated non-system local NTFS volume.'
}
$marker = Get-Item -LiteralPath (Join-Path ($target.DriveLetter + ':\') ('.lychd-volume-request-' + $Cut.ToString()))
if ($marker.Length -ne 36 -or ($marker.Attributes -band [IO.FileAttributes]::ReparsePoint) -or [IO.File]::ReadAllText($marker.FullName) -cne $Volume.ToString()) {
    throw 'Expected the current one-time public capture request.'
}
# Drive letters, the exact volume GUID and a fixed alias are the entire input to DiskShadow.
$letter = 90..68 | ForEach-Object { [char]$_ } | Where-Object { !([IO.DriveInfo]::GetDrives().Name -contains ($_ + ':\')) } | Select-Object -First 1
if (!$letter) { throw 'A free local drive letter is required to expose the snapshot.' }
$drive = [string]$letter + ':'
$parent = [Environment]::GetFolderPath('ProgramFiles')
$directory = Join-Path $parent ('LychD-Volume-' + $Cut.ToString())
# Exclusive fresh directory inherits the OS-protected Program Files ACL. Never reuse a previous request.
$null = New-Item -ItemType Directory -Path $directory -ErrorAction Stop
function Set-RequestorOwner($path) {
    $acl = Get-Acl -LiteralPath $path
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    Set-Acl -LiteralPath $path -AclObject $acl
}
Set-RequestorOwner $directory
$scriptFile = Join-Path $directory 'request.dsh'
[IO.File]::WriteAllLines($scriptFile, [string[]]@('set context persistent nowriters', "add volume $volumeName alias LychDCold", 'create', "expose %LychDCold% $drive", 'exit'), [Text.Encoding]::ASCII)
Push-Location -LiteralPath $directory
try { & "$env:SystemRoot\System32\diskshadow.exe" /s $scriptFile | Out-Host; if ($LASTEXITCODE -ne 0) {throw "DiskShadow exited $LASTEXITCODE"} }
finally { Pop-Location }
$shadow = @(Get-CimInstance -ClassName Win32_ShadowCopy | Where-Object { $_.VolumeName -eq $volumeName -and $_.ExposedLocally -and $_.ExposedName.TrimEnd('\') -eq $drive })
if ($shadow.Count -ne 1 -or !$shadow[0].Persistent -or !$shadow[0].NoWriters -or $shadow[0].ExposedRemotely -or
    $shadow[0].DeviceObject -notmatch '^\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy[1-9][0-9]*$') { throw 'VSS failed to expose the exact local persistent cold snapshot.' }
$record = $shadow[0] | Select-Object ID,VolumeName,DeviceObject,ProviderID,@{Name='Drive';Expression={$drive}},@{Name='Cut';Expression={$Cut.ToString()}}
$temp = Join-Path $directory 'pending.json'
[IO.File]::WriteAllText($temp,($record | ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Set-RequestorOwner $temp
[IO.File]::Move($temp,(Join-Path $directory 'snapshot.json'))
$record
