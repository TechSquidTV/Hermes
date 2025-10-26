import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { StatsCard } from '@/components/ui/stats-card'
import { formatFileSize } from '@/lib/utils'
import { Download, CheckCircle, TrendingUp, HardDrive } from 'lucide-react'

export function QueueStats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['queue', 'stats'],
    queryFn: () => apiClient.getApiStats(),
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <StatsCard
            key={i}
            title="Loading..."
            value="..."
            isLoading={true}
            size="default"
          />
        ))}
      </div>
    )
  }

  const totalDownloads = stats?.successful_downloads || 0
  const successRate = stats?.success_rate || 0
  const totalSize = stats?.total_bandwidth_used || 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatsCard
        title="Total Downloads"
        value={totalDownloads}
        icon={Download}
        variant="default"
        size="default"
        isLoading={isLoading}
      />

      <StatsCard
        title="Success Rate"
        value={`${successRate.toFixed(1)}%`}
        icon={CheckCircle}
        variant="success"
        size="default"
        isLoading={isLoading}
      />

      <StatsCard
        title="Total Downloaded"
        value={formatFileSize(totalSize)}
        icon={HardDrive}
        variant="default"
        size="default"
        isLoading={isLoading}
      />

      <StatsCard
        title="Avg Download Time"
        value={stats?.average_download_time ? `${Math.round(stats.average_download_time)}s` : 'N/A'}
        icon={TrendingUp}
        variant="default"
        size="default"
        isLoading={isLoading}
      />
    </div>
  )
}

