<div align="center">

```
    ______                 _   _____________   ___  __
   / ____/___ ________  __/ | / / ____/  _/ | / / |/ /
  / __/ / __ `/ ___/ / / /  |/ / / __ / //  |/ /|   / 
 / /___/ /_/ (__  ) /_/ / /|  / /_/ // // /|  //   |  
/_____/\__,_/____/\__, /_/ |_/\____/___/_/ |_//_/|_|  
                 /____/                               
```

### Friendly nginx setup for everyone.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Made for Linux](https://img.shields.io/badge/platform-linux-1f425f.svg)](https://www.kernel.org/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/shell-bash-4eaa25.svg)](https://www.gnu.org/software/bash/)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/nerkoux/EasyNGINX)

**One installer. One command. Every distro.**

📚 **[Full documentation →](https://easynginx.akshatmehta.com)**

[Install](#-install) • [Quick start](#-quick-start) • [Commands](#-command-reference) • [Backup & restore](#-backup--restore) • [Production safety](#-production-safety) • [FAQ](#-faq)

</div>

---

## What is EasyNginx?

EasyNginx is a single, friendly CLI (`easynginx`) that turns nginx into something a beginner can actually use without breaking their server. It walks you through creating virtual hosts (reverse proxies, static sites, PHP, WebSockets, redirects, load balancers), issues Let's Encrypt SSL certificates, opens the firewall, hardens the config, takes backups, and rolls back automatically when anything goes wrong.

It works on **fresh servers** (one install command and you're live) and on **existing production servers** (it preserves what's already there, lets you opt in to overrides, and snapshots before every change so you can always undo).

> **Author:** Akshat Mehta — [akshatmehta.com](https://akshatmehta.com)
> **GitHub:** [@nerkoux](https://github.com/nerkoux)
> **Repo:** [github.com/nerkoux/EasyNGINX](https://github.com/nerkoux/EasyNGINX)

---

## Why

Setting up nginx properly involves writing TLS profiles by hand, fighting certbot output, remembering which distro puts configs in `sites-available` vs `conf.d`, picking firewall rules, surviving the first time you typo a directive and brick the reload. EasyNginx does all of that for you and gives you a sane CLI to manage it afterwards.

```bash
sudo easynginx create
# Answer 4 questions. Done.
```

```bash
sudo easynginx audit
# See every site's missing headers, expiring certs, weak ciphers.
```

```bash
sudo easynginx backup
sudo easynginx restore
# Move a server in two commands.
```

---

## Highlights

| Area | What you get |
|---|---|
| **Setup** | One installer for Ubuntu, Debian, Fedora, RHEL, Rocky, AlmaLinux, Arch, Manjaro, EndeavourOS. |
| **Site creation** | Reverse proxy, static, PHP-FPM, WebSocket, redirect, load balancer, plus presets for WordPress / Laravel / Node / Hugo / Jekyll / Next.js. |
| **SSL** | Let's Encrypt issuance, renewal, revoke, color-coded expiry list, self-signed for dev, bring-your-own-cert. |
| **Security** | Audit, TLS profile picker, HSTS, bot blocker, GeoIP allow/deny, fail2ban + nginx jails, ModSecurity + OWASP CRS. |
| **Observability** | `stub_status` metrics, access-log analyzer (top IPs / paths / slowest URLs), `/healthz` endpoints. |
| **Backups** | Tarball with sha256 manifest, safety snapshot before every restore, cross-distro restore support. |
| **Cluster** | YAML inventory, deploy a site to many servers in one command, per-host rollback if anything fails. |
| **Dashboard** | Stdlib-only token-gated read-only web UI on `127.0.0.1:9088`. |
| **Safety** | `nginx -t` runs before every reload. Failed configs automatically revert to the last known good. |

---

## Why EasyNginx (and why not X?)

The closest neighbours all have a place. Here's where each one beats EasyNginx and where EasyNginx wins.

| Tool | Strength | Weakness for the EasyNginx use case | EasyNginx vs. it |
|---|---|---|---|
| **[Nginx Proxy Manager](https://nginxproxymanager.com/)** | Slick web UI, Docker-first | Runs as its own appliance — your existing nginx isn't managed by it; can't audit or back up arbitrary nginx configs | EasyNginx manages the nginx that's already on the box, no extra container, no UI to maintain. |
| **[Caddy](https://caddyserver.com/)** | Automatic HTTPS, simple Caddyfile | Different web server entirely; switching means re-learning every plugin and integration | EasyNginx keeps stock nginx so all your nginx-specific knowledge and snippets still work. |
| **[Traefik](https://traefik.io/)** | Brilliant Docker / Kubernetes service discovery | Heavy if you have one VPS and three sites; not ideal as a hand-rolled site manager | EasyNginx is a CLI, no daemons added, no Docker required. |
| **[Webmin / Virtualmin](https://www.virtualmin.com/)** | Whole-server admin web UI | Heavyweight Perl install with its own auth, sessions, and filesystem layout | EasyNginx is a single Python CLI, no GUI, no daemon, no auth surface. |
| **[certbot --nginx](https://certbot.eff.org/)** | The industry-standard ACME client | Only handles certificates — you still write configs, manage backups, audits, deploys yourself | EasyNginx wraps certbot and adds creation, audit, backup, restore, cluster, atomic updates. |
| **Ansible / Salt / Puppet roles** | Repeatable, declarative | A full IaC stack to learn for one nginx box | EasyNginx is `sudo easynginx create`. No inventory, no playbook, no DSL. |

If you already love and use one of those, keep using it — they're great. EasyNginx is for people who want stock nginx without typing the same five commands on every server they spin up.

> **Want a deeper dive against EasyEngine and Webinoly?** See the [feature parity matrix and reproducible benchmark suite](https://easynginx.akshatmehta.com/docs/comparison) (also at [`bench/`](bench/) in the repo). PRs to fix any inaccurate row are welcome.

---

## 30-second tour

```bash
$ curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
$ sudo easynginx create

  Domain: api.example.com
  Site type:
    1. Reverse proxy
    2. Static website
    3. PHP site
    4. WebSocket app
    5. Redirect
    6. Load balancer
  Choose [1]: 1
  Backend URL: http://127.0.0.1:3000
  Enable HTTPS via Let's Encrypt? [Y/n]: y
  Email for Let's Encrypt: admin@example.com

