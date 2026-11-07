# Contributing to Hermes

Start work from current `main` and open pull requests back to `main`. Releases
are manually dispatched after the combined changes are validated. Both packages
share one version; see the [release process](RELEASE_PROCESS.md).

## Prerequisites

- Docker with Compose 2.24.4+ for the bundled development stack.
- Node.js 22.22.2+ (22.x), 24.15+ (24.x), or 26+; Docker and CI use Node 26.
- pnpm 12.18.0, pinned in the root `package.json` through Corepack.
- Python 3.11+ and uv for native backend work; Docker and CI use Python 3.15.
- FFmpeg for native downloads and audio-conversion tests. Native yt-dlp challenge
  solving also needs a supported JavaScript runtime; the Docker image includes Node.

## Set up the repository

```bash
git clone https://github.com/TechSquidTV/Hermes.git hermes
cd hermes

# Install the repository's pinned Corepack version and enable pnpm.
npm install --global "corepack@$(node -p 'require("./package.json").devDependencies.corepack')"
corepack enable pnpm
pnpm install --frozen-lockfile

cp .env.example .env
# Generate a secret, then set HERMES_SECRET_KEY in .env.
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

mkdir -p data/downloads data/temp data/data
sudo chown -R 1000:1000 data
```

For a different host owner, set `USER_UID` and `USER_GID` in `.env`, match the
directory ownership to them, and rebuild all backend services together. See
[configuration](CONFIGURATION.md) for environment settings.

## Development with Docker

Run these commands from the repository root:

```bash
pnpm dev          # Build and start the hot-reload stack.
pnpm dev:logs     # Follow logs.
pnpm dev:down     # Stop the stack.
```

| Service | Development URL |
| --- | --- |
| App | [localhost:5173](http://localhost:5173) |
| API docs through Vite | [Swagger UI](http://localhost:5173/api/v1/docs) |
| Direct API | [Readiness check](http://localhost:8000/api/v1/health/ready) |
| Redis | `localhost:6379` |

Vite proxies `/api/*` to the API. The API, worker, and scheduler share the same
database and mounted storage. Only one scheduler should run for a deployment.
Stop this stack before starting native processes on the same ports or database.

## Native development

### Backend

Follow the [API setup](../packages/hermes-api/README.md#native-development) to
install dependencies, configure local paths, and start the API, worker, and
scheduler. Native processes need settings exported in each terminal; the root
`.env` is not automatically loaded by the Python app.

### Frontend

With a native API listening on port 8000, run from the repository root:

```bash
pnpm dev:frontend
```

Vite defaults to proxying `/api` to `http://localhost:8000`. Set
`HERMES_DEV_API_TARGET` in the launching environment for a different upstream.
Keep the browser-facing `VITE_API_BASE_URL=/api/v1` for same-origin requests.
See the [frontend guide](../packages/hermes-app/README.md).

## Checks and tests

Install backend development dependencies before running native checks:

```bash
cd packages/hermes-api
uv sync --locked --all-groups
```

Run the following from the repository root:

| Command | Purpose |
| --- | --- |
| `pnpm pre-check` | API and frontend checks, both test suites, and all three Docker builds |
| `pnpm pre-check:api` | Backend formatting, lint, mypy, and pytest |
| `pnpm pre-check:app` | Frontend lint, build, types, and Vitest |
| `pnpm format` | Apply frontend lint fixes and Python Black/isort formatting |
| `pnpm lint` | Frontend and backend lint |
| `pnpm type-check` | Frontend TypeScript checks |
| `pnpm test:all` | Frontend and backend tests |
| `pnpm generate:types` | Export OpenAPI from the Python app and regenerate frontend types |

Use checks appropriate to the change. Before releasing, run `pnpm pre-check`
against the combined source. CI selects jobs by changed paths and requires the
`pr-checks-complete` summary check. Package documentation changes also match
their package's CI paths.

The backend uses strict mypy, Black, isort, and Ruff. The frontend uses strict
TypeScript and ESLint. Reuse existing models and helpers, and use generated API
schemas instead of duplicating request and response types. Animation imports
use `motion/react`. TypeScript stays below version 7 until the ESLint and OpenAPI
tooling supports its compiler API.

See the [API test guide](../packages/hermes-api/tests/README.md),
[SDK guide](../packages/hermes-app/SDK_GUIDE.md), and
[dependency maintenance guide](DEPENDENCY_MAINTENANCE.md) for focused workflows.

## Pull request workflow

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/describe-the-change

# Make changes and run the relevant checks, then stage the intended files.
git add README.md
git commit -m "docs(readme): clarify setup instructions"
git push -u origin docs/describe-the-change
```

Use conventional commits with a scope where useful, such as `fix(api): ...` or
`feat(app): ...`. Keep each PR focused. Explain the problem, resulting behavior,
and validation; link related issues and include screenshots for UI changes.
Regenerate and commit API types when changing the API contract.

Breaking changes are acceptable when called out explicitly. Include migration
or upgrade instructions and use `!` in the commit title when appropriate. Do not
add compatibility aliases or fallbacks for removed behavior.

The optional `develop` workflow can publish preview images if that branch is
used. It is not required for contributions; test unreleased work with source builds.

## Troubleshooting

- **Startup fails:** review `docker compose -f docker-compose.dev.yml logs` and
  check the secret, storage ownership, and port conflicts before changing data.
- **Native API cannot reach Redis:** use `redis://localhost:6379/0`, not the
  Docker service hostname. See [native settings](CONFIGURATION.md#docker-defaults-and-native-development).
- **Test failure:** run a focused command, for example
  `uv run --locked pytest tests/test_api/test_health.py -v` from the API directory.
- **Type errors after API changes:** run `pnpm generate:types` and
  `pnpm type-check` from the root, then update affected callers.

**Data-loss warning:** `pnpm clean:all` removes persistent database, download,
and temporary files as well as Compose volumes. It is not a routine startup fix.

Use the [issue tracker](https://github.com/TechSquidTV/Hermes/issues) for bugs and
feature requests. Redact credentials and private media URLs from shared logs.
