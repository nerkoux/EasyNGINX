---
id: preset
title: Presets
sidebar_position: 8
---

# Presets

One-shot site presets for common stacks. Each preset renders a tuned nginx config, validates it, reloads, and optionally issues SSL.

## `php install`

Install PHP-FPM with a sensible set of extensions.

```bash
sudo easynginx php install                      # auto-pick PHP version
sudo easynginx php install --version 8.3
sudo easynginx php install --version 8.2
sudo easynginx php status                       # show PHP-FPM service status
```

Distro support:

- **Debian/Ubuntu** — `php8.3-fpm` plus `php8.3-cli/mysql/curl/mbstring/xml/zip`.
- **Fedora/RHEL** — `php-fpm` plus matching extensions.
- **Arch** — `php` and `php-fpm`.

## `preset wordpress`

Drop in a WordPress-tuned site (pretty permalinks, security blocks for `wp-config.php`, denies on `.php` inside `wp-content/uploads/`, asset caching).

```bash
sudo easynginx preset wordpress example.com \
  --root /var/www/example.com \
  --ssl --email admin@example.com
```

After this, drop your WordPress files into `/var/www/example.com` and the site is ready.

## `preset laravel`

Laravel preset with `public/` document root, the canonical `try_files $uri $uri/ /index.php?$query_string` pattern, and storage permissions.

```bash
sudo easynginx preset laravel api.example.com \
  --root /opt/myapp \
  --ssl --email admin@example.com
```

`--root` must point at your Laravel project directory (the one containing `public/`). EasyNginx confirms `public/` exists and adjusts `storage/` permissions.

## `preset node`

Reverse proxy + optional systemd unit for a Node.js app.

```bash
sudo easynginx preset node api.example.com \
  --port 3000 \
  --service-name my-api \
  --service-cmd "/usr/bin/node /opt/my-api/server.js" \
  --service-cwd /opt/my-api \
  --service-user www-data \
  --ssl --email admin@example.com
```

If `--service-name` and `--service-cmd` are passed, EasyNginx writes a systemd unit at `/etc/systemd/system/<name>.service`, enables it, and starts it. The service auto-restarts on failure and starts on boot.

Without those flags, EasyNginx just creates the proxy — you start your Node app yourself.

## `preset static`

Static hosting with the right rewrite rules and aggressive asset caching.

```bash
sudo easynginx preset static example.com --kind nextjs --root /var/www/example.com
sudo easynginx preset static example.com --kind hugo
sudo easynginx preset static example.com --kind jekyll
sudo easynginx preset static example.com --kind html
```

| Kind | Behaviour |
|---|---|
| `nextjs`, `html` | SPA-friendly: `try_files $uri $uri/ /index.html`. |
| `hugo`, `jekyll` | Static-site-generator-friendly: `try_files $uri $uri/ =404`. |

All variants set `expires 365d` and `Cache-Control: public, max-age=31536000, immutable` on hashed assets.
