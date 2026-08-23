# Vision · DeepSeek Harness (DSH) 视觉插件

给 DeepSeek Harness 的 agent 提供**自动视觉能力（看）+ 用户级操作（操作）**：模型调用 `see`/`ocr`/`list_windows`
看清屏幕/窗口，再用 `click`/`type_text`/`press_key`/`scroll`/`focus_window` 像人一样操作，形成 **看→操作→看** 的 computer-use 闭环。

这是一个 **DSH 组合包（bundle）**，通过 `dsh plugin add` 安装。插件注册工具 → 跨语言调用**包内捆绑的 Python 版 cvision** 截屏/OCR/输入 → 写入 Harness 附件服务（`ctx.attachments.saveImage`）或返回文本 → 以 **`image` ContentBlock / `text`** 返回给模型。

## 特性

- **原生看图**：`see` 抓真实截图（WGC 抓窗口合成内容，GPU/被遮挡窗口也稳），模型直接看到。
- **快速读字**：`ocr` 直接返回文本；`see`/`ocr` 支持 `region="x,y,w,h"` 只取一块，省 token。
- **用户级操作**：鼠标点击/移动/滚动、键盘输入/快捷键、窗口聚焦（模拟人操作）。
- **跨平台**：Windows（完整）/ macOS(Phase 1) / Linux(Phase 2)。
- **开箱即用**：包内自带 Python cvision 与依赖清单，`CVISION_DIR` 默认指向包内。

## 工具一览

### 看（观察）
| 工具 | 说明 |
| --- | --- |
| `see(window?, region?, delay?, maximize?)` | 截屏/窗口 → **图片**返回（模型原生看）。`region="x,y,w,h"` 只取一块（省 token）；`delay=毫秒` 等渲染；`maximize` 默认关 |
| `ocr(window?, region?, delay?)` | 截屏后 **OCR** → 返回**文本**（终端/网页/文档快速读字，省整图 token） |
| `list_windows()` | 列出可见窗口（标题+句柄+尺寸） |

### 操作（computer-use，模拟用户级输入）
| 工具 | 说明 |
| --- | --- |
| `click(x, y, button?)` | 屏幕绝对坐标**单击**（left/right/middle） |
| `double_click(x, y)` | 屏幕绝对坐标**双击** |
| `mouse_move(x, y)` | 移动鼠标到屏幕坐标（不点击） |
| `scroll(x, y, dy)` | 在 (x,y) 处滚动（dy>0 上滚，<0 下滚） |
| `type_text(text)` | 像键盘一样**输入文本**到当前焦点 |
| `press_key(keys)` | 发送**快捷键**，如 `ctrl+l`、`enter`、`ctrl+shift+t`、`alt+tab` |
| `focus_window(title)` | 按标题子串把窗口**置前**（用户级激活） |

> **关键**：默认**不最大化、不切前台**——WGC 抓窗口合成内容，与前台/遮挡无关。
> **computer-use 闭环**：`see` 看清 → `click`/`type_text`/`press_key`/`scroll` 操作 → 再 `see` 确认 …（"看→操作→看"循环）。

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
  - 跑 Python 纯逻辑单测（`encoding`/`detect`，仅需 Pillow），在 **ubuntu + macOS** 矩阵上运行。
- **发布**：打一个 `v*` 标签（如 `v0.1.7`）推送到 GitHub，CI 在构建+测试通过后自动
  `npm pack` 出 `vision-<version>.tgz` 并创建 GitHub Release 上传该产物，
  可直接 `dsh plugin add ./vision-0.1.7.tgz` 安装。

```bash
git tag v0.1.7 && git push origin v0.1.7
```

## 前提

- 目标机器：Windows 桌面 + 有 Python 3（插件靠 `child_process` 调 `python -m cvision.cli_capture`）。
- 安装依赖（依赖文件已随插件打包）：

```powershell
python -m pip install -r requirements.txt
```

> 放到插件目录下执行，或先 `cd` 到该目录。

## 安装（DSH Desktop）

> ⚠️ `dsh` 命令通常**不在系统 PATH**（它是 npx 缓存里的 CLI），要用 **`npx -y @deepseek-ai/dsh`** 调用；
> 且 `dsh plugin` 是 **pnpm 前向器**，需本机有 `pnpm`（`pnpm -v` 确认）。
> `--profile web` 表示装进 **web**（浏览器面板 / 3080）profile；DSH Desktop 原生 App 用 `--profile desktop`。

