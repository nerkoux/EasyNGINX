---
id: node
title: Node.js
---

# Node.js

Reverse proxy nginx in front of a Node.js app, with an optional systemd unit so the app starts on boot.

## With systemd unit (recommended)

```bash
sudo easynginx preset node api.example.com \
  --port 3000 \
  --service-name my-api \
  --service-cmd "/usr/bin/node /opt/my-api/server.js" \
  --service-cwd /opt/my-api \
  --service-user www-data \
  --ssl --email admin@example.com
```

EasyNginx writes:

- `/etc/nginx/sites-available/api.example.com.conf` — proxy to `127.0.0.1:3000` with WebSocket upgrade headers.
- `/etc/systemd/system/my-api.service` — runs your Node command, restarts on failure, starts on boot.

Then enables and starts the service.

## Without a systemd unit

If you manage your Node process with PM2, Docker, or your own thing:

```bash
sudo easynginx preset node api.example.com \
  --port 3000 \
  --ssl --email admin@example.com
```

EasyNginx just creates the reverse proxy. Your Node app keeps running however you started it.

## Environment variables

The systemd unit hard-codes `NODE_ENV=production` and `PORT=<your-port>`. For more, edit the unit and reload:

```ini
[Service]
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=DATABASE_URL=postgres://...
EnvironmentFile=/etc/my-api/secrets.env
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart my-api
```

## WebSockets

The bundled config sets `Upgrade` / `Connection` headers, so Socket.IO and raw WebSockets work without additional changes.

If your app handles long-lived connections (chat, streaming), bump `proxy_read_timeout`:

```bash
sudo easynginx edit api.example.com
# add inside the location / { ... } block:
#   proxy_read_timeout 3600s;
```

EasyNginx validates and reloads on save.

## Multiple Node apps on one server

```bash
sudo easynginx preset node api.example.com   --port 3000
sudo easynginx preset node admin.example.com --port 3001
sudo easynginx preset node ws.example.com    --port 3002
```

Each gets its own server block and (optionally) systemd unit.

## Logs

```bash
sudo easynginx logs api.example.com -f         # nginx access log
sudo journalctl -u my-api -f                   # Node app log
```
