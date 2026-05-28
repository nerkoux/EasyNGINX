---
id: multi-server
title: Multi-server deployments
---

# Multi-server deployments

Push the same site to many servers in one command.

## Setup

Install EasyNginx on every server you want to manage:

```bash
# on each host
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
```

On your **control machine** (your laptop, or a bastion), set up SSH keys to each host with passwordless sudo. EasyNginx uses standard `ssh`/`scp`.

## Build the inventory

```bash
sudo easynginx cluster add prod-1 192.0.2.10  --user root --key /root/.ssh/id_ed25519
sudo easynginx cluster add prod-2 192.0.2.11  --user root --key /root/.ssh/id_ed25519
sudo easynginx cluster add prod-3 192.0.2.12  --user root --key /root/.ssh/id_ed25519
```

The inventory lives at `/etc/easynginx/cluster.yaml` (mode `0600`).

## Author the site locally

Create the site on the control machine (or any one host) and verify it's working:

```bash
sudo easynginx create --domain api.example.com \
  --type reverse-proxy --upstream http://127.0.0.1:3000 \
  --no-ssl
```

Skip SSL on the source — each host issues its own cert.

## Deploy

```bash
sudo easynginx cluster deploy api.example.com --to prod-1,prod-2,prod-3
sudo easynginx cluster deploy api.example.com --to all
```

For each target host:

1. Snapshot the existing `<domain>.conf` to `/etc/easynginx/backups/<domain>.cluster-prev`.
2. SCP the new config.
3. Move it into place, run `nginx -t`, reload nginx.
4. **If anything fails**, roll back this host. Other hosts are unaffected.

You get a per-host pass/fail summary at the end:

```
[easynginx] Deploying api.example.com to 3 host(s)
[easynginx] -> prod-1 (192.0.2.10)
[ ok  ]   prod-1 deployed.
[easynginx] -> prod-2 (192.0.2.11)
[ ok  ]   prod-2 deployed.
[easynginx] -> prod-3 (192.0.2.12)
[err ]   remote deploy failed; rolling back:
       nginx: [emerg] ...

EasyNginx Summary
2/3 hosts succeeded.
```

Successful hosts keep the new config. Failed hosts revert to the previous one. Decide whether to retry or investigate.

## Issue certs after deploy

Each host issues its own cert via certbot:

```bash
ssh prod-1 sudo easynginx cert renew api.example.com --force
ssh prod-2 sudo easynginx cert renew api.example.com --force
ssh prod-3 sudo easynginx cert renew api.example.com --force
```

Or use a [wildcard cert via DNS-01](wildcard-cert.md) and ship the cert files via [`easynginx cert upload`](../commands/cert.md).

## Limitations today

- Configs ship verbatim. There's no per-host overrides yet (e.g. different upstreams per host).
- Failure isolation is per-host, not transactional across the whole cluster.
- TLS issuance still happens per-host.

For more control, drive `cluster deploy` from your CI runner so you can interleave database migrations, smoke tests, and deploys.
