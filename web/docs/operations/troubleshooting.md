---
id: troubleshooting
title: Troubleshooting
sidebar_position: 5
---

# Troubleshooting

Common problems and how to fix them.

## `easynginx: command not found`

The CLI didn't end up on `$PATH`. Check the installer log and ensure `/usr/local/bin` is in your `$PATH`:

```bash
ls -la /usr/local/bin/easynginx
echo $PATH
```

Re-run the installer if the binary is missing.

## `nginx -t` fails after I edited a file

If you edited via `easynginx edit`, the rollback was automatic — just check the error message and try again.

If you edited a file by hand outside EasyNginx and saved a broken config:

```bash
sudo nginx -t                       # see the error
sudo easynginx restore              # full restore from your last backup
```

Or for a single site, find its pre-edit snapshot:

```bash
ls /etc/easynginx/backups/<domain>.conf.pre-edit-*
sudo cp /etc/easynginx/backups/<domain>.conf.pre-edit-<unix> /etc/nginx/sites-available/<domain>.conf
sudo nginx -t && sudo systemctl reload nginx
```

## SSL issuance failed

Common causes:

1. **DNS doesn't resolve to this host yet.** Check with `dig +short example.com`. Wait for propagation, then:
   ```bash
   sudo easynginx cert renew example.com --force
   ```

2. **Port 80 is blocked.** Let's Encrypt verifies via http-01 on port 80. Confirm:
   ```bash
   sudo ss -tlnp | grep ':80'      # should show nginx
   curl -I http://example.com/      # should hit your server
   ```

3. **Rate-limited by Let's Encrypt.** If you've issued the same cert many times in a short window, use staging while debugging:
   ```bash
   sudo easynginx create --staging ...
   ```

4. **Cloudflare proxy enabled.** Either disable proxy temporarily during issuance, or use a [DNS-01 wildcard](../guides/wildcard-cert.md).

## Update check is failing

```bash
sudo easynginx update check
```

If you see `Could not reach GitHub`, it's almost always a network/firewall problem. Test:

```bash
curl -fsSL https://api.github.com/repos/nerkoux/EasyNGINX/releases/latest
```

If outbound HTTPS is blocked on the server, silence the daily check:

```bash
echo 'EASYNGINX_NO_UPDATE_CHECK=1' >> /etc/environment
```

## My site returns 502 Bad Gateway

Almost always means the upstream backend is down. Confirm:

```bash
sudo easynginx info api.example.com         # see configured upstream
curl http://127.0.0.1:3000/                  # is the backend up?
sudo journalctl -u my-api -n 50              # backend logs
```

## My site returns 503

If you used `easynginx maintenance ... on`, that's the maintenance page. Turn it off:

```bash
sudo easynginx maintenance api.example.com off
```

Otherwise check rate-limiting (`limit_req`) or backend timeouts.

## DNS check warns "doesn't match this host"

EasyNginx compares the domain's A/AAAA records against this host's outbound IPs. False warnings happen behind:

- **Cloudflare proxy mode** — DNS resolves to CF, not your origin. Pass `--cloudflare` and ignore the warning.
- **NAT** — your server might not know its own public IP. Confirm with `curl -s https://ifconfig.me`. Compare against `dig +short example.com`.

In both cases the warning is informational — issuance still works as long as port 80 is reachable from the public internet.

## Logs aren't where I expect

EasyNginx tails the per-site log paths if your config sets `access_log` / `error_log`, otherwise it falls back to nginx's globals:

```
/var/log/nginx/access.log
/var/log/nginx/error.log
```

Check what your site has configured:

```bash
sudo grep -E 'access_log|error_log' /etc/nginx/sites-available/<domain>.conf
```

## Restore failed `nginx -t` after extraction

EasyNginx aborts the reload but leaves the restored files in place. Your safety snapshot is at `/etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz`. To revert:

```bash
sudo tar xzf /etc/easynginx/backups/snapshots/pre-restore-<timestamp>.tar.gz -C /
sudo nginx -t && sudo systemctl reload nginx
```

Then look at why the restored config didn't validate — usually a path that exists on the source but not on the target (e.g. an `include` referring to a file that wasn't in the backup).

## `audit` keeps reporting the same issue I think I fixed

Check that nginx actually reloaded after your edit:

```bash
sudo systemctl status nginx
sudo nginx -t
sudo easynginx reload
sudo easynginx audit
```

The audit reads files from disk, not nginx's running state, but a stale running config can mask the difference between "fixed" and "fixed and live".

## Still stuck?

```bash
sudo easynginx doctor
```

Then [open an issue](https://github.com/nerkoux/EasyNGINX/issues) with the `doctor` output and the failing command. Include `easynginx --version` and your distro/version.
