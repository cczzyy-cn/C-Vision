"""detect 模块纯逻辑单元测试（仅 PIL，不依赖 win32/窗口/网络）。

可在 Linux CI 上运行（`pip install Pillow` 后 `python -m unittest discover -s tests`）。
"""

import unittest

from PIL import Image

from cvision.detect import is_blank_image, looks_like_gpu_class


def _solid(color, size=(64, 64)):
    return Image.new("RGB", size, color)


def _content_image():
    """白色底 + 红色方块与深色文字，方差显著，应判定为有内容。"""
    img = Image.new("RGB", (64, 64), (255, 255, 255))
    for x in range(10, 40):
        for y in range(10, 40):
            img.putpixel((x, y), (255, 0, 0))
    for x in range(5, 60):
        for y in range(50, 55):
            img.putpixel((x, y), (10, 10, 10))
    return img


def _gradient_image():
    """水平渐变，非纯色，应判定为有内容。"""
    img = Image.new("L", (64, 64), 0)
    px = img.load()
    for x in range(64):
        for y in range(64):
            px[x, y] = int(255 * x / 63)
    return img


def _partial_blank_image():
    """≈98% 纯白 + 一小块黑角：方差被拉高，但主色覆盖极高 → 应判定为空白。"""
    img = Image.new("RGB", (64, 64), (255, 255, 255))
    for x in range(8):
        for y in range(8):
            img.putpixel((x, y), (0, 0, 0))
    return img


class TestIsBlankImage(unittest.TestCase):
    def test_none_is_blank(self):
        self.assertTrue(is_blank_image(None))

    def test_solid_white_is_blank(self):
        self.assertTrue(is_blank_image(_solid((255, 255, 255))))

    def test_solid_black_is_blank(self):
        self.assertTrue(is_blank_image(_solid((0, 0, 0))))

    def test_solid_color_is_blank(self):
        self.assertTrue(is_blank_image(_solid((120, 30, 200))))

    def test_real_content_not_blank(self):
        self.assertFalse(is_blank_image(_content_image()))

    def test_gradient_not_blank(self):
        self.assertFalse(is_blank_image(_gradient_image()))

    def test_partial_blank_dominant_color(self):
        self.assertTrue(is_blank_image(_partial_blank_image()))


class TestGpuClassDetection(unittest.TestCase):
    def test_opus_host(self):
        self.assertTrue(looks_like_gpu_class("OrpheusBrowserHost"))

    def test_chrome_widget(self):
        self.assertTrue(looks_like_gpu_class("Chrome_WidgetWin_1"))

    def test_electron(self):
        self.assertTrue(looks_like_gpu_class("Electron"))

    def test_cef(self):
        self.assertTrue(looks_like_gpu_class("CefBrowserWindow"))

    def test_uwp(self):
        self.assertTrue(looks_like_gpu_class("ApplicationFrameWindow"))

    def test_normal_class(self):
        self.assertFalse(looks_like_gpu_class("Notepad"))

    def test_empty_or_none(self):
        self.assertFalse(looks_like_gpu_class(""))
        self.assertFalse(looks_like_gpu_class(None))


if __name__ == "__main__":
    unittest.main()
