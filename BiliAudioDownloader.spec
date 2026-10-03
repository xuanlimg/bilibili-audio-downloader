# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).resolve()
ffmpeg_dir = project_root / "tools" / "ffmpeg" / "bin"
if not ffmpeg_dir.is_dir():
    raise SystemExit(f"没有找到项目内 ffmpeg 目录：{ffmpeg_dir}")

yt_datas, yt_binaries, yt_hiddenimports = collect_all("yt_dlp")
datas = yt_datas + [(str(project_root / "assets"), "assets"), (str(ffmpeg_dir), "tools/ffmpeg/bin")]
binaries = yt_binaries
hiddenimports = yt_hiddenimports + [
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.scrolledtext",
    "tkinter.ttk",
]


a = Analysis(
    ["bilibili_audio_app.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BiliAudioDownloader",
    icon=str(project_root / "assets" / "app.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BiliAudioDownloader",
)
