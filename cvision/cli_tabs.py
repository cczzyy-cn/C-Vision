"""命令行入口：浏览网页标签自动切换后截图。

用法::

    python -m cvision.cli_tabs --port 9222 --out tabcaps
    python -m cvision.cli_tabs --launch --urls https://a.com https://b.com --headless --out tabcaps

- 无 ``--launch`` 时连接**已运行**的 Chromium（需 ``--remote-debugging-port=<port>``）。
- ``--launch`` 时新建一个带调试端口的 Chrome/Edge（可用 ``--urls`` 提供页签），
  截图后会自动关闭该进程。此时若未显式给 ``--port``，会自动挑一个空闲端口以避免冲突。
输出 JSON（每个页签的标题/URL/保存路径）。
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time

from cvision import tabs


def _free_port() -> int:
    """挑一个空闲端口（绑定 0 由系统分配）。"""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="浏览器网页标签自动切换后截图（Chromium via CDP）")
    p.add_argument("--port", type=int, default=None, help="CDP 调试端口；--launch 时留空则自动挑空闲端口")
    p.add_argument("--out", default="tabcaps", help="截图保存目录（默认 tabcaps）")
    p.add_argument("--launch", action="store_true", help="新建一个带调试端口的浏览器实例")
    p.add_argument("--browser", default="chrome", choices=["chrome", "edge"], help="--launch 用哪个浏览器")
    p.add_argument("--headless", action="store_true", help="--launch 时用无头模式")
    p.add_argument("--urls", nargs="*", default=None, help="--launch 时打开的页面（多个）")
    p.add_argument("--url-substr", default=None, help="连接已有浏览器时，按 URL 子串定位单个目标页签并只截它")
    p.add_argument("--title-substr", default=None, help="连接已有浏览器时，按标题子串定位单个目标页签并只截它")
    p.add_argument("--full-page", action="store_true", help="整页截图（captureBeyondViewport=true）")
    args = p.parse_args(argv)

    port = args.port
    proc = None
    try:
        if args.launch:
            if port is None:
                port = _free_port()
            # 无头 Chrome 不支持命令行多 target：这里只以 about:blank 启动，再用 CDP 逐个开 URL
            proc = tabs.launch_browser(port=port, browser=args.browser, headless=args.headless)
            if not tabs.wait_ready(port, timeout=25):
                raise RuntimeError("浏览器调试端口未就绪（--launch 时若反复失败，可先清理残留 chrome 进程）")
            if args.urls:
                for u in args.urls:
                    tabs.new_tab(port, u)
                time.sleep(1.0)  # 给新页签一点加载时间
                # 关掉初始 about:blank，避免多出一张空白图
                for t in tabs.list_tabs(port):
                    if t.get("url", "").startswith("about:blank"):
                        try:
                            tabs.close_tab(port, t["id"])
                        except Exception:
                            pass
        else:
            if port is None:
                port = 9222
            # 有目标定位：只截命中的单个页签；否则截全部页签
            target = args.url_substr or args.title_substr
            if target:
                tab = tabs.find_tab(port, url_substr=args.url_substr, title_substr=args.title_substr)
                if tab is None:
                    raise RuntimeError(
                        f"未在 http://127.0.0.1:{port} 的浏览器页签中找到匹配（url={args.url_substr}, title={args.title_substr}）。"
                        "请确认浏览器已带 --remote-debugging-port 启动，且该页已打开。"
                    )
                results = [tabs.capture_tab(port, tab["id"], args.out, full_page=args.full_page)]
            elif not tabs.list_tabs(port):
                print(
                    f"警告：未能从 http://127.0.0.1:{port} 取到页签。"
                    "Chrome/Edge 需以 --remote-debugging-port=<port> 启动；或加 --launch。",
                    file=sys.stderr,
                )
                results = []
            else:
                results = tabs.capture_all_tabs(port, args.out, full_page=args.full_page)

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
