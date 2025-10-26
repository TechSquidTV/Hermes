import { Badge } from '@/components/ui/badge'
import {
  XCircle,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock
} from 'lucide-react'
import { getStatusVariant } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
  size?: 'sm' | 'default' | 'lg'
  showIcon?: boolean
  className?: string
}

const statusIcons = {
  completed: CheckCircle2,
  failed: XCircle,
  downloading: Loader2,
  processing: Loader2,
  queued: Clock,
  default: AlertCircle,
} as const

export function StatusBadge({
  status,
  variant,
  size = 'default',
  showIcon = true,
  className
}: StatusBadgeProps) {
  const statusVariant = variant || getStatusVariant(status)
  const Icon = statusIcons[status.toLowerCase() as keyof typeof statusIcons] || statusIcons.default

  const iconProps = {
    className: cn(
      size === 'sm' && 'h-3 w-3',
      size === 'default' && 'h-3 w-3',
      size === 'lg' && 'h-4 w-4'
    )
  }

  const isAnimated = ['downloading', 'processing'].includes(status.toLowerCase())

  return (
    <Badge
      variant={statusVariant}
      className={cn(
        'flex items-center gap-1',
        isAnimated && 'animate-pulse',
        className
      )}
    >
      {showIcon && (
        <Icon
          {...iconProps}
          className={cn(
            iconProps.className,
            isAnimated && status.toLowerCase() === 'downloading' && 'animate-spin'
          )}
        />
      )}
      <span className="capitalize">{status}</span>
    </Badge>
  )
}
