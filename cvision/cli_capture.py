"""cvision 命令行入口：截屏输出 Base64 data URL，或列出窗口。

供 DeepSeek Harness 插件等外部程序跨语言调用：:

    python -m cvision.cli_capture [--window 标题] [--maximize] [--region x,y,w,h] [--delay ms] [--format PNG]
    python -m cvision.cli_capture --list

- 不传 --window/--handle 时截整屏；输出 ``data:<mime>;base64,<data>`` 到 stdout。
- ``--list`` 则列出当前可见顶层窗口并输出 JSON 数组到 stdout（不截图）。
- ``--region`` 裁剪截图区域（相对该图的像素），``--delay`` 抓取前等待毫秒；
  输出前会缩放到附件限制（保证 saveImage 不被拒）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from cvision import capturer, encoding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="截屏输出 base64 data URL，或列出窗口")
    parser.add_argument("--list", action="store_true", help="列出可见窗口(JSON)，不截图")
    parser.add_argument("--window", default=None, help="窗口标题子串；留空则截全屏")
    parser.add_argument("--handle", type=int, default=None, help="窗口句柄")
    parser.add_argument("--maximize", action="store_true", help="先最大化目标窗口再截")
    parser.add_argument("--region", default=None, help="裁剪区域 x,y,w,h（像素，相对截图）")
    parser.add_argument("--delay", type=float, default=0, help="抓取前等待毫秒")
    parser.add_argument("--format", default="JPEG", help="JPEG/PNG/WEBP/GIF，默认 JPEG")
    args = parser.parse_args(argv)

    if args.list:
        # ensure_ascii=True：中文窗口标题转成 \uXXXX，输出纯 ASCII，避免 GBK 控制台
        # 编码问题；插件端 JSON.parse 会还原成正确的中文。
        sys.stdout.write(
            json.dumps([w.to_dict() for w in capturer.list_windows()], ensure_ascii=True)
        )
        return 0

    if args.delay:
        time.sleep(args.delay / 1000.0)

    if args.handle is not None or args.window:
        img = capturer.capture_window(handle=args.handle, title_substr=args.window, maximize=args.maximize)
    else:
        img = capturer.capture_screen()

    if args.region:
        img = encoding.crop_region(img, args.region)
    img = encoding.fit_for_attachment(img, format=args.format)

    sys.stdout.write(encoding.image_to_data_url(img, format=args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
