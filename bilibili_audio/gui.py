"""B 站音频下载器的 Tkinter 桌面界面。"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .history import HistoryRecord, HistoryStore
from .history_window import show_history_window
from .core import (
    AUDIO_FORMATS,
    SUPPORTED_BROWSERS,
    AudioDownloader,
    DownloadCancelled,
    DownloadOptions,
    DownloadResult,
    ProgressInfo,
    check_dependencies,
    get_bundled_ffmpeg_dir,
    get_default_output_dir,
    normalize_and_validate_url,
)


COLORS = {
    "bg": "#f3f6fb",
    "card": "#ffffff",
    "border": "#dce5ef",
    "text": "#203040",
    "muted": "#6c7b8b",
    "primary": "#1677ff",
    "primary_active": "#0f5bd7",
    "danger": "#d94b4b",
    "success": "#208a4b",
    "warning": "#b26a00",
    "header": "#153b5b",
}


def enable_windows_dpi_awareness() -> None:
    """让 Windows 高 DPI 屏幕上的界面和字体正确缩放。"""
    if os.name != "nt":
        return

    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        # 老版本 Windows 没有 shcore 时直接忽略。
        pass


class BilibiliAudioApp(tk.Tk):
    """第一版桌面应用主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.title("B站音频下载器")
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass
        self._setup_window_geometry()
        self.configure(bg=COLORS["bg"])

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(get_default_output_dir()))
        self.format_var = tk.StringVar(value="mp3")
        self.quality_var = tk.StringVar(value="0")
        self.browser_var = tk.StringVar(value="不使用")
        self.proxy_var = tk.StringVar()
        self.playlist_var = tk.BooleanVar(value=False)
        self.thumbnail_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="等待任务")
        self.progress_var = tk.DoubleVar(value=0.0)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event: threading.Event | None = None
        self.downloader: AudioDownloader | None = None
        self.task_running = False
        self._closed = False
        self.history_store = HistoryStore()

        self._configure_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._poll_events)
        self.after(300, self._show_dependency_warning)

    def _configure_style(self) -> None:
        """统一设置控件颜色和字体。"""
        self.option_add("*Font", ("Microsoft YaHei UI", 12))
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"], relief="flat")
        style.configure(
            "Card.TLabelframe",
            background=COLORS["card"],
            bordercolor=COLORS["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"])
        style.configure(
            "Primary.TButton",
            background=COLORS["primary"],
            foreground="#ffffff",
            borderwidth=0,
            padding=(22, 12),
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLORS["primary_active"]), ("disabled", "#9bbbe6")],
            foreground=[("disabled", "#f0f5fb")],
        )
        style.configure("Secondary.TButton", padding=(18, 11))
        style.configure("Danger.TButton", foreground=COLORS["danger"], padding=(14, 9))
        style.configure("Status.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#dce5ef",
            background=COLORS["primary"],
            bordercolor="#dce5ef",
            lightcolor=COLORS["primary"],
            darkcolor=COLORS["primary"],
        )

    def _setup_window_geometry(self) -> None:
        """按屏幕尺寸放大窗口，并适配 Windows 的 DPI 缩放。"""
        self.update_idletasks()
        try:
            dpi_scale = self.winfo_fpixels("1i") / 72.0
            if dpi_scale > 0:
                self.tk.call("tk", "scaling", dpi_scale)
        except tk.TclError:
            pass

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        available_width = max(900, screen_width - 40)
        available_height = max(600, screen_height - 80)

        window_width = min(max(1080, int(screen_width * 0.9)), available_width, 1600)
        window_height = min(max(720, int(screen_height * 0.88)), available_height, 1000)
        min_width = min(1080, window_width)
        min_height = min(700, window_height)
        x = max(0, (screen_width - window_width) // 2)
        y = max(0, (screen_height - window_height) // 2)

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(min_width, min_height)

    def _build_ui(self) -> None:
        """创建窗口布局。"""
        header = tk.Frame(self, bg=COLORS["header"], height=110)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg=COLORS["header"])
        header_inner.pack(fill="both", expand=True, padx=28, pady=18)
        tk.Label(
            header_inner,
            text="B站音频下载器",
            bg=COLORS["header"],
            fg="#ffffff",
            font=("Microsoft YaHei UI", 24, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header_inner,
            text="粘贴链接，提取音轨，保存成你喜欢的格式",
            bg=COLORS["header"],
            fg="#c9dff4",
            font=("Microsoft YaHei UI", 12),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self, style="App.TFrame", padding=(26, 20, 26, 20))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(4, weight=1, minsize=320)

        self._build_url_card(content)
        self._build_options_card(content)
        self._build_action_card(content)
        self._build_log_card(content)

        footer = ttk.Label(
            content,
            text="仅下载你有权保存的内容，并遵守 B 站服务条款与版权规定。",
            style="Status.TLabel",
            anchor="w",
        )
        footer.grid(row=5, column=0, sticky="ew", pady=(10, 0))

    def _build_url_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(
            parent,
            text="视频链接",
            style="Card.TLabelframe",
            padding=(12, 10, 12, 12),
        )
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        url_row = ttk.Frame(card, style="Card.TFrame")
        url_row.grid(row=0, column=0, sticky="ew")
        url_row.columnconfigure(0, weight=1)

        self.url_entry = ttk.Entry(
            url_row,
            textvariable=self.url_var,
            font=("Microsoft YaHei UI", 13),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            url_row,
            text="粘贴",
            style="Secondary.TButton",
            command=self._paste_url,
        ).grid(row=0, column=1)

        ttk.Label(
            card,
            text="支持完整 B 站链接、BV 号、av 号和 b23.tv 短链接。",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))

    def _build_options_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(
            parent,
            text="下载设置",
            style="Card.TLabelframe",
            padding=(12, 10, 12, 12),
        )
        card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(1, weight=1)
        card.columnconfigure(4, weight=0)

        ttk.Label(card, text="输出目录", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 10)
        )
        ttk.Entry(card, textvariable=self.output_var).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=(0, 10)
        )
        ttk.Button(
            card,
            text="浏览",
            style="Secondary.TButton",
            command=self._browse_output,
        ).grid(row=0, column=4, sticky="e", padx=(8, 0), pady=(0, 10))

        ttk.Label(card, text="输出格式", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 10)
        )
        ttk.Combobox(
            card,
            textvariable=self.format_var,
            values=AUDIO_FORMATS,
            state="readonly",
            width=10,
        ).grid(row=1, column=1, sticky="w", pady=(0, 10))

        ttk.Label(card, text="音频质量", style="Card.TLabel").grid(
            row=1, column=2, sticky="w", padx=(20, 10), pady=(0, 10)
        )
        ttk.Combobox(
            card,
            textvariable=self.quality_var,
            values=tuple(str(value) for value in range(10)),
            state="readonly",
            width=6,
        ).grid(row=1, column=3, sticky="w", pady=(0, 10))

        ttk.Label(card, text="Cookie 来源", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 10)
        )
        ttk.Combobox(
            card,
            textvariable=self.browser_var,
            values=("不使用",) + SUPPORTED_BROWSERS,
            state="readonly",
            width=12,
        ).grid(row=2, column=1, sticky="w", pady=(0, 10))
        ttk.Label(
            card,
            text="需要登录的视频才需要选择浏览器 Cookie。",
            style="Muted.TLabel",
        ).grid(row=2, column=2, columnspan=3, sticky="w", padx=(20, 0), pady=(0, 10))

        ttk.Label(card, text="代理地址", style="Card.TLabel").grid(
            row=3, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Entry(card, textvariable=self.proxy_var).grid(
            row=3, column=1, columnspan=3, sticky="ew"
        )
        ttk.Label(
            card,
            text="例如 http://127.0.0.1:7890，不需要可留空。",
            style="Muted.TLabel",
        ).grid(row=3, column=4, sticky="w", padx=(8, 0))

        check_row = ttk.Frame(card, style="Card.TFrame")
        check_row.grid(row=4, column=0, columnspan=5, sticky="w", pady=(11, 0))
        ttk.Checkbutton(
            check_row,
            text="下载合集/播放列表",
            variable=self.playlist_var,
        ).pack(side="left")
        ttk.Checkbutton(
            check_row,
            text="嵌入视频封面",
            variable=self.thumbnail_var,
        ).pack(side="left", padx=(24, 0))

    def _build_action_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(12, 10))
        card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=0, column=0, sticky="ew")
        button_row.columnconfigure(5, weight=1)

        self.start_button = ttk.Button(
            button_row,
            text="开始下载",
            style="Primary.TButton",
            command=self._start_download,
        )
        self.start_button.grid(row=0, column=0, sticky="w")

        self.cancel_button = ttk.Button(
            button_row,
            text="取消",
            style="Danger.TButton",
            command=self._cancel_download,
            state=tk.DISABLED,
        )
        self.cancel_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Button(
            button_row,
            text="打开文件夹",
            style="Secondary.TButton",
            command=self._open_output_folder,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        ttk.Button(
            button_row,
            text="历史记录",
            style="Secondary.TButton",
            command=self._open_history_window,
        ).grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Button(
            button_row,
            text="清空日志",
            style="Secondary.TButton",
            command=self._clear_log,
        ).grid(row=0, column=4, sticky="w", padx=(8, 0))

        self.progress_bar = ttk.Progressbar(
            card,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(14, 5))

        ttk.Label(
            card,
            textvariable=self.status_var,
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w")

    def _build_log_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(
            parent,
            text="运行日志",
            style="Card.TLabelframe",
            padding=(8, 8, 8, 8),
        )
        card.grid(row=4, column=0, sticky="nsew")
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            card,
            height=18,
            wrap="word",
            state="disabled",
            bg="#fbfcfe",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            font=("Microsoft YaHei UI", 12),
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.tag_configure("info", foreground=COLORS["text"])
        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.log_text.tag_configure("error", foreground=COLORS["danger"])

    def _paste_url(self) -> None:
        try:
            self.url_var.set(self.clipboard_get().strip())
        except tk.TclError:
            messagebox.showwarning("没有内容", "剪贴板里没有可粘贴的文本。")

    def _browse_output(self) -> None:
        selected = filedialog.askdirectory(
            title="选择音频保存目录",
            initialdir=self.output_var.get() or str(Path.home()),
        )
        if selected:
            self.output_var.set(selected)

    def _open_output_folder(self) -> None:
        path = Path(self.output_var.get().strip() or str(get_default_output_dir())).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("无法打开目录", str(exc))

    def _start_download(self) -> None:
        if self.task_running:
            return

        raw_url = self.url_var.get().strip()
        output_text = self.output_var.get().strip() or str(get_default_output_dir())

        try:
            url = normalize_and_validate_url(raw_url)
            output_dir = Path(output_text).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            browser = None if self.browser_var.get() == "不使用" else self.browser_var.get()
            options = DownloadOptions(
                url=url,
                output_dir=output_dir,
                audio_format=self.format_var.get(),
                audio_quality=int(self.quality_var.get()),
                cookies_from_browser=browser,
                proxy=self.proxy_var.get().strip() or None,
                playlist=self.playlist_var.get(),
                embed_thumbnail=self.thumbnail_var.get(),
            )
        except (ValueError, OSError) as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.progress_var.set(0)
        self.status_var.set("正在创建下载任务...")
        self._append_log("info", f"任务开始：{options.url}")
        self._append_log("info", f"输出目录：{options.output_dir}")

        self.cancel_event = threading.Event()
        self.downloader = AudioDownloader(self.cancel_event)
        self._set_running(True)

        worker = threading.Thread(
            target=self._download_worker,
            args=(options,),
            daemon=True,
        )
        worker.start()

    def _download_worker(self, options: DownloadOptions) -> None:
        """在后台线程执行下载，所有界面更新都通过队列回传。"""
        assert self.downloader is not None

        try:
            result = self.downloader.download(
                options,
                progress_callback=lambda info: self.events.put(("progress", info)),
                log_callback=lambda level, message: self.events.put(("log", (level, message))),
            )
            self.events.put(("done", result))
        except DownloadCancelled:
            self.events.put(("cancelled", None))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        """定期取出后台线程事件并更新界面。"""
        try:
            while True:
                event_name, payload = self.events.get_nowait()
                if event_name == "log":
                    level, message = payload  # type: ignore[misc]
                    self._append_log(str(level), str(message))
                elif event_name == "progress":
                    self._show_progress(payload)  # type: ignore[arg-type]
                elif event_name == "done":
                    self._handle_done(payload)  # type: ignore[arg-type]
                elif event_name == "error":
                    self._handle_error(str(payload))
                elif event_name == "cancelled":
                    self._handle_cancelled()
        except queue.Empty:
            pass

        if not self._closed:
            self.after(80, self._poll_events)

    def _show_progress(self, info: ProgressInfo) -> None:
        if info.percent is not None:
            self.progress_var.set(max(0.0, min(100.0, info.percent)))

        text = info.message
        if info.speed != "--":
            text += f"  |  {info.speed}"
        if info.eta != "--":
            text += f"  |  剩余 {info.eta}"
        self.status_var.set(text)

    def _open_history_window(self) -> None:
        """打开下载历史窗口。"""
        show_history_window(self, self.history_store)

    def _handle_done(self, result: DownloadResult) -> None:
        self._set_running(False)
        self.progress_var.set(100)
        self.status_var.set("下载完成")
        self.history_store.add(
            HistoryRecord(
                url=result.url,
                title=result.title or result.url,
                output_dir=str(result.output_dir),
                audio_format=result.audio_format,
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        self._append_log("success", f"文件已保存到：{result.output_dir}")
        messagebox.showinfo("下载完成", f"音频已经保存到：\n{result.output_dir}")

    def _handle_error(self, error: str) -> None:
        self._set_running(False)
        self.status_var.set("下载失败")
        self._append_log("error", error)
        messagebox.showerror("下载失败", error)

    def _handle_cancelled(self) -> None:
        self._set_running(False)
        self.progress_var.set(0)
        self.status_var.set("已取消")
        self._append_log("warning", "用户取消了当前任务。")

    def _cancel_download(self) -> None:
        if not self.task_running or self.cancel_event is None:
            return
        self.cancel_event.set()
        self.status_var.set("正在取消...")
        self._append_log("warning", "已发送取消请求，请稍等片刻。")

    def _set_running(self, running: bool) -> None:
        self.task_running = running
        self.start_button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.cancel_button.configure(state=tk.NORMAL if running else tk.DISABLED)

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "success": "[完成] ",
            "warning": "[提醒] ",
            "error": "[错误] ",
        }.get(level, "[信息] ")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {prefix}{message}\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _show_dependency_warning(self) -> None:
        missing = check_dependencies()
        if not missing:
            return
        message = "、".join(missing)
        self._append_log("warning", f"没有找到：{message}，音频转换可能失败。")
        messagebox.showwarning(
            "缺少依赖",
            f"没有找到：{message}\n\n请将 ffmpeg 和 ffprobe 加入 PATH 后再下载。",
        )

    def _on_close(self) -> None:
        if self.task_running:
            if not messagebox.askyesno("任务进行中", "下载还没结束，确定要退出吗？"):
                return
            if self.cancel_event is not None:
                self.cancel_event.set()

        self._closed = True
        self.destroy()


def run() -> None:
    """启动桌面程序。"""
    enable_windows_dpi_awareness()
    app = BilibiliAudioApp()

    # 打包后可用 --smoke-test 做隐藏启动检测，避免自动化测试时弹窗。
    if "--smoke-test" in sys.argv:
        if get_bundled_ffmpeg_dir() is None:
            raise RuntimeError("打包自检失败：没有找到自带的 ffmpeg")
        app.attributes("-alpha", 0.0)
        app.update()
        app.destroy()
        return

    app.mainloop()


if __name__ == "__main__":
    run()



