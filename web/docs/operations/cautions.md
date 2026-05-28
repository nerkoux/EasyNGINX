---
id: cautions
title: Cautions & warnings
sidebar_position: 4
---

# Cautions & warnings

Read this before running EasyNginx on a server you care about.

:::warning You are running this as root
The installer modifies `/etc/nginx`, `/etc/letsencrypt`, your firewall, and systemd unit state. It will not delete data, but it can change service behaviour. Always have a backup of your server before installing third-party automation.
:::

:::important Existing nginx configs are preserved by default
The installer never overwrites anything in `/etc/nginx` on a fresh install. Your current sites continue to serve. EasyNginx only manages files it creates (under `sites-available`/`conf.d`) plus the snippets it writes into `/etc/nginx/easynginx-snippets/`.
:::

:::warning `easynginx restore` will overwrite key paths
Restore overwrites `/etc/nginx`, `/etc/easynginx`, and `/etc/letsencrypt` — that's the whole point. A safety snapshot of the previous state is taken to `/etc/easynginx/backups/snapshots/` before any file is touched. If `nginx -t` fails after restore, EasyNginx tells you where the snapshot lives so you can revert manually.
:::

:::warning Firewall is never auto-enabled
The installer adds rules to allow HTTP/HTTPS but never enables a disabled firewall. If you're on a fresh Ubuntu box and `ufw` was off, it stays off. Decide consciously whether you want a firewall enabled. Same applies to firewalld.
:::

:::important DNS must point at your server before SSL can succeed
Let's Encrypt verifies you control the domain by hitting it on port 80. EasyNginx checks DNS for you and warns when records don't resolve to this host, but it cannot proxy DNS. If you're behind Cloudflare, the warning is informational — issuance still works through the http-01 challenge.
:::

:::caution HSTS preload is permanent
Once you submit a domain to the HSTS preload list, removing it takes weeks to months. EasyNginx warns when you toggle on `--preload` but the warning won't stop you. Only enable preload when **every** subdomain serves HTTPS, including ones you might add later.
:::

:::caution `cert revoke` is irreversible
A revoked certificate cannot be un-revoked. You can issue a new one immediately, but any client that pinned the old cert will break.
:::

:::note HTTP/3 (QUIC) requires a recent nginx
Distro packages on Debian 11, Ubuntu 20.04, and older RHEL builds don't ship a QUIC-capable nginx. EasyNginx detects this and falls back to HTTP/2 with a hint.
:::

:::note GeoIP and ModSecurity require nginx modules
The matching modules aren't installed by default on every distro. EasyNginx's `geoip` and `waf` commands warn when the module isn't present and refuse to write a config that would fail `nginx -t`.
:::

## Risk levels

| Operation | Risk | Reversible? |
|---|---|---|
| `easynginx create`, `edit`, `enable`, `disable` | Low — auto-rollback on failure | Yes |
| `easynginx audit`, `info`, `list`, `logs`, `update check` | None — read-only | n/a |
| `easynginx update install` | Low — engine-only, snapshotted | `easynginx update rollback` |
| `easynginx restore` | Medium — overwrites managed paths | Manual restore from safety snapshot |
| `easynginx cert revoke` | High — cannot be undone | No |
| `easynginx uninstall --purge` | Medium — deletes EasyNginx state | No (but nginx + certs preserved) |
| HSTS `--preload` | High — long-lived browser commitment | Months to undo |

## Best practices

1. **Take a backup before your first changes** on a production server.
2. **Try changes in a staging environment** when possible — `easynginx clone` makes this trivial.
3. **Read the audit output** after major changes.
4. **Keep update snapshots** — don't manually delete `/etc/easynginx/backups/updates/`.
5. **Pin EasyNginx version** in CI with `--target v<version>` so updates land on your schedule.
