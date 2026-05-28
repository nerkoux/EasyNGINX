---
id: overview
title: Command overview
sidebar_position: 1
---

# Command overview

Every EasyNginx feature lives under a single binary: `easynginx`. Run `sudo easynginx --help` for a list, or `sudo easynginx <command> --help` for any individual command.

## Quick map

| Group | Commands |
|---|---|
| [Site management](site.md) | `create`, `list`, `info`, `edit`, `logs`, `enable`, `disable`, `remove`, `clone`, `maintenance` |
| [nginx control](nginx-control.md) | `reload`, `restart`, `status`, `test`, `doctor` |
| [Backup & restore](backup.md) | `backup`, `backups`, `inspect`, `verify`, `restore` |
| [Certificates](cert.md) | `cert list`, `cert renew`, `cert revoke`, `cert self-sign`, `cert upload` |
| [Security](security.md) | `audit`, `tls`, `hsts`, `botblock`, `geoip`, `fail2ban`, `modsec`, `waf` |
| [Observability](observability.md) | `metrics`, `stats`, `healthz` |
| [Presets](preset.md) | `php install`, `preset wordpress`, `preset laravel`, `preset node`, `preset static` |
| [Cluster](cluster.md) | `cluster add`, `cluster list`, `cluster deploy` |
| [Dashboard](dashboard.md) | `dashboard start`/`stop`/`status`/`enable`/`disable`/`token` |
| [Updates](update.md) | `update check`, `update install`, `update rollback`, `update snapshots` |
| [Admin](admin.md) | `self-update`, `uninstall`, `--version` |

## Conventions

- **Every command requires root** because it touches `/etc/nginx`, the firewall, or systemd. Use `sudo`.
- **Interactive by default.** Skip flags to be prompted; pass `-y` / `--yes` to answer yes to confirmations.
- **`--help` is universal.** Run it on any command to see the full flag list.
- **Failure is loud and reversible.** Anything that writes config takes a snapshot first and runs `nginx -t` before reloading.
