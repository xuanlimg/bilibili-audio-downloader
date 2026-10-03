$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$destination = Join-Path $root "tools\ffmpeg\bin"
$ffmpeg = Join-Path $destination "ffmpeg.exe"
$ffprobe = Join-Path $destination "ffprobe.exe"

if ((Test-Path -LiteralPath $ffmpeg) -and (Test-Path -LiteralPath $ffprobe)) {
    Write-Host "ffmpeg is already available:"
    Write-Host $destination
    exit 0
}

$cacheDir = Join-Path $root ".cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$archive = Join-Path $cacheDir "ffmpeg-release-essentials.zip"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if (-not (Test-Path -LiteralPath $archive)) {
    Write-Host "Downloading ffmpeg..."
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
}

$extractDir = Join-Path ([System.IO.Path]::GetTempPath()) ("bili-audio-ffmpeg-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

try {
    Write-Host "Extracting ffmpeg..."
    Expand-Archive -LiteralPath $archive -DestinationPath $extractDir -Force
    $ffmpegFile = Get-ChildItem -LiteralPath $extractDir -Recurse -File -Filter "ffmpeg.exe" | Select-Object -First 1
    if (-not $ffmpegFile) {
        throw "ffmpeg.exe was not found in the downloaded archive."
    }

    $sourceBin = $ffmpegFile.Directory.FullName
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $sourceBin "*") -Destination $destination -Recurse -Force
}
finally {
    if (Test-Path -LiteralPath $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $ffmpeg) -or -not (Test-Path -LiteralPath $ffprobe)) {
    throw "ffmpeg setup failed."
}

Write-Host "ffmpeg setup complete:"
Write-Host $destination
