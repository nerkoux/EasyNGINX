---
id: backup
title: Backup & restore
sidebar_position: 4
---

# Backup & restore

EasyNginx backups are reproducible, sha256-verified tarballs of `/etc/nginx`, `/etc/easynginx`, and (optionally) `/etc/letsencrypt`, document roots, and PHP pools.

For the underlying mechanics see [Backup & restore mechanics](../operations/backup-restore.md).

## `backup`

```bash
sudo easynginx backup
sudo easynginx backup --with-www --with-php \
                      --label "before-php8-upgrade" \
                      --note "All sites green pre-upgrade"
```

### Flags

| Flag | Default | Effect |
|---|---|---|
| `--no-ssl` | off | Skip `/etc/letsencrypt`. Config-only snapshots. |
| `--with-www` | off | Include `/var/www` and `/srv/www` document roots. |
| `--with-php` | off | Include `/etc/php` and PHP-FPM pools. |
| `--include PATH` | — | Add an arbitrary path. Repeatable. |
| `--label NAME` | `manual` | Free-form label baked into the filename. |
| `--note "..."` | empty | Note stored inside the manifest. |
| `--output-dir DIR` | `/etc/easynginx/backups` | Where the tarball is written. |

A sidecar `.sha256` file is written next to each tarball. You can verify with plain `sha256sum -c` even without EasyNginx installed.

## `backups`

List local backups with date, host, label, size.

```bash
sudo easynginx backups
sudo easynginx backups --dir /var/backups
```

Searches the explicit `--dir` first, then falls back to the usual locations (`~`, `/root`, `/tmp`, `/var/backups`, `/etc/easynginx/backups`).

## `inspect`

Show the manifest of a backup without extracting anything.

```bash
sudo easynginx inspect /etc/easynginx/backups/easynginx-backup-prod-...tar.gz
```

Prints: format version, creation date, source hostname and distro, label, note, included roots, file count.

## `verify`

Re-checksum every payload file against the manifest.

```bash
sudo easynginx verify /etc/easynginx/backups/easynginx-backup-prod-...tar.gz
```

Detects bit-flips, partial transfers, and tampering. A missing or corrupted file causes a non-zero exit.

## `restore`

Restore a backup onto the live filesystem.

```bash
sudo easynginx restore                         # interactive picker
sudo easynginx restore /path/to/backup.tar.gz  # explicit
sudo easynginx restore /path/to/backup.tar.gz --yes  # skip confirmation
sudo easynginx restore /path/to/backup.tar.gz --skip-verify  # skip checksum
```

What restore does:

1. Inspects the manifest. Aborts if it isn't an EasyNginx backup.
2. Verifies sha256 of every file (unless `--skip-verify`).
3. Snapshots the live `/etc/nginx`, `/etc/easynginx`, and `/etc/letsencrypt` to `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz`.
4. Extracts the payload to a temp dir, validates against tar-traversal, then copies into place preserving mode/owner/mtime.
5. Runs `nginx -t`. If validation fails, EasyNginx aborts and tells you where the safety snapshot lives so you can revert manually.
6. Reloads nginx if validation passes.

:::warning Restore overwrites
Restore is destructive by design. The safety snapshot is your undo button:

```bash
sudo tar xzf /etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz -C /
sudo systemctl reload nginx
```
:::

See [Backup & restore mechanics](../operations/backup-restore.md) for tar layout, manifest format, and cross-distro restore notes.
