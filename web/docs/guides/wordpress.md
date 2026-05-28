---
id: wordpress
title: WordPress
---

# WordPress

A complete WordPress install behind EasyNginx in three commands.

## 1. Install PHP-FPM

```bash
sudo easynginx php install --version 8.3
```

This pulls in `php8.3-fpm` plus `cli`, `mysql`, `curl`, `mbstring`, `xml`, `zip` (Debian/Ubuntu naming; the engine adapts for RHEL and Arch).

## 2. Drop the preset

```bash
sudo easynginx preset wordpress example.com \
  --root /var/www/example.com \
  --ssl --email admin@example.com
```

Behind the scenes EasyNginx:

- Creates `/var/www/example.com` if needed.
- Writes a WordPress-tuned nginx config with pretty permalinks, security headers, asset caching, and explicit denies on `wp-config.php`, `readme.html`, and `.php` files inside `wp-content/uploads/`.
- Issues a Let's Encrypt cert.

## 3. Install WordPress files

```bash
cd /var/www/example.com
sudo curl -fsSL https://wordpress.org/latest.tar.gz | sudo tar xzf - --strip-components=1
sudo chown -R www-data:www-data /var/www/example.com
```

Visit `https://example.com/` and finish the WordPress installer.

## Recommended hardening

```bash
sudo easynginx hsts example.com on
sudo easynginx botblock example.com on
sudo easynginx audit              # confirm everything is green
```

## Backups

After your first successful run:

```bash
sudo easynginx backup --with-www --label "wordpress-baseline"
```

`--with-www` includes the WordPress filesystem so you can restore the whole site (including content) from the tarball.

## Database backups

EasyNginx doesn't manage your database. For MySQL/MariaDB the simplest companion:

```bash
mysqldump --all-databases | gzip > /etc/easynginx/backups/db-$(date +%F).sql.gz
```

Wire it into cron alongside `easynginx backup`.

## Updating WordPress core / plugins

EasyNginx doesn't get in the way of WordPress's own update flow. Update inside the dashboard or via WP-CLI as usual.
