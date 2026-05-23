import { describe, expect, it } from 'vitest'

import { formatVersion, isComparableVersion, resolveCurrentAppVersion } from '@/lib/version'

describe('version utilities', () => {
  it('uses CI build version before package version', () => {
    expect(resolveCurrentAppVersion('0.4.0', 'v0.4.0')).toBe('v0.4.0')
  })

  it('falls back to package version when build version is missing', () => {
    expect(resolveCurrentAppVersion('0.4.0', undefined)).toBe('0.4.0')
    expect(resolveCurrentAppVersion('0.4.0', '   ')).toBe('0.4.0')
  })

  it('formats semantic versions with a v prefix', () => {
    expect(formatVersion('0.4.0')).toBe('v0.4.0')
    expect(formatVersion('v0.4.0')).toBe('v0.4.0')
  })

  it('leaves non-semver build labels unchanged', () => {
    expect(formatVersion('develop-abc123')).toBe('develop-abc123')
  })

  it('identifies versions that can be compared against release tags', () => {
    expect(isComparableVersion('0.4.0')).toBe(true)
    expect(isComparableVersion('v0.4.0')).toBe(true)
    expect(isComparableVersion('develop-abc123')).toBe(false)
  })
})
