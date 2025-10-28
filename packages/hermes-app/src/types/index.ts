/**
 * Central type exports for the application
 *
 * This file re-exports commonly used types from:
 * - Auto-generated API types (api.generated.ts)
 * - Custom application types (auth.ts, github.ts, etc.)
 */

// Re-export custom types
export * from './auth'
export * from './github'

// Re-export the full generated components namespace for advanced usage
export type { components, paths, operations } from './api.generated'

// Convenience aliases for commonly used API types
// These save you from writing `components["schemas"]["TypeName"]` everywhere
import type { components } from './api.generated'

export type DownloadStatus = components["schemas"]["DownloadStatus"]
export type DownloadResult = components["schemas"]["DownloadResult"]
export type DownloadProgress = components["schemas"]["DownloadProgress"]
export type VideoInfo = components["schemas"]["VideoInfo"]
export type PlaylistEntry = components["schemas"]["PlaylistEntry"]
export type DownloadRequest = components["schemas"]["DownloadRequest"]
export type BatchDownloadRequest = components["schemas"]["BatchDownloadRequest"]
export type BatchDownloadResponse = components["schemas"]["BatchDownloadResponse"]
export type DownloadResponse = components["schemas"]["DownloadResponse"]

// Add more type aliases here as needed
// Pattern: export type TypeName = components["schemas"]["TypeName"]