[ ok ] DNS for api.example.com → 192.0.2.10 (matches this host)
[ ok ] Port 80 listening
[ ok ] Upstream http://127.0.0.1:3000 reachable
[ ok ] Wrote /etc/nginx/sites-available/api.example.com.conf
[ ok ] Site enabled.
[ ok ] nginx config validated.
[ ok ] nginx reloaded.
[ ok ] Let's Encrypt certificate issued for api.example.com.
[ ok ] api.example.com is live at https://api.example.com/
```

What just happened: domain validation, DNS check, upstream probe, snapshot, render, write, `nginx -t`, reload, certbot issuance — all wrapped in automatic rollback if any step fails. nginx is never reloaded with a broken config.

Other one-liners worth trying:

```bash
sudo easynginx audit                      # security report across every site
sudo easynginx info api.example.com       # status + cert expiry
sudo easynginx logs api.example.com -f    # tail access log
sudo easynginx backup --with-www          # tarball with sha256 manifest
sudo easynginx update check               # check GitHub for newer versions
```

---

## 📦 Install

### Recommended: one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
```

> [!CAUTION]
> **Always inspect installer scripts before piping them to a shell.** This is good advice for anything you find on the internet, including this. To audit first:
> ```bash
> curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh -o install.sh
> less install.sh
> sudo bash install.sh
> ```

### Local clone

```bash
git clone https://github.com/nerkoux/EasyNGINX.git
cd EasyNGINX
sudo bash install.sh
```

### Non-interactive (CI, cloud-init, Ansible)

```bash
# Fresh install, no prompts
sudo EASYNGINX_FRESH=1 bash install.sh

# Restore an existing backup at install time
sudo EASYNGINX_RESTORE=/root/easynginx-backup.tar.gz bash install.sh
```

### What the installer does

The interactive installer asks **one question** up front:

```
Choose install mode:
  1) Fresh install (default)
  2) Restore from a previous EasyNginx backup
```

Then it:

