import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { QueueFilters } from './QueueFilters'
import { QueueCharts } from './QueueCharts'
import { QueueTabContent } from './QueueTabContent'
import { useViewMode } from '@/hooks/useViewMode'
import { useFilters } from '@/hooks/useFilters'
import type { FilterState } from '@/hooks/useFilters'

export function QueueView() {
  const { mode: viewMode, setMode: setViewMode } = useViewMode()
  const { filters, updateFilter } = useFilters({ initialViewMode: viewMode as FilterState['viewMode'] })

  return (
    <div className="space-y-6">
      <Tabs value={viewMode} onValueChange={(value: string) => setViewMode(value as FilterState['viewMode'])}>
        <TabsList>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="charts">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4">
          <QueueFilters
            statusFilter={filters.statusFilter}
            onStatusFilterChange={(status) => updateFilter('statusFilter', status)}
            searchQuery={filters.searchQuery}
            onSearchQueryChange={(query) => updateFilter('searchQuery', query)}
            viewMode="active"
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
            onSortChange={(sortBy, sortOrder) => {
              updateFilter('sortBy', sortBy as FilterState['sortBy'])
              updateFilter('sortOrder', sortOrder as FilterState['sortOrder'])
            }}
          />

          <QueueTabContent
            viewMode="active"
            statusFilter={filters.statusFilter}
            searchQuery={filters.searchQuery}
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
          />
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <QueueFilters
            statusFilter={filters.statusFilter}
            onStatusFilterChange={(status) => updateFilter('statusFilter', status)}
            searchQuery={filters.searchQuery}
            onSearchQueryChange={(query) => updateFilter('searchQuery', query)}
            viewMode="history"
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
            onSortChange={(sortBy, sortOrder) => {
              updateFilter('sortBy', sortBy as FilterState['sortBy'])
              updateFilter('sortOrder', sortOrder as FilterState['sortOrder'])
            }}
          />

          <QueueTabContent
            viewMode="history"
            statusFilter={filters.statusFilter}
            searchQuery={filters.searchQuery}
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
            showStats={true}
          />
        </TabsContent>

        <TabsContent value="all" className="mt-6">
          <QueueFilters
            statusFilter={filters.statusFilter}
            onStatusFilterChange={(status) => updateFilter('statusFilter', status)}
            searchQuery={filters.searchQuery}
            onSearchQueryChange={(query) => updateFilter('searchQuery', query)}
            viewMode="all"
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
            onSortChange={(sortBy, sortOrder) => {
              updateFilter('sortBy', sortBy as FilterState['sortBy'])
              updateFilter('sortOrder', sortOrder as FilterState['sortOrder'])
            }}
          />

          <QueueTabContent
            viewMode="all"
            statusFilter={filters.statusFilter}
            searchQuery={filters.searchQuery}
            sortBy={filters.sortBy}
            sortOrder={filters.sortOrder}
          />
        </TabsContent>

        <TabsContent value="charts" className="mt-6">
          <QueueCharts />
        </TabsContent>
      </Tabs>
    </div>
  )
}

