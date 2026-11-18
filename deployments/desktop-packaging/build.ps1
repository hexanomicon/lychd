# Run with PowerShell 7.4+ on the matching release host, from a clean checkout.
# PostgreSQL data, login registration, and credentials are managed only by the installed CLI.
#Requires -Version 7.4
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Revision,
    [Parameter(Mandatory)][string]$BuildDirectory,
    [switch]$Sign
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$root = (Resolve-Path "$PSScriptRoot/../..").Path
Set-Location $root
$arch = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture
if ($IsMacOS -and $arch -eq 'Arm64') { $target = 'macos-arm64' }
elseif ($IsWindows -and $arch -eq 'X64') { $target = 'windows-x64' }
else { throw 'Build natively on Apple Silicon macOS or x64 Windows.' }
$build = [IO.Path]::GetFullPath($BuildDirectory)
if ($build -eq $root -or $build.StartsWith("$root$([IO.Path]::DirectorySeparatorChar)", [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Select a fresh build directory outside the checkout.'
}
if (Test-Path -LiteralPath $build) { throw 'The build directory must be new.' }
if ((uv --version).Split(' ')[1] -ne '0.13.0') { throw 'Use uv 0.13.0 and its reviewed managed CPython download catalogue.' }
if ((node --version) -ne ('v' + (Get-Content .nvmrc -Raw).Trim().TrimStart('v')) -or (npm --version) -ne '12.0.2') {
    throw 'Use the Node version in .nvmrc and npm 12.0.2.'
}
$version = '3.14.8'
uv run --no-project --python $version -- python scripts/verify_release_source.py $Revision
$work = New-Item -ItemType Directory -Path $build
$payload = (New-Item -ItemType Directory -Path "$work/payload").FullName
$out = (New-Item -ItemType Directory -Path "$work/artifacts").FullName
$stem = "LychD-$target-$Revision"
$env:LYCHD_ALTAR_VERSION = $Revision
npm ci --prefix clients/web
npm --prefix clients/web run build
uv build --python $version --out-dir "$work/distributions"
uv run --no-project --python $version -- python scripts/verify_release_artifacts.py --dist-dir "$work/distributions" --source-revision $Revision
$wheel = (Get-ChildItem "$work/distributions/lychd-*.whl" -File).FullName
uv python install --no-bin --no-registry --install-dir "$work/managed" $version
$managed = @(Get-ChildItem "$work/managed" -Directory -Filter "cpython-$version-*")
if ($managed.Count -ne 1) { throw 'Expected exactly one managed native Python.' }
Move-Item -LiteralPath $managed[0].FullName -Destination "$payload/runtime"
$python = if ($IsWindows) { "$payload/runtime/python.exe" } else { "$payload/runtime/bin/python3" }
if ((& $python -I -c 'import platform; print(platform.python_version())') -ne $version) { throw 'Unexpected staged Python version.' }
uv export --quiet --locked --python $python --no-default-groups --extra postgres-binary --no-emit-project --output-file "$work/requirements.txt"
uv pip install --python $python --break-system-packages --link-mode copy --only-binary :all: --require-hashes --requirements "$work/requirements.txt"
uv pip install --python $python --break-system-packages --link-mode copy --no-deps $wheel
uv pip check --python $python
& $python -I -B "$root/scripts/generate_python_third_party_notices.py" --output "$payload/PYTHON_THIRD_PARTY_NOTICES.txt"
& $python -I -B -m lychd desktop --help
$env:GOTOOLCHAIN = 'local'
if ((go env GOVERSION) -cne 'go1.26.11') { throw 'Use Go 1.26.11 to build Tether.' }
$tether = if ($IsWindows) { "$payload/desktop-tether.exe" } else { "$payload/desktop-tether" }
Push-Location "$root/clients/desktop-tether"
try {
    go build -mod=readonly -trimpath -o $tether .
    & $python -I -B notices.py "$payload/TETHER_THIRD_PARTY_NOTICES.txt"
} finally {
    Pop-Location
}
Copy-Item LICENSE, THIRD_PARTY_NOTICES.md -Destination $payload
$edition = [ordered]@{
    source = "https://github.com/hexanomicon/lychd/tree/$Revision"
    revision = $Revision
    target = $target
    python = $version
    uv = (uv --version)
    go = (go env GOVERSION)
    tether_go_sum_sha256 = (Get-FileHash clients/desktop-tether/go.sum).Hash.ToLowerInvariant()
    wheel_sha256 = (Get-FileHash -LiteralPath $wheel).Hash.ToLowerInvariant()
    uv_lock_sha256 = (Get-FileHash uv.lock).Hash.ToLowerInvariant()
    npm_lock_sha256 = (Get-FileHash clients/web/package-lock.json).Hash.ToLowerInvariant()
}
$edition | ConvertTo-Json | Set-Content "$payload/edition.json" -Encoding utf8NoBOM
if ($IsMacOS) {
    if ($Sign) { & /bin/bash "$PSScriptRoot/sign-macos.sh" runtime $payload }
    $component = "$work/edition.pkg"
    $identifier = "org.lychd.desktop.r$Revision"
    & /usr/bin/pkgbuild --root $payload --identifier $identifier --version 1 --component-plist "$PSScriptRoot/components.plist" --ownership recommended --install-location "/Applications/LychD Editions/$Revision" $component
    (Get-Content "$PSScriptRoot/distribution.xml" -Raw).Replace('EDITION_ID', $identifier) | Set-Content "$work/distribution.xml" -Encoding utf8NoBOM
    $artifact = "$out/$stem.pkg"
    & /usr/bin/productbuild --distribution "$work/distribution.xml" --package-path $work "$work/unsigned.pkg"
    if ($Sign) { & /bin/bash "$PSScriptRoot/sign-macos.sh" installer "$work/unsigned.pkg" $artifact }
    else { Move-Item "$work/unsigned.pkg" $artifact }
} else {
    $compiler = (Get-Command ISCC.exe -CommandType Application).Source
    if ($Sign) { & "$PSScriptRoot/sign-windows.ps1" -Artifact $tether }
    & $compiler "/DEdition=$Revision" "/DPayload=$payload" "/F$stem" "/O$out" "$PSScriptRoot/desktop.iss"
    $artifact = "$out/$stem.exe"
    if ($Sign) { & "$PSScriptRoot/sign-windows.ps1" -Artifact $artifact }
}
$hash = (Get-FileHash -LiteralPath $artifact).Hash.ToLowerInvariant()
$edition.artifact = [IO.Path]::GetFileName($artifact)
$edition.sha256 = $hash
$edition.signing = if ($Sign) { 'platform-verified' } else { 'unsigned-candidate' }
$edition | ConvertTo-Json | Set-Content "$out/provenance.json" -Encoding utf8NoBOM
"$hash  $($edition.artifact)" | Set-Content "$out/SHA256SUMS" -Encoding ascii