1. **Detects the distro** via `/etc/os-release` (with `ID_LIKE` fallback).
2. **Picks the package manager** — `apt`, `dnf`, `yum`, `pacman`, or `apk`.
3. **Enables EPEL** automatically on RHEL-likes (needed for certbot).
4. **Installs** nginx, certbot, the certbot-nginx plugin, python3, dig, openssl, and a firewall (ufw or firewalld).
5. **Enables and starts nginx** via systemd.
6. **Opens 80/443** in the firewall (without enabling the firewall itself if it wasn't already on — see warning below).
7. **Installs the engine** to `/usr/local/share/easynginx`, the CLI to `/usr/local/bin/easynginx`, and writes the detected state to `/etc/easynginx/config.json`.
8. **(Restore mode)** Searches `~`, `/root`, `/tmp`, `/var/backups`, and `/etc/easynginx/backups` for any `easynginx-backup-*.tar.gz`, lets you pick one, takes a safety snapshot of the live nginx config, then extracts the backup. Validates with `nginx -t` before reloading.

### Supported distros

| Distro | Family | Tested | Notes |
|---|---|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | debian | ✅ | Primary target |
| Debian 11 / 12 | debian | ✅ | |
| Linux Mint, Pop!_OS, elementary | debian | ✅ | Via `ID_LIKE` |
| Fedora 38+ | fedora | ✅ | |
| RHEL 8 / 9 | rhel | ✅ | EPEL enabled automatically |
| Rocky Linux 8 / 9 | rhel | ✅ | |
| AlmaLinux 8 / 9 | rhel | ✅ | |
| Amazon Linux 2023 | rhel | ✅ | |
| Arch Linux, Manjaro, EndeavourOS, CachyOS | arch | ✅ | |
| Alpine | alpine | ⏳ | Planned |

---

## ⚠️ Cautions & warnings

Read this **before** running the installer on a server you care about.

> [!WARNING]
> **You are running this as root.** The installer modifies `/etc/nginx`, `/etc/letsencrypt`, your firewall, and systemd unit state. It will not delete data, but it can change service behaviour. Always have a backup of your server before installing third-party automation.

> [!IMPORTANT]
> **Existing nginx configs are preserved by default.** The installer never overwrites anything in `/etc/nginx` on a fresh install. Your current sites continue to serve. EasyNginx only manages files it creates (under `sites-available`/`conf.d`) plus the snippets it writes into `/etc/nginx/easynginx-snippets/`.

> [!WARNING]
> **`easynginx restore` will overwrite `/etc/nginx`, `/etc/easynginx`, and `/etc/letsencrypt`.** This is the entire point of restore — it's how you migrate or roll back. A safety snapshot of the previous state is taken to `/etc/easynginx/backups/snapshots/` before any file is touched. If `nginx -t` fails after restore, EasyNginx tells you where the snapshot lives so you can revert manually.

> [!WARNING]
> **Firewall:** the installer adds rules to allow HTTP/HTTPS but never enables a disabled firewall. If you're on a fresh Ubuntu box and `ufw` was off, it stays off. Decide consciously whether you want a firewall enabled. Same applies to firewalld.

> [!IMPORTANT]
> **DNS must point at your server before SSL can succeed.** Let's Encrypt verifies you control the domain by hitting it on port 80. EasyNginx checks DNS for you and warns when records don't resolve to this host, but it cannot proxy DNS. If you're behind Cloudflare, the warning is informational — issuance still works through the http-01 challenge.

> [!CAUTION]
> **HSTS preload is permanent.** Once you submit a domain to the HSTS preload list, removing it takes weeks to months. EasyNginx warns when you toggle on `--preload` but the warning won't stop you. Only enable preload when **every** subdomain serves HTTPS, including ones you might add later.

> [!CAUTION]
> **`certbot revoke` is irreversible.** A revoked certificate cannot be un-revoked. You can issue a new one immediately, but any client that pinned the old cert will break.

> [!NOTE]
> **HTTP/3 (QUIC) requires a recent nginx.** Distro packages on Debian 11, Ubuntu 20.04 and older RHEL builds don't ship a QUIC-capable nginx. EasyNginx detects this and falls back to HTTP/2 with a hint.

> [!NOTE]
> **GeoIP and ModSecurity require nginx modules** that aren't installed by default. EasyNginx's `geoip` and `waf` commands warn when the modules aren't present and refuse to write a config that would fail `nginx -t`.

---

## 🚀 Quick start

### Brand new server

```bash
# 1. Install
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash

# 2. Create your first site
sudo easynginx create

# 3. Done. Your site is live with HTTPS.
```

### Existing nginx server (don't worry, nothing is overwritten)

EasyNginx happily runs alongside an existing nginx install. Your current configs stay where they are. New sites you create with `easynginx` go into `/etc/nginx/sites-available/<domain>.conf` (Debian/Arch) or `/etc/nginx/conf.d/<domain>.conf` (RHEL/Fedora).

```bash
# Install (won't touch existing configs)
sudo bash install.sh

# Optional: import an existing site under EasyNginx management
# (Just create it again with the same domain — EasyNginx detects the
#  duplicate and asks before overwriting.)
sudo easynginx create --domain api.example.com --type reverse-proxy \
                      --upstream http://127.0.0.1:3000 --no-ssl
```

If you genuinely want to override an existing site:

```bash
sudo easynginx create --domain example.com --yes
# Existing config is backed up to /etc/easynginx/backups/<domain>.conf.bak
# before being replaced. Use `easynginx restore` if you change your mind.
```

### Migrate from another server

On the old server:

```bash
sudo easynginx backup --with-www --with-php --label "migration"
scp /etc/easynginx/backups/easynginx-backup-*.tar.gz user@new-server:/root/
```

On the new server:

```bash
sudo EASYNGINX_RESTORE=/root/easynginx-backup-*.tar.gz bash install.sh
```

That's it. Your sites, certs, and EasyNginx state are all back online.

---

## 🛠 Command reference

The whole CLI is one binary: `easynginx`. Run `sudo easynginx --help` for an overview, or `sudo easynginx <command> --help` for any individual command.

### Site management

| Command | Description |
|---|---|
| `easynginx create [domain]` | Create a new virtual host (interactive by default). |
| `easynginx list` | List managed sites with enable/SSL status. |
| `easynginx info <domain>` | Show domain, type, upstream, SSL cert, expiry, log paths. |
| `easynginx edit <domain>` | Open the config in `$EDITOR`. Validates on save, rolls back if `nginx -t` fails. |
| `easynginx logs <domain> [-f] [--errors] [--both]` | Tail access/error log for a site. |
| `easynginx enable <domain>` | Enable a previously disabled site. |
| `easynginx disable <domain>` | Disable a site without deleting it. |
| `easynginx remove <domain> [--keep-cert]` | Remove a site (and by default its certificate). |
| `easynginx clone <src> <new>` | Copy a site config under a new domain (great for staging). |
| `easynginx maintenance <d> on/off [--page PATH]` | 503 mode with a custom HTML page. |

### nginx control

| Command | Description |
|---|---|
| `easynginx reload` | Zero-downtime nginx reload. |
| `easynginx restart` | Restart nginx via systemd. |
| `easynginx status` | Show nginx service status. |
| `easynginx test` | Run `nginx -t`. |
| `easynginx doctor` | Environment diagnostics (paths, packages, service state). |

### Backup & restore

| Command | Description |
|---|---|
| `easynginx backup [opts]` | Create a tarball of `/etc/nginx`, `/etc/easynginx`, optionally `/etc/letsencrypt`, `/var/www`, `/etc/php`. |
| `easynginx backups` | List local backups with date, host, label, size. |
| `easynginx inspect <archive>` | Show the manifest. |
| `easynginx verify <archive>` | Re-checksum every file inside. |
| `easynginx restore [<archive>]` | Restore a backup. Interactive picker if no path given. |

Backup options:

| Flag | Default | Effect |
|---|---|---|
| `--no-ssl` | off | Skip `/etc/letsencrypt`. Use for config-only snapshots. |
| `--with-www` | off | Include `/var/www` and `/srv/www` document roots. |
| `--with-php` | off | Include `/etc/php` and PHP-FPM pools. |
| `--include PATH` | — | Add an arbitrary path. Repeatable. |
| `--label NAME` | `manual` | Free-form label baked into the filename. |
| `--note "..."` | empty | Free-form note stored in the manifest. |
| `--output-dir DIR` | `/etc/easynginx/backups` | Where the tarball is written. |

### Certificates

| Command | Description |
|---|---|
| `easynginx cert list` | All Let's Encrypt certs with expiry, color-coded by remaining days. |
| `easynginx cert renew [domain] [--force]` | Renew everything, or just one cert. |
| `easynginx cert revoke <domain> [--reason]` | Revoke and stop renewals. |
| `easynginx cert self-sign <domain> [--apply]` | Issue a self-signed cert (great for local dev). |
| `easynginx cert upload <domain> --cert FILE --key FILE [--apply]` | Bring your own cert. |

### Security & hardening

| Command | Description |
|---|---|
| `easynginx audit` | Scan all sites: missing headers, weak ciphers, expiring certs, world-readable `.env` files. |
| `easynginx tls modern\|intermediate\|legacy` | Set the global TLS profile. |
| `easynginx hsts <d> on/off [--preload]` | HSTS toggle (with the preload-is-permanent warning). |
| `easynginx botblock <d> on/off` | Block AhrefsBot, SemrushBot, GPTBot, ClaudeBot, and friends. |
| `easynginx geoip allow/deny <d> <CC,...>` | Country allow/deny list (requires GeoIP2 nginx module). |
| `easynginx fail2ban install` | Install + configure fail2ban with three nginx jails. |
| `easynginx modsec install` | Install ModSecurity + OWASP CRS. |
| `easynginx waf <d> on/off` | Toggle ModSecurity per site. |

### Observability

| Command | Description |
|---|---|
| `easynginx metrics enable/disable/status` | Toggle the local-only `stub_status` endpoint at `127.0.0.1:9080`. |
| `easynginx stats <d> [--hours N]` | Top IPs, status codes, slowest URLs from the access log. |
| `easynginx healthz <d> on/off [--upstream URL]` | Add a `/healthz` endpoint. |

### Presets

| Command | Description |
|---|---|
| `easynginx php install [--version 8.3]` | Install PHP-FPM with sensible extensions. |
| `easynginx preset wordpress <d> [--root --email]` | WordPress-tuned site (pretty permalinks, security blocks). |
| `easynginx preset laravel <d> --root /opt/app [--email]` | Laravel preset with `public/` root and storage perms. |
| `easynginx preset node <d> --port 3000 [--service-name --service-cmd]` | Reverse proxy + optional systemd unit. |
| `easynginx preset static <d> --kind nextjs\|hugo\|jekyll\|html` | Static hosting with the right rewrite rules. |

### Cluster

| Command | Description |
|---|---|
| `easynginx cluster add <name> <host> [--user --port --key]` | Add a host to inventory at `/etc/easynginx/cluster.yaml`. |
| `easynginx cluster list` | Show the inventory. |
| `easynginx cluster deploy <d> [--to host1,host2\|all]` | Push a site config to multiple hosts via SSH, with per-host validation and rollback. |

### Dashboard

| Command | Description |
|---|---|
| `easynginx dashboard start` | Stdlib-only HTTP server on `127.0.0.1:9088`, token-gated, read-only. |
| `easynginx dashboard stop` | Stop the dashboard. |
| `easynginx dashboard status` | Show running state. |
| `easynginx dashboard token` | Print the access token. |
| `easynginx dashboard enable` | Install a systemd service (survives reboots). |
| `easynginx dashboard disable` | Remove the systemd service. |

### Admin

| Command | Description |
|---|---|
| `easynginx update check` | Check GitHub for a new release (forces a refresh). |
| `easynginx update install [--target REF] [--force]` | Download and install the latest release. |
| `easynginx update rollback` | Restore the previous engine snapshot. |
| `easynginx update snapshots` | List available rollback snapshots. |
| `easynginx self-update` | Alias for `easynginx update install`. |
| `easynginx uninstall [--purge]` | Remove the CLI and engine. `--purge` also deletes `/etc/easynginx`. |
| `easynginx --version` | Print the version. |

---

## ⬆️ Updates

EasyNginx checks for new versions automatically and never overwrites your data when updating.

### How it works

Every command silently reads `/etc/easynginx/version-cache.json`. If the cached "latest" is newer than what you're running, you see a one-line banner:

```
[easynginx] Update available: 0.3.0 → 0.3.1  (run easynginx update to install)
```

The cache refreshes itself in the background at most once per 24 hours, in a detached subprocess, so commands never block waiting on GitHub.

To silence the banner globally, set `EASYNGINX_NO_UPDATE_CHECK=1` in your environment.

### Check now

```bash
sudo easynginx update check
```

Forces an immediate refresh and prints a summary. Add `--json` for machine-readable output (handy for monitoring).

### Install an update

```bash
sudo easynginx update install
```

What this does, in order:

1. Probes GitHub for the latest version.
2. Downloads every engine file into a staging directory (`/tmp/easynginx-update-*`).
3. Runs `py_compile` on each downloaded Python module — aborts if any fails to parse.
4. Snapshots your current engine + config to `/etc/easynginx/backups/updates/engine-before-<version>-<timestamp>.tar.gz`.
5. Atomically replaces each engine file in place with `os.replace` (atomic on POSIX same-filesystem renames).
6. Bumps the `version` field in `/etc/easynginx/config.json`.

> [!IMPORTANT]
> **Updates only touch engine files.** The updater is hard-coded to a list of paths under `/usr/local/bin/easynginx`, `/usr/local/share/easynginx/lib/`, and `/usr/local/share/easynginx/templates/`. Nothing under `/etc/nginx`, `/etc/letsencrypt`, `/etc/easynginx/cluster.yaml`, `/etc/easynginx/auth/`, `/etc/easynginx/backups/`, or any of your data directories can be modified by an update.

> [!NOTE]
> Want to install a specific tag, branch, or sha (e.g. test main before a release)?
> ```bash
> sudo easynginx update install --target main
> sudo easynginx update install --target v0.3.1
> ```

### Roll back

If an update breaks something, you can revert in one command:

```bash
sudo easynginx update rollback
```

This restores the most recent engine snapshot, byte-for-byte. To pick an older snapshot:

```bash
sudo easynginx update snapshots
# then manually restore one:
sudo tar xzf /etc/easynginx/backups/updates/engine-before-0.2.0-...tar.gz \
            -C /usr/local/share/easynginx --strip-components=0
```

### Cutting a release (maintainers)

```bash
scripts/release.sh 0.3.1
git push && git push --tags
```

The script bumps `lib/version.py`, commits, tags `v0.3.1`, and prints push instructions. Once the tag is on GitHub, every existing install will see the update banner within 24 hours (or immediately on the next `easynginx update check`).

---

## 💾 Backup & restore

EasyNginx ships with a snapshot system that lets you move a server, recover from a bad config, or rebuild after a fresh OS install in minutes.

### Backup format

```
easynginx-backup-<host>-<label>-<timestamp>.tar.gz
├── MANIFEST.json     ← path, mode, sha256 of every file captured
└── payload/
    ├── etc/nginx/...
    ├── etc/easynginx/...
    └── etc/letsencrypt/... (optional)
```

A sidecar `.sha256` file is written next to each tarball so you can verify with plain `sha256sum -c easynginx-backup-...tar.gz.sha256`.

### Create

```bash
# Default: archives /etc/nginx, /etc/easynginx, and /etc/letsencrypt
sudo easynginx backup

# With document roots and PHP pools, labelled and noted
sudo easynginx backup \
  --with-www --with-php \
  --label "before-php8-upgrade" \
  --note "All sites green pre-upgrade"
```

### Verify any time

```bash
sudo easynginx verify /etc/easynginx/backups/easynginx-backup-prod-...tar.gz
```

This re-checksums every payload file against the manifest. A single bit-flip is detected.

### Restore — two paths

**A. From a fresh install** (the easiest way after rebuilding a server):

```bash
# Interactive: installer asks "Fresh install or restore?"
sudo bash install.sh

# Non-interactive
sudo EASYNGINX_RESTORE=/root/easynginx-backup-prod-2026-05-28.tar.gz bash install.sh
```

**B. On a running EasyNginx install:**

```bash
# Pick from a list of detected backups
sudo easynginx restore

# Or pass a path directly
sudo easynginx restore /root/easynginx-backup-prod-2026-05-28.tar.gz

# Skip the confirmation prompt (CI-friendly)
sudo easynginx restore /path/to/backup.tar.gz --yes
```

### What restore does, step by step

1. **Inspect** the manifest. Aborts if the archive isn't an EasyNginx backup.
2. **Verify** every file's sha256 against the manifest. Aborts if any mismatch.
3. **Snapshot** the live `/etc/nginx`, `/etc/easynginx`, and `/etc/letsencrypt` to `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz`.
4. **Extract** the payload into a temp directory, validate against tar-traversal attacks, then copy into place preserving mode, owner, and mtime.
5. **Validate** with `nginx -t`. If validation fails, EasyNginx aborts and tells you where the snapshot lives so you can revert manually:
   ```bash
   sudo tar xzf /etc/easynginx/backups/snapshots/pre-restore-2026-05-28-153012.tar.gz -C /
   sudo systemctl reload nginx
   ```
6. **Reload** nginx if validation passes.

### Cross-distro restores

The manifest records the source distro family. Restoring a Debian-style backup (with `sites-available`/`sites-enabled`) onto a RHEL host works — the files land in `/etc/nginx` exactly as they were captured. EasyNginx warns when source and target families differ so you can hand-tune `nginx.conf` includes if needed.

---

## 🔒 Production safety

EasyNginx is designed to never leave nginx in a broken state. Every operation that writes config follows the same pattern:

```
Snapshot → Write → nginx -t → Reload
                       │
                       └─ failure → restore snapshot → re-test → bail with diagnostics
```

| Operation | What's snapshotted | Where it lives |
|---|---|---|
| `easynginx create` overwriting an existing site | Old `<domain>.conf` | `/etc/easynginx/backups/<domain>.conf.bak` |
| `easynginx edit` | Pre-edit config | `/etc/easynginx/backups/<domain>.conf.pre-edit-<unix>` |
| `easynginx restore` | Live `/etc/nginx`, `/etc/easynginx`, `/etc/letsencrypt` | `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz` |
| `easynginx self-update` | Whole `/usr/local/share/easynginx` | `/etc/easynginx/backups/self-update/share-before-<tag>.tar.gz` |
| `easynginx cluster deploy` | Remote site config | `/etc/easynginx/backups/<domain>.cluster-prev` on each host |

If a deployment fails mid-way through a multi-host cluster deploy, the failed host is rolled back automatically while successful hosts keep the new config. You get a per-host summary at the end.

### Safety checks before any change

Every `easynginx create` runs a pre-flight that reports:

- ✅ Domain syntax (RFC 1035-ish + length limits)
- ✅ DNS A/AAAA records actually point at this host
- ✅ Ports 80 and 443 are listening (or free)
- ✅ Backend URLs are TCP-reachable for proxy/websocket modes
- ✅ Duplicate site detection
- ✅ certbot availability before you ask for SSL
- ✅ `nginx -t` validation before any reload

---

## 📁 Where things live

| Path | What's there |
|---|---|
| `/usr/local/bin/easynginx` | The CLI binary (small bash launcher). |
| `/usr/local/share/easynginx/lib/` | Python engine modules. |
| `/usr/local/share/easynginx/templates/` | nginx config templates and HTML pages. |
| `/etc/easynginx/config.json` | Detected distro + paths the engine uses. |
| `/etc/easynginx/backups/` | Per-site backups and pre-restore snapshots. |
| `/etc/easynginx/maintenance/` | Maintenance-mode HTML pages. |
| `/etc/easynginx/auth/` | Per-site basic-auth htpasswd files. |
| `/etc/easynginx/cluster.yaml` | Cluster inventory (mode 0600). |
| `/etc/easynginx/dashboard-token` | Dashboard auth token (mode 0600). |
| `/etc/nginx/easynginx-snippets/` | Shared snippets (TLS profile, bot-block map, etc). |
| `/etc/nginx/sites-available/<domain>.conf` (Debian/Arch) | Site configs EasyNginx writes. |
| `/etc/nginx/conf.d/<domain>.conf` (RHEL/Fedora) | Same, on RHEL-family distros. |
| `/var/log/easynginx/` | EasyNginx logs (dashboard, etc). |

---

## 🏗 Architecture

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

The installer is bash because it has to run before Python is guaranteed. Once Python and the engine are in place, every later operation runs through Python: real data structures, JSON, regex, templating, clean error handling.

| Module | Responsibility |
|---|---|
| `main.py` | argparse entry, dispatches to commands |
| `commands.py` | High-level verbs (create, list, backup, etc.) |
| `cmd_site.py` | info / edit / logs / clone / maintenance |
| `cmd_admin.py` | reload / restart / status / test / self-update / uninstall |
| `cmd_cert.py` | SSL lifecycle (list / renew / revoke / self-sign / upload) |
| `cmd_security.py` | audit / TLS / HSTS / botblock / GeoIP / fail2ban / modsec / waf |
| `cmd_observability.py` | metrics / stats / healthz |
| `cmd_preset.py` | php / wordpress / laravel / node / static |
| `cmd_cluster.py` | Multi-server deploy over SSH |
| `cmd_dashboard.py` + `dashboard_server.py` | Local web UI |
| `backup.py` | Tar+sha256 backup engine |
| `nginx.py` | Site file management with distro layout abstraction |
| `validation.py` | Domain / email / URL / DNS / port / upstream checks |
| `templates.py` | Tiny `{{ var }}` + `{% if %}` renderer (no PyYAML, no Jinja) |
| `certbot.py` | Wrapper over `certbot --nginx` and renew |
| `firewall.py` | ufw / firewalld helpers |
| `helpers.py` | Cross-module utilities (systemctl, log parsing, cert expiry) |
| `ui.py` | Console output and prompts |

See [`docs/architecture.md`](docs/architecture.md) for more.

---

## ❓ FAQ

<details>
<summary><b>Will this break my existing nginx setup?</b></summary>

No. The installer never touches existing files in `/etc/nginx`. EasyNginx only manages files it creates. Your hand-written configs continue to serve traffic unchanged.

If you ask EasyNginx to overwrite a site (`--yes` to the prompt), it backs up the old config first to `/etc/easynginx/backups/<domain>.conf.bak`. Use `easynginx restore` to bring it back.
</details>

<details>
<summary><b>Can I run it on a server that already has Let's Encrypt certs?</b></summary>

Yes. EasyNginx detects existing certs in `/etc/letsencrypt/live/` and won't reissue them. `easynginx cert list` will show them with the same expiry coloring. Renewals continue to work via the existing certbot timer.
</details>

<details>
<summary><b>What if `nginx -t` fails after I create a site?</b></summary>

EasyNginx automatically restores the previous config from its backup, re-enables it, and exits with the failure output. nginx is never reloaded with a broken config.
</details>

<details>
<summary><b>Does it support Cloudflare?</b></summary>

The CLI accepts `--cloudflare` on `easynginx create` to opt in to setting `real_ip_header CF-Connecting-IP`. DNS-01 wildcard certs via Cloudflare DNS are wired into the parser and will be available in a follow-up release. For now, the http-01 challenge works fine through CF in proxied mode.
</details>

<details>
<summary><b>Can I edit configs by hand?</b></summary>

Yes. `easynginx edit <domain>` opens the file in `$EDITOR` and validates on save with rollback. You can also edit files directly with vim/nano — just run `sudo easynginx test` afterwards to confirm the syntax, then `sudo easynginx reload`.
</details>

<details>
<summary><b>How do I migrate to a new server?</b></summary>

```bash
# old server
sudo easynginx backup --with-www --label "migration"
scp /etc/easynginx/backups/easynginx-backup-*.tar.gz user@new-server:

# new server
sudo EASYNGINX_RESTORE=/home/user/easynginx-backup-*.tar.gz bash install.sh
```

Two commands. Done.
</details>

<details>
<summary><b>Is the dashboard secure?</b></summary>

The dashboard binds to `127.0.0.1` only and requires a 256-bit token in either the `X-EasyNginx-Token` header or the `?token=` query string. It's read-only by design — no mutation endpoints — so a leaked token can't trash your nginx config. To expose it externally, proxy it through nginx with your own auth.
</details>

<details>
<summary><b>How do I uninstall?</b></summary>

```bash
sudo easynginx uninstall            # removes CLI + engine, keeps your configs
sudo easynginx uninstall --purge    # also deletes /etc/easynginx and backups
```

nginx itself is left installed and running. Remove it with your distro's package manager if you want a fully clean machine.
</details>

<details>
<summary><b>What Python version is required?</b></summary>

Python 3.8+. The installer pulls the distro's default `python3` package, which is 3.8+ on every supported distro release. EasyNginx uses only the standard library — no pip, no venv, no third-party deps.
</details>

<details>
<summary><b>Does it work on macOS?</b></summary>

The CLI is portable Python and would mostly work, but the installer is Linux-only (it reaches for systemctl, ufw/firewalld, and Linux package managers). A Homebrew tap is on the roadmap.
</details>

---

## 🤝 Contributing

PRs welcome. The project is structured to make new commands cheap to add:

1. Drop a new template in `templates/`.
2. Add a subparser in `lib/main.py`.
3. Add the implementation in `lib/cmd_<area>.py`.
4. Add a test case to `tests/cli_test.py`.

Run the test suite locally:

```bash
python3 tests/smoke_test.py
python3 tests/backup_test.py
python3 tests/cli_test.py
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Made with care by [Akshat Mehta](https://akshatmehta.com).
If EasyNginx saved you time, give the repo a ⭐ on [GitHub](https://github.com/nerkoux/EasyNGINX).

</div>
