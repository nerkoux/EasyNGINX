---
id: update
title: Updates
sidebar_position: 11
---

# Updates

EasyNginx checks for new versions automatically and never overwrites your data when updating. See [Updates mechanics](../operations/updates.md) for the full design.

## Auto-detection

Every command silently reads `/etc/easynginx/version-cache.json`. If a newer version is published you see one line on stderr:

```
[easynginx] Update available: 0.1.0 → 0.1.1  (run easynginx update to install)
```

The cache refreshes itself in the background **at most once per 24 hours** in a detached subprocess, so commands never block waiting on GitHub.

To silence the banner:

```bash
export EASYNGINX_NO_UPDATE_CHECK=1
```

## `update check`

Force an immediate check.

```bash
sudo easynginx update check
sudo easynginx update check --json   # machine-readable
```

## `update install`

Download and install the update.

```bash
sudo easynginx update install
sudo easynginx update install --target v0.2.0   # specific tag
sudo easynginx update install --target main     # bleeding edge
sudo easynginx update install --force            # reinstall current version
sudo easynginx update install --yes              # skip confirmation
```

What happens, in order:

1. Probe GitHub for the latest version.
2. Download every engine file into `/tmp/easynginx-update-*`.
3. Run `py_compile` on every Python module — abort if any fails to parse.
4. Snapshot the current engine + config to `/etc/easynginx/backups/updates/engine-before-<version>-<timestamp>.tar.gz`.
5. Atomically replace each engine file in place with `os.replace`.
6. Bump the `version` field in `/etc/easynginx/config.json`.

:::important Updates only touch engine files
The updater is hard-coded to a list of paths under `/usr/local/bin/easynginx`, `/usr/local/share/easynginx/lib/`, and `/usr/local/share/easynginx/templates/`. Nothing under `/etc/nginx`, `/etc/letsencrypt`, your data directories, or any other location can be modified by an update.
:::

## `update rollback`

Restore the previous engine snapshot.

```bash
sudo easynginx update rollback
```

Picks the most recent snapshot from `/etc/easynginx/backups/updates/`. To restore an older one, list snapshots first.

## `update snapshots`

```bash
sudo easynginx update snapshots
```

Lists all rollback points (newest first) with file size. To restore a specific older snapshot:

```bash
sudo tar xzf /etc/easynginx/backups/updates/engine-before-0.1.0-...tar.gz \
            -C /usr/local/share/easynginx --strip-components=0
```

## `self-update`

```bash
sudo easynginx self-update
```

Alias for `easynginx update install`. Kept for muscle memory.
