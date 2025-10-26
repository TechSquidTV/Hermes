// GitHub API Service for version checking

import type { GitHubRelease, VersionInfo } from '@/types/github'

class GitHubService {
  private readonly GITHUB_API_BASE = 'https://api.github.com'
  private readonly HERMES_MONOREPO = 'techsquidtv/hermes'

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

  async getAllReleases(): Promise<GitHubRelease[]> {
    return this.request<GitHubRelease[]>(`${this.GITHUB_API_BASE}/repos/${this.HERMES_MONOREPO}/releases`)
  }

  getAppReleases(releases: GitHubRelease[]): GitHubRelease[] {
    return releases.filter(release =>
      release.tag_name.startsWith('hermes-app-v') &&
      !release.prerelease &&
      !release.draft
    )
  }

  getApiReleases(releases: GitHubRelease[]): GitHubRelease[] {
    return releases.filter(release =>
      release.tag_name.startsWith('hermes-api-v') &&
      !release.prerelease &&
      !release.draft
    )
  }

  extractVersionFromTag(tagName: string): string | null {
    // Handle tags like 'hermes-app-v1.0.0' -> '1.0.0'
    const match = tagName.match(/hermes-(?:app|api)-v(.+)/)
    return match ? match[1] : null
  }

  getLatestVersion(releases: GitHubRelease[]): string | null {
    if (!releases || releases.length === 0) {
      return null
    }

    const latestRelease = releases[0]
    return this.extractVersionFromTag(latestRelease.tag_name)
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
      const allReleases = await this.getAllReleases()

      const appReleases = this.getAppReleases(allReleases)
      const apiReleases = this.getApiReleases(allReleases)

      const latestAppVersion = this.getLatestVersion(appReleases)
      const latestApiVersion = this.getLatestVersion(apiReleases)

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
          app: appReleases,
          api: apiReleases
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
