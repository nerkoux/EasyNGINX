---
id: migrate
title: Migrate to a new server
sidebar_position: 4
---

# Migrate to a new server

Two commands move every site, certificate, and EasyNginx state from one server to another.

## On the old server

```bash
sudo easynginx backup --with-www --with-php --label "migration"
scp /etc/easynginx/backups/easynginx-backup-*.tar.gz user@new-server:/root/
```

`--with-www` includes `/var/www` and `/srv/www` document roots. `--with-php` includes `/etc/php` and PHP-FPM pools. Drop these flags if you only want config-level state.

## On the new server

```bash
sudo EASYNGINX_RESTORE=/root/easynginx-backup-*.tar.gz bash install.sh
```

The installer detects you've passed a backup, runs a fresh install, then extracts the archive on top. It validates with `nginx -t` before reloading — if validation fails the restore aborts and points you at the safety snapshot for manual recovery.

## What gets migrated

- `/etc/nginx/` — every site, snippet, and the main `nginx.conf`.
- `/etc/easynginx/` — config, cluster inventory, dashboard token, auth files, maintenance pages.
- `/etc/letsencrypt/` — your certs.
- `/var/www` and `/srv/www` if `--with-www` was used.
- `/etc/php` and PHP-FPM pools if `--with-php` was used.

## Cross-distro migration

The manifest records the source distro family. You can:

- Migrate Ubuntu → Debian or RHEL → Rocky without changes.
- Migrate Debian-style (with `sites-available`/`sites-enabled`) → RHEL-style (`conf.d`-only). EasyNginx will warn that the layouts differ and recommend a quick review of `nginx.conf` for any include lines that point at paths that don't exist on the new distro.

## Updating DNS

Change your domain's A/AAAA records to point at the new server **before** running the restore on the new server. Otherwise certbot won't be able to renew certs (issuance was already done on the old box, so the certs themselves still work, but renewal will fail).

If DNS hasn't propagated yet:

```bash
# Renew once DNS points at the new server
sudo easynginx cert renew --force
```

## Rolling back

If anything goes wrong on the new server, the original server is still running and serving traffic. Just point DNS back. EasyNginx made no changes to the old machine.
