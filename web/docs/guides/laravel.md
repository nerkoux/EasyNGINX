---
id: laravel
title: Laravel
---

# Laravel

A production-ready Laravel deploy behind EasyNginx.

## 1. Set up PHP-FPM

```bash
sudo easynginx php install --version 8.3
```

## 2. Drop the project

```bash
sudo mkdir -p /opt/myapp
sudo chown $USER /opt/myapp
git clone git@github.com:you/myapp.git /opt/myapp
cd /opt/myapp
composer install --no-dev --optimize-autoloader
cp .env.example .env
php artisan key:generate
php artisan storage:link
```

## 3. Run the preset

```bash
sudo easynginx preset laravel api.example.com \
  --root /opt/myapp \
  --ssl --email admin@example.com
```

EasyNginx:

- Confirms `/opt/myapp/public` exists.
- Writes the canonical `try_files $uri $uri/ /index.php?$query_string` pattern.
- Sets `storage/` to group-writable for `www-data` (best-effort — adjust if your distro uses a different group).
- Issues a Let's Encrypt cert.

## Permissions

Laravel's `storage/` and `bootstrap/cache/` need to be writable by the PHP-FPM user. The preset attempts this, but if you see permission errors:

```bash
sudo chown -R www-data:www-data /opt/myapp/storage /opt/myapp/bootstrap/cache
sudo chmod -R 775 /opt/myapp/storage /opt/myapp/bootstrap/cache
```

## Queue workers and schedulers

Use systemd directly for these. Example queue worker unit at `/etc/systemd/system/myapp-worker.service`:

```ini
[Unit]
Description=Laravel queue worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/php artisan queue:work --sleep=3 --tries=3
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now myapp-worker
```

## Cron

For Laravel's scheduler:

```cron
* * * * * cd /opt/myapp && php artisan schedule:run >> /dev/null 2>&1
```

## Hardening

```bash
sudo easynginx hsts api.example.com on
sudo easynginx audit
```

## Deploys

For zero-downtime deploys, point the document root at a `current` symlink:

```bash
sudo easynginx preset laravel api.example.com --root /opt/myapp/current --ssl --email you@example.com
```

…and have your deploy script flip `current` between release directories. nginx just sees the symlink change.
