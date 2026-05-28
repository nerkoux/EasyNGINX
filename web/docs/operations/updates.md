---
id: updates
title: Updates mechanics
sidebar_position: 3
---

# Updates mechanics

How auto-detection, install, and rollback work under the hood.

## Cache file

Every command silently reads `/etc/easynginx/version-cache.json`:

```json
{
  "checked_at"     : "2026-05-28T15:00:00Z",
  "latest_version" : "0.2.0",
  "latest_tag"     : "v0.2.0",
  "release_url"    : "https://github.com/nerkoux/EasyNGINX/releases/tag/v0.2.0",
  "release_notes"  : "...",
  "source"         : "release"
}
```

If the cached `latest_version` is newer than what's installed, the banner prints to stderr:

```
[easynginx] Update available: 0.1.0 → 0.2.0  (run easynginx update to install)
```

`source` tells you how the version was discovered:

- `release` — from a published GitHub release.
- `tag` — from a git tag (no release notes).
- `commit` — from `lib/version.py` on the default branch (when neither releases nor tags exist).

## Background refresh

When the cache is older than 24h (or missing), the next CLI invocation forks a detached subprocess that refreshes it. The current command never blocks waiting for GitHub.

To prevent any update probing globally:

```bash
export EASYNGINX_NO_UPDATE_CHECK=1
```

Useful for air-gapped servers and tightly-sandboxed containers.

## Probe order

The updater tries three sources in fallback order:

1. `GET https://api.github.com/repos/nerkoux/EasyNGINX/releases/latest`
2. `GET https://api.github.com/repos/nerkoux/EasyNGINX/tags?per_page=1`
3. `GET https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/lib/version.py`

Any one succeeding is enough. Total network failure just leaves the cache empty — no banner, no error.

## Install pipeline

`easynginx update install` runs:

1. **Probe** GitHub for the latest version.
2. **Download** every engine file into a staging directory (`/tmp/easynginx-update-*`).
3. **Compile** each downloaded `.py` with `py_compile`. If anything fails to parse, abort — no files are installed.
4. **Snapshot** the current engine + config to `/etc/easynginx/backups/updates/engine-before-<version>-<timestamp>.tar.gz`.
5. **Atomically replace** each engine file with `os.replace`. On POSIX same-filesystem renames this is atomic — no half-written state.
6. **Bump** the `version` field in `/etc/easynginx/config.json`.

## What can be touched

The updater's allow-list of paths (in `lib/updater.py`):

- `/usr/local/bin/easynginx`
- `/usr/local/share/easynginx/lib/*.py`
- `/usr/local/share/easynginx/templates/*.conf`
- `/usr/local/share/easynginx/templates/html_vendors/*.html`

That's the entire surface area. Nothing else.

## Rollback

The most recent snapshot tarball lives at:

```
/etc/easynginx/backups/updates/engine-before-<version>-<timestamp>.tar.gz
```

It contains the same set of engine files plus `config.json`. `easynginx update rollback` extracts it back into place.

For older snapshots, `easynginx update snapshots` lists everything available and you can restore manually:

```bash
sudo tar xzf /etc/easynginx/backups/updates/engine-before-0.1.0-...tar.gz \
            -C /usr/local/share/easynginx --strip-components=0
```

The snapshot has the same path-traversal validation as restore: the tarball can only restore files in the allow-list, never anything else.

## Pinning a specific version

Keep an old version, or test a release before letting auto-update suggest it:

```bash
sudo easynginx update install --target v0.1.0
sudo easynginx update install --target main
sudo easynginx update install --target 9b3a2f1   # specific commit sha
```

`--target main` installs from the tip of the default branch — handy for verifying unreleased features.
