import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Search, ArrowUpDown, ChevronDown } from 'lucide-react'

interface QueueFiltersProps {
  statusFilter: string
  onStatusFilterChange: (status: string) => void
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  viewMode: 'active' | 'history' | 'all'
  // Sorting props
  sortBy: 'date' | 'size' | 'title' | 'status'
  sortOrder: 'asc' | 'desc'
  onSortChange: (sortBy: string, sortOrder: string) => void
}

export function QueueFilters({
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange,
  viewMode,
  sortBy,
  sortOrder,
  onSortChange,
}: QueueFiltersProps) {
  // Define available status filters based on view mode
  const getStatusFilters = () => {
    if (viewMode === 'active') {
      return [
        { value: 'all', label: 'All' },
        { value: 'downloading', label: 'Downloading' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'failed', label: 'Failed' },
      ]
    } else if (viewMode === 'history') {
      return [
        { value: 'all', label: 'All' },
        { value: 'completed', label: 'Completed' },
      ]
    } else {
      return [
        { value: 'all', label: 'All' },
        { value: 'downloading', label: 'Downloading' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'completed', label: 'Completed' },
        { value: 'failed', label: 'Failed' },
      ]
    }
  }

  const statusFilters = getStatusFilters()

  // Define available sort options
  const sortOptions = [
    { value: 'date', label: 'Date' },
    { value: 'size', label: 'Size' },
    { value: 'title', label: 'Title' },
    { value: 'status', label: 'Status' },
  ]

  // Get contextually appropriate sort order labels based on sort type
  const getSortOrderLabel = (sortType: string, order: 'asc' | 'desc'): string => {
    switch (sortType) {
      case 'date':
        return order === 'desc' ? 'Newest First' : 'Oldest First'
      case 'size':
        return order === 'desc' ? 'Largest First' : 'Smallest First'
      case 'title':
        return order === 'asc' ? 'A-Z' : 'Z-A'
      case 'status':
        return order === 'asc' ? 'A-Z' : 'Z-A'
      default:
        return order === 'desc' ? 'Descending' : 'Ascending'
    }
  }

  const currentSortLabel = sortOptions.find(opt => opt.value === sortBy)?.label || 'Date'
  const currentOrderLabel = getSortOrderLabel(sortBy, sortOrder)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search downloads..."
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 px-3 py-2 border rounded-md text-sm hover:bg-accent">
              {currentSortLabel} ({currentOrderLabel})
              <ChevronDown className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[200px]">
              {sortOptions.map((option) => (
                <div key={option.value}>
                  <DropdownMenuItem
                    onClick={() => onSortChange(option.value, 'desc')}
                    className={sortBy === option.value && sortOrder === 'desc' ? 'bg-accent' : ''}
                  >
                    {option.label} ({getSortOrderLabel(option.value, 'desc')})
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onSortChange(option.value, 'asc')}
                    className={sortBy === option.value && sortOrder === 'asc' ? 'bg-accent' : ''}
                  >
                    {option.label} ({getSortOrderLabel(option.value, 'asc')})
                  </DropdownMenuItem>
                </div>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {statusFilters.map((filter) => (
          <Badge
            key={filter.value}
            variant={statusFilter === filter.value ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => onStatusFilterChange(filter.value)}
          >
            {filter.label}
          </Badge>
        ))}
      </div>
    </div>
  )
}

