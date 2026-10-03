$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment not found: $python"
}

$ffmpeg = Join-Path $root "tools\ffmpeg\bin\ffmpeg.exe"
if (-not (Test-Path -LiteralPath $ffmpeg)) {
    & (Join-Path $root "setup_ffmpeg.ps1")
}

& $python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install -r (Join-Path $root "requirements-build.txt")
}

& $python -m PyInstaller --noconfirm --clean (Join-Path $root "BiliAudioDownloader.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code: $LASTEXITCODE"
}

Write-Host ""
Write-Host "Build complete:"
Write-Host (Join-Path $root "dist\BiliAudioDownloader")
