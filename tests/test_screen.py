"""screen_info 兜底形状（无显示环境也能返回稳定结构）测试。"""

import unittest

from cvision import screen

REQUIRED_KEYS = {"index", "x", "y", "width", "height", "primary", "scale"}


class TestScreenInfo(unittest.TestCase):
    def test_returns_list_of_displays(self):
        info = screen.screen_info()
        self.assertIsInstance(info, list)
        self.assertGreaterEqual(len(info), 1)
        for d in info:
            self.assertIsInstance(d, dict)
            self.assertTrue(REQUIRED_KEYS.issubset(d.keys()), d.keys())
            self.assertIsInstance(d["primary"], bool)
            self.assertIsInstance(d["scale"], float)

    def test_fallback_single_primary(self):
        # 在 headless/无显示环境走 PIL 兜底：仍应带 primary=True 的单屏结构。
        if screen.screen_info() and screen.screen_info()[0]["width"] == 0:
            # 无显示环境：单一兜底显示
            self.assertEqual(len(screen.screen_info()), 1)
            self.assertTrue(screen.screen_info()[0]["primary"])


if __name__ == "__main__":
    unittest.main()
