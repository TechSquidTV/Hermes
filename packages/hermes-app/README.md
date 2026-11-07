# Hermes App

React and TypeScript frontend for Hermes, built with Vite, TanStack Router,
TanStack Query, Tailwind CSS, and shadcn/ui. It provides download creation,
live progress, queue and history views, API-key settings, and user administration.

## Development

Follow the [contributing guide](../../docs/CONTRIBUTING.md) for prerequisites and
workspace dependency installation. All commands below run from the repository
root, so they cannot be confused with the root `pnpm dev` Docker command.

For the full hot-reload stack:

```bash
pnpm dev
```

For a frontend-only process with an API already running on port 8000:

```bash
pnpm dev:frontend
```

Open [localhost:5173](http://localhost:5173). Vite proxies `/api/*` to
`http://localhost:8000`; development Compose sets the upstream to `http://api:8000`.
Set `HERMES_DEV_API_TARGET` in the launching environment to change that upstream.

## Commands

Run from the repository root:

| Command | Purpose |
| --- | --- |
| `pnpm --filter hermes-app dev` | Start native Vite development server |
| `pnpm --filter hermes-app build` | TypeScript compilation and production build into `packages/hermes-app/dist` |
| `pnpm --filter hermes-app preview` | Preview the production build |
| `pnpm --filter hermes-app type-check` | Check TypeScript without emitting files |
| `pnpm --filter hermes-app lint` | Run ESLint |
| `pnpm --filter hermes-app test` | Run Vitest once |
| `pnpm --filter hermes-app test:watch` | Run Vitest in watch mode |
| `pnpm --filter hermes-app test:coverage` | Run tests with coverage |
| `pnpm generate:types` | Export backend OpenAPI and generate TypeScript schemas |
| `pnpm generate:routes` | Generate TanStack Router route definitions |

## API integration

Reuse the [API client](src/services/api/client.ts) and generated schemas in
[src/types/api.generated.ts](src/types/api.generated.ts). JSON fields use
camelCase, such as `downloadId` and `downloadSubtitles`; query parameter names
follow the API schema.

`pnpm generate:types` imports the Python app and exports its OpenAPI schema into
a temporary file, then runs `openapi-typescript`. It requires uv and installed
workspace dependencies, but no running API server. After changing backend models,
regenerate the types, update callers, run the relevant checks, and commit the
generated file. See the [SDK guide](SDK_GUIDE.md) for examples.

Live API documentation is at [Swagger UI](http://localhost:5173/api/v1/docs) and
[OpenAPI JSON](http://localhost:5173/api/v1/openapi.json) during development.

## Configuration and deployment

The browser API URL comes from runtime `config.js`, then Vite's build-time
`VITE_API_BASE_URL`, then `/api/v1`. Production Docker generates `config.js` at
container startup, so changing its environment requires recreating the container.
Native static builds need a rebuild to change Vite's captured value.

Keep `/api/v1` for the default same-origin deployment. For a separate API origin,
set a full browser-reachable URL and configure API CORS to allow the frontend
origin. See [configuration](../../docs/CONFIGURATION.md#compose-and-frontend-settings)
and [reverse proxies](../../docs/PROXY_DEPLOYMENT.md).

The production container serves the static build with nginx and proxies `/api`
to the internal API. Use the root Compose files to deploy matching app, API,
worker, and scheduler versions.

## Structure and conventions

| Path | Contents |
| --- | --- |
| `src/components/` | UI, authentication, queue, and settings components |
| `src/hooks/` | Query hooks and shared UI behavior |
| `src/routes/` | TanStack Router route components |
| `src/services/` | API client, authentication, sessions, and HTTP helpers |
| `src/types/` | Generated API schemas and shared application types |
| `src/themes/` | Theme styles and metadata |

Use the shared session service for authentication. It coordinates refresh-token
rotation across tabs; direct independent refresh calls can invalidate a session.
Use the existing SSE hooks for live updates and TanStack Query for server state.
See [themes](src/themes/README.md) for adding light and dark color schemes.

Hermes is licensed under [AGPL-3.0](../../LICENSE).
