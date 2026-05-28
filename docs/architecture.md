# EasyNginx architecture

```
  ┌──────────────┐    pipes JSON-ish state     ┌────────────────────────┐
  │  install.sh  │ ──────────────────────────▶ │  /etc/easynginx/...    │
  │  (bash)      │                             │  config.json, backups  │
  └──────┬───────┘                             └────────────────────────┘
         │ installs
         ▼
  ┌──────────────┐                             ┌────────────────────────┐
  │ create-host  │   exec → python3 main.py    │ /usr/local/share/      │
  │ (bash shim)  │ ──────────────────────────▶ │   easynginx/lib/*.py   │
  └──────────────┘                             │   easynginx/templates/ │
                                               └────────────────────────┘
```

## Why two languages

`install.sh` runs on machines where Python may not yet exist, so it stays in
plain bash with POSIX-leaning idioms. Once the installer drops Python and the
EasyNginx engine in place, every later operation runs through Python where
we get real data structures, JSON, regex, templating and clean error
handling.

## Module layout

| Module             | Responsibility                                       |
|--------------------|------------------------------------------------------|
| `main.py`          | argparse entry point, dispatches to commands         |
| `commands.py`      | High-level verbs (create, list, enable, disable, …)  |
| `config.py`        | Loads `/etc/easynginx/config.json`, distro paths     |
| `validation.py`    | Domain/email/URL checks, DNS, port, upstream probes  |
| `templates.py`     | Tiny `{{var}}` + `{% if %}` renderer                 |
| `nginx.py`         | Site files: write/enable/disable/remove/reload       |
| `certbot.py`       | Wrapper over `certbot --nginx` + renew               |
| `firewall.py`      | ufw / firewalld helpers                              |
| `ui.py`            | Console output and prompts                           |

## Distro abstraction

`config.py` translates the `distro_family` recorded by the installer into the
right paths:

- **debian / arch**: `/etc/nginx/sites-available` + symlinks in `sites-enabled`
- **rhel / fedora / alpine**: single `/etc/nginx/conf.d` (disabled sites get a
  `.disabled` suffix instead of a symlink toggle)

`install.sh` keeps the table of package names and firewall tools, so adding a
new distro is a matter of extending one `case` block in bash and one mapping
in `_detect_nginx_paths`.

## Rollback story

Every site write goes through `nginx.write_site()` which copies the prior
`.conf` to `/etc/easynginx/backups/<domain>.conf.bak` first. If `nginx -t`
fails after an edit:

1. The new config is removed.
2. The backup (if any) is restored and the symlink re-created.
3. `nginx` is never reloaded with a broken config.

If certbot fails the site stays live on plain HTTP — the user sees the
certbot error and can re-run after fixing DNS without losing their config.

## Adding a new site type

1. Drop a new template in `templates/`.
2. Add an entry to `SITE_TYPES` in `commands.py`.
3. Add a branch to `_gather_inputs` for the new fields it needs.
4. Map the type to the template filename in `_render`.

That's it. No further bash changes are required.
