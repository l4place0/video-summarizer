#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/version.sh"

echo "Current version: $CURRENT_VERSION"
echo "Checking for updates..."

LATEST=$(curl -sf "https://api.github.com/repos/$GITHUB_REPO/releases/latest" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null || echo "")

if [ -z "$LATEST" ]; then
    echo "Error: Could not check for updates. Network error or no releases found."
    exit 1
fi

echo "Latest version: $LATEST"

if [ "$CURRENT_VERSION" = "$LATEST" ]; then
    echo "You are up to date!"
else
    echo ""
    echo "Update available: $CURRENT_VERSION -> $LATEST"
    echo "Update with:"
    echo "  cd $SCRIPT_DIR/../../.. && git pull origin master"
fi
