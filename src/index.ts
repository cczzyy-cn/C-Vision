/**
 * C-Vision 视觉插件（DeepSeek Harness / DSH bundle）
 *
 * 注册 `see` 工具：跨语言调用本插件包内捆绑的 Python 版 cvision 截屏（全屏或指定
 * 窗口），把截图写入 Harness 附件服务（`ctx.attachments.saveImage`），并通过 `image`
 * ContentBlock 返回，使模型能**原生看到**这张图片（描述 / 识别截图文字 / 读图表）。
 *
 * 分发：插件包自带 `cvision/` 与 `requirements.txt`，`CVISION_DIR` 默认定位到本插件
 * 安装目录（向上查找含 `cvision/` 的包根），无需外部绝对路径。目标机器只需有
 * Python 3 并 `pip install -r requirements.txt` 一次。
 *
 * 构建：本文件为 TypeScript 源，`pnpm build`（tsc）编译到 `lib/index.js`；DSH 运行
 * 时只加载编译后的 JS。
 *
 * 环境变量：
 *   CVISION_PYTHON   Python 可执行文件（默认 `python`）。
 *   CVISION_DIR      cvision 项目根（含 `cvision/` 包）。默认 = 本插件安装目录。
 */
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type JsonValue } from '@deepseek-ai/dsh-tools'
import type { ImageAttachmentRef } from '@deepseek-ai/dsh-attachment'

const execFileAsync = promisify(execFile)

export const name = 'Vision'
export const inject = ['tools', 'attachments']

const MEDIA_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'] as const
type MediaType = (typeof MEDIA_TYPES)[number]

/** 从插件自身位置向上查找含 `cvision/` 的包根（入口在 lib/index.js 时需上移一层）。 */
function findPluginRoot(): string {
  let dir = dirname(fileURLToPath(import.meta.url))
  for (let i = 0; i < 4; i++) {
    if (existsSync(resolve(dir, 'cvision'))) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return dirname(fileURLToPath(import.meta.url))
}

const PLUGIN_DIR = findPluginRoot()
const PYTHON = process.env.CVISION_PYTHON ?? 'python'
const CVISION_DIR = process.env.CVISION_DIR || PLUGIN_DIR

interface ParsedCapture {
  data: Uint8Array
  mediaType: MediaType
  ext: string
}

/** 解析 `data:<mime>;base64,<data>` 为附件服务所需的字节与媒体类型。 */
function parseDataUrl(dataUrl: string): ParsedCapture {
  const m = /^data:(image\/[a-z+]+);base64,(.+)$/s.exec(String(dataUrl).trim())
  if (!m || !m[1] || !m[2]) throw new Error(`无法解析截屏 data URL（长度 ${String(dataUrl).length}）`)
  const mediaType = m[1] as MediaType
  if (!MEDIA_TYPES.includes(mediaType)) throw new Error(`不支持的图片类型 ${mediaType}`)
  const ext = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
    'image/gif': 'gif',
  }[mediaType]
  return { data: new Uint8Array(Buffer.from(m[2], 'base64')), mediaType, ext }
}

/** 断言包内（或 CVISION_DIR 指向）的 Python 版 cvision 存在，否则给出可操作报错。 */
function assertCvisionPresent(): void {
  if (!existsSync(resolve(CVISION_DIR, 'cvision'))) {
    throw new Error(
      `未找到 Python 版 cvision（${resolve(CVISION_DIR, 'cvision')} 不存在）。` +
        `请安装配套的 cvision 包，或将环境变量 CVISION_DIR 指向含 cvision/ 的项目根。`,
    )
  }
}

/** 运行一次用户级输入（python -m cvision.cli_input <args>），失败会抛出子进程错误。 */
async function runCliInput(args: string[], exec: { signal: AbortSignal }): Promise<void> {
  assertCvisionPresent()
  await execFileAsync(PYTHON, ['-m', 'cvision.cli_input', ...args], {
    cwd: CVISION_DIR,
    maxBuffer: 1 * 1024 * 1024,
    signal: exec.signal,
  })
}

