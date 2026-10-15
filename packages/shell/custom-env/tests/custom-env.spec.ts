/**
 * Plugin apply: process.env assignment and Windows persist hand-off.
 */

import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Context } from '@deepseek-ai/cordis'

const persist = vi.hoisted(() => vi.fn())

vi.mock('../src/windows-user-env.ts', () => ({
  persistWindowsUserEnv: persist,
}))

afterEach(() => {
  persist.mockReset()
  vi.unstubAllEnvs()
})

describe('custom-env apply', () => {
  it('assigns $DSH_HOME/.env onto process.env and persists on Windows', async () => {
    const home = mkdtempSync(join(tmpdir(), 'dsh-custom-env-'))
    writeFileSync(join(home, '.env'), 'CUSTOM_ENV_TEST_KEY=hello\n', 'utf8')
    vi.stubEnv('DSH_HOME', home)
    persist.mockImplementation(() => {})

    const { apply } = await import('../src/index.ts')
    apply(new Context())

    expect(process.env.CUSTOM_ENV_TEST_KEY).toBe('hello')
    expect(persist).toHaveBeenCalledWith({ CUSTOM_ENV_TEST_KEY: 'hello' })
    delete process.env.CUSTOM_ENV_TEST_KEY
  })

  it('keeps process.env when Windows persist throws', async () => {
    const home = mkdtempSync(join(tmpdir(), 'dsh-custom-env-'))
    writeFileSync(join(home, '.env'), 'CUSTOM_ENV_TEST_KEY=kept\n', 'utf8')
    vi.stubEnv('DSH_HOME', home)
    persist.mockImplementation(() => {
      throw new Error('boom')
    })
    const write = vi.spyOn(process.stderr, 'write').mockImplementation(() => true)

    const { apply } = await import('../src/index.ts')
    apply(new Context())

    expect(process.env.CUSTOM_ENV_TEST_KEY).toBe('kept')
    expect(write).toHaveBeenCalled()
    write.mockRestore()
    delete process.env.CUSTOM_ENV_TEST_KEY
  })
})
