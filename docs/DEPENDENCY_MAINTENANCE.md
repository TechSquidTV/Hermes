# Dependency maintenance

The hosted [Renovate GitHub app](https://github.com/apps/renovate) owns automated
version updates. Its repository configuration is in `.github/renovate.json`;
no scheduled Renovate workflow or repository token is required.

## Activation and migration

Install or configure the app for **TechSquidTV/Hermes** before merging this
configuration into the default branch. Review its onboarding PR if one is
created; the checked-in configuration is the source of truth for update policy.
Keep GitHub's dependency graph and Dependabot alerts enabled. Disable
Dependabot **security update PRs** in repository settings so Renovate is the
only update-PR producer; deleting `dependabot.yml` stops scheduled version
updates but does not disable security update PRs. Close remaining Dependabot
update PRs after the first successful Renovate run confirms coverage.

**Breaking maintenance change:** Dependabot's scheduled version updates are
removed. Renovate updates require the app installation. PR grouping, schedules,
and limits change; no compatibility updater remains.

## Update policy

All windows use `America/New_York`. They permit branch creation during a window;
the hosted app decides when it runs, so these are not exact execution times.

| Area | Window | Update policy |
| --- | --- | --- |
| yt-dlp and yt-dlp-ejs | Daily, 05:00–09:00, including weekends | One download-tool group with no release-age delay, including calendar-version year changes. |
| Other Python dependencies | Mondays, 00:00–06:00 | Minor and patch updates grouped; new direct releases wait three days. |
| JavaScript workspace | Mondays, 00:00–06:00 | TanStack Query, TanStack Router, and Vitest each have a related-package group. Other minor and patch updates form the JavaScript group; new releases wait three days. |
| GitHub Actions | Mondays, 00:00–06:00 | Minor and patch action updates grouped. |
| Container images | Mondays, 00:00–06:00 | Dockerfiles, `Dockerfile.dev`, CI containers, and root Compose files covered. Image digests are pinned and refreshed so mutable tags such as `redis:8-alpine` receive update PRs. |
| Lockfile maintenance | Mondays, before 04:00 | Refreshes the pnpm and uv lockfiles, including eligible transitive dependencies. |

`yt-dlp-ejs` is explicitly declared in `pyproject.toml` so Renovate can update
it independently when yt-dlp has no new release. Ordinary uv updates use
targeted package upgrades rather than upgrading the whole Python lockfile daily.
Weekly lockfile maintenance delegates resolution to the package manager and
does not enforce Renovate's three-day release-age delay for transitive updates.

Major updates stay separate and require approval in the Dependency Dashboard
before a PR is opened, except the download-tool group. **Major dependency
updates may require breaking application or tooling changes.** TypeScript stays
below version 7 until the ESLint and OpenAPI tooling supports its compiler API.
All PRs require review; automerge is disabled. Up to five Renovate PRs may be open
at once, with at most two created per hour. Download-tool updates have higher
priority. Review pending PRs regularly so the limit does not block newer updates.

Hermes's own published application images are excluded from updates to avoid
release-driven changes to the example Compose files. `.github/CODEOWNERS`
requests KyleTryon reviews for dependency manifests, lockfiles, Dockerfiles,
Compose files, workflow changes, and the Renovate configuration.

## Validation and release

Dependency PRs run checks for affected packages on both `main` and `develop`.
Renovate configuration and root Compose changes run both packages' checks.
Configuration or workflow changes also run the strict Renovate configuration
validator. The summary check requires every applicable job to succeed.
Checks include formatting, linting, types, tests, and Docker builds.
Workflow permissions are read-only, including for bot PRs.
Every workflow that runs API tests installs FFmpeg so the local audio-conversion
regression test runs instead of skipping. These fixtures need no external media.

Python installs and validation commands use `--locked`: a stale lockfile fails
instead of being rewritten during the checks. The API Docker build uses the
same rule. JavaScript installs use `--frozen-lockfile`. To intentionally update
Python dependencies, run `uv lock --upgrade-package <name>` in
`packages/hermes-api`, then commit the updated manifest and lockfile together.
The release workflow may regenerate lockfiles after changing the project
version, and commits those files in the release commit.

Merging a bot PR does not update an already deployed Hermes image: use the
normal release process. There is no scheduled external video download check.

## Checking automation

Use the repository's **Dependency Dashboard** issue for pending updates,
major-update approvals, and configuration warnings. Renovate PRs link to hosted
run logs in the Mend Developer Portal. After activation, confirm the first run
finds both workspace manifests, the pnpm override, all Python dependency groups,
both download components, Dockerfiles, GitHub Actions, and Redis in Compose.
Verify a pnpm update preserves both YAML documents in `pnpm-lock.yaml`, and a
Python update keeps `pyproject.toml` and `uv.lock` synchronized. Keep the
`pr-checks-complete` check required in branch protection.

GitHub's static dependency graph has a known pnpm 12 multi-document lockfile
issue ([dependabot-core#15904](https://github.com/dependabot/dependabot-core/issues/15904)).
Renovate's pnpm updater reads the project document, but changing update bots does
not repair GitHub's graph. An empty graph must not be treated as proof that the
workspace has no dependencies or vulnerabilities. Keep pnpm's native lockfile
format and version enforcement. A separate native pnpm security audit can
supplement GitHub alerts, but is not included in this configuration: it sends
the dependency graph to npm and requires approval before enabling it here.

References: [Renovate npm support](https://docs.renovatebot.com/modules/manager/npm/),
[Renovate uv support](https://docs.renovatebot.com/modules/manager/pep621/),
[Renovate configuration](https://docs.renovatebot.com/configuration-options/),
and [uv lockfile validation](https://docs.astral.sh/uv/concepts/projects/sync/).
