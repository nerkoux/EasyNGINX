---
id: admin
title: Admin
sidebar_position: 12
---

# Admin

## `--version`

```bash
easynginx --version
```

Prints the installed EasyNginx version.

## `uninstall`

```bash
sudo easynginx uninstall            # removes CLI + engine, keeps configs
sudo easynginx uninstall --purge    # also deletes /etc/easynginx and backups
sudo easynginx uninstall --yes      # skip confirmation
```

What's removed:

- `/usr/local/bin/easynginx`
- `/usr/local/share/easynginx/`
- `/etc/easynginx/` and `/var/log/easynginx/` *(only with `--purge`)*

What's preserved (always):

- nginx itself.
- `/etc/nginx/` — your sites continue to serve.
- `/etc/letsencrypt/` — your certs.
- Without `--purge`: `/etc/easynginx/backups/` so you can re-install and restore.

To remove nginx itself afterwards, use your distro's package manager.
