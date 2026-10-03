"""B 站音频下载核心。

这里只负责 URL 校验、yt-dlp 配置、下载进度和取消逻辑，
不直接依赖 Tkinter，方便以后替换成 PySide6 或其他界面。
"""

from __future__ import annotations

import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import yt_dlp


SUPPORTED_HOSTS = ("bilibili.com", "b23.tv", "bilibili.tv")
AUDIO_FORMATS = ("mp3", "m4a", "opus", "flac", "wav")
SUPPORTED_BROWSERS = ("edge", "chrome", "firefox", "brave", "opera", "vivaldi")
VIDEO_ID_PATTERN = re.compile(r"^(?:BV[0-9A-Za-z]{10}|av\d+)$", re.IGNORECASE)


class DownloadCancelled(Exception):
    """用户主动取消下载时抛出的异常。"""


@dataclass(slots=True)
class DownloadOptions:
    """一次音频下载任务需要的全部参数。"""

    url: str
    output_dir: Path
    audio_format: str = "mp3"
    audio_quality: int = 0
    cookies_file: Path | None = None
    cookies_from_browser: str | None = None
    proxy: str | None = None
    playlist: bool = False
    embed_thumbnail: bool = False
    write_metadata: bool = True
    ffmpeg_location: Path | None = None

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir).expanduser()
        if self.cookies_file:
            self.cookies_file = Path(self.cookies_file).expanduser()
        if self.ffmpeg_location:
            self.ffmpeg_location = Path(self.ffmpeg_location).expanduser()

        if self.audio_format not in AUDIO_FORMATS:
            raise ValueError(f"不支持的音频格式：{self.audio_format}")
        if not 0 <= self.audio_quality <= 9:
            raise ValueError("音频质量必须在 0 到 9 之间")


@dataclass(slots=True)
class ProgressInfo:
    """传给界面的统一进度对象。"""

    phase: str
    message: str
    percent: float | None = None
    speed: str = "--"
    eta: str = "--"


@dataclass(slots=True)
class DownloadResult:
    """下载结束后的结果。"""

    success: bool
    title: str
    output_dir: Path
    url: str
    audio_format: str


def normalize_and_validate_url(raw_url: str) -> str:
    """把 BV 号、短链接或完整 URL 统一成 yt-dlp 可识别的地址。"""
    url = raw_url.strip()
    if not url:
        raise ValueError("请输入 B 站视频链接")

    if VIDEO_ID_PATTERN.fullmatch(url):
        url = f"https://www.bilibili.com/video/{url}"
    elif "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    is_supported = any(
        host == supported or host.endswith("." + supported)
        for supported in SUPPORTED_HOSTS
    )

    if parsed.scheme not in {"http", "https"} or not is_supported:
        raise ValueError(f"不是有效的 B 站链接：{raw_url}")

    return url


def get_default_output_dir() -> Path:
    """返回适合普通用户使用的默认输出目录。"""
    return Path.home() / "Music" / "B站音频"


def get_bundled_ffmpeg_dir() -> Path | None:
    """返回项目自带的 ffmpeg 目录。"""
    bundled_dir = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg" / "bin"
    if (bundled_dir / "ffmpeg.exe").is_file() and (bundled_dir / "ffprobe.exe").is_file():
        return bundled_dir
    return None


def check_dependencies() -> list[str]:
    """检查运行时需要的外部程序。"""
    if get_bundled_ffmpeg_dir() is not None:
        return []

    missing: list[str] = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("ffprobe"):
        missing.append("ffprobe")
    return missing


def _format_speed(value: object) -> str:
    """把字节每秒转换成容易阅读的速度。"""
    if not isinstance(value, (int, float)) or value <= 0:
        return "--"

    units = ("B/s", "KB/s", "MB/s", "GB/s")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return "--"


def _format_eta(value: object) -> str:
    """把剩余秒数转换成时分秒。"""
    if not isinstance(value, (int, float)) or value < 0:
        return "--"

    seconds = int(value)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class _YtdlpLogger:
    """把 yt-dlp 日志转发给界面，而不是打印到控制台。"""

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        self._callback = callback

    def debug(self, message: str) -> None:
        # yt-dlp 的 debug 信息通常很吵，第一版只保留非调试内容。
        if not message.startswith("[debug]"):
            self._callback("info", message)

    def warning(self, message: str) -> None:
        self._callback("warning", message)

    def error(self, message: str) -> None:
        self._callback("error", message)


