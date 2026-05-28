---
id: wildcard-cert
title: Wildcard certificates (DNS-01)
---

# Wildcard certificates

Wildcard certificates (`*.example.com`) require the DNS-01 challenge — Let's Encrypt verifies you control the domain by reading a DNS TXT record. EasyNginx wires this through the `--dns-provider` and `--dns-credentials` flags on `create`.

:::note Status
Plumbing is in place; provider-specific wiring lands in a follow-up release. Use `certbot` directly for now if you need a wildcard immediately. The flag interface below is what will land.
:::

## What you'll need

- An API token from your DNS host with permission to create TXT records on the zone.
- The matching certbot DNS plugin installed.
- A credentials file with the right format for that plugin.

## Cloudflare

```bash
# /root/cloudflare.ini  (mode 0600)
dns_cloudflare_api_token = your-token-here
```

```bash
sudo chmod 600 /root/cloudflare.ini

sudo apt install python3-certbot-dns-cloudflare    # Debian/Ubuntu
sudo dnf install python3-certbot-dns-cloudflare    # Fedora/RHEL

sudo easynginx create \
  --domain *.example.com \
  --alt-names example.com \
  --type reverse-proxy \
  --upstream http://127.0.0.1:3000 \
  --ssl --email admin@example.com \
  --dns-provider cloudflare \
  --dns-credentials /root/cloudflare.ini
```

## Route53

```bash
# /root/aws.ini  (mode 0600)
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

```bash
sudo apt install python3-certbot-dns-route53
sudo easynginx create --dns-provider route53 --dns-credentials /root/aws.ini ...
```

## DigitalOcean

```bash
# /root/digitalocean.ini  (mode 0600)
dns_digitalocean_token = your-token-here
```

```bash
sudo apt install python3-certbot-dns-digitalocean
sudo easynginx create --dns-provider digitalocean --dns-credentials /root/digitalocean.ini ...
```

## Why DNS-01 is different

The default HTTP-01 challenge requires Let's Encrypt to hit `http://yourdomain/.well-known/acme-challenge/...`. That doesn't work for wildcards because there's no specific subdomain to verify against.

DNS-01 sidesteps that by asking you to put a TXT record on the zone. EasyNginx (via certbot) creates the TXT record using your DNS provider's API, waits for propagation, and lets Let's Encrypt verify.

The whole flow is automatic — you just supply the credentials file once.

## Renewal

DNS-01 renewals work without any changes — certbot stores the credential reference and re-uses it on renewal. The standard certbot timer covers it; `easynginx cert renew` triggers it manually.
