#!/usr/bin/env bash
# EasyNginx target adapter — used by run.sh.
# Defines a function for each scenario.

set -euo pipefail

t_install() {
    curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh \
        | sudo bash
}

t_create_site() {
    local domain="$1"
    local upstream="$2"
    sudo easynginx create \
        --domain "$domain" \
        --type reverse-proxy \
        --upstream "$upstream" \
        --no-ssl --yes
}

t_audit() {
    sudo easynginx audit
}

t_backup() {
    sudo easynginx backup --label benchmark --output-dir /tmp/easynginx-bench-out
    ls -1 /tmp/easynginx-bench-out/*.tar.gz | tail -n1
}

t_restore() {
    local archive="$1"
    sudo easynginx restore "$archive" --yes --skip-verify
}

t_remove_site() {
    local domain="$1"
    sudo easynginx remove "$domain" --yes --keep-cert
}

t_uninstall() {
    sudo easynginx uninstall --purge --yes
}
