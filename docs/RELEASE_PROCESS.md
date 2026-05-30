# 🚀 Release Process

This document describes the release process for Hermes, including semantic versioning, creating releases, and publishing Docker images.

## 📦 Package Versioning

Hermes uses **unified versioning** - both packages share the same version number and are released together:

- **hermes-app**: The React/TypeScript frontend application
- **hermes-api**: The FastAPI/Python backend service

Both packages follow [Semantic Versioning 2.0.0](https://semver.org/) and are always kept in sync. The version is managed in the root `package.json` and automatically synchronized across all package files.

## 🔢 Semantic Versioning

We use semantic versioning (MAJOR.MINOR.PATCH) for all releases:

### Version Format: `MAJOR.MINOR.PATCH`

- **MAJOR** (1.x.x): Breaking changes that require user action
  - API endpoint changes that break existing clients
  - Database schema changes requiring migration
  - Removed or renamed features
  - Configuration file format changes

- **MINOR** (x.1.x): New features that are backwards-compatible
  - New API endpoints
  - New UI features or pages
  - Enhanced functionality
  - Performance improvements

- **PATCH** (x.x.1): Bug fixes and small improvements
  - Bug fixes
  - Security patches
  - Documentation updates
  - Minor UI tweaks

### Examples

```
1.0.0 → 1.0.1  # Bug fix
1.0.1 → 1.1.0  # New feature (backwards compatible)
1.1.0 → 2.0.0  # Breaking change
```

## 🏷️ Creating a Release

Releases follow a structured workflow to ensure stability:

1. **Develop Branch** → Changes merge to `develop`, automatically builds `develop` Docker images
2. **Testing** → Test using `develop` Docker images before releasing
3. **Main Branch** → When ready, merge `develop` to `main`
4. **Release Workflow** → Manually trigger release from `main` branch

Releases are created using the GitHub Actions workflow, which ensures consistency and runs in a clean CI environment. Do not create GitHub Releases manually; the workflow creates the release only after the version bump, tags, and Docker images have all succeeded.

### Using GitHub UI

1. Go to the [Actions tab](../../actions)
2. Select the **Release** workflow in the left sidebar
3. Click **Run workflow** button (top right)
4. Choose your release type:
   - **bump_type**: Select `patch`, `minor`, or `major` (follows semver)
   - **version**: Or enter a specific version like `1.2.3` (overrides bump_type)
5. Click **Run workflow**

### Using GitHub CLI

```bash
# Bump patch version (0.1.1 → 0.1.2)
gh workflow run release.yml -f bump_type=patch

# Bump minor version (0.1.1 → 0.2.0)
gh workflow run release.yml -f bump_type=minor

# Bump major version (0.1.1 → 1.0.0)
gh workflow run release.yml -f bump_type=major

# Set specific version
gh workflow run release.yml -f version=1.2.3
```

### What the Workflow Does

The release workflow automatically handles everything in one go:

1. ✅ Reads current version from root `package.json` (source of truth)
2. ✅ Calculates new version based on bump type (or uses specified version)
3. ✅ Updates all package files:
   - `package.json` (root)
   - `packages/hermes-app/package.json`
   - `packages/hermes-api/pyproject.toml`
4. ✅ Runs comprehensive pre-checks:
   - Linting (frontend & backend)
   - Type checking
   - Tests (all packages)
   - Build verification
5. ✅ Commits version bump with conventional commit message: `chore(release): bump version to X.X.X`
6. ✅ Creates three tags:
   - `hermes-app-vX.X.X`
   - `hermes-api-vX.X.X`
   - `vX.X.X` (general project version)
7. ✅ Pushes commit and tags to main
8. ✅ Builds and pushes Docker images to GitHub Container Registry:
   - `ghcr.io/[org]/hermes-app:X.X.X`, `X.X`, `X`, `latest`
   - `ghcr.io/[org]/hermes-api:X.X.X`, `X.X`, `X`, `latest`
9. ✅ Creates the GitHub Release for `vX.X.X`

**If pre-checks fail, nothing is committed, tagged, or published - your main branch stays clean.**

**Why one workflow?** This approach is more secure for organization repositories - no need for Personal Access Tokens with broad permissions. Everything runs with the built-in `GITHUB_TOKEN`.

## 📦 What Gets Published

When the release workflow completes successfully, the following are available:

1. **Git Tags** on the main branch:
   - `hermes-app-vX.X.X`
   - `hermes-api-vX.X.X`
   - `vX.X.X`

2. **Docker Images** in GitHub Container Registry:
   - **hermes-app**: `ghcr.io/[org]/hermes-app:X.X.X`, `X.X`, `X`, `latest`
   - **hermes-api**: `ghcr.io/[org]/hermes-api:X.X.X`, `X.X`, `X`, `latest`

3. **Updated Version Files** in the repository:
   - `package.json` (root)
   - `packages/hermes-app/package.json`
   - `packages/hermes-api/pyproject.toml`

4. **GitHub Release** for the project tag:
   - `vX.X.X`

### 📊 Version Status Integration

The application includes an automatic version status feature that integrates with the release process:

#### How It Works

1. **Frontend Version**: Automatically reads from `package.json` and updates when rebuilt
2. **API Version**: Fetched from the API's health endpoint (`/api/v1/health/`)
3. **Latest Versions**: Queried from published component Git tags in the monorepo
4. **Status Detection**: Compares current vs latest versions and shows appropriate status

#### User Experience

When users access the deployed application, they see:

- **Current versions** in the sidebar (e.g., "App: v1.0.0 | API: v1.0.0")
- **Update notifications** when new releases are available
- **Clickable links** to GitHub releases for easy access to changelogs
- **Visual indicators**:
  - 🟢 Green: Running latest version
  - 🟠 Orange: Update available (clickable)
  - 🔘 Gray: Unable to check for updates

#### Release Detection

The version status feature automatically detects updates by:

- **Monitoring Git tags** in the `techsquidtv/hermes` repository
- **Filtering by published-image tag patterns** (`hermes-app-v*`, `hermes-api-v*`)
- **Semantic version comparison** (MAJOR.MINOR.PATCH)
- **Real-time updates** without requiring application restart

## 📥 Using Released Images

### Pull a Specific Version

```bash
# Pull a specific semantic version
docker pull ghcr.io/<your-org>/hermes-app:1.0.0
docker pull ghcr.io/<your-org>/hermes-api:1.0.0

# Pull the latest version
docker pull ghcr.io/<your-org>/hermes-app:latest
docker pull ghcr.io/<your-org>/hermes-api:latest
```

### Update docker-compose.yml

Update your `docker-compose.yml` to use released images:

```yaml
services:
  app:
    image: ghcr.io/<your-org>/hermes-app:1.0.0
    # ... rest of config

  api:
    image: ghcr.io/<your-org>/hermes-api:1.0.0
    # ... rest of config
```

### Authentication for Private Repositories

If your repository is private, authenticate with GitHub Container Registry:

```bash
# Create a Personal Access Token (PAT) with read:packages scope
# Then login:
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## 🔍 Verifying Releases

### Check GitHub Actions

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Find the workflow run for your tag
4. Verify all steps completed successfully

### Check GitHub Packages

1. Go to your repository on GitHub
2. Click **Packages** in the right sidebar
3. Find `hermes-app` or `hermes-api`
4. Verify the new version tag appears

### Test the Released Image

```bash
# Pull and test the released image
docker pull ghcr.io/<your-org>/hermes-app:1.0.0
docker run -p 3000:80 ghcr.io/<your-org>/hermes-app:1.0.0

# Test the API
docker pull ghcr.io/<your-org>/hermes-api:1.0.0
docker run -p 8000:8000 ghcr.io/<your-org>/hermes-api:1.0.0
```

## 🔄 Rollback a Release

If you need to rollback a release:

### Option 1: Deploy a Previous Version

Simply deploy a previous working version:

```bash
docker pull ghcr.io/<your-org>/hermes-app:1.0.0  # Previous working version
```

### Option 2: Create a Hotfix Release

1. Fix the issue in your code
2. Merge the fix to `main`
3. Run the Release workflow with the next patch version:
   ```bash
   gh workflow run release.yml -f version=1.0.1
   ```

### Option 3: Delete a Bad Tag (Use Sparingly)

If you haven't deployed the release yet:

```bash
# Delete local tags
git tag -d v1.0.0 hermes-app-v1.0.0 hermes-api-v1.0.0

# Delete remote tags
git push origin :refs/tags/v1.0.0
git push origin :refs/tags/hermes-app-v1.0.0
git push origin :refs/tags/hermes-api-v1.0.0
```

**Note**: Only delete tags that haven't been deployed to production. Once deployed, create a new version instead.

## 🛡️ Pre-release Testing

### Develop Branch (Recommended)

The **preferred method** for testing before production is using the `develop` branch:

```bash
# Pull and test develop images (automatically built on push to develop)
docker pull ghcr.io/techsquidtv/hermes-app:develop
docker pull ghcr.io/techsquidtv/hermes-api:develop

# Test with docker-compose by updating image tags to :develop
docker compose -f docker-compose.example.yml up -d
```

**Benefits:**
- Automatic builds on every push to `develop`
- No manual tagging required
- Clear separation from production `latest` tag
- Easy to test accumulated changes before release

### Pre-release Version Tags

Pre-release version tags are not published automatically. Use `develop` images for release-candidate testing, or add a dedicated pre-release workflow before publishing `alpha`, `beta`, or `rc` tags.

## 📋 Release Checklist

Before triggering a release:

**Development & Testing:**
- [ ] All feature PRs are merged to `develop` branch
- [ ] `develop` workflow has run successfully (check Actions tab)
- [ ] Test using `develop` Docker images:
  ```bash
  docker pull ghcr.io/techsquidtv/hermes-app:develop
  docker pull ghcr.io/techsquidtv/hermes-api:develop
  ```
- [ ] Verify all functionality works with `develop` images
- [ ] Optional: Run `pnpm pre-check` locally to catch issues early

**Pre-Release:**
- [ ] Create PR from `develop` to `main`
- [ ] Verify all PR checks pass
- [ ] Merge PR to `main`
- [ ] Update changelog (if maintained)
- [ ] Document breaking changes (if any)

**Release:**

- [ ] Trigger release workflow via GitHub UI or CLI (choose patch/minor/major)
- [ ] Monitor workflow run in Actions tab
- [ ] Verify workflow completes all steps:
  - Version bump and commit
  - Tag creation
  - Docker image builds (both app and api)
  - GitHub Release creation
- [ ] Verify Docker images are published in [GitHub Packages](https://github.com/TechSquidTV?tab=packages)
- [ ] Verify the GitHub Release links to the same `vX.X.X` tag
- [ ] Test pulling and running the new images (optional)

### Version Status Integration

The version status feature will automatically:

- ✅ Detect the updated versions after release
- ✅ Show update notifications to users when new versions are available
- ✅ Provide direct links to GitHub releases for changelogs
- ✅ Update status indicators in real-time without requiring application restart

## 🆘 Troubleshooting

### Pre-checks Fail

**Symptom**: The workflow fails at the "Run pre-checks" step.

**Cause**: Tests, linting, type-checking, or build failed.

**Solution**:
1. Run `pnpm pre-check` locally to identify the issue
2. Fix the failing checks
3. Commit and push fixes
4. Re-run the release workflow

### Docker Build Fails

**Symptom**: The workflow fails during "Build and push Docker image" steps.

**Cause**: Dockerfile syntax error, missing dependencies, or build context issues.

**Solution**:
1. Check the workflow logs for specific error messages
2. Test Docker builds locally:
   ```bash
   docker build -f packages/hermes-app/Dockerfile .
   docker build -f packages/hermes-api/Dockerfile packages/hermes-api
   ```
3. Fix any issues and re-run the release workflow

### Published Release Has No Docker Images

**Symptom**: A GitHub Release exists, but `docker pull ghcr.io/...:X.Y.Z` fails with `manifest unknown`.

**Cause**: The release was likely created manually from a `vX.Y.Z` tag that was not produced by the Release workflow, so the package versions or component tags do not match.

**Solution**:
1. If the release was not deployed, delete the bad GitHub Release and its tag, then rerun the Release workflow.
2. If the release may have been deployed, leave it in place and cut the next patch version.
3. Use the manual **Publish Release Images** workflow only for tags created by the Release workflow.

### Permission Denied When Pushing Images

**Symptom**: The workflow fails with permission denied error when pushing to ghcr.io.

**Cause**: Repository permissions issue.

**Solution**:
1. Verify the workflow has `packages: write` permission (should be automatic)
2. Check repository settings → Actions → General → Workflow permissions
3. Ensure "Read and write permissions" is enabled

### Can't Pull Docker Image

1. Verify you're logged in: `docker login ghcr.io`
2. Check the image name and tag are correct
3. For private repos, ensure your PAT has `read:packages` scope

## 📚 Additional Resources

- [Semantic Versioning 2.0.0](https://semver.org/)
- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🤝 Questions?

If you have questions about the release process:

- Open an issue on GitHub
- Check existing documentation in the `docs/` folder
- Review the GitHub Actions workflow files in `.github/workflows/`

---

**Happy Releasing! 🎉**
