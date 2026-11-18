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
# Read only the 36 consent bytes in a plain, singly-linked file at the root of the exact
# volume GUID. Open the reparse point itself; prohibit writers and renames during validation.
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class LychDColdRequest {
    [StructLayout(LayoutKind.Sequential)] private struct FileInfo {
        public uint Attributes;
        public FILETIME Created, Accessed, Written;
        public uint Serial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true, SetLastError=true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", ExactSpelling=true, SetLastError=true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out FileInfo info);
    [DllImport("kernel32.dll", ExactSpelling=true)]
    private static extern uint GetFileType(SafeFileHandle handle);
    public static bool Matches(string path, string expected) {
        using (var handle = CreateFileW(path, 0x80000000, 1, IntPtr.Zero, 3, 0x00200000, IntPtr.Zero)) {
            FileInfo info;
            if (handle.IsInvalid || GetFileType(handle) != 1 || !GetFileInformationByHandle(handle, out info)
                || (info.Attributes & 0x410) != 0 || info.Links != 1 || info.SizeHigh != 0 || info.SizeLow != 36) return false;
            using (var input = new FileStream(handle, FileAccess.Read)) {
                var bytes = new byte[36];
                int offset = 0;
                while (offset < bytes.Length) {
                    int count = input.Read(bytes, offset, bytes.Length - offset);
                    if (count == 0) return false;
                    offset += count;
                }
                return String.Equals(Encoding.ASCII.GetString(bytes), expected, StringComparison.Ordinal);
            }
        }
    }
}
'@
$marker = $volumeName + '.lychd-volume-request-' + $Cut.ToString()
if (![LychDColdRequest]::Matches($marker, $Volume.ToString())) { throw 'The requested volume and pending cut do not match.' }
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