装**最新**（从 GitHub 源码，公开仓库免认证）：

```powershell
npx -y @deepseek-ai/dsh plugin --profile web add github:cczzyy-cn/C-Vision
```

或装**指定 tarball**（从 Release 下载 `vision-0.1.7.tgz` 后）：

```powershell
npx -y @deepseek-ai/dsh plugin --profile web add C:\Users\14339\Downloads\vision-0.1.7.tgz
```

或装**本地目录**（已 clone 本仓库）：

```powershell
npx -y @deepseek-ai/dsh plugin --profile web add C:\Users\14339\Desktop\git\C-Vision\C-Vision
```

装完**重启 DSH Desktop**。用 `npx -y @deepseek-ai/dsh --dump-config` 可看到多出 `# == Vision` 配置层。

> 也可 `pnpm pack` 打成 tarball 分发：`npx -y @deepseek-ai/dsh plugin --profile web add ./vision-0.1.7.tgz`（无需构建权限）。
> 若 `add` 因已存在同名 `vision` 依赖报错，先 `npx -y @deepseek-ai/dsh plugin --profile web rm vision` 再装。

## 配置（可选）

默认即可用；如需覆盖：

- `CVISION_PYTHON`：Python 可执行文件，默认 `python`
- `CVISION_DIR`：cvision 项目根（含 `cvision/` 包）。默认 = 本插件安装目录（包内捆绑版）。若不使用包内副本，可指向仓库根。

## 模型怎么用

模型选择支持图片的 `deepseek-v4-flash-vision-exp` 后：

- "列一下可见窗口" → `list_windows()`（先找到目标窗口）→ "用 see 看 VS Code" → `see(window="Visual Studio Code")`。
- 直接说 "用 see 看一下屏幕" → `see()`。
- 只看窗口内一小块 → `see(window="X", region="x,y,w,h")`；需要渲染慢的页面 → `see(..., delay=800)`。
- 只要读文字 → `ocr(window="X")`（识别屏幕/窗口中的文本并返回，省去整图 token）。

> 请遵守下面的「给 AI 智能体的使用提示」——**默认不要 `maximize`，也不要用它去切换/激活前台窗口**。

## 给 AI 智能体的使用提示（重要）

- **默认不要传 `maximize=true`**：Windows Graphics Capture 抓的是窗口**自身的合成内容**，
  跟窗口是否在前台、是否被其它窗口遮挡**无关**。因此**不需要**把窗口切到前台，也**不需要**最大化。
- **不要为了截图去激活/切换前台窗口**：WGC 路径**不抢焦点、不切走你正在用的窗口**，全程无打扰。
- **什么情况才用 `maximize=true`**：仅当窗口已**最小化**（内容很小/看不清）、或**太小**、
  或**被其它窗口完全挡住且内容读不出来**时才用。插件抓完会**自动还原**窗口原状态。
- **推荐流程**：先 `list_windows()` 看有哪些窗口 → 直接 `see(window="<窗口标题>")` 抓目标窗口；
  需要整屏用 `see()`。

## 电脑使用（computer-use）推荐流程

把"看 → 操作 → 看"写成可复用的循环（配合上面的鼠标/键盘工具）：

1. **观察**：`list_windows()` 找到目标窗口；或 `see(window="<标题>")` 看清内容。
2. **定位**：从截图读出目标的**屏幕绝对坐标 (x, y)**。
3. **操作**：`focus_window`（需要时）→ `click(x,y)` / `double_click` / `type_text` / `press_key` / `scroll`。
4. **确认**：再 `see` 看结果；不对就回到 2/3 重试，直到目标达成（循环）。

示例（浏览器打开一个页面并看内容）：

```
focus_window("Google Chrome") → press_key("ctrl+l") → type_text("https://…") → press_key("enter") → see()  # 再看结果
```

> ⚠️ 操作会**真实移动/点击/输入**到你的鼠标键盘；务必先 `see` 确认坐标再操作，避免误触。

## OCR 文本识别

`ocr` 工具对截屏/窗口做文字识别：
- **Windows**：用 `Windows.Media.Ocr`（`winsdk`，系统语言包，免额外二进制）；
- 回退：装 `pytesseract` + Tesseract 后用其识别（跨平台）。

## 多平台支持

- **Windows**：完整支持（WGC/PrintWindow/桌面区域回退），最稳。
- **macOS**：Phase 1 已支持（`Quartz/CGWindowList` 枚举 + `screencapture -l` 抓窗口，与前台无关）；需在「系统设置 → 隐私与安全 → 屏幕录制」授权，否则标题为空/只能抓到壁纸。
- **Linux**：Phase 2 占位（调用 `capture/linux.py` 会 `NotImplementedError`）。

