// GitHub API Types for version checking

export interface GitHubRelease {
  id: number
  tag_name: string
  target_commitish: string
  name: string | null
  body: string | null
  url: string
  html_url: string
  assets_url: string
  upload_url: string
  tarball_url: string
  zipball_url: string
  draft: boolean
  prerelease: boolean
  created_at: string
  published_at: string | null
  author: {
    login: string
    id: number
    node_id: string
    avatar_url: string
    gravatar_id: string | null
    url: string
    html_url: string
    followers_url: string
    following_url: string
    gists_url: string
    starred_url: string
    subscriptions_url: string
    organizations_url: string
    repos_url: string
    events_url: string
    received_events_url: string
    type: string
    site_admin: boolean
  }
  assets: GitHubAsset[]
}

export interface GitHubAsset {
  id: number
  name: string
  size: number
  download_count: number
  browser_download_url: string
}

export interface VersionInfo {
  current: {
    app: string
    api: string
  }
  latest: {
    app: string | null
    api: string | null
  }
  status: {
    app: 'up-to-date' | 'outdated' | 'unknown'
    api: 'up-to-date' | 'outdated' | 'unknown'
  }
  releases: {
    app: GitHubRelease[]
    api: GitHubRelease[]
  }
}

export type VersionStatus = 'up-to-date' | 'outdated' | 'unknown'
