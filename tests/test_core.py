"""下载核心基础测试。"""

import unittest

from bilibili_audio.core import DownloadOptions, normalize_and_validate_url


class UrlValidationTests(unittest.TestCase):
    def test_bv_id_is_normalized(self) -> None:
        self.assertEqual(
            normalize_and_validate_url("BV1xx411c7mD"),
            "https://www.bilibili.com/video/BV1xx411c7mD",
        )

    def test_short_url_is_normalized(self) -> None:
        self.assertEqual(
            normalize_and_validate_url("b23.tv/abc123"),
            "https://b23.tv/abc123",
        )

    def test_other_host_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_and_validate_url("https://example.com/video/123")


class DownloadOptionsTests(unittest.TestCase):
    def test_invalid_format_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DownloadOptions(url="BV1xx411c7mD", output_dir=".", audio_format="aac")

    def test_invalid_quality_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DownloadOptions(url="BV1xx411c7mD", output_dir=".", audio_quality=20)


if __name__ == "__main__":
    unittest.main()
