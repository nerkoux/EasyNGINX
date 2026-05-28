---
id: install
title: Install
sidebar_position: 1
---

# Install

EasyNginx ships a single bash installer that detects your distro, installs nginx and certbot, configures the firewall, and lays down the `easynginx` CLI.

## Recommended: one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
```

:::caution Always review installer scripts
This is good advice for anything you find on the internet, including this. To audit before running:

```bash
curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh -o install.sh
less install.sh
sudo bash install.sh
```
:::

## Local clone

```bash
git clone https://github.com/nerkoux/EasyNGINX.git
cd EasyNGINX
sudo bash install.sh
```

## Non-interactive installs (CI, cloud-init, Ansible)

Skip every prompt:

```bash
sudo EASYNGINX_FRESH=1 bash install.sh
```

Or restore an existing backup as part of the install:

```bash
sudo EASYNGINX_RESTORE=/root/easynginx-backup-prod-2026-05-28.tar.gz bash install.sh
```

## What the installer does

When you run the installer interactively it asks one question:

```
Choose install mode:
  1) Fresh install (default)
  2) Restore from a previous EasyNginx backup
```

Then, in order:

1. **Detects the distro** via `/etc/os-release` (with `ID_LIKE` fallback).
2. **Picks the package manager** — `apt`, `dnf`, `yum`, `pacman`, or `apk`.
3. **Enables EPEL** automatically on RHEL-based systems (needed for certbot).
4. **Installs** nginx, certbot, certbot-nginx, python3, dig, openssl, and a firewall (ufw or firewalld).
5. **Enables and starts nginx** via systemd.
6. **Opens ports 80 and 443** in the firewall (without enabling a disabled firewall — see [Cautions](../operations/cautions.md)).
7. **Installs the engine** to `/usr/local/share/easynginx`, the CLI to `/usr/local/bin/easynginx`, and writes the detected state to `/etc/easynginx/config.json`.
8. *(Restore mode only)* Searches `~`, `/root`, `/tmp`, `/var/backups`, and `/etc/easynginx/backups` for any `easynginx-backup-*.tar.gz`, lets you pick one, takes a safety snapshot of the live nginx config, then extracts the backup. Validates with `nginx -t` before reloading.

## Supported distros

| Distro | Family | Status | Notes |
|---|---|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | debian | ✅ | Primary target |
| Debian 11 / 12 | debian | ✅ | |
| Linux Mint, Pop!_OS, elementary | debian | ✅ | Detected via `ID_LIKE` |
| Fedora 38+ | fedora | ✅ | |
| RHEL 8 / 9 | rhel | ✅ | EPEL enabled automatically |
| Rocky Linux 8 / 9 | rhel | ✅ | |
| AlmaLinux 8 / 9 | rhel | ✅ | |
| Amazon Linux 2023 | rhel | ✅ | |
| Arch Linux, Manjaro, EndeavourOS | arch | ✅ | |
| Alpine | alpine | ⏳ | Planned |

## After install

```bash
sudo easynginx --version       # confirm the install
sudo easynginx doctor          # run diagnostics
sudo easynginx create          # create your first site
```

Next: [Quick start](quick-start.md).
