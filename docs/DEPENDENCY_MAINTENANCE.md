# Dependency maintenance

Dependabot owns automated dependency updates. Its configuration is in
`.github/dependabot.yml`; no Renovate app, workflow, or token is required.

| Area | Schedule (America/New_York) | Update policy |
| --- | --- | --- |
| Python API, including transitive dependencies | Daily at 05:15, including weekends | Native `uv` updates keep `pyproject.toml` and `uv.lock` together. yt-dlp and yt-dlp-ejs have their own group with no cooldown; other releases wait three days. |
| JavaScript workspace | Mondays at 03:00 | One root updater covers root tools, the frontend, and the shared `pnpm-lock.yaml`. |
| GitHub Actions | Mondays at 02:00 | Minor and patch updates are grouped. |
| Docker images | Mondays at 04:00 | Both package directories are covered, including `Dockerfile.dev` and the API's uv stage. |

Minor and patch updates are grouped by ecosystem. Major updates get separate
PRs, except yt-dlp's calendar versions, which stay with its EJS dependency in
the yt-dlp group. Each ecosystem permits up to five open update PRs. Review
pending PRs regularly so the limit does not block newer updates.
`.github/CODEOWNERS` requests KyleTryon reviews for dependency manifests,
lockfiles, Dockerfiles, and workflow changes; it replaces the retired
Dependabot `reviewers` option.

## Validation and release

Dependency PRs run checks for the affected packages on both `main` and
`develop`. Changes to the Dependabot configuration run both packages' checks.
Checks include formatting, linting, types, tests, and Docker builds. Workflow
permissions are read-only, including for bot PRs.
Every workflow that runs API tests installs FFmpeg so the local audio-conversion
regression test runs instead of skipping. These fixtures need no external media.

Python installs and validation commands use `--locked`: a stale lockfile fails
instead of being rewritten during the checks. The API Docker build uses the
same rule. JavaScript installs use `--frozen-lockfile`. To intentionally update
Python dependencies, run `uv lock --upgrade-package <name>` in
`packages/hermes-api`, then commit the updated manifest and lockfile together.
The release workflow may regenerate lockfiles after changing the project
version, and commits those files in the release commit.

**Maintenance behavior change:** stale Python lockfiles now fail validation and
Docker builds. Regenerate and commit the lockfile when changing dependencies.

The new schedules activate when this configuration reaches the default branch.
Dependency PRs require review and the normal release process; merging a bot PR
does not update an already deployed Hermes image. There is no scheduled
external video download check.

## Checking automation

Use the repository's **Actions → Dependabot Updates** runs to check updater
results and logs. GitHub also exposes per-ecosystem update status under
**Insights → Dependency graph → Dependabot**. A successful configuration change
does not prove a hosted updater run succeeded; inspect its first run after
merging, and keep the required PR checks enabled in branch protection.

GitHub's static dependency graph has a known pnpm 12 multi-document lockfile
issue ([dependabot-core#15904](https://github.com/dependabot/dependabot-core/issues/15904)).
The update-PR parser handles this format, but an empty GitHub dependency graph
must not be treated as proof that the workspace has no dependencies or
vulnerabilities. Keep pnpm's native lockfile format and version enforcement.

References: [uv with Dependabot](https://docs.astral.sh/uv/guides/integration/dependabot/),
[Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
and [uv lockfile validation](https://docs.astral.sh/uv/concepts/projects/sync/).
