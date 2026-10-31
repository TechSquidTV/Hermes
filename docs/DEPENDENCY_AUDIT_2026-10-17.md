# Dependency dashboard disposition — 2026-10-17

Snapshot: [dashboard #144](https://github.com/TechSquidTV/Hermes/issues/144),
baseline `9b7b76195e59f34ca1d426c3a424353fd9a9e08a`.
The dashboard is a living bot-owned inventory and must remain open. This audit
does not edit its body or approve its checkboxes. Recheck live versions and
existing branches before acting on any deferred item.

## Selected update set

Update the test/CI toolchain without application behavior changes:

- `vitest` and `@vitest/coverage-v8`: 5.0.1 → 5.0.4, pinned together because
  the coverage adapter requires the matching Vitest version. Keep pnpm 12.3.4
  and regenerate its native lockfile with that version.
- `astral-sh/setup-uv`: v10.2.0 → v10.3.0 in all four workflows. Existing
  `enable-cache` configuration remains supported; the action still uses Node 24.
  The release adds an optional architecture input and embedded uv checksums.

The selected releases are older than the three-day direct dependency delay.
At selection time GitHub had no open PRs and `git ls-remote --heads origin
'renovate/*'` returned no branches, so this set does not duplicate a bot branch.
Do not unschedule the same groups while this manual PR is open. After merging,
let Renovate reconcile the dashboard with the manifests.

**Breaking-change warning:** no direct major upgrade is selected. Vitest's
dependency tree moves `obug` 2 → 3 and `why-is-node-running` 2 → 3; these are
internal tooling dependencies, validated by the test/build checks. Deferred
major and runtime upgrades below can require breaking changes. Do not add
compatibility aliases or fallbacks when implementing them.

## Pending approval: individual dispositions

These Python declarations use lower bounds. A dashboard target is not necessarily
the version currently installed. Raising an old floor does not downgrade an
already-newer lockfile, and should not be confused with validating a new major.

| Dashboard branch/group | Disposition and next action |
| --- | --- |
| `black-25.x` | Hold approval. Floor is `>=25.9.0`, but uv already locks 26.5.1. Reconcile the floor with the supported formatter in a Python-only PR; run Black over API, tests, typings and infrastructure tests. Black 26 is a major, so review formatting changes explicitly. |
| `js-yaml-=4.0.0-4.3.2-5.x` | Reject as a routine override bump. Keep the targeted security override at 4.3.2. **Major 5** must first be supported by the Redocly/OpenAPI consumer; verify type generation and generated-schema parity before replacing/removing the override. |
| `mypy-1.x` | Hold approval. Floor `>=1.18.2` already resolves 2.3.1. Reconcile the floor separately; **major 2** needs API/tests/infra type checking, including local stubs, without weakening types. |
| `pytest-asyncio-0.x` | Hold approval. Floor `>=0.24.0` already resolves 1.4.0. Reconcile separately; review **0.x → 1.x** fixture/event-loop changes and run the complete async API suite. |
| `bcrypt-4.x` | Hold approval. Floor `>=4.0.0` already resolves 5.0.0. Reconcile the floor only with authentication validation; **major 5** requires explicit password-length/hash compatibility checks. Coordinate with security owner. |
| `framer-motion-14.x` | Do not approve the deprecated package's major while replacement is pending. Prefer the same-major `motion` replacement first, then evaluate **major 14** separately against upstream release notes and UI checks. |
| `sse-starlette-1.x` | Hold approval. Floor `>=1.6.5` already resolves 3.5.0. Reconcile separately; **major 3** needs stream connection/disconnection, heartbeat and terminal-event validation. Coordinate with frontend SSE owner. |
| `structlog-23.x` | Hold approval. Floor `>=23.0.0` already resolves 26.1.0. Reconcile separately; review **23 → 26** logging/processor compatibility and run API startup/tests. |

## Awaiting schedule: individual dispositions

The ordinary window is Monday 00:00–06:00 America/New_York; lockfile maintenance
uses Monday before 04:00. These are branch-creation windows, not guaranteed run
times. Saturday's awaiting-schedule entries are expected. yt-dlp is the explicit
daily 05:00–09:00 exception, with no release-age delay.

| Dashboard branch/group | Disposition and next action |
| --- | --- |
| `framer-motion-replacement` | Defer to a dedicated dependency migration after the frontend behavior PRs. Replace the direct package with `motion` at the same supported major, migrate all nine source imports to `motion/react`, and regenerate pnpm lock. Run lint/types/build/coverage and smoke animated tooltip, sidebar, sheet and collapsible interactions. No alias or dual direct dependency. Follow the [official upgrade guide](https://motion.dev/docs/react-upgrade-guide). |
| `vitest` | Implemented in this set: matching 5.0.4 runner and coverage adapter. Validate coverage/JUnit generation as well as tests. Leave its schedule checkbox untouched. |
| `python` | Leave scheduled; do not combine with the active PostgreSQL resolver change. After asyncpg lands, regenerate from the resulting uv lock using targeted upgrades. Compare resolved versions rather than just floors; run locked sync, API formatting/lint/types/tests, schema parity and API image build. Review Redis, pytest, isort and other effective major changes independently. |
| `tanstack-router` | Leave scheduled as its related-package group. Run route generation, type checks, build and route/navigation tests together; do not mix with account/SSE behavior fixes. |
| `docker-images` | Leave scheduled. Keep uv image, Renovate CI image, nginx, Node, Python and Redis changes reviewable with digest pins. Run infra tests, all image builds and Compose smoke for both deployment topologies; separate Python 3.15 runtime migration from digest/patch refreshes. |
| `github-actions` | Implemented in this set: setup-uv v10.3.0 everywhere. Validate workflow syntax and referenced action inputs/runtime; GitHub CI must still exercise cache restore, locked installs and post-job cache save. |
| `python-3.x` | Hold early execution. **Python 3.14 → 3.15 is a potentially breaking runtime upgrade**, despite SemVer classifying it as minor. Validate interpreter/wheel availability, uv lock markers and all API/image/Compose checks together; do not raise the library's `>=3.11` support floor as an incidental CI update. |
| `javascript` | Leave scheduled. Keep pnpm engine/packageManager and native two-document lock format aligned. Validate full app checks, schema generation and Docker build; defer deprecated framer-motion updates in favor of its dedicated migration. Review tooling engines, peer requirements and zero-major packages for breaking behavior even within this group. |
| `tanstack-query` | Leave scheduled with runtime/devtools paired. Run query/cache tests and full app checks after the account-cache behavior fix is independently reviewed; keep the dependency PR separate. |
| `lock-file-maintenance` | Leave scheduled until overlapping manifest changes settle. Refresh pnpm and uv from the integrated manifests, preserve both pnpm YAML documents, and require frozen/locked installs plus both suites. Do not copy a worker's lockfile over another worker's additions. |

Neither bulk approval nor bulk unscheduling is appropriate for this snapshot.

## Lockfiles, coordination and CI

- Frontend owner confirmed behavior changes are confined to account cache/SSE
  code and tests, with no dependency additions or lockfile edits.
- PostgreSQL owner owns `pyproject.toml` and `uv.lock`, including asyncpg. This
  set changes neither file, schema/repositories, nor generated API types.
- pnpm's policy document and project document remain present. The root importer,
  other app dependencies, packageManager/engines and js-yaml override remain
  unchanged; the diff is the Vitest tree and its peer references.
- PR path filters already cover both packages for pnpm lock and workflow
  changes. The strict Renovate validator and required summary gate remain in
  place. Frozen pnpm and locked uv installs remain enforced.
- The CI container stays Renovate 44.147.0; its scheduled image refresh remains
  a separate group. Configuration validation here uses that exact validator.
- Documentation mentions `develop`, but the remote currently exposes only
  `main` of those two branches. Target this maintenance PR at the existing
  `main` baseline; do not create an integration branch as part of dependencies.

See the PR and task attachment for executed validation and review evidence.
Docker/Compose execution requires a running Docker daemon; a missing daemon is
a validation limitation, not a passing build. No deployment or merge is part of
this assignment.

Release references: [Vitest 5.0.4](https://github.com/vitest-dev/vitest/releases/tag/v5.0.4),
[setup-uv 10.3.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0),
[Renovate dashboard](https://docs.renovatebot.com/key-concepts/dashboard/).
