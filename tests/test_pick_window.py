"""pick_window 纯逻辑单元测试（仅依赖 Window 数据类，不依赖 win32/窗口）。

覆盖：定位“看 —> 抓”语义的核心——精确标题优先于子串匹配（避免“微信”误中标题含
它的浏览器标签）、非最小化优先、无命中返回 None。
"""

import unittest

from cvision.capture.base import Window, pick_window


def _w(handle, title, left, top, width, height):
    return Window(handle, title, left, top, width, height)


class TestPickWindow(unittest.TestCase):
    def test_exact_title_beats_substring(self):
        # “微信”必须命中标题恰为“微信”的微信主窗，而不是标题里含“微信”的浏览器标签
        browser = _w(67994, "安装微信图片插件 — DeepSeek Harness - Google Chrome", -8, -8, 2576, 1408)
        wechat = _w(68420, "微信", 1885, 240, 1355, 998)
        self.assertEqual(pick_window([browser, wechat], "微信").handle, 68420)

    def test_substring_match(self):
        a = _w(1, "Visual Studio Code", 100, 100, 800, 600)
        b = _w(2, "Notepad", 200, 200, 400, 300)
        self.assertEqual(pick_window([a, b], "studio").handle, 1)
        self.assertEqual(pick_window([a, b], "visual").handle, 1)
        self.assertIsNone(pick_window([a, b], "zzz"))

    def test_non_minimized_preferred(self):
        mini = _w(1, "Notepad", -32000, -32000, 160, 28)
        full = _w(2, "Notepad", 100, 100, 800, 600)
        self.assertEqual(pick_window([mini, full], "Notepad").handle, 2)

    def test_case_insensitive(self):
        a = _w(1, "Google Chrome", 0, 0, 800, 600)
        self.assertEqual(pick_window([a], "google chrome").handle, 1)
        self.assertEqual(pick_window([a], "GOOGLE").handle, 1)

    def test_no_match_returns_none(self):
        self.assertIsNone(pick_window([_w(1, "A", 0, 0, 10, 10)], "zzz"))

    def test_empty_or_none_title(self):
        self.assertIsNone(pick_window([_w(1, "A", 0, 0, 10, 10)], ""))
        self.assertIsNone(pick_window([_w(1, "A", 0, 0, 10, 10)], None))


if __name__ == "__main__":
    unittest.main()
