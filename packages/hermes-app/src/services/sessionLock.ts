import { debug } from '@/lib/debug'
import { waitForSignal } from './http'

const DATABASE = 'hermes-session-coordination'
const STORE = 'leases'
const KEY = 'refresh'
export const SESSION_REFRESH_TIMEOUT_MS = 30_000
const LEASE_MS = SESSION_REFRESH_TIMEOUT_MS * 2

interface Lease { owner: string; expiresAt: number }

function openDatabase(signal: AbortSignal): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('Browser storage is required to refresh your session'))
      return
    }
    let unavailable = false
    const request = indexedDB.open(DATABASE, 1)
    const abort = () => { unavailable = true; reject(signal.reason) }
    signal.addEventListener('abort', abort, { once: true })
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onerror = () => {
      signal.removeEventListener('abort', abort)
      reject(new Error('Unable to open session coordination storage'))
    }
    request.onblocked = () => {
      unavailable = true
      signal.removeEventListener('abort', abort)
      reject(new Error('Session coordination storage is blocked'))
    }
    request.onsuccess = () => {
      signal.removeEventListener('abort', abort)
      if (unavailable || signal.aborted) { request.result.close(); reject(signal.reason); return }
      request.result.onversionchange = () => request.result.close()
      resolve(request.result)
    }
  })
}

function changeLease(database: IDBDatabase, owner: string, operation: 'acquire' | 'release', signal?: AbortSignal): Promise<boolean> {
  return new Promise((resolve, reject) => {
    signal?.throwIfAborted()
    const transaction = database.transaction(STORE, 'readwrite')
    const store = transaction.objectStore(STORE)
    const request = store.get(KEY)
    let acquired = false
    const abort = () => transaction.abort()
    signal?.addEventListener('abort', abort, { once: true })
    request.onsuccess = () => {
      const lease: Lease | undefined = request.result
      if (operation === 'release') {
        if (lease?.owner === owner) store.delete(KEY)
      } else if (!lease || lease.expiresAt <= Date.now()) {
        store.put({ owner, expiresAt: Date.now() + LEASE_MS } satisfies Lease, KEY)
        acquired = true
      }
    }
    transaction.oncomplete = () => {
      signal?.removeEventListener('abort', abort)
      resolve(acquired)
    }
    transaction.onabort = () => {
      signal?.removeEventListener('abort', abort)
      reject(signal?.aborted ? signal.reason : new Error('Session coordination transaction failed'))
    }
  })
}

/** Short atomic leases coordinate tabs on HTTP and HTTPS without holding a transaction during fetch. */
export async function withSessionLock<T>(signal: AbortSignal, action: (assertCurrent: () => void) => Promise<T>): Promise<T> {
  const deadline = Date.now() + SESSION_REFRESH_TIMEOUT_MS
  const owner = Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-')
  const assertCurrent = () => {
    signal.throwIfAborted()
    // Wall time also fences a tab that was suspended while its timers were paused.
    if (Date.now() >= deadline) throw new DOMException('Session refresh timed out', 'TimeoutError')
  }
  assertCurrent()
  const database = await openDatabase(signal)
  let acquired = false
  try {
    while (!acquired) {
      assertCurrent()
      acquired = await changeLease(database, owner, 'acquire', signal)
      if (!acquired) await waitForSignal(new Promise<void>(resolve => setTimeout(resolve, 100)), signal)
    }
    assertCurrent()
    return await action(assertCurrent)
  } finally {
    if (acquired) {
      try { await changeLease(database, owner, 'release') }
      catch (error) { debug.error('Unable to release session coordination lease', error) }
    }
    database.close()
  }
}
