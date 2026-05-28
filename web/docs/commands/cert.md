---
id: cert
title: Certificates
sidebar_position: 5
---

# Certificates

SSL lifecycle commands. Let's Encrypt by default, with self-signed and bring-your-own paths for dev or air-gapped scenarios.

## `cert list`

```bash
sudo easynginx cert list
```

All Let's Encrypt certs with expiry, color-coded by remaining days:

- 🟢 Green — more than 30 days
- 🟡 Yellow — 14 to 30 days
- 🔴 Red — under 14 days, or expired

## `cert renew`

```bash
sudo easynginx cert renew                     # renew everything that's due
sudo easynginx cert renew api.example.com     # one specific cert
sudo easynginx cert renew --force             # force-renew even if not due
```

Equivalent to `certbot renew` plus `nginx reload`. Safe to call from cron; certbot is also installing its own timer.

`easynginx renew` (no `cert` prefix) is a shortcut for `cert renew`.

## `cert revoke`

```bash
sudo easynginx cert revoke api.example.com
sudo easynginx cert revoke api.example.com --reason keycompromise
sudo easynginx cert revoke api.example.com --yes
```

:::caution Irreversible
A revoked certificate cannot be un-revoked. You can issue a new one immediately, but any client that pinned the old cert will break.
:::

## `cert self-sign`

Issue a self-signed cert (great for local dev).

```bash
sudo easynginx cert self-sign dev.local --days 365 --apply
```

`--apply` wires the new cert into the existing site config. Without `--apply`, EasyNginx just produces the cert files at `/etc/easynginx/certs/<domain>/`.

Browsers will warn about the certificate authority, which is the point — self-signed means there is no trusted CA.

## `cert upload`

Bring your own cert (e.g. from a paid CA, an internal PKI, or an existing wildcard).

```bash
sudo easynginx cert upload api.example.com \
  --cert /path/to/fullchain.pem \
  --key  /path/to/privkey.pem \
  --apply
```

EasyNginx copies the files into `/etc/easynginx/certs/api.example.com/` with `0600` on the key, then (with `--apply`) updates the site config to use them.
