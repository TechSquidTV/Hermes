import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { QueueFilters } from './QueueFilters'
import { QueueCharts } from './QueueCharts'
import { QueueTabContent } from './QueueTabContent'
import { getQueueDisplayStatusFilter } from '@/lib/queueData'
import type { QueueSearch } from '@/lib/queueSearch'

interface QueueViewProps {
  search: QueueSearch
  onChange: (patch: Partial<QueueSearch>) => void
}
export function QueueView({ search, onChange }: QueueViewProps) {
  return (
    <Tabs
      value={search.view}
      onValueChange={(view) => {
        if (view === 'active' || view === 'history' || view === 'all' || view === 'charts')
          onChange({ view, status: 'all' })
      }}
      className="space-y-6"
    >
      <TabsList>
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="history">History</TabsTrigger>
        <TabsTrigger value="all">All</TabsTrigger>
        <TabsTrigger value="charts">Analytics</TabsTrigger>
      </TabsList>
      {(['active', 'history', 'all'] as const).map((view) => (
        <TabsContent key={view} value={view} className="space-y-4">
          <QueueFilters
            statusFilter={getQueueDisplayStatusFilter(view, search.status)}
            onStatusFilterChange={(status) => onChange({ status })}
            searchQuery={search.search}
            onSearchQueryChange={(value) => onChange({ search: value })}
            viewMode={view}
            sortBy={search.sort}
            sortOrder={search.order}
            onSortChange={(sort, order) => onChange({ sort, order })}
          />
          <QueueTabContent
            key={`${view}:${search.status}:${search.search}:${search.sort}:${search.order}`}
            viewMode={view}
            statusFilter={search.status}
            searchQuery={search.search}
            sortBy={search.sort}
            sortOrder={search.order}
            showStats={view === 'history'}
          />
        </TabsContent>
      ))}
      <TabsContent value="charts">
        <QueueCharts />
      </TabsContent>
    </Tabs>
  )
}
