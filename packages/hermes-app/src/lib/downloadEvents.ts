import type { components } from '@/types/api.generated'

type DownloadStatus = components['schemas']['DownloadStatus']
type Snake<S extends string> = S extends `${infer First}${infer Rest}`
  ? `${First extends Lowercase<First> ? First : `_${Lowercase<First>}`}${Snake<Rest>}`
  : S
type SnakeKeys<T> = T extends readonly (infer Item)[]
  ? SnakeKeys<Item>[]
  : T extends object
    ? { [Key in keyof T as Key extends string ? Snake<Key> : Key]: SnakeKeys<T[Key]> }
    : T

/** The worker emits snake_case event data; HTTP responses use the generated camelCase schema. */
export type DownloadEvent = Omit<
  Partial<SnakeKeys<DownloadStatus>>,
  'error' | 'current_filename'
> & {
  error_message?: string | null
  output_path?: string | null
}

export function normalizeDownloadEvent(
  raw: DownloadEvent,
  previous?: DownloadStatus
): DownloadStatus | null {
  if (!raw.download_id || !raw.status) return null
  const progress = raw.progress
  const result = raw.result
  return {
    ...previous,
    downloadId: raw.download_id,
    status: raw.status,
    message: raw.message ?? `Download ${raw.status}`,
    createdAt: previous?.createdAt ?? raw.created_at ?? new Date().toISOString(),
    currentFilename: raw.output_path ?? previous?.currentFilename,
    error: raw.error_message ?? null,
    progress: progress
      ? {
          percentage: progress.percentage,
          status: progress.status,
          downloadedBytes: progress.downloaded_bytes,
          totalBytes: progress.total_bytes,
          speed: progress.speed,
          eta: progress.eta,
        }
      : previous?.progress,
    result: result
      ? {
          url: result.url ?? previous?.result?.url,
          title: result.title ?? previous?.result?.title,
          fileSize: result.file_size ?? previous?.result?.fileSize,
          duration: result.duration ?? previous?.result?.duration,
          thumbnailUrl: result.thumbnail_url ?? previous?.result?.thumbnailUrl,
          extractor: result.extractor ?? previous?.result?.extractor,
          description: result.description ?? previous?.result?.description,
        }
      : previous?.result,
  }
}
