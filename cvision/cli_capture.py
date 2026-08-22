"""cvision 命令行入口：截屏并输出 Base64 data URL。

供 DeepSeek Harness 插件等外部程序跨语言调用：:

    python -m cvision.cli_capture [--window 标题] [--maximize] [--format JPEG]

不传 --window/--handle 时截整屏；输出 ``data:<mime>;base64,<data>`` 到 stdout。
"""

from __future__ import annotations

import argparse
import sys

from cvision import capturer, encoding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="截屏并输出 base64 data URL")
    parser.add_argument("--window", default=None, help="窗口标题子串；留空则截全屏")
    parser.add_argument("--handle", type=int, default=None, help="窗口句柄")
    parser.add_argument("--maximize", action="store_true", help="先最大化目标窗口再截")
    parser.add_argument("--format", default="JPEG", help="JPEG/PNG/WEBP/GIF，默认 JPEG")
    args = parser.parse_args(argv)

    if args.handle is not None or args.window:
        img = capturer.capture_window(handle=args.handle, title_substr=args.window, maximize=args.maximize)
    else:
        img = capturer.capture_screen()

    sys.stdout.write(encoding.image_to_data_url(img, format=args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