## 目录结构

```
vision/                      # 仓库根 = 插件本体
  src/index.ts          # TypeScript 源（作者用 dsh-tools/cordis/dsh-attachment 类型）
  lib/index.js          # 编译产物（DSH 实际加载；main/exports 指向它）
  tsconfig.json         # TS 配置（pnpm build -> tsc）
  package.json          # 声明 dsh.bundle，files 含 lib/cvision/requirements.txt
  cordis.patch.yml      # bundle 的配置层，按包名引用
  requirements.txt      # Python 依赖（随包分发；Windows 含 pywin32/winsdk，macOS 含 pyobjc-Quartz）
  cvision/              # 捆绑的 Python 版 cvision（截屏 / OCR / 用户级输入；已裁剪为插件所需）
    __init__.py         #   包标记
    capturer.py         #   兼容层：转发到平台捕获后端（cvision.capture）
    capture/            #   平台捕获后端（门面，按 sys.platform 选）
      __init__.py       #     选后端并暴露 list_windows/capture_window/capture_screen
      base.py           #     平台无关 Window + CaptureBackend 协议
      windows.py        #     Windows 后端（WGC > PrintWindow > 读合成桌面区域 回退）
      macos.py          #     macOS 后端（Quartz 枚举 + screencapture -l 抓窗口）
      linux.py          #     Linux 后端（Phase 2，暂为占位）
    detect.py           #   纯逻辑判定（GPU 类/空白帧），不依赖 win32，可跨平台单测
    encoding.py         #   PIL -> base64 data URL；crop_region；fit_for_attachment(附件缩图)
    ocr.py              #   OCR（Windows.Media.Ocr 优先 / pytesseract 回退）
    input.py            #   用户级输入（pyautogui：点击/移动/滚动/输入/快捷键/聚焦）
    cli_capture.py      #   跨语言 CLI：python -m cvision.cli_capture [--list] [--region] [--delay]
    cli_ocr.py          #   OCR CLI：python -m cvision.cli_ocr [--window] [--region]
    cli_input.py        #   输入 CLI：python -m cvision.cli_input --click/--type/--keys/--focus ...
  tests/
    test_detect.py      #   detect 模块单测（PIL only）
    test_encoding.py    #   encoding 模块单测（dataURL/crop/fit，PIL only）
  README.md
```

> 注：MCP server 相关的 `config.py`/`deepseek.py`/`server.py` 已从捆绑包移除（插件截屏无需它们，也免去了 `DEEPSEEK_API_KEY` 依赖）。

## 说明与限制

- 跨语言：插件用 `child_process` 调 `python -m cvision.cli_capture`，需目标机器桌面 + Python（Windows 用 pywin32，macOS 用 pyobjc-Quartz）。
- 截图能力：`capture_window` 依次尝试：**Windows Graphics Capture**（真实合成内容，抓 GPU/Chromium/被遮挡窗口最准，需 `winsdk`）→ `PrintWindow`（普通 GDI 窗口）→ 读合成桌面区域（兜底）。见 `cvision/capture/windows.py`。未装 `winsdk` 时自动跳过 WGC。
- 附件限制：Harness attachment 单图源 ≤20MiB、单边 ≤8192px、每条消息 ≤20 张；截图输出前会自动缩放到限制内（`encoding.fit_for_attachment`），超大屏也不会被拒。
- 省 token：`see`/`ocr` 支持 `region="x,y,w,h"` 只处理一块；`ocr` 直接返回文本；超大图自动降采样。
- 截图尽量不打扰：**WGC 抓取不切前台、不抢焦点、默认不最大化**；仅当 WGC 失效回退到"读合成桌面区域"时才可能置前，且抓完立即还原窗口状态。
- WGC 设备复用：单进程内缓存 Direct3D 设备，多次抓屏更快（CLI 每次独立进程用不到；MCP/循环采集受益）。
- 输入/操作类工具（`click`/`type_text` 等）依赖 `pyautogui`，会**真实操作你的鼠标键盘**；调用前请先 `see` 确认屏幕坐标。
- 工具本体（`see`/`ocr`/`list_windows` 及输入工具）已在 DSH 会话中直接调用过；**macOS/Linux 后端**为编写实现，需在对应平台 + 权限（屏幕录制等）下验证。
