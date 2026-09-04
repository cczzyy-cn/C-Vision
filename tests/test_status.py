"""status() 健康探针结构测试（平台无关：仅依赖 Pillow）。"""

import unittest

from cvision import status


class TestStatus(unittest.TestCase):
    def test_shape(self):
        s = status.status()
        for key in [
            "platform",
            "python",
            "cvison_dir",
            "backend",
            "backend_known",
            "backend_implemented",
            "ocr_engine",
            "input_capabilities",
            "deps",
            "ok",
        ]:
            self.assertIn(key, s, f"missing {key}")
        self.assertIsInstance(s["deps"], dict)
        self.assertIsInstance(s["input_capabilities"], list)
        self.assertIsInstance(s["ok"], bool)

    def test_backend_known(self):
        self.assertTrue(status.status()["backend_known"])


if __name__ == "__main__":
    unittest.main()
