# Only the disposable hosted Windows trial invokes these functions as administrator.
function New-TrialDatabaseVolume($Stage, $Sid) {
    $file = Join-Path $Stage 'volume.vhdx'
    $batch = Join-Path $Stage 'prepare-volume.txt'
    if (Test-Path -LiteralPath $file) { throw 'Expected fresh trial VHD.' }
    $letter = 86..68 | ForEach-Object { [char]$_ } | Where-Object { !([IO.DriveInfo]::GetDrives().Name -contains ($_ + ':\')) } | Select-Object -First 1
    if (!$letter) { throw 'No free trial drive letter.' }
    [IO.File]::WriteAllLines($batch,[string[]]@("create vdisk file=`"$file`" maximum=3072 type=expandable", "select vdisk file=`"$file`"", 'attach vdisk', 'create partition primary', 'format fs=ntfs quick label=LychD-CI', "assign letter=$letter"),[Text.Encoding]::ASCII)
    & "$env:SystemRoot\System32\diskpart.exe" /s $batch | Out-Host
    $drive = [string]$letter + ':\'
    $image = Get-DiskImage -ImagePath $file
    $partition = $image | Get-Disk | Get-Partition | Where-Object DriveLetter -eq $letter
    if (!$partition -or (Get-Volume -DriveLetter $letter).FileSystemLabel -ne 'LychD-CI') { throw 'VHD identity mismatch.' }
    & icacls.exe $drive /grant "*${Sid}:(OI)(CI)M" | Out-Host
    if ($LASTEXITCODE) { throw 'Cannot grant the trial owner access to the VHD.' }
    return $drive
}
function Invoke-TrialVolumeRequest($Drive, $Process, $Stage) {
    $volume = Get-Volume -DriveLetter $Drive[0]
    $id = [guid]($volume.Path.Substring(11,36))
    $end = [DateTime]::UtcNow.AddMinutes(12)
    while (!$Process.HasExited -and [DateTime]::UtcNow -lt $end) {
        $requests = @(Get-ChildItem -Force -LiteralPath $Drive -Filter '.lychd-volume-request-*')
        if ($requests.Count -eq 1) {
            $cut = [guid]($requests[0].Name.Substring('.lychd-volume-request-'.Length))
            & "$Stage\src\lychd\system\desktop\volume_vss.ps1" -Volume $id -Cut $cut | Out-Host
            return
        }
        Start-Sleep -Seconds 1
    }
    if (!$Process.HasExited) { throw 'Timed out before the cold snapshot request.' }
}
