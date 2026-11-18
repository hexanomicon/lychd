#Requires -Version 7.4
param([Parameter(Mandatory)][string]$Artifact)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$thumbprint = $env:LYCHD_SIGNER_THUMBPRINT
if ($thumbprint -notmatch '^[0-9A-Fa-f]{40}$') { throw 'Set the expected code-signing certificate thumbprint.' }
if (-not $env:LYCHD_TIMESTAMP_URL -or ([uri]$env:LYCHD_TIMESTAMP_URL).Scheme -ne 'https') {
    throw 'Configure the HTTPS RFC 3161 timestamp service approved for this signer.'
}
# /sha1 selects the exact certificate from the current user's Personal certificate store.
signtool.exe sign /fd SHA256 /sha1 $thumbprint /tr $env:LYCHD_TIMESTAMP_URL /td SHA256 $Artifact
signtool.exe verify /pa /all /tw $Artifact
$signature = Get-AuthenticodeSignature -LiteralPath $Artifact
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $thumbprint -or -not $signature.TimeStamperCertificate) {
    throw 'The artifact must have a valid timestamped signature from the configured certificate.'
}
