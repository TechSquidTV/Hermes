import { ApiError } from '@/lib/errors'
import type { components } from '@/types/api.generated'

type JsonValue = components['schemas']['JsonValue']

export function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

function errorDetail(body: JsonValue): string | null {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null
  const detail: JsonValue = 'detail' in body ? body.detail : null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const entries: JsonValue[] = detail
    const messages = entries.flatMap((item) =>
      item &&
      typeof item === 'object' &&
      !Array.isArray(item) &&
      'msg' in item &&
      typeof item.msg === 'string'
        ? [item.msg]
        : []
    )
    if (messages.length) return messages.join('; ')
  }
  const error: JsonValue = 'error' in body ? body.error : null
  return error &&
    typeof error === 'object' &&
    !Array.isArray(error) &&
    'message' in error &&
    typeof error.message === 'string'
    ? error.message
    : null
}

export async function checkResponse(response: Response): Promise<Response> {
  if (response.ok) return response
  let detail = response.statusText || 'Request failed'
  try {
    const body: JsonValue = await response.json()
    detail = errorDetail(body) ?? detail
  } catch {
    /* A proxy can return an empty or non-JSON error response. */
  }
  throw new ApiError(response.status, detail)
}

export async function withRequestSignal<T>(
  signal: AbortSignal | null | undefined,
  timeoutMs: number,
  action: (signal: AbortSignal) => Promise<T>
): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(
    () => controller.abort(new DOMException('Request timed out', 'TimeoutError')),
    timeoutMs
  )
  const combined = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal
  try {
    combined.throwIfAborted()
    return await action(combined)
  } finally {
    clearTimeout(timeout)
  }
}

export function waitForSignal<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  signal.throwIfAborted()
  return new Promise<T>((resolve, reject) => {
    const abort = () => reject(signal.reason)
    signal.addEventListener('abort', abort, { once: true })
    void promise.then(
      (value) => {
        signal.removeEventListener('abort', abort)
        resolve(value)
      },
      (error) => {
        signal.removeEventListener('abort', abort)
        reject(error)
      }
    )
  })
}
