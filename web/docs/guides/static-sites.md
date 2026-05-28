---
id: static-sites
title: Static sites
---

# Static sites

Hosting Next.js exports, Hugo / Jekyll output, or plain HTML.

## Pick your variant

```bash
sudo easynginx preset static example.com --kind nextjs --root /var/www/example.com
sudo easynginx preset static example.com --kind hugo
sudo easynginx preset static example.com --kind jekyll
sudo easynginx preset static example.com --kind html
```

| Kind | Behaviour |
|---|---|
| `nextjs`, `html` | SPA-friendly: `try_files $uri $uri/ /index.html`. |
| `hugo`, `jekyll` | SSG-friendly: `try_files $uri $uri/ =404`. |

All variants enable gzip, security headers, and aggressive caching on hashed assets.

## Deploy flow

Build locally, then sync to the document root:

```bash
# Hugo
hugo --minify
rsync -avz --delete public/ user@server:/var/www/example.com/

# Jekyll
bundle exec jekyll build
rsync -avz --delete _site/ user@server:/var/www/example.com/

# Next.js (static export)
npx next build && npx next export
rsync -avz --delete out/ user@server:/var/www/example.com/
```

Or build on the server, with a CI hook that runs `rsync` from your laptop.

## Cache busting

The bundled config caches hashed assets for 1 year (`Cache-Control: public, max-age=31536000, immutable`). Rebuild your static site so file contents change → hash changes → URL changes → cache busted.

For HTML files (which shouldn't be cached aggressively), nginx's defaults apply: short-lived cache with revalidation. Modern static-site generators handle the hashing automatically.

## SSL + HSTS

```bash
sudo easynginx hsts example.com on
sudo easynginx audit
```

## Multi-domain (apex + www)

By default, `easynginx create` and the static preset register only the bare domain. To redirect `www.example.com` to `example.com`:

```bash
sudo easynginx create \
  --domain www.example.com \
  --type redirect \
  --redirect-to https://example.com \
  --ssl --email admin@example.com
```

This issues a separate cert for `www` and 301s every request to the apex.
