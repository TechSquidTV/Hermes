import type { QueueRequestParams } from '@/types'

export interface QueueSearch {
  view: NonNullable<QueueRequestParams['view_mode']> | 'charts'
  status: string
  search: string
  sort: NonNullable<QueueRequestParams['sort_by']>
  order: NonNullable<QueueRequestParams['sort_order']>
}
const views = ['active', 'history', 'all', 'charts'] as const
const sorts = ['date', 'size', 'title', 'status'] as const
export function validateQueueSearch(input: Record<string, unknown>): QueueSearch {
  return {
    view: views.find((value) => value === input.view) ?? 'active',
    status: typeof input.status === 'string' ? input.status : 'all',
    search: typeof input.search === 'string' ? input.search.slice(0, 200) : '',
    sort: sorts.find((value) => value === input.sort) ?? 'date',
    order: input.order === 'asc' ? 'asc' : 'desc',
  }
}
