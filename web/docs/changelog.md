---
id: changelog
title: Changelog
sidebar_position: 100
---

# Changelog

The canonical changelog lives in the repo at [`CHANGELOG.md`](https://github.com/nerkoux/EasyNGINX/blob/main/CHANGELOG.md). The current release is mirrored below.

## [0.1.0] — 2026-05-28

First public release.

### Installer
- One-line bootstrap (`install.sh`) for Ubuntu, Debian, Fedora, RHEL, Rocky, AlmaLinux, Arch, Manjaro, EndeavourOS.
- Distro detection via `/etc/os-release` with `ID_LIKE` fallback.
- Automatic EPEL enablement on RHEL-based systems for certbot.
- Installs nginx, certbot, certbot-nginx, python3, dig, openssl, and a firewall (ufw or firewalld).
- Opens HTTP/HTTPS in the firewall without enabling a disabled firewall.
- Interactive choice between fresh install and restore-from-backup (or `EASYNGINX_RESTORE=path` for non-interactive).
- ASCII banner shown when running on a TTY.

### CLI (`easynginx`)

**Site management:** `create`, `list`, `info`, `edit`, `logs`, `enable`, `disable`, `remove`, `clone`, `maintenance`.

**nginx control:** `reload`, `restart`, `status`, `test`, `doctor`.

**Backups:** `backup`, `backups`, `inspect`, `verify`, `restore`. Tarball with sha256 manifest, sidecar `.sha256` file, safety snapshot before every restore, cross-distro restore support.

**Certificates:** `cert list/renew/revoke/self-sign/upload`. Color-coded expiry list.

**Security:** `audit`, `tls modern|intermediate|legacy`, `hsts`, `botblock`, `geoip allow|deny`, `fail2ban install`, `modsec install`, `waf`.

**Observability:** `metrics enable|disable`, `stats`, `healthz`.

**Presets:** `php install`, `preset wordpress|laravel|node|static`. Node preset can register a systemd unit for the upstream service.

**Cluster:** `cluster add|list|deploy`. SSH-based per-host deploy with snapshot, validate, reload, and automatic rollback on failure. Inventory in `/etc/easynginx/cluster.yaml`.

**Dashboard:** `dashboard start|stop|status|enable|disable|token`. Stdlib HTTP server on `127.0.0.1:9088`, token-gated, read-only by design.

**Updates:** `update check|install|rollback|snapshots`. Background 24h cache. Atomic engine swap with `os.replace`. Pre-install `py_compile` check. Engine-only — never touches `/etc/nginx`, `/etc/letsencrypt`, or your data.

**Admin:** `self-update` (alias), `uninstall [--purge]`, `--version`.

### Site templates
Reverse proxy, static, PHP-FPM, WebSocket, redirect, load balancer. All support optional gzip, security headers, basic auth, and rate limiting via `{% if %}` blocks.

### Safety
- Every config write goes through snapshot → write → `nginx -t` → reload, with automatic rollback to the last known good config if validation fails.
- Pre-flight checks on `create`: domain syntax, DNS resolution, port reachability, upstream reachability, duplicate detection, certbot availability.
- Existing configs in `/etc/nginx` are never overwritten without explicit user confirmation.

### Tests
- `tests/smoke_test.py` — validators and template rendering.
- `tests/backup_test.py` — backup round-trip + tamper detection.
- `tests/cli_test.py` — every CLI subcommand parses (55 surfaces).
- `tests/updater_test.py` — version parsing, cache behaviour, network fallbacks.
