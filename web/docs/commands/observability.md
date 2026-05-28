---
id: observability
title: Observability
sidebar_position: 7
---

# Observability

## `metrics`

Toggle the local-only `stub_status` endpoint.

```bash
sudo easynginx metrics enable     # on at http://127.0.0.1:9080/stub_status
sudo easynginx metrics disable
sudo easynginx metrics status
```

The endpoint binds to localhost only, with `allow 127.0.0.1` and `deny all`. To expose it externally, proxy through nginx with your own auth.

Sample output:

```
Active connections: 12
server accepts handled requests
 38912 38912 91827
Reading: 0 Writing: 3 Waiting: 9
```

Hook it into Prometheus with [nginx-prometheus-exporter](https://github.com/nginxinc/nginx-prometheus-exporter), or scrape it directly with curl in your monitoring system.

## `stats`

Quick analyzer over a site's access log.

```bash
sudo easynginx stats api.example.com               # last 24h
sudo easynginx stats api.example.com --hours 6
sudo easynginx stats api.example.com --hours 168   # last week
```

Reports:

- Total requests in the window.
- Status code breakdown.
- Top 10 IPs.
- Top 10 paths.
- Top 10 slowest URLs (only if `request_time` is logged).

This works on the standard combined log format. If you've customized the log format, EasyNginx will silently skip lines it can't parse.

## `healthz`

Add a `/healthz` endpoint for uptime monitoring.

```bash
sudo easynginx healthz api.example.com on                              # returns 200 "ok"
sudo easynginx healthz api.example.com on --upstream http://127.0.0.1:3000/ping
sudo easynginx healthz api.example.com off
```

With no `--upstream`, EasyNginx returns a static 200 from nginx. With `--upstream`, it proxies the check to your backend with short timeouts (2s connect, 5s read), so a slow or dead backend returns a non-200 within seconds.

The endpoint has `access_log off` so it won't pollute your access log with monitor pings.
