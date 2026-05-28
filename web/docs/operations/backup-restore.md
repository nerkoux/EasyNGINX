---
id: backup-restore
title: Backup & restore mechanics
sidebar_position: 2
---

# Backup & restore mechanics

How the backup format works, what's included, and exactly what restore does.

## Tarball layout

```
easynginx-backup-<host>-<label>-<timestamp>.tar.gz
├── MANIFEST.json     ← path, mode, sha256 of every file captured
└── payload/
    ├── etc/nginx/...
    ├── etc/easynginx/...
    └── etc/letsencrypt/... (optional)
```

A sidecar `.sha256` file is written next to the tarball so you can verify even without EasyNginx installed:

```bash
sha256sum -c easynginx-backup-prod-...tar.gz.sha256
```

## Manifest

Inside the tarball, `MANIFEST.json` describes every payload file:

```json
{
  "version": 1,
  "created_at": "2026-05-28T15:00:00Z",
  "created_by": "root",
  "hostname": "prod-1",
  "distro_id": "ubuntu",
  "distro_family": "debian",
  "platform": "Linux-6.8.0-x86_64",
  "label": "before-php8-upgrade",
  "note": "All sites green",
  "options": {
    "include_ssl": true,
    "include_www": false,
    "include_php": false,
    "extra_paths": []
  },
  "targets": ["/etc/nginx", "/etc/easynginx", "/etc/letsencrypt"],
  "files": [
    {
      "arcname": "payload/etc/nginx/sites-available/example.com.conf",
      "src": "/etc/nginx/sites-available/example.com.conf",
      "size": 1042,
      "mode": 420,
      "sha256": "..."
    }
  ]
}
```

`easynginx verify` re-checksums every file against this manifest. A single bit-flip in the archive is detected.

## Default contents

| Path | Default | Flag |
|---|---|---|
| `/etc/nginx` | always | — |
| `/etc/easynginx` | always | — |
| `/etc/letsencrypt` | included | `--no-ssl` to skip |
| `/var/www`, `/srv/www` | excluded | `--with-www` to include |
| `/etc/php`, `/etc/php-fpm.d`, `/etc/php-fpm.conf` | excluded | `--with-php` to include |
| Anything else | — | `--include /path` (repeatable) |

## Restore step-by-step

1. **Inspect** the manifest. Aborts if the archive isn't an EasyNginx backup.
2. **Verify** every file's sha256 against the manifest. Aborts if any mismatch (skip with `--skip-verify` only if you have a reason).
3. **Snapshot** the live `/etc/nginx`, `/etc/easynginx`, and `/etc/letsencrypt` to `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz`.
4. **Extract** the payload to a temp dir, validate against tar-traversal attacks, then copy into place preserving mode, owner, and mtime.
5. **Validate** with `nginx -t`. If validation fails, EasyNginx aborts and tells you where the snapshot lives so you can revert manually:
   ```bash
   sudo tar xzf /etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz -C /
   sudo systemctl reload nginx
   ```
6. **Reload** nginx if validation passes.

## Cross-distro restore

The manifest records the source distro family. Restoring a Debian-style backup (with `sites-available`/`sites-enabled`) onto a RHEL host works — the files land in `/etc/nginx` exactly as they were captured. EasyNginx warns when source and target families differ so you can hand-tune `nginx.conf` includes if needed.

The most common edits after a cross-distro restore:

- Debian → RHEL: ensure `nginx.conf` includes `/etc/nginx/conf.d/*.conf`. Move site files from `sites-available/` if they didn't already get there.
- RHEL → Debian: ensure `nginx.conf` includes `/etc/nginx/sites-enabled/*`. Set up symlinks from `sites-available/` to `sites-enabled/`.

## Path-traversal defence

Tar files can contain entries like `../../../etc/passwd`. EasyNginx validates every member's resolved path before extracting and refuses anything outside the destination directory. A tampered backup can corrupt itself but cannot escape the temp extraction directory.

## Format versioning

The manifest's `version` field starts at `1`. Future format changes will bump it. The restore code refuses any version it doesn't understand, so an old EasyNginx won't try to extract a newer-format backup it might mishandle.

## Where backups go

Default: `/etc/easynginx/backups/`. Override with `--output-dir`:

```bash
sudo easynginx backup --output-dir /mnt/nas/easynginx
```

`easynginx backups` lists from the explicit dir first, then falls back to common locations (`~`, `/root`, `/tmp`, `/var/backups`, `/etc/easynginx/backups`).

For off-server backups, sync the directory yourself with `rclone`, `restic`, `borgbackup`, or your favourite tool.
