---
id: architecture
title: Architecture
sidebar_position: 99
---

# Architecture

EasyNginx is intentionally split between bash (for bootstrap) and Python (for everything else). The installer has to run before Python is guaranteed; everything afterwards runs through Python where we get real data structures, JSON, regex, templating, and clean error handling.

## Process diagram

```
┌──────────────┐   pipes JSON-ish state    ┌────────────────────────┐
│  install.sh  │ ─────────────────────────▶│  /etc/easynginx/...    │
│  (bash)      │                           │  config.json, backups  │
└──────┬───────┘                           └────────────────────────┘
       │ installs
       ▼
┌──────────────┐                           ┌────────────────────────┐
│  easynginx   │  exec → python3 main.py   │ /usr/local/share/      │
│  (bash shim) │ ─────────────────────────▶│   easynginx/lib/*.py   │
└──────────────┘                           │   easynginx/templates/ │
                                           └────────────────────────┘
```

## Module map

| Module | Responsibility |
|---|---|
| `main.py` | argparse entry, dispatches to commands |
| `commands.py` | High-level verbs (create, list, backup, etc.) |
| `cmd_site.py` | info / edit / logs / clone / maintenance |
| `cmd_admin.py` | reload / restart / status / test / uninstall |
| `cmd_cert.py` | SSL lifecycle (list / renew / revoke / self-sign / upload) |
| `cmd_security.py` | audit / TLS / HSTS / botblock / GeoIP / fail2ban / modsec / waf |
| `cmd_observability.py` | metrics / stats / healthz |
| `cmd_preset.py` | php / wordpress / laravel / node / static |
| `cmd_cluster.py` | Multi-server deploy over SSH |
| `cmd_dashboard.py` + `dashboard_server.py` | Local web UI |
| `cmd_update.py` + `updater.py` + `version.py` | Update system |
| `backup.py` | Tar+sha256 backup engine |
| `nginx.py` | Site file management with distro-layout abstraction |
| `validation.py` | Domain / email / URL / DNS / port / upstream checks |
| `templates.py` | Tiny `{{ var }}` + `{% if %}` renderer (no Jinja) |
| `certbot.py` | Wrapper over `certbot --nginx` and renew |
| `firewall.py` | ufw / firewalld helpers |
| `helpers.py` | Cross-module utilities (systemctl, log parsing, cert expiry) |
| `ui.py` | Console output and prompts |

## Why no third-party deps

The whole engine uses only the Python standard library. No `pip install`, no `venv`, no version-pinning surprises. EasyNginx works on a freshly-installed server with whatever `python3` package the distro ships.

This includes:

- `templates.py` — handwritten `{{var}}` + `{% if %}` renderer.
- `dashboard_server.py` — `http.server.BaseHTTPRequestHandler`, no Flask/FastAPI.
- `updater.py` — `urllib.request` + `tarfile` + `os.replace`.
- `cluster.py` — `ssh`/`scp` shelled out, no Paramiko.

## Distro abstraction

`config.py` translates the `distro_family` recorded by the installer into the right paths:

- **debian / arch**: `/etc/nginx/sites-available` + symlinks in `sites-enabled`.
- **rhel / fedora / alpine**: single `/etc/nginx/conf.d` directory; disabled sites get a `.disabled` suffix instead of a symlink toggle.

Adding a new distro is one new `case` block in `install.sh` and (if the layout differs) one new mapping in `_detect_nginx_paths()`.

## File layout on disk

| Path | What's there |
|---|---|
| `/usr/local/bin/easynginx` | The CLI binary (small bash launcher). |
| `/usr/local/share/easynginx/lib/` | Python engine modules. |
| `/usr/local/share/easynginx/templates/` | nginx config templates. |
| `/usr/local/share/easynginx/templates/html_vendors/` | Bundled HTML pages (maintenance, error). |
| `/etc/easynginx/config.json` | Detected distro + paths the engine uses. |
| `/etc/easynginx/version-cache.json` | Update probe cache. |
| `/etc/easynginx/backups/` | Per-site backups and pre-restore snapshots. |
| `/etc/easynginx/backups/updates/` | Pre-update engine snapshots. |
| `/etc/easynginx/backups/snapshots/` | Pre-restore safety snapshots. |
| `/etc/easynginx/maintenance/` | Maintenance-mode HTML pages. |
| `/etc/easynginx/auth/` | Per-site basic-auth htpasswd files. |
| `/etc/easynginx/cluster.yaml` | Cluster inventory (mode `0600`). |
| `/etc/easynginx/dashboard-token` | Dashboard auth token (mode `0600`). |
| `/etc/nginx/easynginx-snippets/` | Shared snippets (TLS profile, bot-block map, etc). |
| `/etc/nginx/sites-available/<domain>.conf` (Debian/Arch) | Site configs EasyNginx writes. |
| `/etc/nginx/conf.d/<domain>.conf` (RHEL/Fedora) | Same, on RHEL-family distros. |
| `/var/log/easynginx/` | EasyNginx logs (dashboard, etc.). |
