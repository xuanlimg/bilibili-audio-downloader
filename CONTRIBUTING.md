# Contributing

感谢你愿意改进这个项目。

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
```

## 提交前检查

```powershell
python -m unittest discover -s tests -v
python -m compileall bilibili_audio
```

打包前运行：

```powershell
.\setup_ffmpeg.ps1
.\build_windows.ps1
```

请勿提交 `.venv`、`build`、`dist`、ffmpeg 二进制或安装程序。
