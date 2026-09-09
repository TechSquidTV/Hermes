# Dependency update and maintenance review — 2026-09-08

The update started from the latest `origin/main` on a clean working tree. Changes are on `chore/update-dependencies-and-fix-issues`.

## Dependency and runtime changes

- Refreshed all JavaScript direct dependencies to their latest stable releases except TypeScript, and upgraded the Python lockfile to the latest mutually compatible versions.
- Retained TypeScript 6.0.3 because current TypeScript ESLint peers require `<6.1` and the OpenAPI generator needs the JavaScript compiler API. No TypeScript 7 compatibility aliases were added.
- Redis resolves to 6.4.0 because Celery's current Kombu Redis extra requires `<6.5`; removing Hermes' old upper bounds cannot override that upstream constraint.
- Updated GitHub Actions majors, Node 24 images, Python 3.14 images, nginx 1.30, and pinned uv 0.12.11.
- Updated pnpm to 12.3.4 and moved its settings into the workspace configuration. Frontend images now install the real workspace with a frozen lockfile. The explicit release-age setting permits current stable releases; esbuild is the only dependency build script enabled.
- Pinned the vulnerable transitive js-yaml 4.x dependency to its patched 4.3.2 release. npm and Python dependency audits report no known vulnerabilities.

**Breaking tooling requirements:** use Node 22.22.2+ within 22.x, Node 24.15+ within 24.x, or Node 26+, and pnpm 12.3.4. CI uses Node 24 and Python 3.14. Python source support remains 3.11+.

## Findings fixed

| Area | Finding and correction |
| --- | --- |
| URL input | Pasting a valid URL could insert it twice. The handler now reads clipboard text synchronously and prevents the duplicate browser insertion. |
| API keys | The form offered unsupported `delete` permissions. Choices now use the generated permission type. Copy/revoke controls have accessible labels; clipboard failures produce an error rather than a false success. |
| SSE connections | Native retries overlapped scheduled retries; manual reconnect did not restore automatic retries; inline callback/event arrays caused reconnect churn. Connection ownership, timer cleanup, stable options, and stale-event guards now cover these cases. |
| Statistics SSE | The endpoint accepted `stats`, but the stored-token model rejected it with HTTP 500. Both now use one scope validator, with tests for queue, stats, and system tokens. |
| File listing | Pagination only searched a small recent subset, ignored zero-byte size limits, included sibling directories with matching prefixes, and reported page-only totals. A joined stream scans all matching managed files, retains only the requested page, and returns full totals. |
| Database setup | Tables could be created before models were registered, and absolute SQLite paths were parsed incorrectly. Models are now registered explicitly and the database path comes from SQLAlchemy's URL parser. |
| Schema consistency | Alembic autogeneration had no registered models. Registration exposed three ORM constraint mismatches; the models now match the existing migration schema without adding a migration. |
| Test isolation | Tests could inherit a developer database URL and had stale skipped cases. Each process now gets a temporary database, and all skipped signup, API-key, and SSE tests have been restored or replaced with working coverage. |
| CI | The aggregate PR gate could succeed after failed change detection or cancelled/skipped required checks. It now requires success for each required job; workflow/workspace changes trigger checks. |
| Release workflow | Version input was interpolated into shell source before validation. It now enters through environment variables. |
| Development scripts | Development commands targeted the default production Compose file. They now consistently target the development file. CI image builds no longer require a local `.env` file. |

## Validation

- Full frontend lint, TypeScript checks, production build, and 474 tests: passed, no skips.
- Full API formatting, import sorting, Ruff, mypy, and 295 tests: passed, no skips; also exercised under Python 3.14 in Docker.
- Frontend production, frontend development, and API Docker builds.
- Fresh database migrations and `alembic check` against the ORM metadata.
- Disposable nginx/API/Redis/Celery stack: service health, first-user signup through nginx, and worker health.
- Browser checks: login, dashboard, queue, and analytics. The browser-discovered stats-token failure was fixed and the final analytics check produced no new console errors.
- PR status gate: 192 status combinations. Release version calculation: six valid/invalid input cases.
- Frozen dependency installation and generated API types.

The suite does not prove every supported third-party video site works: no external video download was performed. Browser checks used an empty queue. Local API coverage was about 66% and frontend line coverage about 36%; two deprecation warnings remain in upstream test-client dependencies. Hosted GitHub Actions and multi-architecture image publishing were not executed.
