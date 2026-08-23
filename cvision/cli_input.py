"""命令行入口：模拟一次用户级输入（鼠标/键盘/窗口聚焦）。

用法::

    python -m cvision.cli_input --focus "Google Chrome"
    python -m cvision.cli_input --click 400 300 --button left
    python -m cvision.cli_input --double 400 300
    python -m cvision.cli_input --move 200 200
    python -m cvision.cli_input --scroll 500 400 -3      # 在(500,400)向下滚3格
    python -m cvision.cli_input --type "Hello"
    python -m cvision.cli_input --keys "ctrl+l"

每次只执行一个动作，输出 JSON ``{"ok": true}``。调用前请先 ``see`` 确认目标。
"""

from __future__ import annotations

import argparse
import json
import sys

from cvision import input as inp


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="模拟用户级输入（鼠标/键盘/聚焦）")
    p.add_argument("--focus", default=None, help="按标题子串把窗口置前")
    p.add_argument("--click", nargs=2, type=int, metavar=("X", "Y"), help="鼠标单击屏幕坐标(绝对像素)")
    p.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p.add_argument("--double", nargs=2, type=int, metavar=("X", "Y"), help="鼠标双击")
    p.add_argument("--move", nargs=2, type=int, metavar=("X", "Y"), help="移动鼠标到屏幕坐标")
    p.add_argument("--scroll", nargs=3, type=int, metavar=("X", "Y", "DY"), help="在 (X,Y) 滚动 DY 格")
    p.add_argument("--type", dest="text", default=None, help="输入/键入文本")
    p.add_argument("--keys", default=None, help="发送快捷键，如 ctrl+l / enter / ctrl+shift+t")
    args = p.parse_args(argv)

    if args.focus:
        inp.focus_window(args.focus)
    elif args.click:
        inp.click(args.click[0], args.click[1], button=args.button)
    elif args.double:
        inp.click(args.double[0], args.double[1], button=args.button, double=True)
    elif args.move:
        inp.move(args.move[0], args.move[1])
    elif args.scroll:
        inp.scroll(args.scroll[0], args.scroll[1], dx=0, dy=args.scroll[2])
    elif args.text is not None:
        inp.type_text(args.text)
    elif args.keys:
        inp.press_keys(args.keys)
    else:
        raise SystemExit("未指定动作：--focus/--click/--double/--move/--scroll/--type/--keys 之一")

    sys.stdout.write(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
