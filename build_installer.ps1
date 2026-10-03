$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Inno Setup 6\ISCC.exe"),
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 ISCC.exe not found. Install Inno Setup 6 first."
}

$exe = Join-Path $root "dist\BiliAudioDownloader\BiliAudioDownloader.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Application package not found. Run build_windows.ps1 first."
}

$iss = Join-Path $root "installer\BiliAudioDownloader.iss"
& $iscc "/Qp" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed with exit code: $LASTEXITCODE"
}

Write-Host ""
Write-Host "Installer build complete:"
Get-ChildItem -LiteralPath (Join-Path $root "dist\installer") -Filter "*.exe" | Select-Object FullName, Length, LastWriteTime
