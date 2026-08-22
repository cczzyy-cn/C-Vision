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

export function apply(ctx: Context): void {
  ctx.tools.register(
    defineTool({
      name: 'see',
      description:
        '截取整个屏幕或某个窗口，并把截图以图片形式返回，让模型直接查看画面内容（描述、识别截图文字、读取图表/文档）。' +
        '用 window 指定窗口标题子串（如 "Visual Studio Code"），留空则截全屏；maximize=true 会先把窗口最大化再截（截图后还原原状态、不抢焦点）。',
      parameters: {
        window: { type: 'string', description: '窗口标题子串（忽略大小写）；留空则截整屏' },
        maximize: { type: 'boolean', description: '是否先最大化目标窗口再截图' },
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
}
