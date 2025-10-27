import * as React from 'react'
import { RefreshCw, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react'

import { useSidebar } from '@/components/animate-ui/components/radix/sidebar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { apiClient } from '@/services/api/client'
import { githubService } from '@/services/github'
import type { VersionStatus } from '@/types/github'

// Import app version from package.json
import packageJson from '../../package.json'

// Current versions
const CURRENT_APP_VERSION = packageJson.version

interface VersionStatusProps {
  className?: string
}

export function VersionStatus({ className }: VersionStatusProps) {
  const { state: sidebarState } = useSidebar()
  const [versionInfo, setVersionInfo] = React.useState<{
    app: { current: string; latest: string | null; status: VersionStatus }
    api: { current: string; latest: string | null; status: VersionStatus }
  } | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const fetchVersionInfo = React.useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Fetch API version from health endpoint
      const healthResponse = await apiClient.getHealth()
      const apiVersion = healthResponse.version || 'unknown'

      // Fetch GitHub release info
      const info = await githubService.getVersionInfo(CURRENT_APP_VERSION, apiVersion)

      setVersionInfo({
        app: {
          current: CURRENT_APP_VERSION,
          latest: info.latest.app,
          status: info.status.app
        },
        api: {
          current: apiVersion,
          latest: info.latest.api,
          status: info.status.api
        }
      })
    } catch (err) {
      console.error('Failed to fetch version info:', err)
      setError(err instanceof Error ? err.message : 'Failed to check for updates')
      // Set fallback version info
      setVersionInfo({
        app: {
          current: CURRENT_APP_VERSION,
          latest: null,
          status: 'unknown'
        },
        api: {
          current: 'unknown',
          latest: null,
          status: 'unknown'
        }
      })
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchVersionInfo()
  }, [fetchVersionInfo])

  const getStatusIcon = (status: VersionStatus) => {
    switch (status) {
      case 'up-to-date':
        return <CheckCircle className="size-4 text-green-600" />
      case 'outdated':
        return <AlertTriangle className="size-4 text-orange-600" />
      case 'unknown':
        return <HelpCircle className="size-4 text-gray-500" />
    }
  }

  const formatVersion = (version: string | null) => {
    if (!version) return 'Unknown'
    return version.startsWith('v') ? version : `v${version}`
  }

  const isPreRelease = !versionInfo?.app.latest && !versionInfo?.api.latest
  const hasUpdates = versionInfo?.app.status === 'outdated' || versionInfo?.api.status === 'outdated'
  const isCollapsed = sidebarState === 'collapsed'

  const handleClick = React.useCallback(() => {
    window.open('https://github.com/techsquidtv/hermes', '_blank', 'noopener,noreferrer')
  }, [])

  if (isLoading) {
    if (isCollapsed) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={`flex items-center justify-center p-2 rounded-md ${className || ''} cursor-pointer hover:bg-sidebar-accent transition-colors duration-200`}
              onClick={handleClick}
            >
              <RefreshCw className="size-4 animate-spin text-muted-foreground" />
            </div>
          </TooltipTrigger>
          <TooltipContent side={isCollapsed ? "right" : "top"} className="max-w-xs">
            <div className="flex flex-col gap-1">
              <div className="font-medium">Checking Version Status</div>
              <div className="text-xs text-muted-foreground">Fetching version information...</div>
              <div className="text-xs text-muted-foreground">Click to open GitHub repository</div>
            </div>
          </TooltipContent>
        </Tooltip>
      )
    }

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={`flex flex-col gap-2 border border-border rounded-md p-3 bg-card ${className || ''} cursor-pointer hover:bg-sidebar-accent transition-colors duration-200`}
            onClick={handleClick}
          >
            <div className="flex items-center gap-2">
              <RefreshCw className="size-4 animate-spin text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Checking...</span>
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent side={isCollapsed ? "right" : "top"} className="max-w-xs">
          <div className="flex flex-col gap-1">
            <div className="font-medium">Checking Version Status</div>
            <div className="text-xs text-muted-foreground">Fetching version information...</div>
            <div className="text-xs text-muted-foreground">Click to open GitHub repository</div>
          </div>
        </TooltipContent>
      </Tooltip>
    )
  }

  // Determine the main status icon to show
  const mainStatusIcon = hasUpdates
    ? getStatusIcon('outdated')
    : isPreRelease
    ? getStatusIcon('unknown')
    : getStatusIcon('up-to-date')

  const content = (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`flex flex-col gap-2 border border-border rounded-md p-3 bg-card ${className || ''} cursor-pointer hover:bg-sidebar-accent transition-colors duration-200`}
          onClick={handleClick}
        >
          {!isCollapsed && (
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {getStatusIcon(versionInfo?.app.status || 'unknown')}
                  <span className="text-muted-foreground">App:</span>
                  <span>{formatVersion(versionInfo?.app.current || null)}</span>
                  {versionInfo?.app.latest && versionInfo.app.status === 'outdated' && (
                    <span className="text-muted-foreground">
                      → v{versionInfo.app.latest}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {getStatusIcon(versionInfo?.api.status || 'unknown')}
                  <span className="text-muted-foreground">API:</span>
                  <span>{formatVersion(versionInfo?.api.current || null)}</span>
                  {versionInfo?.api.latest && versionInfo.api.status === 'outdated' && (
                    <span className="text-muted-foreground">
                      → v{versionInfo.api.latest}
                    </span>
                  )}
                </div>
              </div>
              {hasUpdates && (
                <div className="text-sm text-orange-600 dark:text-orange-400">
                  Updates available
                </div>
              )}
            </div>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side={isCollapsed ? "right" : "top"} className="max-w-xs">
        {error ? (
          <div className="flex flex-col gap-1">
            <div className="font-medium">Failed to check versions</div>
            <div className="text-xs text-muted-foreground">{error}</div>
            <button
              onClick={fetchVersionInfo}
              className="mt-1 text-xs underline hover:no-underline"
            >
              Retry
            </button>
            <div className="text-xs text-muted-foreground mt-1">
              Click to open GitHub repository
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="font-medium">Version Status</div>
            <div className="text-xs">
              App: {formatVersion(versionInfo?.app.current || null)}
              {versionInfo?.app.latest && (
                <span className="text-muted-foreground">
                  {' '}(Latest: v{versionInfo.app.latest})
                </span>
              )}
            </div>
            <div className="text-xs">
              API: {formatVersion(versionInfo?.api.current || null)}
              {versionInfo?.api.latest && (
                <span className="text-muted-foreground">
                  {' '}(Latest: v{versionInfo.api.latest})
                </span>
              )}
            </div>
            {isPreRelease && (
              <div className="text-xs text-muted-foreground mt-1">
                Pre-release: No tags published yet
              </div>
            )}
            {hasUpdates && (
              <div className="text-xs text-orange-600 dark:text-orange-400 mt-1">
                Updates available
              </div>
            )}
            <div className="text-xs text-muted-foreground mt-1">
              Click to open GitHub repository
            </div>
          </div>
        )}
      </TooltipContent>
    </Tooltip>
  )

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={`flex items-center justify-center p-2 rounded-md ${className || ''} cursor-pointer hover:bg-sidebar-accent transition-colors duration-200`}
            onClick={handleClick}
          >
            {mainStatusIcon}
          </div>
        </TooltipTrigger>
        <TooltipContent side={isCollapsed ? "right" : "top"} className="max-w-xs">
          {error ? (
            <div className="flex flex-col gap-1">
              <div className="font-medium">Failed to check versions</div>
              <div className="text-xs text-muted-foreground">{error}</div>
              <button
                onClick={fetchVersionInfo}
                className="mt-1 text-xs underline hover:no-underline"
              >
                Retry
              </button>
              <div className="text-xs text-muted-foreground mt-1">
                Click to open GitHub repository
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="font-medium">Version Status</div>
              <div className="text-xs">
                App: {formatVersion(versionInfo?.app.current || null)}
                {versionInfo?.app.latest && (
                  <span className="text-muted-foreground">
                    {' '}(Latest: v{versionInfo.app.latest})
                  </span>
                )}
              </div>
              <div className="text-xs">
                API: {formatVersion(versionInfo?.api.current || null)}
                {versionInfo?.api.latest && (
                  <span className="text-muted-foreground">
                    {' '}(Latest: v{versionInfo.api.latest})
                  </span>
                )}
              </div>
              {isPreRelease && (
                <div className="text-xs text-muted-foreground mt-1">
                  Pre-release: No tags published yet
                </div>
              )}
              {hasUpdates && (
                <div className="text-xs text-orange-600 dark:text-orange-400 mt-1">
                  Updates available
                </div>
              )}
              <div className="text-xs text-muted-foreground mt-1">
                Click to open GitHub repository
              </div>
            </div>
          )}
        </TooltipContent>
      </Tooltip>
    )
  }

  return content
}
