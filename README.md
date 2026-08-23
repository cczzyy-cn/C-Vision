# Vision · DeepSeek Harness (DSH) 视觉插件

给 DeepSeek Harness 的 agent 提供**自动视觉能力**：模型调用 `see` 工具，得到一张**真实截图（作为图片）**，从而**原生看到画面**（描述、识别截图文字、读图表/文档）。

这是一个 **DSH 组合包（bundle）**，通过 `dsh plugin add` 安装。插件注册 `see` 工具 → 跨语言调用**包内捆绑的 Python 版 cvision** 截屏 → 写入 Harness 附件服务（`ctx.attachments.saveImage`）→ 以 **`image` ContentBlock** 返回 → 模型直接看到图片。

## 分发：自带 Python 版 cvision

插件**打包了 Python 版 cvision**（目录 `cvision/`）与 `requirements.txt`。因此：

- 安装者**无需克隆 / 拷贝本仓库**，也**不需要设置 `CVISION_DIR` 指向某个绝对路径**；
- `CVISION_DIR` 默认解析为**本插件安装目录**（`import.meta.url` 推导），即包内捆绑版；
- 目标机器只需有 **Python 3**，并执行一次依赖安装。

> 注意：`cvision/` 是随包复制的源码快照。仓库根 `cvision/` 的改动不会自动同步到包内；
> 升级时重新拷贝 → 重新 `dsh plugin add` 即可。

## 构建（仅当改了 `src/*.ts` 才需要）

插件入口 `lib/index.js` 由 `src/index.ts` 编译而来（DSH 运行时只加载 JS）。仓库已提交
编译好的 `lib/index.js`，装包即可用；若你改了 `src/index.ts`，请在本目录执行：

```bash
npm run build        # 即 tsc -p tsconfig.json，重生成 lib/index.js
```

## CI / 发布

- **CI**（`.github/workflows/ci.yml`）：每次 `push` / `pull_request` 自动：
  - `npm ci && npm run build`，并校验 `lib/` 编译产物与提交一致（改了 `src` 却忘编译会失败）；
  - 跑 Python 纯逻辑单测（`test_detect.py`，仅需 Pillow，Linux 可运行）。
- **发布**：打一个 `v*` 标签（如 `v0.1.2`）推送到 GitHub，CI 在构建+测试通过后自动
  `npm pack` 出 `vision-<version>.tgz` 并创建 GitHub Release 上传该产物，
  可直接 `dsh plugin add ./vision-0.1.2.tgz` 安装。

```bash
git tag v0.1.2 && git push origin v0.1.2
```

## 前提

- 目标机器：Windows 桌面 + 有 Python 3（插件靠 `child_process` 调 `python -m cvision.cli_capture`）。
- 安装依赖（依赖文件已随插件打包）：

```powershell
python -m pip install -r requirements.txt
```

> 放到插件目录下执行，或先 `cd` 到该目录。

## 安装（DSH Desktop）

在 DSH Desktop 的终端（profile 目录）里，从插件目录执行：

```powershell
dsh plugin add <此目录的绝对路径>
```

例如（PowerShell）：

```powershell
dsh plugin add C:\Users\14339\Desktop\git\C-Vision\C-Vision
```

然后**重启 DSH Desktop**。用 `dsh --dump-config` 可看到多出 `# == Vision` 配置层。

> 也可打成 tarball 分发：`npm pack` 后在 DSH 里 `dsh plugin add ./vision-0.1.2.tgz`（无需构建权限）。

## 配置（可选）

默认即可用；如需覆盖：

- `CVISION_PYTHON`：Python 可执行文件，默认 `python`
- `CVISION_DIR`：cvision 项目根（含 `cvision/` 包）。默认 = 本插件安装目录（包内捆绑版）。若不使用包内副本，可指向仓库根。

## 模型怎么用

模型选择支持图片的 `deepseek-v4-flash-vision-exp` 后：

- "列一下可见窗口" → `list_windows()`（先找到目标窗口）→ "用 see 看 VS Code" → `see(window="Visual Studio Code")`。
- 直接说 "用 see 看一下屏幕" → `see()`。

> 请遵守下面的「给 AI 智能体的使用提示」——**默认不要 `maximize`，也不要用它去切换/激活前台窗口**。

## 给 AI 智能体的使用提示（重要）

- **默认不要传 `maximize=true`**：Windows Graphics Capture 抓的是窗口**自身的合成内容**，
  跟窗口是否在前台、是否被其它窗口遮挡**无关**。因此**不需要**把窗口切到前台，也**不需要**最大化。
- **不要为了截图去激活/切换前台窗口**：WGC 路径**不抢焦点、不切走你正在用的窗口**，全程无打扰。
- **什么情况才用 `maximize=true`**：仅当窗口已**最小化**（内容很小/看不清）、或**太小**、
  或**被其它窗口完全挡住且内容读不出来**时才用。插件抓完会**自动还原**窗口原状态。
