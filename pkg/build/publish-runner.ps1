<#
.SYNOPSIS
  Stage a self-contained MetaMorpheus CLI into the pyMetaMorpheus wheel payload.

.DESCRIPTION
  The analogue of pyMzLib's publish-bridge.ps1. Publishes the MetaMorpheus CMD
  project self-contained for a given .NET runtime identifier (RID) and copies the
  output into src/pymetamorpheus/_dotnet/, which the wheel ships (gitignored;
  built, not committed). A self-contained build runs WITHOUT a .NET install on the
  target machine — the "just works" guarantee (decision D2).

  Runs on any OS: pwsh (PowerShell Core) is cross-platform, and `dotnet publish`
  cross-compiles to any RID. So Windows/Linux/macOS wheels are all producible.

  NOTE on size (gap G-dist): a self-contained build can exceed PyPI's 100 MB
  per-file limit. The shipping model — bundle in the wheel vs. download-at-install
  on first use — is decided in G-dist before the first public release. This script
  produces the payload either way.

.PARAMETER Rid
  .NET runtime identifier: win-x64 | linux-x64 | osx-x64 | osx-arm64.

.PARAMETER MetaMorpheusRoot
  Path to the MetaMorpheus checkout (contains MetaMorpheus\CMD\CMD.csproj). Its
  HEAD must match the commit in code/metamorpheus.pin — this script checks, and
  refuses to stage a payload built from anything else, because the wheel would
  then be a projection of a build nothing recorded. See code/PINNED.md.

.PARAMETER IgnorePin
  Stage the payload even when the checkout's HEAD is not the pinned commit. For
  deliberate experiments (testing an upstream fix before it is pinned). The
  resulting payload must not be released.

.PARAMETER Configuration
  Debug | Release. Default Release.

.EXAMPLE
  pwsh pkg/build/publish-runner.ps1 -Rid win-x64 -MetaMorpheusRoot E:\GitClones\MetaMorpheus
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("win-x64", "linux-x64", "osx-x64", "osx-arm64")]
    [string]$Rid,

    [Parameter(Mandatory = $true)]
    [string]$MetaMorpheusRoot,

    [switch]$IgnorePin,

    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$csproj = Join-Path $MetaMorpheusRoot "MetaMorpheus/CMD/CMD.csproj"
if (-not (Test-Path $csproj)) {
    throw "CMD.csproj not found at $csproj. Point -MetaMorpheusRoot at the MetaMorpheus checkout root."
}

# --- The pin ------------------------------------------------------------------
# code/metamorpheus.pin holds the one copy of the commit this package projects.
# Validate what we read, so a mangled pin fails naming itself rather than being
# compared against and quietly mismatching everything.
$pinFile = Join-Path $PSScriptRoot "../../code/metamorpheus.pin"
if (-not (Test-Path $pinFile)) {
    throw "Pin file not found at $pinFile. It holds the MetaMorpheus commit this package is built from."
}
$pin = (Get-Content -Raw $pinFile) -replace '\s', ''
if ($pin -notmatch '^[0-9a-f]{40}$') {
    throw "code/metamorpheus.pin must hold a full 40-character sha; got '$pin'."
}

# Compare it with what is actually checked out. A payload built from an unrecorded
# commit is the failure this whole file exists to prevent: the wheel ships, the
# record says something else, and nothing anywhere can tell you which is right.
$head = (& git -C $MetaMorpheusRoot rev-parse HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $head) {
    if (-not $IgnorePin) {
        throw "Could not read HEAD from $MetaMorpheusRoot (is it a git checkout?). Pass -IgnorePin to stage anyway."
    }
    Write-Warning "Could not read HEAD from $MetaMorpheusRoot; -IgnorePin given, staging anyway."
}
elseif ($head.Trim() -ne $pin) {
    $msg = "MetaMorpheusRoot is at $($head.Trim().Substring(0,8)) but code/metamorpheus.pin says $($pin.Substring(0,8))."
    if (-not $IgnorePin) {
        throw ("$msg`nCheck out the pinned commit, or bump the pin (see code/PINNED.md), " +
               "or pass -IgnorePin for a payload you will not release.")
    }
    Write-Warning "$msg -IgnorePin given; this payload must not be released."
}
else {
    Write-Host "Pin check: $MetaMorpheusRoot is at the pinned commit $($pin.Substring(0,8))."
}

# Destination inside the package (gitignored).
$pkgSrc = Join-Path $PSScriptRoot "../python/src/pymetamorpheus"
$dest = Join-Path $pkgSrc "_dotnet"
Resolve-Path $pkgSrc | Out-Null

Write-Host "Publishing MetaMorpheus CMD ($Configuration, $Rid) self-contained..."
$publishDir = Join-Path ([System.IO.Path]::GetTempPath()) "pymm_publish_$Rid"
if (Test-Path $publishDir) { Remove-Item -Recurse -Force $publishDir }

# Self-contained, single native apphost (CMD.exe / extensionless CMD) so the
# target needs no .NET runtime installed.
& dotnet publish $csproj `
    -c $Configuration `
    -r $Rid `
    --self-contained true `
    -p:PublishSingleFile=false `
    -o $publishDir
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed (exit $LASTEXITCODE)." }

Write-Host "Staging into $dest ..."
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force (Join-Path $publishDir "*") $dest

# On POSIX the native apphost needs the execute bit; a Windows-built wheel for a
# POSIX RID must carry it. pwsh on POSIX can chmod; on Windows this is a no-op and
# the CI job that builds the POSIX wheel (running on Linux/macOS) sets it.
$apphost = Join-Path $dest "CMD"
if (Test-Path $apphost -PathType Leaf) {
    if ($IsLinux -or $IsMacOS) { & chmod +x $apphost }
}

$size = (Get-ChildItem -Recurse $dest | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("Staged payload: {0:N1} MB at {1}" -f $size, $dest)
Write-Host "Done. (Payload is gitignored; the commit it was built from is code/metamorpheus.pin.)"
