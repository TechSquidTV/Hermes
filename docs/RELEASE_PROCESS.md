# Release process

Hermes uses one version for the root workspace, `hermes-app`, and `hermes-api`.
Release both packages together. The root `package.json` is the version source;
the Release workflow updates both package manifests and lockfiles.

## Prepare a release

1. Merge reviewed changes to `main` with passing required checks.
2. Validate the combined source with `pnpm pre-check`, which runs both packages'
   checks and tests and builds all three Dockerfiles.
3. Test the app, API, worker, and scheduler together, including persistent storage,
   authentication, downloads, and progress events.
4. Review [.github/release-notes.md](../.github/release-notes.md), including breaking
   changes and migration instructions for the release.
5. Choose a new stable `MAJOR.MINOR.PATCH` version. Use a major bump for breaking
   changes, minor for compatible features, and patch for compatible fixes.

Use source builds for unreleased validation. The optional `develop` workflow
publishes preview images when that branch is used; it is not a prerequisite for
release. Prerelease tags such as `alpha`, `beta`, and `rc` are not supported
by the release workflows.

## Publish

Use the [Release workflow](https://github.com/TechSquidTV/Hermes/actions/workflows/release.yml)
from `main`. In the Actions UI, choose **Run workflow** and select `bump_type`
(`patch`, `minor`, or `major`), or provide an explicit `version` such as `1.2.3`.
An explicit version overrides the bump type.

With the GitHub CLI:

```bash
gh workflow run release.yml --ref main -f bump_type=patch
# Or select an explicit unused stable version:
gh workflow run release.yml --ref main -f version=1.2.3
```

The workflow:

1. Checks out `main` and verifies the requested version and tags are available.
2. Updates all three manifests and both lockfiles, then runs `pnpm pre-check`.
3. Commits `chore(release): bump version to X.Y.Z` and pushes it to `main`.
4. Creates `vX.Y.Z`, `hermes-app-vX.Y.Z`, and `hermes-api-vX.Y.Z` at that commit.
5. Builds and publishes the app and API images for `linux/amd64` and `linux/arm64`.
6. Creates the GitHub Release only after both images publish successfully.

Pre-check failures happen before the release commit and tags are pushed. Later
failures can leave tags or partially published images; use the recovery procedure
below. Do not create an ad-hoc GitHub Release to trigger image publication.

## Published artifacts

| Artifact | Name |
| --- | --- |
| Project tag and GitHub Release | `vX.Y.Z` |
| Component tags | `hermes-app-vX.Y.Z`, `hermes-api-vX.Y.Z` |
| Frontend image | `ghcr.io/techsquidtv/hermes-app:X.Y.Z` |
| API, worker, and scheduler image | `ghcr.io/techsquidtv/hermes-api:X.Y.Z` |

Images also receive eligible mutable aliases: `X.Y`, `X`, and `latest`. The
[alias policy](../.github/scripts/release_aliases.py) compares numeric stable
project tags: `latest` only points to the highest version, the major alias to the
highest version in that major, and the minor alias to the highest patch in that
minor. Component and prerelease tags do not participate. Historical recovery
cannot move an alias backward.

Use an exact `HERMES_IMAGE_TAG` for deployment, even when mutable aliases exist.
One setting selects the frontend, API, worker, and scheduler together.

## Verify publication

1. Confirm the workflow completed and the version commit, all three tags, and
   manifest versions agree.
2. Verify both image manifests contain both supported architectures:

   ```bash
   docker buildx imagetools inspect ghcr.io/techsquidtv/hermes-app:1.2.3
   docker buildx imagetools inspect ghcr.io/techsquidtv/hermes-api:1.2.3
   ```

3. Confirm the GitHub Release points to the same project tag and includes the
   appropriate upgrade notes.
4. Test a fresh deployment with the release's Compose files and one exact image
   tag, following the [quick start](../README.md#prebuilt-releases-and-upgrades).
5. Exercise the [upgrade and recovery flow](UPGRADING.md) on a representative
   installation before deploying broadly.

Do not deploy until both images are available. App/API versions are reported in
the sidebar and compared with published component tags. Open tabs separately
check the deployed frontend build and offer an explicit reload after deployment.

## Recovering a partial image publication

Release and Publish Release Images share the `hermes-release-publication`
concurrency group. They run serially without cancelling an in-progress publisher.
A registry failure can still interrupt publication between the two images.

If Release pushed the version commit and all three tags but an image push failed:

1. Leave the commit and tags intact. Verify all three tags identify the same
   commit and that commit's package versions match.
2. Repair registry access or the transient build environment. If source changes
   are needed, cut a new version; do not move an existing release tag.
3. For unchanged source, dispatch
   [Publish Release Images](https://github.com/TechSquidTV/Hermes/actions/workflows/publish-release-images.yml)
   from `main` with the existing project tag:

   ```bash
   gh workflow run publish-release-images.yml --ref main -f tag=v1.2.3
   ```

4. The recovery workflow verifies matching tags and versions, reruns validation,
   and republishes both exact-version images. It creates a missing GitHub Release
   or preserves the existing one. Mutable aliases change only when eligible.
5. Verify both image manifests and architectures before deployment.

Recovery loads the alias policy from the workflow commit, so historical source
tags do not need to contain that script. Do not rerun the version-bumping Release
workflow to repair an already-tagged version. Do not delete or retag a version
that may already be deployed.

## Deployment rollback and hotfixes

After a schema migration, an older image alone cannot safely roll back the
installation. Use [upgrade recovery](UPGRADING.md#failed-upgrades-and-recovery)
to restore a matching database snapshot, configuration, and images, or deploy a
forward fix. Restoring a snapshot discards database writes made afterward.

For a hotfix, merge the reviewed fix to `main`, select a new version, and run the
normal Release workflow. Preserve previously published versions for diagnosis
and recovery.

## Troubleshooting

| Failure | Next step |
| --- | --- |
| Pre-checks fail | Reproduce with `pnpm pre-check`, fix the failure, and rerun with an unused version |
| Requested tag already exists | Inspect the existing release state; recover publication or choose a new version |
| One or both images missing after tags were pushed | Use Publish Release Images for unchanged tagged source |
| Image push denied | Check workflow `packages: write` permission and registry/package access |
| Private image cannot be pulled | Authenticate to GHCR with a credential that has `read:packages` |
| Deployment fails after migration | Follow the saved upgrade recovery procedure; avoid image-only rollback |

The workflow files are the executable source of truth:
[Release](../.github/workflows/release.yml),
[Publish Release Images](../.github/workflows/publish-release-images.yml), and
[optional develop builds](../.github/workflows/develop.yml).

## Upgrade notes for the next release

Back up the database, `.env`, media and scheduler state. Stop old workers before
migrating and rebuild/recreate the API, worker and scheduler together. Use one
migration process with the downloads filesystem mounted. The managed-path
migration needs an online database and real filesystem paths; SQL-only upgrades
are unsupported. The PostgreSQL counter migration follows that revision in a
single chain. The seeded SQLite upgrade test uses a schema snapshot created by
original 0.6.0 migrations and verifies account, policy and media preservation.

SQLite stays the default. PostgreSQL is an explicit opt-in using
`postgresql+asyncpg`; changing the URL does not transfer SQLite data. Follow
[PostgreSQL deployment guidance](POSTGRESQL.md), including supported worker pools.

`PUT /api/v1/admin/config` now rejects unsupported runtime updates with HTTP 501.
Change deployment environment settings and restart affected processes. Its GET
response exposes actual startup settings rather than former placeholder fields.
Signup policy keeps its dedicated endpoint. See [configuration guidance](CONFIGURATION.md).

Previously issued SSE tokens lack credential binding and are rejected after this
upgrade. Clients automatically request new tokens. Streams recheck authorization
at least once per second and close after logout, account disable, key revocation
or token expiry. Manual temporary cleanup defaults to files older than 24 hours,
protects active task outputs and skips symlinks. Failed-record cleanup now honors
preview mode and the shared deletion limit, reporting record counts separately.

### Release alias ordering

Release and recovery share a numeric stable-version policy. `latest` can point
only to the highest `vX.Y.Z` tag, a major alias only to the highest version in
that major, and a minor alias only to the highest patch in that minor. Prerelease
and component tags do not participate. Historical recovery cannot move an alias
backwards, even if its package versions and component tags all match. Recovery
loads the policy from the workflow commit rather than the historical source tag,
so older releases do not need to contain this script.

### Download dispatch outcomes

A publication failure is recorded on an unclaimed download as `failed` with an
explanation, rather than leaving it pending forever. The API returns the created
record and its status; callers must inspect that status. Batches continue through
individual broker failures and return `partial` or `failed` with `failedDownloads`
listing only the unsuccessful IDs. Retry those items instead of resubmitting
successful batch members. HTTP transport failures remain ambiguous; request-level
idempotency is not provided. Workers atomically claim pending records, preventing
duplicate broker deliveries from executing the same ID twice. An uncertain broker
acknowledgement does not fail a record already claimed by a worker.

### Final release fixes

Session refresh is coordinated across tabs through atomic IndexedDB leases on
HTTP and HTTPS origins. A late refresh rejection can reuse credentials
already rotated by another tab only when their signed session-family ID matches;
logout and account changes still invalidate the initiating operation.

Failed downloads remove their task-prefixed partial outputs immediately. Scheduled
temporary cleanup also reclaims failed/cancelled task outputs in download storage
after the configured temporary-file age. Retention previews include unregistered
task outputs, and failed-record cleanup counts file removals and records against
the same limit. Cleanup skips symlinks and preserves records when removal fails.
Completed media and active task outputs remain protected from temporary cleanup.
New successful and failed history records retain extractor, video and format
metadata when extraction supplied it.

The queue summary now reports all download attempts and converts success fractions
to percentages. Unfinished Retry and Forgot password controls are hidden until
implemented. The unused shadcn generator was removed from normal dependencies,
eliminating the development-only deepmerge advisory; the JavaScript audit reports
zero vulnerabilities as of 2026-11-06.

### Startup and worker recovery upgrade

New releases prepend the versioned upgrade guidance from
`.github/release-notes.md` to GitHub's generated change summaries. Review that
template before release: it includes the migration and coordinated upgrade
warning, exact one-command upgrade, and required sign-in. Image-publication
recovery uses the template committed with the selected tag, when present, so
older releases do not acquire instructions for features they never shipped.

Recovery records now include a private resolved Compose snapshot. Keep it with
the database backup; older records without the snapshot require manual recovery.
Output disconnects cannot turn a completed upgrade into a service shutdown.

Analytics summaries use exact success counts before rounding. Peak usage is the
most frequent UTC completion hour in the selected period (earliest hour wins
ties, midnight when empty); current storage is the regular-file size under the
download root, independent of history and period filters. Symlinks and the
separate temp root are excluded.

Password changes revoke all of the user's access, refresh and live-event
credentials in the same database commit. **Sign in again after this release:**
older tokens without the password binding are rejected. No additional database
revision is required for this binding.

Terminal download transitions now commit history alongside status and file
registration. Failed history writes roll back the terminal transition and its
file records, and duplicate deliveries cannot append duplicate history.

Managed upgrades retain the resolved Compose project identity for recovery in a
fresh shell. Pre-migration interruptions can resume the original services without
restoring a database; recovery after a completed restore resumes startup rather
than applying the snapshot twice. See the [upgrade guide](UPGRADING.md).

**Migration required:** use `python3 scripts/upgrade.py X.Y.Z` with the target
release's prebuilt Compose files. It drains work, backs up the database, runs
migrations and verifies matching API/worker/scheduler images. Native deployments
follow the [manual upgrade steps](UPGRADING.md#backups-and-native-deployments).
Revision `a7c4e19d82b6` adds the nullable worker heartbeat and its active
download index. Active historical records use their start/creation timestamp
until they have a heartbeat. The API fails abandoned active records after
`HERMES_DOWNLOAD_STALE_AFTER_SECONDS` (300 by default), recording failure history
and publishing a status update. Submit the failed URL again to create new work.
Workers acknowledge downloads after execution and reject worker-loss deliveries;
duplicate delivery never starts an already-claimed record. Stale work cannot
complete after recovery has made its status terminal.

Configured initial-administrator seeding failures now stop API startup with a
redacted error. Empty installations with partially supplied seed credentials
also stop. Existing installations may remove the seed password after bootstrap;
the presence of users continues to prevent seeding. An installation with no seed
credentials retains the documented first-user-admin bootstrap.

Open tabs now prompt to reload after deployment; save changes and choose Reload.
Refresh coordination requires
IndexedDB storage and works on plain HTTP too; a closed tab's lease expires after
60 seconds. Refresh operations are bounded to 30 seconds, and a suspended tab
cannot persist credentials after that deadline. A storage failure leaves the
current credentials intact and reports an error so the user can retry.
