import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// File size formatting utility
export function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

// Time formatting utilities
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

export function formatTimeRemaining(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }
  if (seconds < 3600) {
    return `${Math.round(seconds / 60)}m`
  }
  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
}

// Date formatting utilities
export function formatRelativeTime(date: Date | string): string {
  const now = new Date()
  const target = new Date(date)
  const diffInSeconds = Math.floor((now.getTime() - target.getTime()) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
  return `${Math.floor(diffInSeconds / 86400)} days ago`
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'Unknown date'

  try {
    const date = new Date(dateString)
    // Check if date is valid
    if (isNaN(date.getTime())) return 'Unknown date'

    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date)
  } catch {
    return 'Unknown date'
  }
}

// URL validation utility
export function isValidUrl(string: string): boolean {
  try {
    new URL(string)
    return true
  } catch {
    return false
  }
}

// Status utilities
export function getStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'default' // Will be styled as success with CSS
    case 'failed':
      return 'destructive'
    case 'downloading':
    case 'processing':
      return 'default'
    case 'queued':
      return 'secondary'
    default:
      return 'outline'
  }
}

export function getStatusIcon(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'CheckCircle'
    case 'failed':
      return 'XCircle'
    case 'downloading':
    case 'processing':
      return 'Loader2'
    case 'queued':
      return 'Clock'
    default:
      return 'AlertCircle'
  }
}

// Progress utilities for download progress calculations
/**
 * Safely extract a numeric value from a progress object
 * @param progressObj The progress object from the API
 * @param key The key to extract from the progress object
 * @returns The numeric value or undefined if not found/invalid
 */
export function getProgressValue(progressObj: { [key: string]: unknown } | null | undefined, key: string): number | undefined {
  if (!progressObj || typeof progressObj !== 'object') return undefined
  const value = progressObj[key]
  return typeof value === 'number' ? value : undefined
}

/**
 * Calculate download progress percentage from progress object
 * @param progressObj The progress object from the API
 * @returns Progress percentage (0-100) or undefined if not calculable
 */
export function calculateProgressPercentage(progressObj: { [key: string]: unknown } | null | undefined): number | undefined {
  if (!progressObj || typeof progressObj !== 'object') return undefined

  // Try different ways the progress might be represented
  const progress = getProgressValue(progressObj, 'percentage') ||
                   getProgressValue(progressObj, 'progress')

  if (typeof progress === 'number' && !isNaN(progress)) {
    return Math.max(0, Math.min(100, progress))
  }

  // Calculate from bytes if percentage is not available
  const downloaded = getProgressValue(progressObj, 'downloaded_bytes') ||
                     getProgressValue(progressObj, 'downloaded') ||
                     getProgressValue(progressObj, 'current')
  const total = getProgressValue(progressObj, 'total_bytes') ||
                getProgressValue(progressObj, 'total')

  if (typeof downloaded === 'number' && typeof total === 'number' && total > 0) {
    const percentage = (downloaded / total) * 100
    return Math.max(0, Math.min(100, percentage))
  }

  return undefined
}




