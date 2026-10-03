"""下载历史存储测试。"""

import tempfile
import unittest
from pathlib import Path

from bilibili_audio.history import HistoryRecord, HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def test_add_load_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = HistoryStore(path=Path(temp_dir) / "history.json")
            record = HistoryRecord(
                url="https://www.bilibili.com/video/BV1xx411c7mD",
                title="测试音频",
                output_dir=temp_dir,
                audio_format="mp3",
                finished_at="2026-10-04 12:00:00",
            )

            store.add(record)
            records = store.load()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].title, "测试音频")

            store.clear()
            self.assertEqual(store.load(), [])


if __name__ == "__main__":
    unittest.main()
