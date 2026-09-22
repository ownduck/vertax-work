/**
 * Host-process defaults for skill/shell children.
 * @module @deepseek-ai/dsh-custom-env
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { parseEnv } from 'node:util'
import { spawnSync } from 'node:child_process'
import type { Context } from '@deepseek-ai/cordis'
import { resolveDshHome } from '@deepseek-ai/dsh-home-paths'

/** Cordis plugin id. */
export const name = 'custom-env'

/** No service injections; only mutates the Host process environment. */
export const inject: string[] = []

/**
 * Built-in defaults. `$DSH_HOME/.env` string entries overlay these keys
 * (file wins on conflict). Keep secrets out of this map.
 */
const DEFAULT_ENV: Readonly<Record<string, string>> = {}

/**
 * Escape a string for a PowerShell single-quoted literal.
 * @param value - Raw string.
 * @returns Value safe inside `'...'`.
 */
function psSingleQuoted(value: string): string {
  return `'${value.replaceAll("'", "''")}'`
}

/**
 * Read non-empty string entries from `$DSH_HOME/.env`, or `{}` when absent.
 * @returns Variable map from the harness-home dotenv file.
 */
function loadDshHomeEnvFile(): Readonly<Record<string, string>> {
  const path = join(resolveDshHome(), '.env')
  if (!existsSync(path)) return {}
  const raw = readFileSync(path, 'utf8').replace(/^\uFEFF/u, '').trim()
  if (raw === '') return {}
  let parsed: NodeJS.ProcessEnv
  try {
    parsed = parseEnv(raw)
  } catch (error) {
    throw new Error(`custom-env: invalid dotenv syntax in ${path}`, { cause: error })
  }
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(parsed)) {
    if (typeof value === 'string' && value !== '') out[key] = value
  }
  return out
}

/**
 * Persist entries into the Windows user environment (HKCU). No-op on other platforms.
 * @param entries - Variable map to write.
 */
function persistWindowsUserEnv(entries: Readonly<Record<string, string>>): void {
  if (process.platform !== 'win32') return
  const statements = Object.entries(entries).map(
    ([key, value]) =>
      `[Environment]::SetEnvironmentVariable(${psSingleQuoted(key)}, ${psSingleQuoted(value)}, 'User')`,
  )
  if (statements.length === 0) return
  spawnSync(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-Command', statements.join('; ')],
    { windowsHide: true, stdio: 'ignore' },
  )
}

/**
 * Assign defaults plus `$DSH_HOME/.env` onto the Host (and Windows user env).
 * @param _ctx - unused; registration is the side effect of loading the plugin.
 */
export function apply(_ctx: Context): void {
  const merged: Readonly<Record<string, string>> = { ...DEFAULT_ENV, ...loadDshHomeEnvFile() }
  for (const [key, value] of Object.entries(merged)) {
    process.env[key] = value
  }
  persistWindowsUserEnv(merged)
}
