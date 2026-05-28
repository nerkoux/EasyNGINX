---
id: nginx-control
title: nginx control
sidebar_position: 3
---

# nginx control

Friendly wrappers over `systemctl` and `nginx -t`.

## `reload`

Zero-downtime reload.

```bash
sudo easynginx reload
```

Equivalent to `sudo systemctl reload nginx`. Workers finish their current requests before being replaced — no dropped connections.

## `restart`

Full restart.

```bash
sudo easynginx restart
```

Use this when:

- You changed kernel-level limits (file descriptors, etc).
- You added a new dynamic module.
- A `reload` isn't picking up a config change (very rare).

## `status`

```bash
sudo easynginx status
```

Prints the systemctl status block: active state, recent log lines, uptime, master PID.

## `test`

```bash
sudo easynginx test
```

Equivalent to `nginx -t`. Runs the full config syntax check and reports any errors. Always passes before any EasyNginx reload, but useful to run by hand after editing files outside of `easynginx edit`.

## `doctor`

```bash
sudo easynginx doctor
```

A one-shot diagnostic dump:

- Detected distro and package manager.
- Configured firewall tool.
- Engine and template paths.
- `sites-available` / `sites-enabled` paths.
- Whether nginx and certbot are on `$PATH`.
- Result of `nginx -t`.

Run this when you file a bug — paste the output into the issue.
