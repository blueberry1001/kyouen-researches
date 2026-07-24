param([string]$AssetDirectory = "release-assets")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
& (Join-Path $Root "scripts/check-all-certificates.ps1") $AssetDirectory
if (-not (Get-Command lake -ErrorAction SilentlyContinue)) { throw "Lake is required for the Lean build" }
Push-Location $Root
try {
  & lake build
  if ($LASTEXITCODE -ne 0) { throw "Lean build failed" }
  & lake exe kyouen-classification-demo
  if ($LASTEXITCODE -ne 0) { throw "Lean demo failed" }
} finally { Pop-Location }
