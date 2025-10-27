// GitHub API Service for version checking

import type { VersionInfo } from '@/types/github'

// GitHub Tag API response types
interface GitHubTagRef {
  ref: string
  node_id: string
  url: string
  object: {
    sha: string
    type: string
    url: string
  }
}

class GitHubService {
  private readonly GITHUB_API_BASE = 'https://api.github.com'
  private readonly HERMES_MONOREPO = 'techsquidtv/hermes'

  /**
   * Service for checking version information from GitHub tags.
   * Uses Git tags (hermes-app-v*, hermes-api-v*) instead of releases for better reliability.
   */

  private async request<T>(url: string): Promise<T> {
    try {
      const response = await fetch(url, {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'Hermes-Version-Checker/1.0'
        }
      })

      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status} ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error('[GitHubService] Request failed:', error)
      throw error
    }
  }

  /**
   * Fetch all Git tags from the repository.
   * Uses the GitHub API to get tag references in the format refs/tags/hermes-app-v1.0.0
   */
  async getAllTags(): Promise<GitHubTagRef[]> {
    return this.request<GitHubTagRef[]>(`${this.GITHUB_API_BASE}/repos/${this.HERMES_MONOREPO}/git/refs/tags`)
  }

  getAppTags(tags: GitHubTagRef[]): GitHubTagRef[] {
    return tags.filter(tag =>
      tag.ref.startsWith('refs/tags/hermes-app-v') &&
      // Validate semantic version pattern (e.g., hermes-app-v1.0.0)
      tag.ref.match(/refs\/tags\/hermes-app-v\d+\.\d+\.\d+/)
    )
  }

  getApiTags(tags: GitHubTagRef[]): GitHubTagRef[] {
    return tags.filter(tag =>
      tag.ref.startsWith('refs/tags/hermes-api-v') &&
      // Validate semantic version pattern (e.g., hermes-api-v1.0.0)
      tag.ref.match(/refs\/tags\/hermes-api-v\d+\.\d+\.\d+/)
    )
  }

  extractVersionFromTag(tagRef: string): string | null {
    // Handle tags like 'refs/tags/hermes-app-v1.0.0' -> '1.0.0'
    const match = tagRef.match(/hermes-(?:app|api)-v(.+)/)
    return match ? match[1] : null
  }

  getLatestVersion(tags: GitHubTagRef[]): string | null {
    if (!tags || tags.length === 0) {
      return null
    }

    // Sort tags by version (semantic versioning - highest first)
    const sortedTags = tags.sort((a, b) => {
      const versionA = this.extractVersionFromTag(a.ref)
      const versionB = this.extractVersionFromTag(b.ref)

      if (!versionA || !versionB) return 0

      const partsA = versionA.split('.').map(Number)
      const partsB = versionB.split('.').map(Number)

      for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
        const partA = partsA[i] || 0
        const partB = partsB[i] || 0

        if (partA < partB) return 1 // Higher version first
        if (partA > partB) return -1
      }
      return 0
    })

    const latestTag = sortedTags[0]
    return this.extractVersionFromTag(latestTag.ref)
  }

  compareVersions(currentVersion: string, latestVersion: string | null): 'up-to-date' | 'outdated' | 'unknown' {
    if (!latestVersion) {
      return 'unknown'
    }

    // Remove 'v' prefix if present
    const current = currentVersion.replace(/^v/, '')
    const latest = latestVersion.replace(/^v/, '')

    // Simple semantic version comparison
    const currentParts = current.split('.').map(Number)
    const latestParts = latest.split('.').map(Number)

    for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
      const currentPart = currentParts[i] || 0
      const latestPart = latestParts[i] || 0

      if (currentPart < latestPart) {
        return 'outdated'
      } else if (currentPart > latestPart) {
        return 'up-to-date'
      }
    }

    return 'up-to-date'
  }

  async getVersionInfo(currentAppVersion: string, currentApiVersion: string): Promise<VersionInfo> {
    try {
      const allTags = await this.getAllTags()

      const appTags = this.getAppTags(allTags)
      const apiTags = this.getApiTags(allTags)

      const latestAppVersion = this.getLatestVersion(appTags)
      const latestApiVersion = this.getLatestVersion(apiTags)

      return {
        current: {
          app: currentAppVersion,
          api: currentApiVersion
        },
        latest: {
          app: latestAppVersion,
          api: latestApiVersion
        },
        status: {
          app: this.compareVersions(currentAppVersion, latestAppVersion),
          api: this.compareVersions(currentApiVersion, latestApiVersion)
        },
        releases: {
          app: [], // Keep for backward compatibility, but not used with tags
          api: []
        }
      }
    } catch (error) {
      console.error('[GitHubService] Failed to fetch version info:', error)
      return {
        current: {
          app: currentAppVersion,
          api: currentApiVersion
        },
        latest: {
          app: null,
          api: null
        },
        status: {
          app: 'unknown',
          api: 'unknown'
        },
        releases: {
          app: [],
          api: []
        }
      }
    }
  }

  getReleaseUrl(repo: 'app' | 'api', version: string | null): string | null {
    if (!version) return null

    // Construct the full tag name like 'hermes-app-v1.0.0'
    const tagName = `hermes-${repo}-v${version}`
    return `https://github.com/${this.HERMES_MONOREPO}/releases/tag/${tagName}`
  }
}

export const githubService = new GitHubService()
