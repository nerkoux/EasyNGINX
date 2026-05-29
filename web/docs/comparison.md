---
id: comparison
title: Comparison & benchmarks
sidebar_position: 98
---

# Comparison & benchmarks

EasyNginx isn't the only tool in this space. This page documents the trade-offs honestly and points at a reproducible benchmark suite anyone can re-run.

## Feature parity

A check (✅) means the tool ships this out of the box on its happy path. A warning (⚠️) means it's possible but requires custom config, plugins, or manual work. An ❌ means the tool doesn't do this.

| Capability | EasyNginx | EasyEngine | Webinoly |
|---|:---:|:---:|:---:|
| **Architecture** | Bare metal | Docker per site | Bare metal |
| **Engine language** | Python stdlib | PHP wrapper + Docker | Bash |
| **Distros** | Ubuntu, Debian, Fedora, RHEL, Rocky, Alma, Arch | Any with Docker | Ubuntu only |
| **Third-party runtime deps** | None | Docker, docker-compose | None |
| **Reverse proxy** | ✅ | ✅ | ⚠️ via custom |
| **Static site presets** | ✅ HTML / Hugo / Jekyll / Next.js | ⚠️ HTML | ⚠️ HTML |
| **PHP-FPM site** | ✅ | ✅ | ✅ |
| **WordPress** | ✅ rewrites + security blocks | ✅ DB + Redis included | ✅ DB + Redis + Memcached optional |
| **Laravel** | ✅ public/ + storage perms | ❌ | ❌ |
| **Node.js (proxy + systemd unit)** | ✅ | ❌ | ❌ |
| **WebSocket reverse proxy** | ✅ | ⚠️ manual | ⚠️ manual |
| **Load balancer (multi-upstream)** | ✅ | ❌ | ❌ |
| **Maintenance mode + custom HTML** | ✅ | ❌ | ❌ |
| **Site clone for staging** | ✅ | ❌ | ❌ |
| **Let's Encrypt HTTP-01** | ✅ | ✅ | ✅ |
| **Let's Encrypt DNS-01 wildcard** | ⚠️ flag interface, plugins WIP | ✅ Cloudflare | ✅ Cloudflare / DigitalOcean / EasyDNS |
| **Self-signed cert helper** | ✅ | ✅ | ✅ |
| **Bring-your-own-cert** | ✅ | ⚠️ manual | ✅ |
| **Color-coded cert expiry list** | ✅ | ❌ | ⚠️ |
| **Snapshot before write** | ✅ every command | ❌ | ❌ |
| **Auto-rollback on `nginx -t` failure** | ✅ | ❌ | ❌ |
| **sha256-verified backup tarball** | ✅ | ✅ DB + files | ✅ |
| **Restore-during-install** | ✅ `EASYNGINX_RESTORE=path bash install.sh` | ❌ | ❌ |
| **Cross-distro restore** | ✅ | n/a (Docker-portable) | ❌ |
| **Security audit** | ✅ ciphers, headers, expiry, world-readable .env | ❌ | ⚠️ partial |
| **TLS profile picker** | ✅ modern / intermediate / legacy | ❌ | ⚠️ via stack tweak |
| **HSTS toggle (with preload warning)** | ✅ | ❌ | ✅ |
| **Bot blocker (named bot list)** | ✅ | ❌ | ✅ |
| **GeoIP allow/deny** | ✅ requires GeoIP2 module | ❌ | ⚠️ via custom |
| **fail2ban integration** | ✅ + 3 jails | ✅ | ✅ |
| **ModSecurity / WAF** | ✅ install + per-site toggle | ❌ | ❌ |
| **Access-log analyzer** | ✅ top IPs / paths / slow URLs | ❌ | ❌ |
| **Stub_status metrics** | ✅ localhost-only | ❌ | ⚠️ via stack |
| **/healthz endpoint helper** | ✅ | ❌ | ❌ |
| **Multi-server SSH deploy + rollback** | ✅ | ❌ | ❌ |
| **Read-only web dashboard** | ✅ stdlib HTTP, token-gated | ❌ | ❌ |
| **Auto-update with snapshot rollback** | ✅ atomic `os.replace` | ⚠️ no rollback | ⚠️ no rollback |
| **Update-available notification** | ✅ background 24h cache | ❌ | ❌ |
| **First release** | 2026-05 | 2014-04 (v1) / 2018-09 (v4) | 2018-08 |
| **License** | MIT | MIT | GPL-3.0 |

## Where each tool wins

**EasyEngine** is the right choice when:

- You want one-command WordPress with full Docker isolation per site.
- You like batteries-included stacks (MariaDB / Redis / mail catcher).
- Your deploy target is "any Linux that has Docker".

**Webinoly** is the right choice when:

- You're on Ubuntu and WordPress is your primary workload.
- You want bare-metal performance without Docker overhead.
- You need its mature DNS-01 Cloudflare / DigitalOcean / EasyDNS plugins today.

**EasyNginx** is the right choice when:

- You want stock nginx on the metal, no daemons added.
- You manage many distros (Ubuntu, Debian, Fedora, RHEL, Arch) from one tool.
- You want **safety guarantees** baked into every command — snapshot before write, validate before reload, atomic rollback on failure.
- You want first-class **audit / cluster deploy / atomic-update / backup-as-archive** without writing Ansible.
- Your sites aren't all WordPress.

If you already love and use EasyEngine or Webinoly, keep using them — they've earned their place.

## Reproducible benchmark suite

The repo ships a Docker-based benchmark at [`bench/`](https://github.com/nerkoux/EasyNGINX/tree/main/bench).

```bash
git clone https://github.com/nerkoux/EasyNGINX
cd EasyNGINX/bench
./run.sh
cat results/*/summary.md
```

For each (target, scenario, run), the suite spins up a fresh Ubuntu 22.04 container, installs the tool from upstream, runs the scenario, and writes one CSV line. Three runs per scenario, median reported.

### Scenarios

- `01-install` — cold install from a fresh container.
- `02-create-site` — one reverse-proxy site, no SSL.
- `03-audit` — security scan after 5 sites exist (n/a for tools without an audit).
- `04-backup` — full backup tarball.
- `05-resources` — disk used by the tool, RSS of any persistent daemon added.

### What's measured

Wall-clock seconds, disk added, daemon memory. Not measured: nginx throughput (would benchmark nginx, not the tool), WordPress page-load time (would benchmark PHP / DB / cache).

### Why this matters

Without numbers, "EasyNginx is fast" is marketing. With numbers in a script anyone can re-run, it's a fact you can verify or refute. PRs that fix incorrect upstream commands or add scenarios are welcome.

See [`bench/methodology.md`](https://github.com/nerkoux/EasyNGINX/blob/main/bench/methodology.md) for the full methodology, biases, and limitations.

## Honest limitations

- **WordPress on EasyNginx is a preset, not a stack.** EasyNginx writes nginx config and (optionally) installs PHP-FPM, but expects you to bring MariaDB / MySQL. EasyEngine and Webinoly install the database for you.
- **DNS-01 wildcard plugin support** is wired into the CLI surface but the per-provider plugins land in a follow-up release. Webinoly is more mature here today.
- **No DB / Redis / cache management.** EasyNginx is an nginx tool. EasyEngine is closer to a "WP appliance".

## Contributing to the comparison

The comparison is honest, but it's also written by the EasyNginx maintainer. If a row is wrong, file an issue or open a PR with the upstream command that proves it. Every benchmarked behaviour is in `bench/scenarios/` so the evidence is reproducible.
