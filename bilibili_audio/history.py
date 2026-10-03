"""下载历史记录存储。"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class HistoryRecord:
    """一条下载历史。"""

    url: str
    title: str
    output_dir: str
    audio_format: str
    finished_at: str


class HistoryStore:
    """使用 JSON 文件保存最近的下载记录。"""

    def __init__(self, max_records: int = 200, path: Path | None = None) -> None:
        self.max_records = max_records
        self.path = Path(path) if path is not None else self._default_path()
        self._lock = threading.Lock()

    @staticmethod
    def _default_path() -> Path:
        """把历史文件放到当前用户的 AppData 或配置目录。"""
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA") or Path.home())
        else:
            base = Path.home() / ".config"
        return base / "BiliAudioDownloader" / "history.json"

    def load(self) -> list[HistoryRecord]:
        """读取历史记录，文件损坏时返回空列表。"""
        with self._lock:
            raw_items = self._read_raw()

        records: list[HistoryRecord] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                records.append(
                    HistoryRecord(
                        url=str(item["url"]),
                        title=str(item.get("title") or item["url"]),
                        output_dir=str(item["output_dir"]),
                        audio_format=str(item.get("audio_format") or ""),
                        finished_at=str(item["finished_at"]),
                    )
                )
            except (KeyError, TypeError):
                continue
        return records

    def add(self, record: HistoryRecord) -> None:
        """把新记录放到最前面，并限制最大数量。"""
        with self._lock:
            raw_items = self._read_raw()
            raw_items.insert(0, asdict(record))
            raw_items = raw_items[: self.max_records]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(raw_items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.path)

    def clear(self) -> None:
        """清空历史文件。"""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[]", encoding="utf-8")

    def _read_raw(self) -> list[dict]:
        if not self.path.is_file():
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return []

        return data if isinstance(data, list) else []

