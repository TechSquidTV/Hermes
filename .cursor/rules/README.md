# Hermes Cursor Rules

Hierarchical rule structure for the Hermes project with specific file glob patterns.

## Rule Structure

Rules are organized in 4 levels with numeric prefixes indicating precedence:

### Level 0: Project-Wide (00-)
- **00-project.mdc** (54 lines)
  - Glob: `**/*`
  - Monorepo conventions, Git commits, environment variables, tooling

### Level 1: Package-Level (10-)
- **10-hermes-api.mdc** (114 lines)
  - Glob: `packages/hermes-api/**/*.py`
  - Python 3.11+, FastAPI, async/await, Black/isort/mypy, UV package manager

- **10-hermes-app.mdc** (168 lines)
  - Glob: `packages/hermes-app/**/*.{ts,tsx}`
  - TypeScript/React, TanStack Router/Query, Tailwind v4, shadcn/ui, pnpm

### Level 2: Directory-Specific (20-)

**Backend (hermes-api):**
- **20-hermes-api-db.mdc** (198 lines)
  - Glob: `packages/hermes-api/app/db/**/*.py`
  - SQLAlchemy async, repository pattern, migrations

- **20-hermes-api-api.mdc** (223 lines)
  - Glob: `packages/hermes-api/app/api/**/*.py`
  - FastAPI endpoints, dependency injection, error handling

- **20-hermes-api-tests.mdc** (244 lines)
  - Glob: `packages/hermes-api/tests/**/*.py`
  - Pytest, async testing, fixtures, markers

**Frontend (hermes-app):**
- **20-hermes-app-components.mdc** (290 lines)
  - Glob: `packages/hermes-app/src/components/**/*.tsx`
  - React components, props typing, shadcn/ui, accessibility

- **20-hermes-app-hooks.mdc** (284 lines)
  - Glob: `packages/hermes-app/src/hooks/**/*.ts`
  - Custom hooks (use prefix), TanStack Query, TypeScript

- **20-hermes-app-routes.mdc** (299 lines)
  - Glob: `packages/hermes-app/src/routes/**/*.tsx`
  - TanStack Router, loaders, protected routes

### Level 3: Cross-Cutting (30-)
- **30-docker.mdc** (302 lines)
  - Globs: `**/Dockerfile`, `**/.dockerignore`, `docker-compose.yml`
  - Multi-stage builds, optimization, security, docker compose

- **30-docs.mdc** (287 lines)
  - Glob: `**/*.md`
  - Markdown standards, code blocks, API documentation

- **30-tests.mdc** (279 lines)
  - Globs: `**/tests/**/*`, `**/__tests__/**/*`, `**/*.test.{ts,tsx,py}`, `**/test_*.py`
  - Test pyramid, AAA pattern, mocking, coverage

## Key Features

✅ **All files under 300 lines** - Focused, scannable rules  
✅ **Hierarchical precedence** - Specific rules (30) override general (00)  
✅ **Precise file globs** - Each rule targets exact patterns  
✅ **Tech stack aligned** - References actual tools (Black, mypy, ESLint, pytest)  
✅ **Pattern enforcement** - Repository pattern, async patterns, React best practices  
✅ **Practical examples** - Real code snippets from the codebase  

## Total Coverage

12 rule files covering:
- 2,742 total lines of guidance
- 2 programming languages (Python, TypeScript)
- 2 main packages (hermes-api, hermes-app)
- Multiple tech stacks (FastAPI, React, Docker, etc.)

## Usage

Rules are automatically loaded by Cursor based on file glob patterns. More specific rules (higher numbers) take precedence over general rules (lower numbers).
