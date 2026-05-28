---
id: dashboard
title: Dashboard
sidebar_position: 10
---

# Dashboard

Stdlib-only HTTP server bound to `127.0.0.1:9088`, token-gated, **read-only by design**.

There is no remote-write API — a leaked token can let someone see your site list and cert expiry, but cannot trash your nginx config.

## Start

```bash
sudo easynginx dashboard start
```

Prints the access token. Visit:

```
http://127.0.0.1:9088/
```

Paste the token when prompted. It's stored in your browser's `localStorage`.

To expose it externally, proxy through nginx with your own auth — never bind it to a public interface directly.

## Lifecycle

```bash
sudo easynginx dashboard status      # is it running?
sudo easynginx dashboard stop        # stop it
sudo easynginx dashboard token       # print the token (e.g. for env files)
```

## Persistent install

Use systemd to keep the dashboard running across reboots:

```bash
sudo easynginx dashboard enable      # creates a systemd service + auto-starts
sudo easynginx dashboard disable     # removes the service
```

The service unit lives at `/etc/systemd/system/easynginx-dashboard.service` with the token loaded from `/etc/easynginx/dashboard.env` (mode `0600`).

## What you see

- **Overview** — hostname, distro, nginx running state, site count, cert count.
- **Sites** — every managed site with enabled/disabled badge.
- **Certificates** — every Let's Encrypt cert with color-coded days remaining.

The page auto-fetches three JSON endpoints (`/api/overview`, `/api/sites`, `/api/certs`) and renders them with a tiny dark-mode dashboard.

## Auth

Either header:

```
X-EasyNginx-Token: <your-token>
```

…or query string:

```
http://127.0.0.1:9088/api/overview?token=<your-token>
```

Both work for `curl`, monitoring, etc.

## Token rotation

Rotate by deleting `/etc/easynginx/dashboard-token` and restarting:

```bash
sudo rm /etc/easynginx/dashboard-token
sudo easynginx dashboard stop
sudo easynginx dashboard start
sudo easynginx dashboard token
```
