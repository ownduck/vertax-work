/**
 * Unit coverage for Windows user-env persistence without loading real koffi.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  encodeRegSz,
  persistWindowsUserEnv,
  setWindowsUserEnvBindingsForTests,
  type WindowsUserEnvBindings,
} from '../src/windows-user-env.ts'

afterEach(() => {
  setWindowsUserEnvBindingsForTests(undefined)
})

function mockBindings(overrides: Partial<WindowsUserEnvBindings> = {}) {
  const openKey = vi.fn((_h: number, _sub: string, _opt: number, _sam: number, result: [unknown]) => {
    result[0] = { handle: 1 }
    return 0
  })
  const setValue = vi.fn(() => 0)
  const closeKey = vi.fn(() => 0)
  const sendMessageTimeout = vi.fn(() => 1)
  setWindowsUserEnvBindingsForTests({
    openKey: overrides.openKey ?? openKey,
    setValue: overrides.setValue ?? setValue,
    closeKey: overrides.closeKey ?? closeKey,
    sendMessageTimeout: overrides.sendMessageTimeout ?? sendMessageTimeout,
  })
  return { openKey, setValue, closeKey, sendMessageTimeout }
}

describe('encodeRegSz', () => {
  it('encodes UTF-16LE with a trailing NUL', () => {
    expect(encodeRegSz('ab')).toEqual(Buffer.from('ab\0', 'utf16le'))
  })
})

describe('persistWindowsUserEnv', () => {
  it('is a no-op on non-Windows platforms', () => {
    const api = mockBindings()
    persistWindowsUserEnv({ A: '1' }, 'linux')
    expect(api.openKey).not.toHaveBeenCalled()
  })

  it('is a no-op for an empty map', () => {
    const api = mockBindings()
    persistWindowsUserEnv({}, 'win32')
    expect(api.openKey).not.toHaveBeenCalled()
  })

  it('writes each entry and broadcasts WM_SETTINGCHANGE on Windows', () => {
    const api = mockBindings()
    persistWindowsUserEnv({ FOO: 'bar', BAZ: 'qux' }, 'win32')
    expect(api.openKey).toHaveBeenCalledOnce()
    expect(api.setValue).toHaveBeenCalledTimes(2)
    expect(api.closeKey).toHaveBeenCalledOnce()
    expect(api.sendMessageTimeout).toHaveBeenCalledOnce()
  })

  it('closes the key when RegSetValueExW fails', () => {
    const api = mockBindings({
      setValue: vi.fn(() => 5),
    })
    expect(() => persistWindowsUserEnv({ FOO: 'bar' }, 'win32')).toThrow(/RegSetValueExW\(FOO\)/)
    expect(api.closeKey).toHaveBeenCalledOnce()
  })

  it('throws when RegOpenKeyExW fails', () => {
    mockBindings({
      openKey: vi.fn(() => 2),
    })
    expect(() => persistWindowsUserEnv({ FOO: 'bar' }, 'win32')).toThrow(/RegOpenKeyExW/)
  })
})
