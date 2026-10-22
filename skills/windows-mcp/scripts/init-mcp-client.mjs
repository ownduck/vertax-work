/** Insert an enabled windows-mcp client into $DSH_HOME/cordis.patch.yml. */
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { readFile, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { isMap, isSeq, parseDocument } from 'yaml'

const clientId = 'mcp-windows-mcp'

/** Prefer the uv tool install, then the first existing where.exe result.
 * @returns Absolute path of windows-mcp.exe.
 */
function resolveExecutable() {
  const explicit = process.argv[2]
  if (explicit) {
    if (!existsSync(explicit)) throw new Error(`指定的 windows-mcp 不存在: ${explicit}`)
    return explicit
  }
  const preferred = join(process.env.USERPROFILE || homedir(), '.local', 'bin', 'windows-mcp.exe')
  if (existsSync(preferred)) return preferred
  const found = spawnSync('where.exe', ['windows-mcp'], { encoding: 'utf8', windowsHide: true })
  const path = (found.stdout ?? '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .find(line => line && existsSync(line))
  if (found.status === 0 && path) return path
  throw new Error('未找到 windows-mcp.exe。先在本 skill 目录运行 scripts/init-env.ps1。')
}

/** @param {import('yaml').Node | null} node */
function containsClient(node) {
  if (isMap(node)) {
    if (node.get('id') === clientId) return true
    return node.items.some(pair => containsClient(pair.value))
  }
  if (isSeq(node)) return node.items.some(containsClient)
  return false
}

const dshHome = process.env.DSH_HOME
if (!dshHome) {
  console.error('DSH_HOME 未设置。请在已启动的 DSH 会话中运行，或先设置该环境变量。')
  process.exit(1)
}

const patchPath = join(dshHome, 'cordis.patch.yml')
let text = '[]\n'
try {
  text = await readFile(patchPath, 'utf8')
  if (text.trim() === '') text = '[]\n'
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}

const document = parseDocument(text, {
  customTags: [{ tag: 'tag:yaml.org,2002:js', resolve: value => value }],
})
const parseError = document.errors[0]
if (parseError !== undefined) throw parseError
if (document.contents == null) document.contents = document.createNode([])
if (!isSeq(document.contents)) throw new Error(`${patchPath} 的顶层必须是 YAML 数组`)

if (containsClient(document.contents)) {
  console.log(`${clientId} 已在 ${patchPath}，未改动`)
  process.exit(0)
}

const command = resolveExecutable()
document.contents.flow = false
document.add({
  insert: [{
    id: clientId,
    name: '@deepseek-ai/dsh-mcp-client',
    config: {
      serverName: 'windows-mcp',
      transport: 'stdio',
      command,
      args: ['serve', '--exclude-tools', 'PowerShell,FileSystem,Registry'],
      toolCallTimeoutMs: 180000,
      env: {
        ANONYMIZED_TELEMETRY: 'false',
        WINDOWS_MCP_SCREENSHOT_SCALE: '0.5',
      },
    },
  }],
})

await writeFile(patchPath, String(document))
console.log(`已写入 ${patchPath}`)
console.log(command)
const waitMs = Number(process.env.WINDOWS_MCP_READY_WAIT_MS ?? 10_000)
if (Number.isFinite(waitMs) && waitMs > 0) {
  console.log(`等待 ${String(waitMs)} ms，让热更新拉起 client`)
  await new Promise(resolve => setTimeout(resolve, waitMs))
}
