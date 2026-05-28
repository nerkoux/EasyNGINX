# EasyNginx

Beginner-friendly Nginx setup and virtual host manager for Linux. One-line install, then a single `create-host` command walks you through reverse proxies, static sites, PHP, WebSockets, redirects, and load balancers — including DNS checks, firewall rules, Let's Encrypt SSL, HTTP/2, gzip, security headers, and automatic rollback if anything breaks.

- **Author:** Akshat Mehta — [akshatmehta.com](https://akshatmehta.com)
- **GitHub:** [github.com/nerkoux](https://github.com/nerkoux)
- **Repo:** [github.com/nerkoux/EasyNGINX](https://github.com/nerkoux/EasyNGINX)

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
```

Or clone and run locally:

```bash
git clone https://github.com/nerkoux/EasyNGINX.git
cd EasyNGINX
sudo bash install.sh
```

The installer:

1. Detects your distro (Ubuntu, Debian, Fedora, RHEL, Rocky, AlmaLinux, Arch, Manjaro).
2. Installs nginx, certbot, the nginx certbot plugin, python3, curl, dig, and a firewall (ufw or firewalld).
3. Enables and starts nginx.
4. Installs the `create-host` CLI to `/usr/local/bin`.
5. Installs the EasyNginx engine to `/usr/local/share/easynginx`.
6. Opens HTTP/HTTPS in the firewall.

## Usage

```bash
sudo create-host
```

You'll be prompted for:

- **Domain** — `api.example.com`
- **Site type** — reverse proxy, static, PHP, WebSocket, redirect, load balancer
- **Backend / root / upstreams** — depending on type
- **SSL** — yes/no, with Let's Encrypt email
- **Extras** — HTTP/2, gzip, security headers, rate limiting, basic auth

EasyNginx then:

- Validates the domain syntax.
- Checks the DNS A/AAAA record points at this server (warns if not).
- Checks ports 80/443 are reachable.
- Confirms the backend is reachable (for proxy modes).
- Renders the config from a template.
- Runs `nginx -t` before any reload.
- Reloads nginx.
- Issues SSL via certbot (with HTTP-01 by default).
- Backs up the prior config and rolls back on any failure.

### Non-interactive flags

```bash
sudo create-host \
  --domain api.example.com \
  --type reverse-proxy \
  --upstream http://127.0.0.1:3000 \
  --ssl --email admin@example.com \
  --yes
```

### Other commands

```bash
sudo create-host list                  # list managed sites
sudo create-host disable api.example.com
sudo create-host enable  api.example.com
sudo create-host remove  api.example.com
sudo create-host renew                 # certbot renew + reload
```

## Supported distros

| Distro      | Status |
|-------------|--------|
| Ubuntu      | ✅     |
| Debian      | ✅     |
| Fedora      | ✅     |
| RHEL        | ✅     |
| Rocky       | ✅     |
| AlmaLinux   | ✅     |
| Arch        | ✅     |
| Manjaro     | ✅     |
| Alpine      | ⏳ planned |

## License

MIT — see [LICENSE](LICENSE).
