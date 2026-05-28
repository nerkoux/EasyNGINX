---
id: cloudflare
title: Cloudflare
---

# Cloudflare

EasyNginx works fine behind Cloudflare. The main wrinkle is **real client IPs**: by default nginx logs Cloudflare's edge IPs as the client. The `--cloudflare` flag fixes this.

## Pass `--cloudflare` on create

```bash
sudo easynginx create \
  --domain api.example.com \
  --type reverse-proxy --upstream http://127.0.0.1:3000 \
  --ssl --email admin@example.com \
  --cloudflare
```

What this does:

- Sets `real_ip_header CF-Connecting-IP` so logs and rate limiting see the real client IP.
- Adds `set_real_ip_from <cf-range>` lines for Cloudflare's published IP ranges.

The CF IP list is updated periodically. Run `easynginx cert renew --force` after a Cloudflare IP range change to pick up the latest list (this is rare; CF only adds ranges, never removes them).

## Issuing SSL behind CF

Two options:

### A. Cloudflare proxy off during issuance

Set the DNS record to "DNS only" (grey cloud) in Cloudflare. Run `easynginx create` with `--ssl`. Once the cert is issued, flip back to "Proxied" (orange cloud).

### B. Cloudflare proxy on always (DNS-01 challenge)

Use a [wildcard certificate via DNS-01](wildcard-cert.md). The challenge happens in DNS so Cloudflare's HTTP proxy doesn't matter.

## SSL/TLS mode

In your Cloudflare dashboard, set SSL/TLS → Overview to **Full (strict)**. This requires a valid cert on your origin — exactly what EasyNginx provides via Let's Encrypt.

"Full" (without strict) accepts self-signed origin certs. "Flexible" only encrypts the visitor↔CF leg and is broken — never use it.

## Origin pull authentication

For paranoid setups, restrict the origin to only accept connections from Cloudflare:

1. Create an Origin Pull cert in Cloudflare and download the `.pem`.
2. Configure nginx with `ssl_client_certificate` and `ssl_verify_client on`.

This is outside the EasyNginx CLI today — edit the site by hand and EasyNginx will validate and reload on save:

```bash
sudo easynginx edit api.example.com
```

## Real-IP gotchas

If you use rate limiting (`--rate-limit`), make sure `--cloudflare` was passed too. Otherwise rate limiting will see all traffic as coming from CF's edge IPs and either rate-limit everyone or no one.

## Health checks

`--upstream` and `easynginx healthz <domain> --upstream <url>` work transparently — your origin sees the real Cloudflare-forwarded request.
