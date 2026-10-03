"""下载历史记录窗口。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .history import HistoryRecord, HistoryStore


def show_history_window(parent: tk.Tk, store: HistoryStore) -> None:
    """打开下载历史窗口。"""
    records = store.load()
    window = tk.Toplevel(parent)
    window.title("下载历史")
    window.geometry("1080x560")
    window.minsize(820, 420)
    window.transient(parent)

    frame = ttk.Frame(window, style="App.TFrame", padding=14)
    frame.pack(fill="both", expand=True)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    tree_frame = ttk.Frame(frame, style="App.TFrame")
    tree_frame.grid(row=0, column=0, sticky="nsew")
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    columns = ("time", "title", "format", "dir")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
    tree.heading("time", text="完成时间")
    tree.heading("title", text="标题")
    tree.heading("format", text="格式")
    tree.heading("dir", text="输出目录")
    tree.column("time", width=150, anchor="center", stretch=False)
    tree.column("title", width=360, anchor="w")
    tree.column("format", width=80, anchor="center", stretch=False)
    tree.column("dir", width=450, anchor="w")
    tree.grid(row=0, column=0, sticky="nsew")

    vertical = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    horizontal = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    for record in records:
        tree.insert(
            "",
            "end",
            values=(record.finished_at, record.title, record.audio_format, record.output_dir),
        )

    def selected_record() -> HistoryRecord | None:
        selection = tree.selection()
        if not selection:
            return None
        index = tree.index(selection[0])
        if 0 <= index < len(records):
            return records[index]
        return None

    def open_selected() -> None:
        record = selected_record()
        if record is None:
            messagebox.showwarning("没有选择", "请先选择一条历史记录。", parent=window)
            return

        try:
            path = Path(record.output_dir)
            path.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("无法打开目录", str(exc), parent=window)

    def copy_selected() -> None:
        record = selected_record()
        if record is None:
            messagebox.showwarning("没有选择", "请先选择一条历史记录。", parent=window)
            return

        parent.clipboard_clear()
        parent.clipboard_append(record.url)
        parent.update_idletasks()
        messagebox.showinfo("已复制", "视频链接已复制到剪贴板。", parent=window)

    def clear_history() -> None:
        if not messagebox.askyesno("清空历史", "确定要清空全部下载历史吗？", parent=window):
            return

        store.clear()
        records.clear()
        for item in tree.get_children():
            tree.delete(item)

    tree.bind("<Double-1>", lambda _event: open_selected())

    button_row = ttk.Frame(frame, style="App.TFrame")
    button_row.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    ttk.Button(
        button_row,
        text="打开选中目录",
        style="Primary.TButton",
        command=open_selected,
    ).pack(side="left")
    ttk.Button(
        button_row,
        text="复制选中链接",
        style="Secondary.TButton",
        command=copy_selected,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        button_row,
        text="清空历史",
        style="Danger.TButton",
        command=clear_history,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        button_row,
        text="关闭",
        style="Secondary.TButton",
        command=window.destroy,
    ).pack(side="right")

    ttk.Label(
        frame,
        text=f"历史文件：{store.path}",
        style="Status.TLabel",
    ).grid(row=2, column=0, sticky="w", pady=(8, 0))
