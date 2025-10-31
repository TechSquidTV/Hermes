import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useStatsSSE } from '@/hooks/useStatsSSE'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts'
import { TrendingUp, TrendingDown, Activity, ChevronDown } from 'lucide-react'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

export function QueueCharts() {
  const [selectedPeriod, setSelectedPeriod] = useState<'day' | 'week' | 'month' | 'year'>('week')

  // Connect to stats SSE for real-time updates
  useStatsSSE()

  // Use React Query for data fetching (will be invalidated by SSE updates)
  const { data: timelineData, isLoading: isLoadingTimeline } = useQuery({
    queryKey: ['timeline', selectedPeriod],
    queryFn: () => apiClient.getTimelineStats(selectedPeriod),
  })

  const { data: timelineSummary, isLoading: isLoadingSummary } = useQuery({
    queryKey: ['timeline', 'summary', selectedPeriod],
    queryFn: () => apiClient.getTimelineSummary(selectedPeriod),
  })

  const { data: statsData, isLoading: isLoadingStats } = useQuery({
    queryKey: ['analytics', 'stats', selectedPeriod],
    queryFn: () => apiClient.getApiStats(selectedPeriod),
  })

  const isLoading = isLoadingTimeline || isLoadingSummary || isLoadingStats

  // Transform timeline data for line chart
  const chartData = timelineData?.map(item => ({
    date: new Date(item.date).toLocaleDateString(),
    downloads: item.downloads,
    successRate: Math.round(item.success_rate * 100),
    totalSize: Math.round(item.total_size / 1024 / 1024), // Convert to MB
  })) || []

  // Transform stats data for extractor pie chart
  const extractorData = statsData?.popular_extractors?.map((item, index) => ({
    name: item.extractor,
    value: item.count,
    percentage: item.percentage,
    fill: COLORS[index % COLORS.length],
  })) || []

  // Transform error data for bar chart
  const errorData = statsData?.error_breakdown?.map((item, index) => ({
    name: item.error_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    count: item.count,
    percentage: item.percentage,
    fill: COLORS[index % COLORS.length],
  })) || []

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Timeline Loading...</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Statistics Loading...</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {timelineSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Downloads</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timelineSummary.total_downloads}</div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                {timelineSummary.trend === 'increasing' ? (
                  <TrendingUp className="h-3 w-3 text-green-500" />
                ) : timelineSummary.trend === 'decreasing' ? (
                  <TrendingDown className="h-3 w-3 text-red-500" />
                ) : (
                  <Activity className="h-3 w-3 text-gray-500" />
                )}
                {timelineSummary.trend} over {timelineSummary.days_count} days
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Math.round(timelineSummary.success_rate * 100)}%</div>
              <div className="text-xs text-muted-foreground">
                {timelineSummary.total_downloads} downloads
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Daily Average</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timelineSummary.avg_daily_downloads}</div>
              <div className="text-xs text-muted-foreground">
                downloads per day
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Peak Day</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timelineSummary.peak_downloads}</div>
              <div className="text-xs text-muted-foreground">
                {timelineSummary.peak_day ? new Date(timelineSummary.peak_day).toLocaleDateString() : 'No data'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="timeline" className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="timeline">Downloads Over Time</TabsTrigger>
            <TabsTrigger value="extractors">By Extractor</TabsTrigger>
            <TabsTrigger value="errors">Error Analysis</TabsTrigger>
          </TabsList>

          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 px-3 py-2 border rounded-md text-sm hover:bg-accent">
              {selectedPeriod === 'day' ? 'Last Day' :
               selectedPeriod === 'week' ? 'Last Week' :
               selectedPeriod === 'month' ? 'Last Month' : 'Last Year'}
              <ChevronDown className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setSelectedPeriod('day')}>
                Last Day
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod('week')}>
                Last Week
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod('month')}>
                Last Month
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSelectedPeriod('year')}>
                Last Year
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Downloads Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="downloads"
                      stroke="#8884d8"
                      strokeWidth={2}
                      dot={{ fill: '#8884d8' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Success Rate Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip formatter={(value) => [`${value}%`, 'Success Rate']} />
                      <Line
                        type="monotone"
                        dataKey="successRate"
                        stroke="#00C49F"
                        strokeWidth={2}
                        dot={{ fill: '#00C49F' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="extractors" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Popular Extractors</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={extractorData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percentage }) => `${name} (${percentage}%)`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {extractorData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Extractor Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {extractorData.map((item) => (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: item.fill }}
                        />
                        <span className="text-sm">{item.name}</span>
                      </div>
                      <span className="text-sm font-medium">{item.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Error Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={errorData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#FF8042" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

