#!/bin/bash

# Hermes Release Script
# Interactive CLI for preparing releases
# Supports both hermes-app and hermes-api packages

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to get current version
get_current_version() {
    local package=$1
    case $package in
        "app")
            jq -r '.version' packages/hermes-app/package.json
            ;;
        "api")
            grep '^version' packages/hermes-api/pyproject.toml | cut -d'"' -f2
            ;;
    esac
}

# Function to update version
update_version() {
    local package=$1
    local new_version=$2
    case $package in
        "app")
            cd packages/hermes-app
            jq ".version = \"$new_version\"" package.json > package.json.tmp && mv package.json.tmp package.json
            cd ../..
            ;;
        "api")
            sed -i.bak "s/^version = \"[^\"]*\"/version = \"$new_version\"/" packages/hermes-api/pyproject.toml
            rm -f packages/hermes-api/pyproject.toml.bak
            ;;
    esac
}

# Function to create conventional commit message
create_commit_message() {
    local package=$1
    local version=$2
    echo "chore(release): bump $package version to $version"
}

# Function to create tag
create_tag() {
    local package=$1
    local version=$2
    local tag="hermes-${package}-v${version}"
    git tag "$tag"
    print_success "Created tag: $tag"
}

# Function to run pre-check
run_precheck() {
    print_info "Running pre-release checks..."

    # Run comprehensive checks
    if pnpm pre-check:full; then
        print_success "All pre-checks passed! 🎉"
        return 0
    else
        print_error "Pre-checks failed. Please fix the issues before releasing."
        return 1
    fi
}

# Main script
main() {
    print_info "🚀 Hermes Release Preparation Script"
    echo ""

    # Get current versions
    current_app_version=$(get_current_version "app")
    current_api_version=$(get_current_version "api")

    print_info "Current versions:"
    echo "  hermes-app: $current_app_version"
    echo "  hermes-api: $current_api_version"
    echo ""

    # Ask for new versions
    read -p "Enter new hermes-app version (current: $current_app_version): " new_app_version
    new_app_version=${new_app_version:-$current_app_version}

    echo ""
    read -p "Enter new hermes-api version (current: $current_api_version): " new_api_version
    new_api_version=${new_api_version:-$current_api_version}

    echo ""
    print_info "Proposed versions:"
    echo "  hermes-app: $current_app_version → $new_app_version"
    echo "  hermes-api: $current_api_version → $new_api_version"
    echo ""

    # Confirm version changes
    read -p "Do you want to proceed with these version changes? (y/N): " confirm_versions
    if [[ ! $confirm_versions =~ ^[Yy]$ ]]; then
        print_info "Version changes cancelled."
        exit 0
    fi

    # Update versions
    print_info "Updating version files..."

    if [ "$new_app_version" != "$current_app_version" ]; then
        update_version "app" "$new_app_version"
        print_success "Updated hermes-app to version $new_app_version"
    fi

    if [ "$new_api_version" != "$current_api_version" ]; then
        update_version "api" "$new_api_version"
        print_success "Updated hermes-api to version $new_api_version"
    fi

    echo ""
    read -p "Do you want to create release commit(s) and tag(s)? (y/N): " confirm_release
    if [[ ! $confirm_release =~ ^[Yy]$ ]]; then
        print_info "Release cancelled. Version files updated but no commit/tag created."
        print_warning "Remember to commit your changes manually."
        exit 0
    fi

    # Run pre-checks
    if ! run_precheck; then
        print_error "Cannot proceed with release due to failed checks."
        print_warning "Version files have been updated but no commit/tag created."
        exit 1
    fi

    # Check if working directory is clean (except for version changes)
    if ! git diff --quiet -- packages/hermes-app/package.json packages/hermes-api/pyproject.toml; then
        print_error "Working directory has uncommitted changes. Please commit or stash them first."
        exit 1
    fi

    # Create commits
    print_info "Creating release commits..."

    if [ "$new_app_version" != "$current_app_version" ]; then
        git add packages/hermes-app/package.json
        git commit -m "$(create_commit_message "hermes-app" "$new_app_version")"
        print_success "Committed hermes-app version bump"

        # Create tag
        create_tag "app" "$new_app_version"
        git push origin "$(git describe --tags --abbrev=0)"
        print_success "Pushed hermes-app tag"
    fi

    if [ "$new_api_version" != "$current_api_version" ]; then
        git add packages/hermes-api/pyproject.toml
        git commit -m "$(create_commit_message "hermes-api" "$new_api_version")"
        print_success "Committed hermes-api version bump"

        # Create tag
        create_tag "api" "$new_api_version"
        git push origin "$(git describe --tags --abbrev=0)"
        print_success "Pushed hermes-api tag"
    fi

    # Push commits if any were created
    if [ "$new_app_version" != "$current_app_version" ] || [ "$new_api_version" != "$current_api_version" ]; then
        git push origin main
        print_success "Pushed commits to main"
    fi

    echo ""
    print_success "🎉 Release preparation complete!"
    echo ""
    print_info "Next steps:"
    echo "1. GitHub Actions will automatically build and publish Docker images"
    echo "2. Check the Actions tab for build status"
    echo "3. Monitor the release in GitHub Container Registry"
    echo ""
    print_info "Tags created:"
    if [ "$new_app_version" != "$current_app_version" ]; then
        echo "  - hermes-app-v$new_app_version"
    fi
    if [ "$new_api_version" != "$current_api_version" ]; then
        echo "  - hermes-api-v$new_api_version"
    fi
}

# Run main function
main "$@"