class AudioDownloader:
    """封装 yt-dlp 的音频下载器。"""

    def __init__(self, cancel_event: threading.Event | None = None) -> None:
        self.cancel_event = cancel_event or threading.Event()

    def cancel(self) -> None:
        """请求取消当前下载。"""
        self.cancel_event.set()

    def download(
        self,
        options: DownloadOptions,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> DownloadResult:
        """执行下载，阻塞当前线程；界面需要在线程中调用。"""
        progress_callback = progress_callback or (lambda _info: None)
        log_callback = log_callback or (lambda _level, _message: None)

        url = normalize_and_validate_url(options.url)
        output_dir = options.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_dir = self._resolve_ffmpeg_dir(options)
        postprocessors: list[dict] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.audio_format,
                "preferredquality": str(options.audio_quality),
            }
        ]

        if options.write_metadata:
            postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

        if options.embed_thumbnail:
            postprocessors.append(
                {
                    "key": "EmbedThumbnail",
                    "already_have_thumbnail": True,
                }
            )

        ydl_options: dict = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / "%(title).100B [%(id)s].%(ext)s"),
            "noplaylist": not options.playlist,
            "windowsfilenames": True,
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
            "file_access_retries": 3,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": 4,
            "postprocessors": postprocessors,
            "progress_hooks": [self._build_progress_hook(progress_callback)],
            "postprocessor_hooks": [self._build_postprocessor_hook(progress_callback)],
            "logger": _YtdlpLogger(log_callback),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "ffmpeg_location": str(ffmpeg_dir),
        }

        if options.embed_thumbnail:
            ydl_options["writethumbnail"] = True

        if options.cookies_file:
            cookie_path = options.cookies_file.resolve()
            if not cookie_path.is_file():
                raise FileNotFoundError(f"Cookie 文件不存在：{cookie_path}")
            ydl_options["cookiefile"] = str(cookie_path)

        if options.cookies_from_browser:
            browser = options.cookies_from_browser.lower()
            if browser not in SUPPORTED_BROWSERS:
                raise ValueError(f"不支持的浏览器 Cookie 来源：{browser}")
            ydl_options["cookiesfrombrowser"] = (browser,)

        if options.proxy:
            ydl_options["proxy"] = options.proxy

        log_callback("info", f"开始解析：{url}")

        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=True)

            if self.cancel_event.is_set():
                raise DownloadCancelled

            title = ""
            if isinstance(info, dict):
                title = str(info.get("title") or "")

            progress_callback(
                ProgressInfo(
                    phase="completed",
                    message="处理完成",
                    percent=100.0,
                )
            )
            log_callback("success", f"下载完成：{title or url}")
            return DownloadResult(
                success=True,
                title=title,
                output_dir=output_dir,
                url=url,
                audio_format=options.audio_format,
            )

        except DownloadCancelled:
            raise
        except yt_dlp.utils.DownloadError as exc:
            if self.cancel_event.is_set():
                raise DownloadCancelled from exc
            raise RuntimeError(str(exc)) from exc

    def _resolve_ffmpeg_dir(self, options: DownloadOptions) -> Path:
        """确认 ffmpeg 和 ffprobe 的位置。"""
        if options.ffmpeg_location:
            location = options.ffmpeg_location.resolve()
            if location.is_file():
                return location.parent
            if location.is_dir():
                return location
            raise FileNotFoundError(f"ffmpeg 路径不存在：{location}")

        # 优先使用项目自带的 ffmpeg，复制或打包后仍然可以独立运行。
        bundled_dir = get_bundled_ffmpeg_dir()
        if bundled_dir is not None:
            return bundled_dir

        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise RuntimeError(
                "没有找到 ffmpeg 或 ffprobe，请先安装并加入 PATH，"
                "或者在下载配置中指定 ffmpeg_location。"
            )

        return Path(ffmpeg).resolve().parent

    def _build_progress_hook(self, callback: Callable[[ProgressInfo], None]):
        """构造 yt-dlp 下载进度回调。"""

        def hook(data: dict) -> None:
            if self.cancel_event.is_set():
                raise DownloadCancelled

            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes") or 0
                percent = None
                if isinstance(total, (int, float)) and total > 0:
                    percent = min(100.0, float(downloaded) / float(total) * 100)

                speed = _format_speed(data.get("speed"))
                eta = _format_eta(data.get("eta"))
                callback(
                    ProgressInfo(
                        phase="downloading",
                        message="正在下载音轨",
                        percent=percent,
                        speed=speed,
                        eta=eta,
                    )
                )
            elif status == "finished":
                callback(
                    ProgressInfo(
                        phase="processing",
                        message="音轨下载完成，正在转换格式",
                        percent=100.0,
                    )
                )

        return hook

    def _build_postprocessor_hook(self, callback: Callable[[ProgressInfo], None]):
        """构造 ffmpeg 后处理阶段回调。"""

        def hook(data: dict) -> None:
            if self.cancel_event.is_set():
                raise DownloadCancelled

            if data.get("status") != "started":
                return

            name = str(data.get("postprocessor") or "")
            if "ExtractAudio" in name:
                message = "正在使用 ffmpeg 转换音频"
            elif "Metadata" in name:
                message = "正在写入音频元数据"
            elif "Thumbnail" in name:
                message = "正在嵌入视频封面"
            else:
                message = f"正在处理：{name or '音频'}"

            callback(ProgressInfo(phase="processing", message=message))

        return hook



