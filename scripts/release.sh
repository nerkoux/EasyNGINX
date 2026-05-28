#!/usr/bin/env bash
# Helper: cut a release.
#
# Usage: scripts/release.sh 0.3.1
#
#   1. Bumps lib/version.py to the new version.
#   2. Creates a CHANGELOG entry stub if missing.
#   3. Commits + tags v<version> + pushes both.
#
# After this runs, the auto-update system on every installed copy of
# EasyNginx will pick up the new version on its next 24h refresh.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <new-version>" >&2
    echo "Example: $0 0.3.1" >&2
    exit 2
fi

NEW_VERSION="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$ROOT/lib/version.py"

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "Error: $VERSION_FILE not found." >&2
    exit 1
fi

CURRENT=$(grep '^__version__' "$VERSION_FILE" | sed -E 's/.*"([^"]+)".*/\1/')
echo "Current version: $CURRENT"
echo "New version    : $NEW_VERSION"

# 1. Bump version.py
python3 - "$VERSION_FILE" "$NEW_VERSION" <<'PY'
import re, sys
path, new = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
text = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new}"', text)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"  bumped __version__ to {new}")
PY

# 2. Commit + tag (only if we're inside a git work tree).
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$ROOT" add lib/version.py CHANGELOG.md 2>/dev/null || true
    git -C "$ROOT" commit -m "release: v$NEW_VERSION" || {
        echo "Nothing to commit (already up to date?)."
    }
    git -C "$ROOT" tag -a "v$NEW_VERSION" -m "EasyNginx v$NEW_VERSION"
    echo
    echo "Tag v$NEW_VERSION created locally."
    echo "Push with:  git push && git push --tags"
else
    echo "Not in a git repo; skipping commit/tag."
fi

echo
echo "Done. Next steps:"
echo "  1. git push && git push --tags"
echo "  2. Optionally publish a GitHub release using the new tag."
echo "  3. Existing installs will see the update banner within 24h, or"
echo "     immediately when users run 'sudo easynginx update check'."
