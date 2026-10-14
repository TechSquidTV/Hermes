import { useState } from 'react'

interface Progress {
  id: string
  status: string | undefined
  value: number
}
export function useMonotonicProgress(
  rawProgress: number | null | undefined,
  status: string | undefined,
  downloadId: string
): number {
  const [previous, setPrevious] = useState<Progress>({ id: downloadId, status, value: 0 })
  const reset =
    previous.id !== downloadId ||
    status === 'pending' ||
    (status === 'downloading' &&
      ['failed', 'cancelled', 'completed'].includes(previous.status ?? ''))
  const value =
    status === 'pending'
      ? 0
      : status === 'completed'
        ? 100
        : reset
          ? (rawProgress ?? 0)
          : status === 'downloading' || status === 'processing'
            ? Math.max(previous.value, rawProgress ?? 0)
            : previous.value
  if (previous.id !== downloadId || previous.status !== status || previous.value !== value)
    setPrevious({ id: downloadId, status, value })
  return value
}
