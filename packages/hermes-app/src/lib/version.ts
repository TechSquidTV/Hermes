const SEMVER_VERSION_PATTERN = /^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/

export function resolveCurrentAppVersion(
  packageVersion: string,
  buildVersion = import.meta.env.VITE_HERMES_BUILD_VERSION
): string {
  const normalizedBuildVersion = buildVersion?.trim()
  return normalizedBuildVersion || packageVersion
}

export function formatVersion(version: string | null): string {
  if (!version) return 'Unknown'
  if (version.startsWith('v')) return version
  if (!SEMVER_VERSION_PATTERN.test(version)) return version
  return `v${version}`
}

export function isComparableVersion(version: string): boolean {
  return SEMVER_VERSION_PATTERN.test(version)
}