- **推荐流程**：先 `list_windows()` 看有哪些窗口 → 直接 `see(window="<窗口标题>")` 抓目标窗口；
  需要整屏用 `see()`。

## 目录结构

```
vision/                      # 仓库根 = 插件本体
  src/index.ts          # TypeScript 源（作者用 dsh-tools/cordis/dsh-attachment 类型）
  lib/index.js          # 编译产物（DSH 实际加载；main/exports 指向它）
  tsconfig.json         # TS 配置（pnpm build -> tsc）
  package.json          # 声明 dsh.bundle，files 含 lib/cvision/requirements.txt
  cordis.patch.yml      # bundle 的配置层，按包名引用
  requirements.txt      # Python 依赖（随包分发；Windows 含 pywin32/winsdk，macOS 含 pyobjc-Quartz）
  cvision/              # 捆绑的 Python 版 cvision（截屏实现；已裁剪为插件所需）
    __init__.py         #   包标记
    capturer.py         #   兼容层：转发到平台捕获后端（cvision.capture）
    capture/            #   平台捕获后端（门面，按 sys.platform 选）
      __init__.py       #     选后端并暴露 list_windows/capture_window/capture_screen
      base.py           #     平台无关 Window + CaptureBackend 协议
      windows.py        #     Windows 后端（WGC > PrintWindow > 读合成桌面区域 回退）
      macos.py          #     macOS 后端（Quartz 枚举 + screencapture -l 抓窗口）
      linux.py          #     Linux 后端（Phase 2，暂为占位）
    detect.py           #   纯逻辑判定（GPU 类/空白帧），不依赖 win32，可跨平台单测
    cli_capture.py      #   跨语言 CLI：python -m cvision.cli_capture [--list]
    tabs.py             #   Chromium 网页标签枚举 + CDP 截图（自动切换页签）
    cli_tabs.py         #   标签截图 CLI：python -m cvision.cli_tabs [--launch]
    encoding.py         #   PIL -> base64 data URL
  tests/
    test_detect.py      #   detect 模块纯逻辑单测（PIL only，Linux CI 可跑）
  README.md
```

> 注：MCP server 相关的 `config.py`/`deepseek.py`/`server.py` 已从捆绑包移除（插件截屏无需它们，也免去了 `DEEPSEEK_API_KEY` 依赖）。

## 浏览器网页标签截图（实验性）

对 **Chrome/Edge 等 Chromium**，用 CDP 枚举页签、自动切换到每页并截取**页面内容**（不是浏览器窗口，与前台/遮挡无关）：

- **控制已打开的浏览器**：需浏览器启动时带
  `--remote-debugging-port=9222 --remote-allow-origins=*`（新版 Chrome 不加后者 WebSocket 会被 403 拒）。
- 或者**新建**一个带调试端口的实例并把 URL 作为页签：
  ```bash
  python -m cvision.cli_tabs --launch --headless --urls https://a.com https://b.com --out tabcaps
  # 或连接已有的：
  python -m cvision.cli_tabs --port 9222 --out tabcaps
  ```
- 输出 JSON（每页签标题/URL/保存路径），截图存在 `--out` 目录。
- 依赖：`requests`、`websocket-client`（已写入 `requirements.txt`）。

## 多平台支持

- **Windows**：完整支持（WGC/PrintWindow/桌面区域回退），最稳。
- **macOS**：Phase 1 已支持（`Quartz/CGWindowList` 枚举 + `screencapture -l` 抓窗口，与前台无关）；需在「系统设置 → 隐私与安全 → 屏幕录制」授权，否则标题为空/只能抓到壁纸。
- **Linux**：Phase 2 占位（未见 `capture/linux.py` 实现前调用会 `NotImplementedError`）。

## 说明与限制

- 跨语言：插件用 `child_process` 调 `python -m cvision.cli_capture`，需目标机器桌面 + Python（Windows 用 pywin32，macOS 用 pyobjc-Quartz）。
- 截图能力：`capture_window` 依次尝试：**Windows Graphics Capture**（真实合成内容，抓 GPU/Chromium/被遮挡窗口最准，需 `winsdk`）→ `PrintWindow`（普通 GDI 窗口）→ 读合成桌面区域（兜底）。见 `cvision/capture/windows.py`。未装 `winsdk` 时自动跳过 WGC。
- 附件限制：Harness attachment 单图源 ≤20MiB、单边 ≤8192px、每条消息 ≤20 张；超大屏默认 PNG/JPEG 视情况。
- 截图尽量不打扰：**WGC 抓取不切前台、不抢焦点、默认不最大化**；仅当 WGC 失效回退到"读合成桌面区域"时才可能置前，且抓完立即还原窗口状态。
- 插件本体（`src/index.ts` → `lib/index.js`）未在本环境端到端跑过（无 DSH 运行时）；按 `@deepseek-ai/dsh-tools` / `ctx.attachments.saveImage` 官方接口编写，需在你的 DSH Desktop 中 `dsh plugin add` + 重启后验证。
