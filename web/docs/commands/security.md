---
id: security
title: Security & hardening
sidebar_position: 6
---

# Security & hardening

EasyNginx ships with the security knobs most beginners would otherwise skip: an audit, TLS profiles, HSTS, a bot blocker, GeoIP allow/deny, fail2ban, and ModSecurity.

## `audit`

```bash
sudo easynginx audit
```

Scans every managed site and reports:

- Missing `X-Frame-Options` header.
- Missing `X-Content-Type-Options` header.
- Missing HSTS on SSL-enabled sites.
- Weak protocols (TLSv1.0, TLSv1.1) in config.
- Certificates expiring in under 14 days.
- World-readable `.env` files in document roots.

A green run means nothing critical is wrong. A yellow or red run lists every issue with the exact site and command to fix it.

## `tls`

Set the global TLS profile by writing a snippet to `/etc/nginx/easynginx-snippets/tls.conf` and including it in `nginx.conf`.

```bash
sudo easynginx tls modern         # TLS 1.3 only
sudo easynginx tls intermediate   # default — TLS 1.2 + 1.3, modern ciphers
sudo easynginx tls legacy         # TLS 1.0+ if you must support old clients
```

The profiles match Mozilla's TLS guidelines. Switching is reversible — just call the command again with a different profile.

## `hsts`

Toggle HTTP Strict Transport Security per site.

```bash
sudo easynginx hsts api.example.com on
sudo easynginx hsts api.example.com on --preload    # one-year, preload
sudo easynginx hsts api.example.com off
```

:::caution HSTS preload is permanent
Once your domain is added to the HSTS preload list shipped with browsers, removing it takes weeks to months. Only enable `--preload` when **every** subdomain serves HTTPS, including ones you might add later.
:::

## `botblock`

Block known scraping bots (AhrefsBot, SemrushBot, GPTBot, ClaudeBot, MJ12bot, DotBot, BLEXBot, PetalBot, and friends).

```bash
sudo easynginx botblock api.example.com on
sudo easynginx botblock api.example.com off
```

EasyNginx writes a `map`-based blocklist to `/etc/nginx/easynginx-snippets/bad-bots.conf` once and includes it from `nginx.conf`. The per-site toggle just adds or removes the `if ($easynginx_bad_bot) { return 403; }` line in the site's `server` block.

## `geoip`

Country allow/deny lists. Requires the GeoIP2 nginx module.

```bash
sudo easynginx geoip allow api.example.com US,CA,GB    # US/Canada/UK only
sudo easynginx geoip deny  api.example.com RU,KP       # block Russia/N.Korea
sudo easynginx geoip off   api.example.com             # remove the rule
```

If the GeoIP2 module isn't installed, EasyNginx warns and refuses to write a config that would fail `nginx -t`.

## `fail2ban`

Install fail2ban and configure jails for nginx auth, bad-request, and bot-search rules.

```bash
sudo easynginx fail2ban install     # install + configure
sudo easynginx fail2ban status      # show jail status
```

Three jails are added at `/etc/fail2ban/jail.d/easynginx.conf`:

- **nginx-http-auth** — bans on repeated 401s.
- **nginx-bad-request** — bans on repeated 400s.
- **nginx-botsearch** — bans on bot-flavored URLs.

Existing jails are left untouched.

## `modsec`

Install ModSecurity and the OWASP Core Rule Set.

```bash
sudo easynginx modsec install
```

Then enable per site:

```bash
sudo easynginx waf api.example.com on
sudo easynginx waf api.example.com off
```

EasyNginx writes `/etc/nginx/modsec/main.conf` once with sane defaults. Per-site toggles are local to that site's `server` block. Some distros don't yet ship a ModSecurity nginx module; in that case `modsec install` warns and asks you to install it manually.
