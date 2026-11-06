import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { withSessionLock } from '../sessionLock'

beforeEach(() => vi.stubGlobal('indexedDB', new IDBFactory()))
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

async function setLease(expiresAt: number): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.open('hermes-session-coordination', 1)
    request.onupgradeneeded = () => request.result.createObjectStore('leases')
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const database = request.result
      const transaction = database.transaction('leases', 'readwrite')
      transaction.objectStore('leases').put({ owner: 'other-tab', expiresAt }, 'refresh')
      transaction.oncomplete = () => { database.close(); resolve() }
      transaction.onabort = () => { database.close(); reject(transaction.error) }
    }
  })
}

it('recovers a lease abandoned by a closed tab', async () => {
  await setLease(Date.now() - 1)
  const action = vi.fn(async () => 'recovered')
  expect(await withSessionLock(new AbortController().signal, action)).toBe('recovered')
  expect(action).toHaveBeenCalledTimes(1)
})

it('cancels a waiting tab without releasing the active owner', async () => {
  let finish!: () => void
  const active = withSessionLock(new AbortController().signal, async () => {
    await new Promise<void>(resolve => { finish = resolve })
    return 'active'
  })
  await vi.waitFor(() => expect(finish).toBeDefined())
  const controller = new AbortController()
  const action = vi.fn(async () => 'should not start')
  const rejected = expect(withSessionLock(controller.signal, action)).rejects.toThrow('cancelled')
  controller.abort(new DOMException('cancelled', 'AbortError'))
  await rejected
  expect(action).not.toHaveBeenCalled()
  finish()
  expect(await active).toBe('active')
  expect(await withSessionLock(new AbortController().signal, async () => 'next')).toBe('next')
})

it('fences a suspended tab after its deadline and preserves a replacement lease', async () => {
  const now = Date.now()
  const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
  await expect(withSessionLock(new AbortController().signal, async assertCurrent => {
    clock.mockReturnValue(now + 61_000)
    await setLease(now + 121_000)
    assertCurrent()
  })).rejects.toThrow('timed out')
  // The old owner's finally must not release a newer owner's lease.
  const controller = new AbortController()
  const action = vi.fn(async () => 'should not start')
  const waiting = expect(withSessionLock(controller.signal, action)).rejects.toThrow('cancelled')
  await new Promise(resolve => setTimeout(resolve, 25))
  controller.abort(new DOMException('cancelled', 'AbortError'))
  await waiting
  expect(action).not.toHaveBeenCalled()
})

it('reports unavailable storage without running the credential exchange', async () => {
  vi.stubGlobal('indexedDB', undefined)
  const action = vi.fn(async () => 'should not start')
  await expect(withSessionLock(new AbortController().signal, action)).rejects.toThrow('Browser storage is required')
  expect(action).not.toHaveBeenCalled()
})
