#!/usr/bin/env bash
#
# Determines the next semantic version based on conventional commits
# since the last tag, then creates and pushes the tag to trigger
# the draft-release workflow.
#
# Usage:
#   ./scripts-build/release.sh           # auto-detect bump type
#   ./scripts-build/release.sh patch     # force patch bump
#   ./scripts-build/release.sh minor     # force minor bump
#   ./scripts-build/release.sh major     # force major bump
#
set -euo pipefail

FORCE_BUMP="${1:-}"

# Get the latest semver tag
LATEST_TAG=$(git tag --sort=-version:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1)

if [[ -z "$LATEST_TAG" ]]; then
  echo "No existing version tags found. Starting at v0.1.0"
  NEXT_TAG="v0.1.0"
else
  # Parse current version
  VERSION="${LATEST_TAG#v}"
  MAJOR=$(echo "$VERSION" | cut -d. -f1)
  MINOR=$(echo "$VERSION" | cut -d. -f2)
  PATCH=$(echo "$VERSION" | cut -d. -f3)

  echo "Current version: $LATEST_TAG"

  if [[ -n "$FORCE_BUMP" ]]; then
    BUMP="$FORCE_BUMP"
    echo "Forced bump type: $BUMP"
  else
    # Analyze commits since last tag to determine bump type
    BUMP="patch"
    BUMP_REASON="no feat or breaking change commits found (defaulting to patch)"
    while IFS= read -r subject; do
      if echo "$subject" | grep -qE '^feat(\(.+\))?!:|^fix(\(.+\))?!:|^refactor(\(.+\))?!:|BREAKING CHANGE'; then
        BUMP="major"
        BUMP_REASON="breaking change: $subject"
        break
      elif echo "$subject" | grep -qE '^feat(\(.+\))?:'; then
        BUMP="minor"
        BUMP_REASON="new feature: $subject"
      fi
    done <<< "$(git log "${LATEST_TAG}..HEAD" --format='%s')"

    echo "Detected bump type: $BUMP"
    echo "  Reason: $BUMP_REASON"
  fi

  # Calculate next version
  case "$BUMP" in
    major)
      NEXT_TAG="v$((MAJOR + 1)).0.0"
      ;;
    minor)
      NEXT_TAG="v${MAJOR}.$((MINOR + 1)).0"
      ;;
    patch)
      NEXT_TAG="v${MAJOR}.${MINOR}.$((PATCH + 1))"
      ;;
    *)
      echo "Error: Invalid bump type '$BUMP'. Use major, minor, or patch."
      exit 1
      ;;
  esac
fi

# Show what will happen
echo ""
echo "Commits since ${LATEST_TAG:-beginning}:"
if [[ -n "$LATEST_TAG" ]]; then
  git log "${LATEST_TAG}..HEAD" --oneline
else
  git log --oneline
fi

echo ""
echo "Next version: $NEXT_TAG"
echo ""

# Confirm with user
read -rp "Create and push tag $NEXT_TAG? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

git tag "$NEXT_TAG"
git push origin "$NEXT_TAG"

echo ""
echo "Tag $NEXT_TAG pushed. The draft-release workflow will create a draft release on GitHub."
echo "Once ready, publish the draft at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/releases"
