#!/usr/bin/env bash
# EasyEngine target adapter.
# Note: EasyEngine v4 runs sites as Docker containers. Some scenarios
# (audit, granular reverse proxy) aren't supported and report n/a.

set -euo pipefail

t_install() {
    wget -qO ee https://rt.cx/ee4
    sudo bash ee
}

t_create_site() {
    local domain="$1"
    local upstream="$2"
    # EasyEngine's reverse proxy site type points at an external URL.
    sudo ee site create "$domain" --proxy="$upstream"
}

t_audit() {
    # EasyEngine has no audit. Report unsupported.
    return 99
}

t_backup() {
    # EasyEngine doesn't ship a unified backup command for nginx config alone.
    # The closest thing is per-site `ee site backup` (community plugin) or a
    # cron-based volume backup. We mark this n/a.
    return 99
}

t_restore() {
    return 99
}

t_remove_site() {
    local domain="$1"
    sudo ee site delete "$domain" --yes
}

t_uninstall() {
    # No supported uninstall — Docker volumes and the ee CLI must be removed
    # by hand.
    sudo rm -f /usr/local/bin/ee
    sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true
}
