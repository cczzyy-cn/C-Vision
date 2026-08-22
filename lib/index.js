/**
 * C-Vision 视觉插件（DeepSeek Harness / DSH bundle）—— 编译产物
 *
 * 本文件由 `pnpm build`（tsc，源：`src/index.ts`）生成。DSH 运行时只加载本 JS。
 */
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineTool } from '@deepseek-ai/dsh-tools'

const execFileAsync = promisify(execFile)

export const name = 'cvision-vision'
export const inject = ['tools', 'attachments']

const MEDIA_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

/** 从插件自身位置向上查找含 `cvision/` 的包根（入口在 lib/index.js 时需上移一层）。 */
function findPluginRoot() {
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
const PYTHON = process.env.CVISION_PYTHON || 'python'
const CVISION_DIR = process.env.CVISION_DIR || PLUGIN_DIR

/** 解析 `data:<mime>;base64,<data>` 为附件服务所需的字节与媒体类型。 */
function parseDataUrl(dataUrl) {
  const m = /^data:(image\/[a-z+]+);base64,(.+)$/s.exec(String(dataUrl).trim())
  if (!m || !m[1] || !m[2]) throw new Error(`无法解析截屏 data URL（长度 ${String(dataUrl).length}）`)
  const mediaType = m[1]
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
function assertCvisionPresent() {
  if (!existsSync(resolve(CVISION_DIR, 'cvision'))) {
    throw new Error(
      `未找到 Python 版 cvision（${resolve(CVISION_DIR, 'cvision')} 不存在）。` +
        `请安装配套的 cvision 包，或将环境变量 CVISION_DIR 指向含 cvision/ 的项目根。`,
    )
  }
}

export function apply(ctx) {
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
        render: (_args, value) => [{ type: 'image', attachment: value.ref }],
      },
      // 协作式超时：把 exec.signal 转给子进程，取消/超时即终止 python 截屏。
      timeoutMs: 60000,
      async execute(args, exec) {
        assertCvisionPresent()
        const format = (args.format || 'PNG').toUpperCase()
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
          name: `cvision-capture.${ext}`,
        })
        return { ref }
      },
    }),
  )
}
