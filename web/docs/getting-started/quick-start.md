---
id: quick-start
title: Quick start
sidebar_position: 2
---

# Quick start

Five minutes from a blank server to a live HTTPS site.

## 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
```

## 2. Point DNS at this server

EasyNginx will issue Let's Encrypt SSL during create, which requires the domain's A/AAAA record to resolve to your server. Add the record at your DNS provider before running the next step.

The installer's pre-flight checks will warn you if DNS doesn't match.

## 3. Create a site

Interactive:

```bash
sudo easynginx create
```

You'll be asked for:

- **Domain** — `api.example.com`
- **Site type** — reverse proxy / static / PHP / websocket / redirect / load balancer
- **Backend / root** — depending on type
- **SSL** — yes/no plus your email
- **Optional extras** — rate limit, basic auth, etc.

Non-interactive equivalent:

```bash
sudo easynginx create \
  --domain api.example.com \
  --type reverse-proxy \
  --upstream http://127.0.0.1:3000 \
  --ssl --email admin@example.com \
  --yes
```

## 4. Visit your site

```
https://api.example.com/
```

## 5. List, inspect, manage

```bash
sudo easynginx list                       # see all managed sites
sudo easynginx info api.example.com       # config, SSL, expiry, log paths
sudo easynginx logs api.example.com -f    # tail live access log
sudo easynginx audit                      # report security gaps
```

## What just happened

EasyNginx:

1. Validated the domain syntax.
2. Checked the DNS A/AAAA record actually points at this host.
3. Verified ports 80 and 443 are listening.
4. Confirmed your backend is reachable.
5. Rendered an nginx config from the right template.
6. Backed up any prior config.
7. Ran `nginx -t` before reloading.
8. Issued a Let's Encrypt certificate via certbot.
9. Reloaded nginx.

If any step had failed, EasyNginx would have rolled back automatically and told you what went wrong. nginx is never reloaded with a broken config.

Next: [Existing-server install](existing-server.md) if you're not on a brand-new box.
