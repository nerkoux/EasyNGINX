"""Single source of truth for the EasyNginx version.

When you cut a new release:
  1. Bump __version__ here.
  2. Add an entry to CHANGELOG.md.
  3. Tag the commit (e.g. `git tag v0.3.0 && git push --tags`).
  4. Optionally publish a GitHub release; the updater handles either.
"""

__version__ = "0.1.0"

# Where update checks point.
GITHUB_OWNER = "nerkoux"
GITHUB_REPO = "EasyNGINX"
GITHUB_BRANCH = "main"


def github_raw_base(ref: str) -> str:
    """Return the raw.githubusercontent.com base for a tag, branch, or sha."""
    return f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{ref}"


def github_api_base() -> str:
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
