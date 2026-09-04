"""OCR 文本识别：对 PIL 图返回文字（含词级边界框）。

优先用 **Windows.Media.Ocr**（winsdk，免额外二进制、跟随系统语言包）；失败/未装时
回退 **pytesseract**（需额外安装 Tesseract）。两者都不可用时给出明确报错。

返回结构（统一）::

    {
      "text": str,          # 全文
      "lines": [str],       # 按行
      "words": [            # 词级边界框（供 computer-use 精确定位点击点）
        {"text": str, "x": int, "y": int, "w": int, "h": int},
        ...
      ],
    }

``x/y/w/h`` 为相对被识别图片的像素坐标。
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from PIL import Image


def _rect_to_xywh(rect) -> dict:
    """把平台 Rect 对象转成 ``{x,y,w,h}``（Windows/Microsoft.UI 矩形）。"""
    try:
        return {
            "x": int(rect.x),
            "y": int(rect.y),
            "w": int(rect.width),
            "h": int(rect.height),
        }
    except Exception:
        return {"x": 0, "y": 0, "w": 0, "h": 0}


def _ocr_via_windows(img: Image.Image) -> dict:
    import winsdk._winrt as wr
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage import StorageFile

    wr.init_apartment(wr.MTA)
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR 没有可用的识别语言")

    # 用安全临时文件（NamedTemporaryFile，避免 mktemp 的可预测路径 / TOCTOU 风险）
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as _tmp:
        tmp = _tmp.name
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

    lines: list[str] = []
    words: list[dict] = []
    for line in res.lines:
        lines.append(line.text)
        for word in line.words:
            words.append(
                {"text": word.text, **_rect_to_xywh(word.bounding_rect)}
            )
    return {"text": res.text, "lines": lines, "words": words}


def _ocr_via_pytesseract(img: Image.Image) -> dict:
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    lines: list[str] = []
    words: list[dict] = []
    cur_line = -1
    cur_text: list[str] = []
    for i in range(len(data["text"] or [])):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        word = {
            "text": txt,
            "x": int(data.get("left", [])[i] if data.get("left") else 0),
            "y": int(data.get("top", [])[i] if data.get("top") else 0),
            "w": int(data.get("width", [])[i] if data.get("width") else 0),
            "h": int(data.get("height", [])[i] if data.get("height") else 0),
        }
        words.append(word)
        ln = int(data.get("line_num", [])[i] if data.get("line_num") else 0) + (
            int(data.get("par_num", [])[i] if data.get("par_num") else 0) * 1000
        )
        if ln != cur_line and cur_text:
            lines.append(" ".join(cur_text))
            cur_text = []
        cur_line = ln
        cur_text.append(txt)
    if cur_text:
        lines.append(" ".join(cur_text))

    # 顺序：pytesseract 的行/词序可能与 y 排序不同，稳一版——按 (y,x) 排序。
    words.sort(key=lambda w: (w["y"], w["x"]))
    return {"text": "\n".join(lines), "lines": lines, "words": words}


def ocr_image(img: Image.Image) -> dict:
    """识别图片文字，返回 ``{"text","lines","words"}``。

    优先 Windows.Media.Ocr，失败回退 pytesseract；两者皆不可用则报错。
    """
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
