import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { User, Mail, LogOut, Key } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { formatDistanceToNow } from 'date-fns'

export function GeneralSettings() {
  const { user, logout } = useAuth()

  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  return (
    <div className="space-y-6">
      {/* Application Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Application Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">Version</Badge>
                <span className="text-sm">{healthData?.version || '1.0.0'}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">Environment</Badge>
                <span className="text-sm">{healthData?.environment || 'development'}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">API Server</Badge>
                <span className="text-sm">
                  {(() => {
                    const apiBase = import.meta.env.VITE_API_BASE_URL
                    if (import.meta.env.DEV) {
                      // Development: API runs on localhost:8000
                      return 'localhost:8000'
                    }
                    // Production: Extract domain from VITE_API_BASE_URL
                    if (apiBase && apiBase.startsWith('http')) {
                      return apiBase.replace(/^https?:\/\//, '').replace(/\/api\/v1$/, '')
                    }
                    // Fallback to current domain
                    return `${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}`
                  })()}
                </span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">Status</Badge>
                <Badge variant={healthData?.status === 'healthy' ? 'success' : 'destructive'}>
                  {healthData?.status || 'checking...'}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">Uptime</Badge>
                <span className="text-sm">
                  {healthData?.timestamp ?
                    formatDistanceToNow(new Date(healthData.timestamp), { addSuffix: true }) :
                    'calculating...'
                  }
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            User Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Email</span>
              </div>
              <p className="text-sm text-muted-foreground pl-6">
                {user?.email || 'admin'}
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Username</span>
              </div>
              <p className="text-sm text-muted-foreground pl-6">
                {user?.username || 'admin'}
              </p>
            </div>
          </div>

          <Separator />

          <div className="flex flex-col sm:flex-row gap-2">
            <Button variant="outline" size="sm">
              <Key className="h-4 w-4 mr-2" />
              Change Password
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={logout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
