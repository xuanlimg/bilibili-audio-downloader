# B站音频下载器

<p align="center">
  <img src="assets/app.png" width="160" alt="B站音频下载器图标">
</p>

一个面向 Windows 的 B 站音频下载工具。输入视频链接后，可以下载音轨并转换为
MP3、M4A、OPUS、FLAC 或 WAV 格式。

> 请只下载你有权保存的内容，并遵守 B 站服务条款和版权规定。

## 功能

- 支持完整 B 站链接、BV 号、av 号和 b23.tv 短链接
- 支持 MP3、M4A、OPUS、FLAC、WAV
- 显示下载进度、速度和剩余时间
- 支持取消下载、打开输出目录
- 支持浏览器 Cookie 和代理
- 支持下载合集和嵌入视频封面
- 保存最近 200 条下载历史
- 历史窗口支持打开目录、复制链接和清空记录
- 提供 PyInstaller 免安装版和 Inno Setup 安装程序

## 系统要求

- Windows 10/11
- Python 3.10 或更高版本，推荐 Python 3.12+
- 从源码运行或打包时，需要项目内 ffmpeg，或者系统 PATH 中的 ffmpeg/ffprobe

## 从源码运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m bilibili_audio
```

也可以双击：

```text
调试运行.bat
```

## 下载 ffmpeg

项目为了控制仓库体积，没有提交 ffmpeg 二进制文件。首次打包前运行：

```powershell
.\setup_ffmpeg.ps1
```

脚本会从 Gyan.dev 下载 ffmpeg essentials，并放到：

```text
tools\ffmpeg\bin
```

如果你已经有 ffmpeg，也可以把 `ffmpeg.exe` 和 `ffprobe.exe` 放入该目录。

## 构建 Windows 免安装版

```powershell
.\build_windows.ps1
```

输出目录：

```text
dist\BiliAudioDownloader
```

请不要只复制 exe，发布时需要复制整个 `BiliAudioDownloader` 文件夹。

## 构建安装程序

安装 Inno Setup 6 后运行：

```powershell
.\build_installer.ps1
```

输出目录：

```text
dist\installer
```

## 项目结构

```text
bilibili_audio/
├── core.py             # 下载核心
├── gui.py              # Tkinter 桌面界面
├── history.py          # 下载历史存储
└── history_window.py   # 历史记录窗口

assets/                 # 图标资源
installer/              # Inno Setup 安装脚本
scripts/                # 辅助脚本
tests/                  # 单元测试
tools/ffmpeg/           # ffmpeg 本地目录，二进制不提交
```

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

## 下载历史

历史记录保存在当前用户目录：

```text
%APPDATA%\BiliAudioDownloader\history.json
```

## 发布说明

GitHub 仓库只提交源代码和构建配置，不提交以下内容：

- `.venv`
- `build`
- `dist`
- ffmpeg 二进制
- 安装程序和便携 ZIP

正式发布时，请把安装程序和便携 ZIP 上传到 GitHub Releases。

## License

当前仓库未指定开源许可证。正式公开或允许他人再发布前，请先选择并添加合适的
`LICENSE` 文件。
