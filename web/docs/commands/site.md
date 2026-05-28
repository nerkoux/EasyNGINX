---
id: site
title: Site management
sidebar_position: 2
---

# Site management

Day-to-day commands for creating, inspecting, editing, and managing virtual hosts.

## `create`

Create a new virtual host. Interactive when called with no arguments.

```bash
sudo easynginx create
```

Non-interactive:

```bash
sudo easynginx create \
  --domain api.example.com \
  --type reverse-proxy \
  --upstream http://127.0.0.1:3000 \
  --ssl --email admin@example.com \
  --yes
```

### Flags

| Flag | Effect |
|---|---|
| `--domain DOMAIN` | Site domain (e.g. `api.example.com`). |
| `--type TYPE` | One of: `reverse-proxy`, `static`, `php`, `websocket`, `redirect`, `load-balancer`. |
| `--upstream URL` | Backend URL for proxy/websocket modes. |
| `--upstreams URL,URL,...` | Two or more upstreams for load balancing. |
| `--root PATH` | Document root for static or PHP. |
| `--redirect-to URL` | Target for redirect-only sites. |
| `--alt-names www.x,api.x` | Extra SAN names on the certificate. |
| `--ssl` / `--no-ssl` | Enable or skip Let's Encrypt issuance. |
| `--email YOU@EXAMPLE.COM` | Email for Let's Encrypt registration. |
| `--http2` / `--no-http2` | Toggle HTTP/2 (default on with SSL). |
| `--http3` | Try to enable HTTP/3 (QUIC) where supported. |
| `--gzip` / `--no-gzip` | Toggle gzip compression. |
| `--brotli` | Try Brotli (auto-fallback to gzip if not present). |
| `--security-headers` / `--no-security-headers` | Toggle the bundled security header set. |
| `--rate-limit` | Enable per-IP rate limiting (20 r/s with burst 40). |
| `--basic-auth user:password` | Protect the whole site with basic auth. |
| `--cors off\|open\|list` | Set a CORS preset. |
| `--cors-origins host1,host2` | Allowed origins for `--cors=list`. |
| `--cloudflare` | Trust CF and set `real_ip_header CF-Connecting-IP`. |
| `--www-redirect auto\|to-apex\|to-www\|off` | How to handle www↔apex. |
| `--tls-profile modern\|intermediate\|legacy` | Per-site TLS profile. |
| `--hsts` / `--hsts-preload` | HSTS toggles. Preload is permanent. |
| `--bot-block` | Block known bad bots from creation time. |
| `--custom-errors` | Drop in branded 404/500 pages. |
| `--staging` | Use Let's Encrypt staging server (testing). |
| `--dns-provider`, `--dns-credentials` | DNS-01 wildcard via Cloudflare/Route53/DigitalOcean. |
| `-y`, `--yes` | Skip confirmation prompts. |

### Pre-flight checks

Before any file is written, EasyNginx confirms:

- Domain syntax and length.
- DNS A/AAAA records resolve to this host (warns if not).
- Ports 80/443 are listening (or free if nginx is offline).
- Backend URLs are TCP-reachable.
- The site doesn't already exist (or you confirmed overwriting).
- certbot is installed if you asked for SSL.

---

## `list`

Show every managed site.

```bash
sudo easynginx list
```

Each entry shows whether it's enabled and whether SSL is configured.

---

## `info`

Detailed inspection of one site.

```bash
sudo easynginx info api.example.com
```

Reports: type, listens, `proxy_pass`, SSL cert path and expiry days (color-coded), access/error log paths, and nginx service state.

---

## `edit`

Open the site config in your `$EDITOR`. Validates on save.

```bash
sudo easynginx edit api.example.com
sudo easynginx edit api.example.com --editor vim
```

What happens:

1. A snapshot is taken to `/etc/easynginx/backups/<domain>.conf.pre-edit-<timestamp>`.
2. `$EDITOR` opens the config.
3. On save, `nginx -t` runs.
4. **If validation fails**, the snapshot is restored and you're told why.
5. If validation passes, nginx is reloaded.

You're never left with a broken nginx config from a bad edit.

---

## `logs`

Tail access or error logs for a site.

```bash
sudo easynginx logs api.example.com               # access log, last 200 + follow
sudo easynginx logs api.example.com --errors      # error log
sudo easynginx logs api.example.com --both        # both
sudo easynginx logs api.example.com -n 1000       # last 1000 lines first
```

Honors per-site `access_log` / `error_log` overrides if your config sets them, falling back to nginx's global `/var/log/nginx/access.log` and `/var/log/nginx/error.log`.

---

## `enable` / `disable`

Toggle a site on or off without deleting it.

```bash
sudo easynginx disable api.example.com   # site stops serving
sudo easynginx enable  api.example.com   # site comes back
```

On Debian/Arch, this manages the symlink in `sites-enabled/`. On RHEL/Fedora, it adds or removes a `.disabled` suffix in `conf.d/`.

---

## `remove`

Delete a site config and (by default) its certificate.

```bash
sudo easynginx remove api.example.com
sudo easynginx remove api.example.com --keep-cert   # keep the LE cert
sudo easynginx remove api.example.com --yes         # skip confirmation
```

---

## `clone`

Duplicate a working site under a new domain — useful for staging.

```bash
sudo easynginx clone api.example.com api-staging.example.com
```

The clone:

- Copies the source config.
- Replaces `server_name`.
- Strips `ssl_certificate*` and `listen 443` directives so the cloned site is HTTP-only until you issue a fresh cert.
- Validates with `nginx -t` and reloads.

To add SSL to the clone:

```bash
sudo easynginx cert renew api-staging.example.com   # re-issue with certbot
```

---

## `maintenance`

Drop a site into 503 mode with a custom HTML page.

```bash
sudo easynginx maintenance api.example.com on
sudo easynginx maintenance api.example.com on --page /tmp/custom-503.html
sudo easynginx maintenance api.example.com off
```

The bundled page lives at `/etc/easynginx/maintenance/default.html`. When `on`, every request returns 503 with that page (the ACME `/.well-known/acme-challenge/` location is left untouched so renewals still work).
