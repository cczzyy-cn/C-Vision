"""命令行入口：浏览网页标签自动切换后截图。

用法::

    python -m cvision.cli_tabs --port 9222 --out tabcaps
    python -m cvision.cli_tabs --launch --urls https://a.com https://b.com --headless --out tabcaps

- 无 ``--launch`` 时连接**已运行**的 Chromium（需 ``--remote-debugging-port=9222``）。
- ``--launch`` 时新建一个带调试端口的 Chrome/Edge（可用 ``--urls`` 提供页签），
  截图后会自动关闭该进程。
输出 JSON（每个页签的标题/URL/保存路径）。
"""

from __future__ import annotations

import argparse
import json
import sys

from cvision import tabs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="浏览器网页标签自动切换后截图（Chromium via CDP）")
    p.add_argument("--port", type=int, default=9222, help="CDP 调试端口（默认 9222）")
    p.add_argument("--out", default="tabcaps", help="截图保存目录（默认 tabcaps）")
    p.add_argument("--launch", action="store_true", help="新建一个带调试端口的浏览器实例")
    p.add_argument("--browser", default="chrome", choices=["chrome", "edge"], help="--launch 用哪个浏览器")
    p.add_argument("--headless", action="store_true", help="--launch 时用无头模式")
    p.add_argument("--urls", nargs="*", default=None, help="--launch 时打开的页面（多个）")
    p.add_argument("--full-page", action="store_true", help="整页截图（captureBeyondViewport=true）")
    args = p.parse_args(argv)

    proc = None
    try:
        if args.launch:
            proc = tabs.launch_browser(port=args.port, urls=args.urls, browser=args.browser, headless=args.headless)
            if not tabs.wait_ready(args.port):
                raise RuntimeError("浏览器调试端口未就绪")
        elif not tabs.list_tabs(args.port):
            print(
                f"警告：未能从 http://127.0.0.1:{args.port} 取到页签。"
                "Chrome/Edge 需以 --remote-debugging-port=<port> 启动；或加 --launch。",
                file=sys.stderr,
            )

        results = tabs.capture_all_tabs(args.port, args.out, full_page=args.full_page)
        sys.stdout.write(json.dumps({"tabs": results}, ensure_ascii=True, indent=2))
        return 0
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
