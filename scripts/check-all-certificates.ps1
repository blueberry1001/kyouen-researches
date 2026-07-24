param([string]$AssetDirectory = "release-assets")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Dir = if ([IO.Path]::IsPathRooted($AssetDirectory)) { $AssetDirectory } else { Join-Path $Root $AssetDirectory }
$Sums = Join-Path $Dir "SHA256SUMS.txt"
if (-not (Test-Path $Sums)) { throw "SHA256SUMS.txt not found: $Sums" }
foreach ($line in Get-Content $Sums) {
  if (-not $line.Trim()) { continue }
  $parts = $line -split '\s+', 2
  $expected = $parts[0].ToUpperInvariant()
  $file = Join-Path $Dir ([IO.Path]::GetFileName($parts[1]))
  if (-not (Test-Path $file)) { throw "Missing asset: $file" }
  $actual = (Get-FileHash -Algorithm SHA256 $file).Hash
  if ($actual -ne $expected) { throw "SHA-256 mismatch: $file" }
  Write-Host "== $([IO.Path]::GetFileName($file)) =="
  & (Join-Path $Root "scripts/check-certificate.ps1") $file
}
