import { describe, expect, it } from 'vitest'
import { getQueueQueryKey } from '../useQueueData'

describe('useQueueData helpers', () => {
  it('keys queue data by filter, view, and pagination', () => {
    expect(getQueueQueryKey('downloading', 'active', 50, 20)).toEqual([
      'queue',
      'downloading',
      'active',
      50,
      20,
    ])
  })
})