export function apply(ctx: Context): void {
  ctx.tools.register(
    defineTool({
      name: 'see',
      description:
        '截取整个屏幕或某个窗口，并把截图以图片形式返回，让模型直接查看画面内容（描述、识别截图文字、读取图表/文档）。' +
        '用 window 指定窗口标题子串（如 "Visual Studio Code"），留空则截全屏。' +
        '默认尽量别传 maximize=true：非最小化窗口会直接抓到其真实内容，且不切换前台、不抢焦点。' +
        '仅当窗口已最小化/太小/被遮挡看不清时才用 maximize=true（截图后会自动还原原状态）。',
      parameters: {
        window: { type: 'string', description: '窗口标题子串（忽略大小写）；留空则截整屏' },
        maximize: {
          type: 'boolean',
          description: '是否先最大化目标窗口再截图。默认 false：非最小化窗口无需最大化且不切前台；仅当窗口太小/被遮挡看不清时设 true（抓后还原）',
        },
        region: { type: 'string', description: '裁剪区域 x,y,w,h（像素，相对截图），只抓窗口内一小块，省 token' },
        delay: { type: 'number', description: '抓取前等待毫秒（给需要渲染的内容），可选' },
        format: { type: 'string', description: 'PNG/JPEG/WEBP/GIF，默认 PNG' },
      },
      output: {
        // 规范：用 DSH value schema DSL；对象节点须显式声明 additionalProperties。
        schema: {
          type: 'object',
          properties: { ref: { type: 'object', additionalProperties: true } },
          additionalProperties: false,
        },
        render: (_args, value) => [{ type: 'image', attachment: value.ref as unknown as ImageAttachmentRef }],
      },
      // 协作式超时：把 exec.signal 转给子进程，取消/超时即终止 python 截屏。
      timeoutMs: 60000,
      async execute(args, exec) {
        assertCvisionPresent()
        const format = (args.format ?? 'PNG').toUpperCase()
        const cmdArgs = ['-m', 'cvision.cli_capture', '--format', format]
        if (args.window) cmdArgs.push('--window', String(args.window))
        if (args.maximize) cmdArgs.push('--maximize')
        if (args.region) cmdArgs.push('--region', String(args.region))
        if (args.delay) cmdArgs.push('--delay', String(args.delay))

        const { stdout } = await execFileAsync(PYTHON, cmdArgs, {
          cwd: CVISION_DIR,
          maxBuffer: 64 * 1024 * 1024,
          signal: exec.signal,
        })
        const { data, mediaType, ext } = parseDataUrl(stdout)
        // 持久化到附件服务，换取模型可见的不可变引用。
        const ref = await ctx.attachments.saveImage({
          data,
          mediaType,
          name: `vision-capture.${ext}`,
        })
        // value schema 推断出的是开放对象（Record<string, JsonValue>），此处为不透明
        // 附件引用，需显式断言到该推断形态。
        return { ref: ref as unknown as Record<string, JsonValue> }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'ocr',
      description:
        '截取屏幕/窗口（可 region/delay），用 OCR 识别其中的文字并**返回文本**。' +
        '适合终端、网页、文档等只要读文字的场合（省去整图 token）。' +
        '参数同 see（window/title/maximize/region/delay）。',
      parameters: {
        window: { type: 'string', description: '窗口标题子串；留空则对整屏 OCR' },
        maximize: { type: 'boolean', description: '是否先最大化目标窗口再截（抓后还原）' },
        region: { type: 'string', description: '裁剪区域 x,y,w,h（像素，相对截图）' },
        delay: { type: 'number', description: '抓取前等待毫秒，可选' },
      },
      output: {
        schema: {
          type: 'object',
          properties: {
            text: { type: 'string' },
            lines: { type: 'array', items: { type: 'string' } },
          },
          additionalProperties: false,
        },
        render: (_args, value) => [{ type: 'text', text: String(value.text ?? '') }],
      },
      timeoutMs: 90000,
      async execute(args, exec) {
        assertCvisionPresent()
        const cmdArgs = ['-m', 'cvision.cli_ocr']
        if (args.window) cmdArgs.push('--window', String(args.window))
        if (args.maximize) cmdArgs.push('--maximize')
        if (args.region) cmdArgs.push('--region', String(args.region))
        if (args.delay) cmdArgs.push('--delay', String(args.delay))
        const { stdout } = await execFileAsync(PYTHON, cmdArgs, {
          cwd: CVISION_DIR,
          maxBuffer: 4 * 1024 * 1024,
          signal: exec.signal,
        })
        const info = JSON.parse(stdout) as { text?: string; lines?: string[] }
        return { text: info.text ?? '', lines: info.lines ?? [] }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'list_windows',
      description:
        '列出当前可见的顶层 Windows 窗口（标题 + 句柄 + 尺寸）。用于让模型先找到要看的窗口，' +
        '再把对应标题传给 see 做截图/视觉分析。',
      parameters: {},
      output: {
        schema: {
          type: 'object',
          properties: {
            windows: {
              type: 'array',
              items: { type: 'object', additionalProperties: true },
            },
          },
          additionalProperties: false,
        },
        render: (_args, value) => [{ type: 'text', text: JSON.stringify(value.windows, null, 2) }],
      },
      timeoutMs: 30000,
      async execute(_args, exec) {
        assertCvisionPresent()
        const { stdout } = await execFileAsync(PYTHON, ['-m', 'cvision.cli_capture', '--list'], {
          cwd: CVISION_DIR,
          maxBuffer: 4 * 1024 * 1024,
          signal: exec.signal,
        })
        const windows = JSON.parse(stdout) as Array<Record<string, JsonValue>>
        return { windows }
      },
    }),
  )

  // ── 用户级操作（computer-use）：鼠标/键盘/聚焦 ──────────────────────────────
  // 用法：先 see 看清屏幕定位坐标，再用这些工具操作，再 see 确认，形成"看→操作→看"闭环。
  const inputOut = {
    schema: {
      type: 'object' as const,
      properties: { ok: { type: 'boolean' as const } },
      additionalProperties: false as const,
    },
    render: (_a: unknown, v: { ok?: boolean }) => [
      { type: 'text' as const, text: v.ok ? '已执行' : '未执行' },
    ],
  }

  ctx.tools.register(
    defineTool({
      name: 'click',
      description: '在屏幕绝对坐标 (x,y) 模拟鼠标单击。先 see 确认目标位置后再点。',
      parameters: { x: { type: 'integer' }, y: { type: 'integer' }, button: { type: 'string', description: 'left/right/middle，默认 left' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        const cmd = ['--click', String(args.x), String(args.y)]
        if (args.button && args.button !== 'left') cmd.push('--button', String(args.button))
        await runCliInput(cmd, exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'double_click',
      description: '在屏幕绝对坐标 (x,y) 模拟鼠标双击。',
      parameters: { x: { type: 'integer' }, y: { type: 'integer' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--double', String(args.x), String(args.y)], exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'mouse_move',
      description: '把鼠标移到屏幕绝对坐标 (x,y)（不点击）。',
      parameters: { x: { type: 'integer' }, y: { type: 'integer' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--move', String(args.x), String(args.y)], exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'scroll',
      description: '在屏幕坐标 (x,y) 处滚动。dy>0 向上滚，dy<0 向下滚（单位：格）。',
      parameters: { x: { type: 'integer' }, y: { type: 'integer' }, dy: { type: 'integer' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--scroll', String(args.x), String(args.y), String(args.dy)], exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'type_text',
      description: '像键盘一样输入文本（到当前焦点）。例如输入到地址栏/输入框，可配合 ctrl+l 先聚焦。',
      parameters: { text: { type: 'string', description: '要输入的文本' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--type', String(args.text)], exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'press_key',
      description: '发送快捷键/按键，如 "ctrl+l"（聚焦地址栏）、"enter"、"ctrl+shift+t"（新标签）、"alt+tab"。',
      parameters: { keys: { type: 'string', description: '按键组合，如 ctrl+l / enter / ctrl+shift+t' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--keys', String(args.keys)], exec)
        return { ok: true }
      },
    }),
  )

  ctx.tools.register(
    defineTool({
      name: 'focus_window',
      description: '把标题含子串的窗口置前（用户级：激活它），便于随后对它键盘/鼠标操作。',
      parameters: { title: { type: 'string', description: '窗口标题子串，如 "Google Chrome"' } },
      output: inputOut,
      timeoutMs: 30000,
      async execute(args, exec) {
        await runCliInput(['--focus', String(args.title)], exec)
        return { ok: true }
      },
    }),
  )

}
