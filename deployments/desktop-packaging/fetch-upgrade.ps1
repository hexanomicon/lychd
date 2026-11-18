# Download and verify both edition archives in a separate, token-scoped CI step.
#Requires -Version 7.4
param([Parameter(Mandatory)][string]$BuildDirectory)
$ErrorActionPreference = 'Stop'
$metadata = Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
if ($env:GITHUB_EVENT_NAME -eq 'pull_request') {
    if ($metadata.pull_request.head.repo.full_name -cne $env:GITHUB_REPOSITORY) { throw 'Expected a same-project PR.' }
    $selection = [regex]::Matches($metadata.pull_request.body, '(?m)^\[desktop-upgrade ([1-9][0-9]{0,15}) ([0-9a-f]{40})\]\r?$')
    if ($selection.Count -ne 1) { throw 'Supply exactly one [desktop-upgrade RUN_ID PREVIOUS_REVISION] line.' }
    $priorRun = $selection[0].Groups[1].Value
    $priorRevision = $selection[0].Groups[2].Value
} elseif ($env:GITHUB_EVENT_NAME -eq 'workflow_dispatch') {
    $priorRun = $metadata.inputs.previous_run
    $priorRevision = $metadata.inputs.previous_revision
} else { throw 'Upgrade drills require explicit selection.' }
if ($priorRun -cnotmatch '^[1-9][0-9]{0,15}$' -or $priorRevision -cnotmatch '^[0-9a-f]{40}$' -or $priorRevision -ceq $env:GITHUB_SHA) {
    throw 'Select a recorded run and a different complete edition revision.'
}
$null = New-Item -ItemType Directory -Path $BuildDirectory -ErrorAction Stop
$headers = @{ Authorization = "Bearer $env:GH_TOKEN"; Accept = 'application/vnd.github+json' }
$api = "$env:GITHUB_API_URL/repos/$env:GITHUB_REPOSITORY/actions"
$current = Invoke-RestMethod -Headers $headers -Uri "$api/runs/$env:GITHUB_RUN_ID"
$previous = Invoke-RestMethod -Headers $headers -Uri "$api/runs/$priorRun"
if ($previous.workflow_id -ne $current.workflow_id -or $previous.conclusion -ne 'success' -or
    $previous.head_repository.full_name -cne $env:GITHUB_REPOSITORY) { throw 'Choose a successful same-project desktop installer run.' }
function Get-VerifiedArtifact($Run, $Revision, $Destination) {
    $name = "desktop-installer-$env:RUNNER_OS-$Revision"
    $found = @((Invoke-RestMethod -Headers $headers -Uri "$api/runs/$Run/artifacts?name=$name").artifacts)
    if ($found.Count -ne 1 -or $found[0].name -cne $name -or $found[0].expired -or $found[0].digest -cnotmatch '^sha256:[0-9a-f]{64}$') {
        throw "Missing or expired verified artifact $name in run $Run."
    }
    $id = $found[0].id
    $zip = "$BuildDirectory/$id.zip"
    Invoke-WebRequest -Headers $headers -Uri "$api/artifacts/$id/zip" -OutFile $zip
    if ((Get-FileHash $zip).Hash -ne $found[0].digest.Substring(7)) { throw 'GitHub archive checksum mismatch.' }
    $null = New-Item -ItemType Directory -Path $Destination
    $installer = if ($IsWindows) { "LychD-windows-x64-$Revision.exe" } else { "LychD-macos-arm64-$Revision.pkg" }
    $members = @($installer, 'SHA256SUMS', 'provenance.json')
    $archive = [IO.Compression.ZipFile]::OpenRead($zip)
    try {
        if ($archive.Entries.Count -ne $members.Count) { throw 'Unexpected archive layout.' }
        foreach ($member in $members) {
            $entry = $archive.GetEntry($member)
            if (!$entry) { throw "Missing $member from $name." }
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $Destination $member))
        }
    } finally { $archive.Dispose() }
    Write-Output "Validated $name from run $Run, artifact $id, $($found[0].digest)."
}
Get-VerifiedArtifact $priorRun $priorRevision "$BuildDirectory/previous"
Get-VerifiedArtifact $env:GITHUB_RUN_ID $env:GITHUB_SHA "$BuildDirectory/artifacts"
"PREVIOUS_EDITION=$priorRevision" >> $env:GITHUB_ENV
