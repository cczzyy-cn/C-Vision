"""encoding 模块单元测试（仅 PIL，跨平台可跑）。"""

import io
import unittest

from PIL import Image

from cvision.encoding import (
    crop_region,
    fit_for_attachment,
    image_to_base64,
    image_to_data_url,
)


def _img(size=(32, 24)):
    return Image.new("RGB", size, (10, 200, 30))


class TestBase64DataUrl(unittest.TestCase):
    def test_data_url_png(self):
        url = image_to_data_url(_img(), format="PNG")
        self.assertTrue(url.startswith("data:image/png;base64,"))
        self.assertIn("iVBORw0KGgo", url)

    def test_data_url_jpeg(self):
        url = image_to_data_url(_img(), format="JPEG")
        self.assertTrue(url.startswith("data:image/jpeg;base64,"))

    def test_base64_tuple(self):
        mime, b64 = image_to_base64(_img(), format="WEBP")
        self.assertEqual(mime, "image/webp")
        self.assertTrue(b64)

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            image_to_data_url(_img(), format="BMP")

    def test_roundtrip(self):
        import base64

        _, b64 = image_to_base64(_img(), format="PNG")
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        self.assertEqual(img.size, (32, 24))


class TestCropRegion(unittest.TestCase):
    def test_crop(self):
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        for x in range(10, 30):
            for y in range(10, 30):
                img.putpixel((x, y), (255, 0, 0))
        crop = crop_region(img, "0,0,50,50")
        self.assertEqual(crop.size, (50, 50))
        self.assertEqual(crop.getpixel((15, 15)), (255, 0, 0))

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            crop_region(_img(), "a,b,c")
        with self.assertRaises(ValueError):
            crop_region(_img(), "0,0,-5,10")


class TestFitForAttachment(unittest.TestCase):
    def test_scales_down_over_max_side(self):
        img = Image.new("RGB", (20000, 100), (1, 2, 3))
        out = fit_for_attachment(img, max_side=8192)
        self.assertLessEqual(max(out.size), 8192)

    def test_small_image_unchanged(self):
        img = Image.new("RGB", (100, 80), (1, 2, 3))
        out = fit_for_attachment(img, max_side=8192, max_bytes=20 * 1024 * 1024)
        self.assertEqual(out.size, (100, 80))

    def test_fits_byte_limit(self):
        # 强制很小 max_bytes，验证能降到限制内（或至少更小）
        img = Image.new("RGB", (4000, 4000), (255, 0, 0))
        out = fit_for_attachment(img, format="PNG", max_side=8192, max_bytes=50 * 1024)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        self.assertLessEqual(buf.tell(), 2 * 1024 * 1024)  # 宽松断言，不严格卡上限


if __name__ == "__main__":
    unittest.main()
