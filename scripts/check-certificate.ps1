param([Parameter(Mandatory=$true)][string]$Certificate)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$InputPath = if ([IO.Path]::IsPathRooted($Certificate)) { $Certificate } else { Join-Path $Root $Certificate }
if (-not (Test-Path $InputPath)) { throw "Certificate not found: $InputPath" }
& cmake -S $Root -B (Join-Path $Root "build") -DCMAKE_BUILD_TYPE=Release
& cmake --build (Join-Path $Root "build") --target kyouen-certcheck --config Release --parallel 2
$Checker = @((Join-Path $Root "build/kyouen-certcheck.exe"),(Join-Path $Root "build/Release/kyouen-certcheck.exe"),(Join-Path $Root "build/kyouen-certcheck")) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Checker) { throw "Checker executable not found" }
$Tmp = $null
try {
  $CertPath = $InputPath
  if ($InputPath.EndsWith(".zst")) {
    if (-not (Get-Command zstd -ErrorAction SilentlyContinue)) { throw "zstd is required" }
    $Tmp = Join-Path ([IO.Path]::GetTempPath()) ("kyouen-" + [guid]::NewGuid() + ".cert")
    & zstd -q -d -f $InputPath -o $Tmp
    $CertPath = $Tmp
  }
  & $Checker $CertPath
  if ($LASTEXITCODE -ne 0) { throw "Certificate check failed" }
} finally {
  if ($Tmp -and (Test-Path $Tmp)) { Remove-Item $Tmp -Force }
}
