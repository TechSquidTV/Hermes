import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatsCardProps {
  title: string
  value: string | number
  icon?: LucideIcon
  description?: string
  trend?: {
    value: number
    isPositive: boolean
    label: string
  }
  variant?: 'default' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'default' | 'lg'
  isLoading?: boolean
  className?: string
  onClick?: () => void
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  variant = 'default',
  size = 'default',
  isLoading = false,
  className,
  onClick,
}: StatsCardProps) {
  const sizeClasses = {
    sm: {
      card: 'p-4',
      header: 'pb-2',
      title: 'text-sm',
      value: 'text-lg',
      icon: 'h-4 w-4',
    },
    default: {
      card: 'p-6',
      header: 'pb-3',
      title: 'text-sm',
      value: 'text-2xl',
      icon: 'h-8 w-8',
    },
    lg: {
      card: 'p-8',
      header: 'pb-4',
      title: 'text-base',
      value: 'text-4xl',
      icon: 'h-12 w-12',
    },
  }

  const variantClasses = {
    default: 'border-border',
    success: 'border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20',
    warning: 'border-yellow-200 bg-yellow-50/50 dark:border-yellow-800 dark:bg-yellow-950/20',
    error: 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20',
  }

  if (isLoading) {
    return (
      <Card className={cn(className)}>
        <CardContent className={sizeClasses[size].card}>
          <div className="flex items-center">
            <Skeleton className={cn('rounded-full', sizeClasses[size].icon)} />
            <div className="ml-4 flex-1">
              <Skeleton className={cn('mb-2', sizeClasses[size].title)} />
              <Skeleton className={sizeClasses[size].value} />
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={cn(
        variantClasses[variant],
        onClick && 'cursor-pointer hover:shadow-md transition-shadow',
        className
      )}
      onClick={onClick}
    >
      <CardContent className={sizeClasses[size].card}>
        <div className="flex items-center">
          {Icon && (
            <div className={cn(
              'rounded-full p-2',
              variant === 'success' && 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400',
              variant === 'warning' && 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-400',
              variant === 'error' && 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400',
              variant === 'default' && 'bg-muted text-muted-foreground'
            )}>
              <Icon className={sizeClasses[size].icon} />
            </div>
          )}
          <div className="ml-4 flex-1">
            <p className={cn(
              'font-medium text-muted-foreground mb-1',
              sizeClasses[size].title
            )}>
              {title}
            </p>
            <p className={cn(
              'font-bold',
              sizeClasses[size].value,
              variant === 'success' && 'text-green-600 dark:text-green-400',
              variant === 'warning' && 'text-yellow-600 dark:text-yellow-400',
              variant === 'error' && 'text-red-600 dark:text-red-400'
            )}>
              {value}
            </p>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">
                {description}
              </p>
            )}
          </div>
          {trend && (
            <Badge
              variant={trend.isPositive ? 'default' : 'secondary'}
              className={cn(
                'ml-2',
                trend.isPositive && 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                !trend.isPositive && 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              )}
            >
              {trend.isPositive ? '+' : ''}{trend.value}% {trend.label}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
