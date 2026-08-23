"""OCR 文本识别：对 PIL 图返回文字。

优先用 **Windows.Media.Ocr**（winsdk，免额外二进制、跟随系统语言包）；失败/未装时
回退 **pytesseract**（需额外安装 Tesseract）。两者都不可用时给出明确报错。
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from PIL import Image


def _ocr_via_windows(img: Image.Image) -> dict:
    import winsdk._winrt as wr
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage import StorageFile

    wr.init_apartment(wr.MTA)
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR 没有可用的识别语言")

    tmp = tempfile.mktemp(suffix=".png")
    img.save(tmp)
    try:
        async def _go():
            f = await StorageFile.get_file_from_path_async(tmp)
            stream = await f.open_read_async()
            dec = await BitmapDecoder.create_async(stream)
            sb = await dec.get_software_bitmap_async()
            return await engine.recognize_async(sb)

        res = asyncio.run(_go())
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return {"text": res.text, "lines": [line.text for line in res.lines]}


def _ocr_via_pytesseract(img: Image.Image) -> dict:
    import pytesseract

    text = pytesseract.image_to_string(img)
    return {"text": text, "lines": [ln for ln in text.split("\n") if ln.strip()]}


def ocr_image(img: Image.Image) -> dict:
    """识别图片文字，返回 ``{"text": str, "lines": [str]}``。"""
    try:
        return _ocr_via_windows(img)
    except Exception:
        pass
    try:
        return _ocr_via_pytesseract(img)
    except Exception:
        raise RuntimeError(
            "OCR 不可用：Windows.Media.Ocr(winsdk) 失败，且未安装 pytesseract/Tesseract。"
            "Windows 请 pip install winsdk（自带系统 OCR）；或 pip install pytesseract 并安装 Tesseract。"
        )
