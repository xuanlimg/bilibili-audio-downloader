# ffmpeg local directory

ffmpeg binaries are intentionally not committed to this repository because the
shared build is larger than GitHub's normal file-size limit.

Run the following command in the repository root:

```powershell
.\setup_ffmpeg.ps1
```

The script downloads ffmpeg essentials and places `ffmpeg.exe`, `ffprobe.exe`
and related files under `tools/ffmpeg/bin`.
