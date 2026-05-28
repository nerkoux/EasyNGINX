---
id: cluster
title: Cluster
sidebar_position: 9
---

# Cluster

Push the same site config to multiple servers in one command, with per-host validation and automatic rollback on failure.

## `cluster add`

Add a host to the inventory at `/etc/easynginx/cluster.yaml` (mode `0600`).

```bash
sudo easynginx cluster add prod-1 192.0.2.10 --user root --port 22 --key /root/.ssh/id_ed25519
sudo easynginx cluster add prod-2 prod2.example.com --user deploy
```

Inventory format (managed by EasyNginx):

```yaml
- name: "prod-1"
  host: "192.0.2.10"
  user: "root"
  port: "22"
  key:  "/root/.ssh/id_ed25519"
- name: "prod-2"
  host: "prod2.example.com"
  user: "deploy"
  port: "22"
```

## `cluster list`

Show the inventory.

```bash
sudo easynginx cluster list
```

## `cluster deploy`

Push a site to one or more hosts.

```bash
sudo easynginx cluster deploy api.example.com --to prod-1,prod-2
sudo easynginx cluster deploy api.example.com --to all
sudo easynginx cluster deploy api.example.com               # all hosts
```

For each target, EasyNginx:

1. Snapshots the existing config to `/etc/easynginx/backups/<domain>.cluster-prev` on the remote.
2. SCPs the new config to a tempfile.
3. SSHes in, moves the tempfile into place, runs `nginx -t`, reloads nginx.
4. **If anything fails on a host**, rolls that host back to its snapshot. Other hosts continue.

You get a per-host pass/fail summary at the end. Successful hosts keep the new config; failed hosts stay on the previous one. You decide whether to retry or investigate.

## Requirements

- `ssh` and `scp` on your control machine.
- Each remote host has EasyNginx installed and the user has passwordless sudo.
- Each remote host's site directories already exist (e.g. `sites-available` if you're on Debian).

## Limitations (for now)

- The local site's full config is shipped as-is. There's no per-host overrides yet.
- TLS certs are not pushed — EasyNginx assumes each host issues its own. Use DNS challenges with shared credentials, or run `easynginx cert renew` on each host after deploy.
