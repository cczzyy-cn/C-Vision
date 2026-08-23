"""命令行入口：截屏 -> OCR -> 输出 JSON 文本。

用法::

    python -m cvision.cli_ocr [--window 标题] [--maximize] [--region x,y,w,h] [--delay ms]

不传 --window/--handle 时对整屏做 OCR；输出 ``{"text": ..., "lines": [...]}`` 到 stdout。
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from cvision import capturer, encoding, ocr


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="截屏并 OCR，输出 JSON 文本")
    p.add_argument("--window", default=None, help="窗口标题子串；留空则对整屏 OCR")
    p.add_argument("--handle", type=int, default=None, help="窗口句柄")
    p.add_argument("--maximize", action="store_true", help="先最大化目标窗口再截")
    p.add_argument("--region", default=None, help="裁剪区域 x,y,w,h（像素，相对截图）")
    p.add_argument("--delay", type=float, default=0, help="抓取前等待毫秒")
    args = p.parse_args(argv)

    if args.delay:
        time.sleep(args.delay / 1000.0)

    if args.handle is not None or args.window:
        img = capturer.capture_window(handle=args.handle, title_substr=args.window, maximize=args.maximize)
    else:
        img = capturer.capture_screen()
    if args.region:
        img = encoding.crop_region(img, args.region)

    result = ocr.ocr_image(img)
    sys.stdout.write(
        json.dumps({"text": result.get("text", ""), "lines": result.get("lines", [])}, ensure_ascii=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
