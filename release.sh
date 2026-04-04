#!/usr/bin/env bash
#
# release.sh — Create a signed release tag with a Conventional Commits message.
#
# Usage:
#   ./release.sh <version>
#
# Example:
#   ./release.sh 1.0.0
#   ./release.sh 2.1.0
#
# The version argument should follow semver (e.g., 1.0.0, 1.2.3).
# The script will create a signed, annotated tag named v<version>.

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <version>" >&2
  echo "Example: $0 1.0.0" >&2
  exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

# Validate semver format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Error: Version must be in semver format (e.g., 1.0.0)" >&2
  exit 1
fi

# Check that the tag doesn't already exist
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: Tag $TAG already exists" >&2
  exit 1
fi

# Verify working tree is clean
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: Working tree is not clean. Commit or stash changes first." >&2
  exit 1
fi

# Verify GPG signing is configured
if ! git config --get commit.gpgsign >/dev/null 2>&1 || \
   [ "$(git config --get commit.gpgsign)" != "true" ]; then
  echo "Error: commit.gpgsign is not enabled." >&2
  echo "Run: git config commit.gpgsign true" >&2
  exit 1
fi

if ! git config --get tag.gpgsign >/dev/null 2>&1 || \
   [ "$(git config --get tag.gpgsign)" != "true" ]; then
  echo "Error: tag.gpgsign is not enabled." >&2
  echo "Run: git config tag.gpgsign true" >&2
  exit 1
fi

echo "Creating signed tag $TAG..."
git tag -s "$TAG" -m "chore: Release $VERSION"

echo "Tag $TAG created and signed."
echo ""
echo "To push the tag:"
echo "  git push origin $TAG"
