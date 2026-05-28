---
id: safety
title: Production safety
sidebar_position: 1
---

# Production safety

EasyNginx is designed to never leave nginx in a broken state. Every operation that writes config follows the same pattern.

## The core flow

```
Snapshot → Write → nginx -t → Reload
                       │
                       └─ failure → restore snapshot → re-test → bail with diagnostics
```

If any step fails, EasyNginx restores the previous version and exits with the failure output. nginx is never reloaded with a broken config.

## What gets snapshotted, where

| Operation | What's snapshotted | Where it lives |
|---|---|---|
| `easynginx create` overwriting an existing site | Old `<domain>.conf` | `/etc/easynginx/backups/<domain>.conf.bak` |
| `easynginx edit` | Pre-edit config | `/etc/easynginx/backups/<domain>.conf.pre-edit-<unix>` |
| `easynginx restore` | Live `/etc/nginx`, `/etc/easynginx`, `/etc/letsencrypt` | `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz` |
| `easynginx update install` | Whole engine + config | `/etc/easynginx/backups/updates/engine-before-<version>-<timestamp>.tar.gz` |
| `easynginx cluster deploy` | Remote site config | `/etc/easynginx/backups/<domain>.cluster-prev` on each host |

If a deployment fails mid-way through a multi-host cluster deploy, the failed host is rolled back automatically while successful hosts keep the new config. You get a per-host summary at the end.

## Pre-flight checks

Every `easynginx create` runs a pre-flight that confirms:

- ✅ Domain syntax (RFC 1035-ish + length limits).
- ✅ DNS A/AAAA records actually point at this host.
- ✅ Ports 80 and 443 are listening (or free).
- ✅ Backend URLs are TCP-reachable for proxy/websocket modes.
- ✅ Duplicate site detection.
- ✅ certbot availability before you ask for SSL.
- ✅ `nginx -t` validation before any reload.

Anything that fails as a hard error stops the create. Anything that's just a warning (e.g. DNS doesn't yet resolve) is reported but lets you continue if you want.

## What EasyNginx never touches

Reasoning by exclusion is the easiest way to trust this. The updater is hard-coded to a list of paths, so:

**Never modified by `easynginx update`:**
- `/etc/nginx/**` — your sites and certs.
- `/etc/letsencrypt/**`.
- `/etc/easynginx/cluster.yaml`.
- `/etc/easynginx/auth/**`.
- `/etc/easynginx/dashboard-token`.
- `/etc/easynginx/backups/**`.
- `/etc/easynginx/maintenance/**`.
- `/var/log/**`.
- Document roots and your application code.

**Never modified by anything outside their own scope:**
- `easynginx hsts api on` only edits `api.example.com.conf` and the global TLS snippet (if it isn't there already).
- `easynginx botblock api on` only edits `api.example.com.conf` and the global bot-block map (if missing).
- `easynginx audit` is read-only.
- `easynginx logs`, `info`, `list`, `inspect`, `verify`, `stats`, `cert list`, `update check` are all read-only.

## Backups before changes

For any production server, take a backup before your first round of EasyNginx commands:

```bash
sudo easynginx backup --label "before-easynginx-changes"
```

If something goes wrong, [`easynginx restore`](../commands/backup.md) brings you back. The restore itself takes a safety snapshot of the live state before doing anything, so even restore is reversible.
