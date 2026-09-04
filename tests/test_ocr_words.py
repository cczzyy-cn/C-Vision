"""ocr 词框坐标提取（纯逻辑，PIL-free）测试。"""

import unittest
from types import SimpleNamespace

from cvision.ocr import _rect_to_xywh


class TestRectToXywh(unittest.TestCase):
    def _rect(self, x=10, y=20, width=30, height=40):
        # Windows/Microsoft.UI 矩形对象有 .x/.y/.width/.height
        return SimpleNamespace(x=x, y=y, width=width, height=height)

    def test_basic(self):
        d = _rect_to_xywh(self._rect(10, 20, 30, 40))
        self.assertEqual(d, {"x": 10, "y": 20, "w": 30, "h": 40})

    def test_zero(self):
        d = _rect_to_xywh(self._rect(0, 0, 0, 0))
        self.assertEqual(d, {"x": 0, "y": 0, "w": 0, "h": 0})

    def test_missing_attrs_fallbacks(self):
        d = _rect_to_xywh(None)
        self.assertEqual(d, {"x": 0, "y": 0, "w": 0, "h": 0})
        d = _rect_to_xywh(SimpleNamespace())
        self.assertEqual(d, {"x": 0, "y": 0, "w": 0, "h": 0})


if __name__ == "__main__":
    unittest.main()
