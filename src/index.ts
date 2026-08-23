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
import { readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
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

// 单次 capture_tabs 最多返回的图片数（附件限制每条消息 ≤20 张图）。
const MAX_TABS = 20

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

  ctx.tools.register(
    defineTool({
      name: 'capture_tabs',
      description:
        '自动切换并截图浏览器（Chrome/Edge 等 Chromium）的各网页标签，返回每页截图（图片）。' +
        '传 urls 会用一个无头浏览器打开这些页面并逐个截图；不传 urls 则连接已带 ' +
        '--remote-debugging-port=<port> 和 --remote-allow-origins=* 的浏览器并截其现有页签。',
      parameters: {
        urls: { type: 'array', items: { type: 'string' }, description: '要打开的页面 URL（开无头浏览器逐个截）；为空则不新开' },
        url: { type: 'string', description: '连接已有浏览器时，按 URL 子串定位单个目标页签并只截它' },
        title: { type: 'string', description: '连接已有浏览器时，按标题子串定位单个目标页签并只截它' },
        port: { type: 'integer', description: 'CDP 端口，默认 9222（连接已有浏览器）' },
        full_page: { type: 'boolean', description: '整页截图（captureBeyondViewport=true），默认 false' },
      },
      output: {
        schema: {
          type: 'object',
          properties: {
            captures: {
              type: 'array',
              items: { type: 'object', additionalProperties: true },
            },
          },
          additionalProperties: false,
        },
        render: (_args, value) =>
          (value.captures as Array<Record<string, JsonValue>>).flatMap((c) => {
            const label = `${String(c.title ?? '')}  ${String(c.url ?? '')}`
            const ref = c.ref as unknown as ImageAttachmentRef | undefined
            return ref
              ? [{ type: 'text' as const, text: label }, { type: 'image' as const, attachment: ref }]
              : [{ type: 'text' as const, text: `${label}  (失败: ${String(c.error ?? '')})` }]
          }),
      },
      timeoutMs: 120000,
      async execute(args, exec) {
        assertCvisionPresent()
        const outDir = join(tmpdir(), `vision-tabs-${Date.now()}`)
        const cmdArgs = ['-m', 'cvision.cli_tabs']
        if (args.urls && args.urls.length > 0) {
          // urls 模式=启动无头浏览器并逐个截图这些页面
          cmdArgs.push('--launch', '--headless', '--urls', ...args.urls)
        } else {
          // 连接已打开的浏览器：传端口，并按需定位单个目标页签
          cmdArgs.push('--port', String(args.port ?? 9222))
          if (args.url) cmdArgs.push('--url-substr', String(args.url))
          if (args.title) cmdArgs.push('--title-substr', String(args.title))
        }
        if (args.full_page) cmdArgs.push('--full-page')
        cmdArgs.push('--out', outDir)

        const { stdout } = await execFileAsync(PYTHON, cmdArgs, {
          cwd: CVISION_DIR,
          maxBuffer: 8 * 1024 * 1024,
          signal: exec.signal,
        })
        const info = JSON.parse(stdout) as { tabs?: Array<Record<string, JsonValue>> }

        const captures: Array<Record<string, JsonValue>> = []
        const seenRef = new Set<string>()
        for (const tab of (info.tabs ?? []).slice(0, MAX_TABS)) {
          const path = String(tab.path ?? '')
          const title = String(tab.title ?? '')
          const url = String(tab.url ?? '')
          if (!path) {
            captures.push({ title, url, error: String(tab.error ?? 'no path') })
            continue
          }
          try {
            const bytes = await readFile(path)
            const key = `${path}:${bytes.length}`
            if (seenRef.has(key)) {
              captures.push({ title, url, error: 'duplicate' })
              continue
            }
            seenRef.add(key)
            const ref = await ctx.attachments.saveImage({
              data: new Uint8Array(bytes),
              mediaType: 'image/png',
              name: `vision-tab.${title.replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, '_').slice(0, 40) || 'tab'}.png`,
            })
            captures.push({ ref: ref as unknown as Record<string, JsonValue>, title, url })
          } catch (e) {
            captures.push({ title, url, error: `read/save failed: ${(e as Error).message}` })
          }
        }

        await rm(outDir, { recursive: true, force: true }).catch(() => undefined)
        return { captures }
      },
    }),
  )
}
