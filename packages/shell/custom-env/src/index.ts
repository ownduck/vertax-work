/**
 * Host-process defaults for skill/shell children.
 * @module @deepseek-ai/dsh-custom-env
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { parseEnv } from 'node:util'
import type { Context } from '@deepseek-ai/cordis'
import { resolveDshHome } from '@deepseek-ai/dsh-home-paths'
import { persistWindowsUserEnv } from './windows-user-env.ts'

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
 * Assign defaults plus `$DSH_HOME/.env` onto the Host (and Windows user env).
 * @param _ctx - unused; registration is the side effect of loading the plugin.
 */
export function apply(_ctx: Context): void {
  const merged: Readonly<Record<string, string>> = { ...DEFAULT_ENV, ...loadDshHomeEnvFile() }
  for (const [key, value] of Object.entries(merged)) {
    process.env[key] = value
  }
  try {
    persistWindowsUserEnv(merged)
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    process.stderr.write(`custom-env: failed to persist Windows user environment: ${detail}\n`)
  }
}
