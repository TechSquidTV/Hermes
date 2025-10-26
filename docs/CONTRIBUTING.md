# 🤝 Contributing to Hermes

Thank you for considering contributing to Hermes! We welcome contributions from developers of all skill levels. This guide will help you get started and ensure your contributions meet our quality standards.

## 🎯 Quick Start

1. **Clone and setup**
   ```bash
   git clone https://github.com/techsquidtv/hermes.git
   cd hermes

   # Install dependencies
   pnpm install

   # Set up environment
   cp .env.example .env
   # Edit .env and set HERMES_SECRET_KEY (use pnpm security:generate-key)
   ```

2. **Start development**
   ```bash
   pnpm dev
   ```

3. **Access the app**
   - Web App: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 🐳 Development Workflow

### Essential Commands

```bash
# Start development (recommended)
pnpm dev

# Stop development
pnpm dev:down

# View logs
pnpm dev:logs

# Frontend-only development (hot reload)
pnpm dev:frontend

# API-only development
pnpm dev:api

# Clean everything (nuclear option)
pnpm clean:all
```

### Ports
- **Web App**: http://localhost:3000 (Docker) or http://localhost:5173 (dev server)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Alternative: Manual Setup
For advanced users who need to work outside Docker:

```bash
# Frontend only
pnpm install && pnpm dev

# Backend only
cd packages/hermes-api && uv sync --dev && uv run uvicorn app.main:app --reload
```

## 📋 Code Quality Standards

We maintain high standards through automated tooling. **Before submitting PRs:**

```bash
# Run all quality checks
pnpm pre-check

# Or run individual checks
pnpm format          # Fix formatting
pnpm lint            # Check linting
pnpm type-check      # Type checking
pnpm test:all        # All tests
```

**Quality Gates:**
- ✅ All tests pass
- ✅ TypeScript/mypy checks pass
- ✅ Code formatting (black, isort, prettier)
- ✅ Linting (ESLint, ruff) passes
- ✅ Docker builds successfully

## 🔄 CI/CD Pipeline

All pull requests run automated checks:

**Frontend Changes:**
- Type checking, linting, build, tests

**Backend Changes:**
- Code formatting, linting, type checking, tests with coverage

**Both:**
- Full pipeline runs in parallel

**🚫 PRs are blocked if:**
- Tests fail
- Type checking errors
- Linting violations
- Build failures

**Local Testing:**
```bash
pnpm pre-check    # Run everything locally
pnpm test:all     # Just tests
pnpm lint         # Just linting
```

All GitHub Actions must pass before merging.

## 🧪 Testing

### Running Tests

```bash
# All tests (frontend + backend)
pnpm test:all

# Frontend only
pnpm test:hermes-app

# Backend only
pnpm test:api

# Backend with coverage report
cd packages/hermes-api && uv run pytest --cov=app --cov-report=html
```

### Writing Tests

**Frontend:** Use Jest + React Testing Library in `__tests__/` folders
**Backend:** Use pytest + httpx in `tests/` folders

**Add tests for:**
- New features (happy path + edge cases)
- Bug fixes (regression tests)
- API changes (request/response validation)

## 🤖 AI Assistance

We use Cursor with AI assistance. The `.cursor/` directory contains project-specific rules and patterns.

**For AI contributors:**
- Reference `.cursor/rules/rule.mdc` for project guidelines
- Follow established code patterns
- Always run tests to validate generated code
- Ask for clarification when unsure

## 📝 Contribution Process

### 1. Choose an Issue
- Check [existing issues](https://github.com/techsquidtv/hermes/issues)
- Comment on issues you're interested in
- Create new issues for new ideas

### 2. Create Feature Branch
```bash
git checkout -b feature/amazing-new-feature
# or fix/bug-description
# or docs/update-readme
```

### 3. Make Changes
- Follow existing code patterns
- Add tests for new features
- Update docs if needed
- Test with `pnpm dev`

### 4. Quality Check
```bash
pnpm pre-check    # All checks (lint, types, tests, build)
pnpm format      # Auto-fix formatting
```

### 5. Commit & Push
```bash
# Clear commit messages
git commit -m "feat: add new feature"
git commit -m "fix: resolve issue"
git commit -m "docs: update guide"

git push origin feature/amazing-new-feature
```

### 6. Create Pull Request
- Clear title and description
- Link related issues
- Add screenshots for UI changes
- Ensure all CI checks pass

## 🏗️ Architecture Guidelines

### Frontend
- **Components**: Functional components with hooks
- **State**: React Context (global), useState (local)
- **Styling**: Tailwind CSS + shadcn/ui
- **API**: Custom hooks in `src/hooks/`
- **Routing**: TanStack Router in `src/routes/`

### Backend
- **Structure**: Feature-based (api, core, db, services, tasks)
- **Async**: All I/O operations async
- **Models**: Pydantic in `models/pydantic/`
- **Database**: SQLAlchemy async sessions
- **Tasks**: Celery for background jobs

### General
- **Error Handling**: Proper HTTP status codes
- **Validation**: Pydantic for all I/O
- **Logging**: Structured logging
- **Security**: Rate limiting, JWT auth

## 🔍 Code Review Process

**We look for:**
- ✅ **Tests**: New features need tests
- ✅ **Documentation**: Update docs for new features
- ✅ **Type Safety**: No TypeScript/mypy errors
- ✅ **Code Style**: Follow project patterns
- ✅ **Security**: No obvious vulnerabilities
- ✅ **Performance**: Reasonable impact

**Review Checklist:**
- [ ] Tests added/modified
- [ ] Documentation updated
- [ ] All CI checks pass
- [ ] Docker still works
- [ ] No breaking changes

## 🚨 Common Issues

**Development won't start:**
```bash
pnpm clean:all    # Nuclear option
pnpm dev          # Restart fresh
```

**Tests failing:**
```bash
pnpm test:all -- --verbose    # See detailed output
# or for specific test
cd packages/hermes-api && uv run pytest tests/test_specific.py::test_function -v
```

**Type errors:**
```bash
pnpm type-check    # Frontend
cd packages/hermes-api && uv run mypy app/  # Backend
```

**Build issues:**
```bash
pnpm build        # Check frontend build
docker compose build  # Check full stack
```

## 🎉 Recognition

Contributors are recognized in README and release notes.

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/techsquidtv/hermes/issues) for bugs/features
- **Discussions**: [GitHub Discussions](https://github.com/techsquidtv/hermes/discussions) for questions
- **Documentation**: Check `docs/` folder first

## 🚀 Releases

See **[Release Process Guide](./RELEASE_PROCESS.md)** for details.

**Quick version:**
- Semantic versioning (MAJOR.MINOR.PATCH)
- Independent package versioning
- Auto-published Docker images

---

**Thank you for contributing to Hermes!** 🎥✨

Your contributions help make Hermes better for everyone. We're excited to see what you build!
