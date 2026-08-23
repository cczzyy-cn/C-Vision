"""浏览器网页标签自动切换后截图（Chromium via CDP）。

原理：Chrome/Edge 等 Chromium 浏览器在启动时加 ``--remote-debugging-port=<端口>``
后，会暴露 CDP 端点。本模块用 ``/json/list`` 枚举页签，逐页签 ``Page.bringToFront``
（自动切换到该页）并 ``Page.captureScreenshot``（抓的是**页面内容**，而非浏览器窗口，
与前台/遮挡无关）。

依赖：``requests`` + ``websocket-client``（websocket-client）。

注意：要控制**已打开的** Chrome/Edge，需在其启动时就带 ``--remote-debugging-port``；
否则请用 ``launch_browser`` 新建一个带调试端口的实例（可带若干 URL 页签）。
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import subprocess
import tempfile
import time

import requests
import websocket

# 常见 Chromium 可执行文件路径（按优先级）
_CHROMIUM = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
}


def _targets(port: int, host: str = "127.0.0.1") -> list[dict]:
    r = requests.get(f"http://{host}:{port}/json/list", timeout=5)
    r.raise_for_status()
    return r.json()


def list_tabs(port: int = 9222, host: str = "127.0.0.1") -> list[dict]:
    """列出浏览器所有页面（type='page'）页签：[{index,id,title,url}]。"""
    out: list[dict] = []
    idx = 0
    for t in _targets(port, host):
        if t.get("type") != "page":
            continue
        out.append(
            {"index": idx, "id": t["id"], "title": t.get("title", ""), "url": t.get("url", "")}
        )
        idx += 1
    return out


def new_tab(port: int, url: str, host: str = "127.0.0.1") -> str:
    """用 CDP ``/json/new`` 打开一个新页签，返回新页签的 id。"""
    r = requests.put(f"http://{host}:{port}/json/new?{url}", timeout=5)
    r.raise_for_status()
    return r.json().get("id")


class _CdpClient:
    """对单个 target WebSocket 的极简 CDP 客户端。"""

    def __init__(self, ws_url: str, timeout: float = 30.0):
        self._ws = websocket.create_connection(ws_url, timeout=timeout)
        self._id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        mid = self._id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} 失败: {msg['error']}")
                return msg

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


def _sanitize(name: str, max_len: int = 40) -> str:
    name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", name).strip("_")
    return name[:max_len] or "tab"


def capture_tab(
    port: int, tab_id: str, out_dir: str, full_page: bool = False
) -> dict:
    """激活并截图一个页签，返回 {id,title,url,path}。"""
    target = next((t for t in _targets(port) if t["id"] == tab_id), None)
    if target is None:
        raise LookupError(f"页签 {tab_id} 不存在")
    ws_url = target["webSocketDebuggerUrl"]
    c = _CdpClient(ws_url)
    try:
        c.call("Page.enable")
        c.call("Page.bringToFront")  # 切换到该页
        resp = c.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": full_page})
    finally:
        c.close()
    png = base64.b64decode(resp["result"]["data"])

    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{_sanitize(target.get('title',''))}_{ts}.png"
    path = os.path.join(out_dir, fname)
    with open(path, "wb") as f:
        f.write(png)
    return {"id": tab_id, "title": target.get("title", ""), "url": target.get("url", ""), "path": path}


def capture_all_tabs(port: int, out_dir: str, full_page: bool = False) -> list[dict]:
    """依次切换到每个页签并截图，返回结果列表。"""
    results: list[dict] = []
    for tab in list_tabs(port):
        try:
            results.append(capture_tab(port, tab["id"], out_dir, full_page=full_page))
        except Exception as e:
            results.append({"id": tab["id"], "title": tab["title"], "url": tab["url"], "error": str(e)})
    return results


def launch_browser(
    port: int = 9222,
    urls: list[str] | None = None,
    browser: str = "chrome",
    headless: bool = False,
    profile: str | None = None,
) -> subprocess.Popen:
    """启动一个带 ``--remote-debugging-port`` 的 Chrome/Edge 实例，返回进程对象。

    需用临时/独立 user-data-dir（不能与被调试的既有实例共用同一 profile）。
    """
    paths = _CHROMIUM.get(browser, _CHROMIUM["chrome"])
    exe = next((p for p in paths if os.path.exists(p)), None)
    if exe is None:
        raise RuntimeError(f"未找到 {browser} 可执行文件")
    prof_dir = profile or tempfile.mkdtemp(prefix="cvision_browser_")
    cmd = [
        exe,
        f"--remote-debugging-port={port}",
        f"--remote-allow-origins=*",  # 允许任意 origin 的 WS 连接（否则 CDP 客户端 403）
        f"--user-data-dir={prof_dir}",
        "--no-first-run", "--no-default-browser-check", "--disable-gpu",
    ]
    if headless:
        cmd.append("--headless=new")
    if urls:
        cmd.extend(urls)
    else:
        cmd.append("about:blank")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ready(port: int, host: str = "127.0.0.1", timeout: float = 20.0) -> bool:
    """等待浏览器调试端口就绪。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            requests.get(f"http://{host}:{port}/json/version", timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False
