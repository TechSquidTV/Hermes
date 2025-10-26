# 🚀 Release Process

This document describes the release process for Hermes, including semantic versioning, creating releases, and publishing Docker images.

## 📦 Package Versioning

Hermes is a monorepo containing two independently versioned packages:

- **hermes-app**: The React/TypeScript frontend application
- **hermes-api**: The FastAPI/Python backend service

Each package follows [Semantic Versioning 2.0.0](https://semver.org/) independently, allowing you to release frontend and backend changes separately.

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

### Option 1: Interactive Release Script (Recommended)

Use the interactive release script for a guided experience:

```bash
# From the project root
pnpm release
# or
./scripts/release.sh
```

**The script will:**
- ✅ Show current version numbers
- ✅ Prompt for new versions (enter to keep unchanged)
- ✅ Run comprehensive pre-checks automatically
- ✅ Create commits and tags only if checks pass
- ✅ Use conventional commit messages
- ✅ Handle both packages separately

**Skip to [Verify Release](#-verifying-releases) after running the script.**

### Option 2: Manual Release Process

#### Step 1: Prepare the Release

Before creating a release, ensure:

1. **All tests and checks pass**
   ```bash
   # Use the automated pre-check (recommended)
   pnpm pre-check:full

   # Or run individual checks
   pnpm pre-check:app    # Frontend checks
   pnpm pre-check:api    # Backend checks
   ```

2. **Working directory is clean**
   ```bash
   git status  # Ensure no uncommitted changes
   ```

3. **Changelog is updated** (if you maintain one)
   - Document new features, bug fixes, and breaking changes

### Step 2: Choose the Version Number

Determine the appropriate version number based on the changes:

- Breaking changes? → Bump MAJOR version
- New features? → Bump MINOR version  
- Bug fixes only? → Bump PATCH version

#### Step 3: Update Version Numbers

For the manual process, update version numbers in:

- **Frontend**: `packages/hermes-app/package.json` (version field)
- **Backend**: `packages/hermes-api/pyproject.toml` (version field)

#### Step 4: Create and Push Tags

**Using the interactive script (recommended):**
The script handles commit messages, tagging, and pushing automatically.

**Manual tagging:**

```bash
# For hermes-app (Frontend)
git tag hermes-app-v1.0.0
git push origin hermes-app-v1.0.0

# For hermes-api (Backend)
git tag hermes-api-v1.0.0
git push origin hermes-api-v1.0.0

# For both packages together
git tag hermes-app-v1.0.0 hermes-api-v1.0.0
git push origin hermes-app-v1.0.0 hermes-api-v1.0.0
```

## 🤖 What Happens Next?

When you push a release tag, GitHub Actions automatically:

1. **Detects the tag** matching the pattern `hermes-app-v*` or `hermes-api-v*`
2. **Extracts the version** (e.g., `hermes-app-v1.0.0` → `1.0.0`)
3. **Builds the Docker image** using the appropriate Dockerfile
4. **Publishes to GitHub Container Registry** with multiple tags:
   - Semantic version: `1.0.0`
   - Minor version: `1.0`
   - Major version: `1`
   - Latest: `latest`

### 📊 Version Status Integration

The application includes an automatic version status feature that integrates with the release process:

#### How It Works

1. **Frontend Version**: Automatically reads from `package.json` and updates when rebuilt
2. **API Version**: Fetched from the API's health endpoint (`/api/v1/health/`)
3. **Latest Versions**: Queried from GitHub releases in the monorepo
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

- **Monitoring GitHub releases** in `techsquidtv/hermes` repository
- **Filtering by tag patterns** (`hermes-app-v*`, `hermes-api-v*`)
- **Semantic version comparison** (MAJOR.MINOR.PATCH)
- **Real-time updates** without requiring application restart

### Example Output

After pushing `hermes-app-v1.2.3`, the following images are published:

```
ghcr.io/<your-org>/hermes-app:1.2.3
ghcr.io/<your-org>/hermes-app:1.2
ghcr.io/<your-org>/hermes-app:1
ghcr.io/<your-org>/hermes-app:latest
```

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
docker run -p 3000:3000 ghcr.io/<your-org>/hermes-app:1.0.0

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
2. Create a new patch version tag:
   ```bash
   git tag hermes-app-v1.0.1
   git push origin hermes-app-v1.0.1
   ```

### Option 3: Delete a Bad Tag (Use Sparingly)

If you haven't deployed the release yet:

```bash
# Delete local tag
git tag -d hermes-app-v1.0.0

# Delete remote tag
git push origin :refs/tags/hermes-app-v1.0.0
```

**Note**: Only delete tags that haven't been deployed to production. Once deployed, create a new version instead.

## 🛡️ Pre-release Versions

For testing before a production release, use pre-release tags:

```bash
# Alpha version
git tag hermes-app-v1.0.0-alpha.1
git push origin hermes-app-v1.0.0-alpha.1

# Beta version
git tag hermes-app-v1.0.0-beta.1
git push origin hermes-app-v1.0.0-beta.1

# Release candidate
git tag hermes-app-v1.0.0-rc.1
git push origin hermes-app-v1.0.0-rc.1
```

These will build and publish Docker images but won't update the `latest` tag.

## 📋 Release Checklist

### Using the Interactive Script (Recommended)
The script handles most of these automatically:

- [ ] Run `pnpm pre-check:full` to verify all checks pass
- [ ] Run `pnpm release` for guided release process
- [ ] Script handles version updates, commits, and tags automatically

### Manual Process Checklist

- [ ] All tests and checks pass (`pnpm pre-check:full`)
- [ ] Working directory is clean (`git status`)
- [ ] Version numbers updated in package files
- [ ] Code committed with conventional commit messages
- [ ] Tags created and pushed (`hermes-app-v*`, `hermes-api-v*`)
- [ ] Changelog updated (if maintained)
- [ ] Breaking changes documented

### Version Status Integration

The version status feature will automatically:

- ✅ Detect the updated versions after release
- ✅ Show update notifications to users when new versions are available
- ✅ Provide direct links to GitHub releases for changelogs
- ✅ Update status indicators in real-time without requiring application restart

## 🆘 Troubleshooting

### GitHub Actions Workflow Fails

1. Check the Actions tab for error details
2. Common issues:
   - Docker build fails: Check Dockerfile syntax
   - Tests fail: Ensure tests pass locally first
   - Permission denied: Check repository secrets and permissions

### Docker Image Not Published

1. Verify the tag format matches `hermes-app-v*` or `hermes-api-v*`
2. Check GitHub Actions workflow logs
3. Ensure `packages: write` permission is granted

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

