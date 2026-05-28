---
id: existing-server
title: Installing on an existing server
sidebar_position: 3
---

# Installing on an existing server

You can run EasyNginx on a server that already has nginx serving production traffic. Your existing configs are preserved.

:::important Existing nginx configs are preserved
The installer never modifies anything in `/etc/nginx` on a fresh install. Your current sites continue to serve. EasyNginx only manages files it creates (under `sites-available` or `conf.d`) plus the snippets it writes into `/etc/nginx/easynginx-snippets/`.
:::

## What's safe

- Your existing `nginx.conf`.
- Your existing site files in `sites-available`, `sites-enabled`, or `conf.d`.
- Existing Let's Encrypt certificates in `/etc/letsencrypt/`.
- Existing certbot timers and renewal hooks.
- Custom directives, snippets, and includes you added by hand.

## What gets added

- The `easynginx` binary in `/usr/local/bin`.
- The engine in `/usr/local/share/easynginx/`.
- A small JSON state file at `/etc/easynginx/config.json`.
- Empty directories for backups, snapshots, auth files, and maintenance pages.
- An optional `include` line in `nginx.conf` if you opt into a global TLS profile or the bot blocker.

## Importing existing sites under management

EasyNginx considers a site "managed" if there's a config file with the same domain name. To bring an existing site under management without changing its content, just create it with the same domain — EasyNginx detects the duplicate and asks before overwriting:

```bash
sudo easynginx create --domain example.com
```

```
A config for example.com already exists. Overwrite? [y/N]
```

Answer **N** and EasyNginx exits without touching anything. Useful when you only want `easynginx info`, `audit`, `logs`, and `backup` to know about the site.

## Deliberately overriding an existing site

```bash
sudo easynginx create --domain example.com --yes
```

The previous config is backed up to `/etc/easynginx/backups/example.com.conf.bak` before being replaced. Use [`easynginx restore`](../commands/backup.md) if you change your mind.

## Running alongside other tools

EasyNginx plays nicely with:

- **certbot** — both can renew the same certs. EasyNginx uses certbot under the hood.
- **fail2ban** — `easynginx fail2ban install` configures jails. Existing jails are untouched.
- **Cloudflare** — pass `--cloudflare` on `create` to set `real_ip_header CF-Connecting-IP`.
- **Container runtimes (Docker, Podman)** — point a reverse proxy at `http://127.0.0.1:<port>` like any other backend.

## Take a backup before your first change

Strongly recommended on any production box:

```bash
sudo easynginx backup --label "before-easynginx-changes" --note "Pre-change baseline"
```

If anything goes sideways, [`easynginx restore`](../commands/backup.md) brings you back to this exact state.

## Removing EasyNginx

```bash
sudo easynginx uninstall          # leaves your configs and certs alone
sudo easynginx uninstall --purge  # also wipes /etc/easynginx and backups
```

Your hand-written nginx configs and certbot setup remain untouched either way.
