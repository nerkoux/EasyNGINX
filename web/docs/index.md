---
id: index
title: Welcome to EasyNginx
slug: /
sidebar_position: 1
---

# Welcome to EasyNginx

EasyNginx is a single, friendly CLI (`easynginx`) that turns nginx into something a beginner can actually use without breaking their server. It walks you through creating virtual hosts, issues Let's Encrypt SSL, opens the firewall, hardens the config, takes backups, and rolls back automatically when anything goes wrong.

It works on **fresh servers** (one install command and you're live) and on **existing production servers** (it preserves what's already there, lets you opt in to overrides, and snapshots before every change so you can always undo).

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
sudo easynginx create
```

## What you can do

- Create reverse proxies, static sites, PHP, WebSocket apps, redirects, and load balancers.
- Issue and renew Let's Encrypt certificates, or bring your own cert.
- Audit security headers, weak ciphers, expiring certs, and world-readable `.env` files.
- Snapshot the whole nginx + EasyNginx state and restore on any server.
- Push the same site to many servers in one command, with per-host rollback.
- Run a local read-only web dashboard.
- Update with one command — engine files only, never your data.

## Where to next

- **New to EasyNginx?** Start at [Install](getting-started/install.md).
- **Already running nginx in production?** Read [Existing-server install](getting-started/existing-server.md) first.
- **Looking for a specific command?** Jump to the [Command reference](commands/overview.md).
- **Worried about safety?** Read [Production safety](operations/safety.md) and [Cautions & warnings](operations/cautions.md).

## Author

Built by [Akshat Mehta](https://akshatmehta.com) ([@nerkoux](https://github.com/nerkoux)).

Source: [github.com/nerkoux/EasyNGINX](https://github.com/nerkoux/EasyNGINX) · License: [MIT](https://github.com/nerkoux/EasyNGINX/blob/main/LICENSE)
