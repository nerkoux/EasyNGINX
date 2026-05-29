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

## 30-second tour

```bash
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

## Why EasyNginx (and why not X?)

The closest neighbours each have a place. Here's where each one beats EasyNginx and where EasyNginx wins.

| Tool | Strength | Weakness for the EasyNginx use case | EasyNginx vs. it |
|---|---|---|---|
| **[Nginx Proxy Manager](https://nginxproxymanager.com/)** | Slick web UI, Docker-first | Runs as its own appliance; can't audit or back up arbitrary nginx configs | EasyNginx manages the nginx already on the box, no extra container. |
| **[Caddy](https://caddyserver.com/)** | Automatic HTTPS, simple Caddyfile | Different web server entirely; switching means re-learning every plugin | Stock nginx, all existing snippets and modules still work. |
| **[Traefik](https://traefik.io/)** | Service discovery for Docker / k8s | Overkill for a single VPS with a few sites | A CLI, no daemons added, no Docker required. |
| **[Webmin / Virtualmin](https://www.virtualmin.com/)** | Whole-server admin UI | Heavy Perl install with its own auth and layout | Single Python CLI, no GUI, no daemon. |
| **[certbot --nginx](https://certbot.eff.org/)** | The industry-standard ACME client | Only handles certificates | EasyNginx wraps certbot and adds creation, audit, backup, restore, cluster. |
| **Ansible / Salt / Puppet** | Declarative IaC | A whole stack to learn for one nginx box | `sudo easynginx create` — no inventory, no playbook. |

If you already love one of those, keep using it. EasyNginx is for people who want stock nginx without typing the same five commands on every server.

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
