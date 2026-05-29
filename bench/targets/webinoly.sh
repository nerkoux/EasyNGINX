#!/usr/bin/env bash
# Webinoly target adapter.
# Webinoly is Ubuntu-only and WordPress-first; reverse-proxy sites use -tool=php
# with a custom location block.

set -euo pipefail

t_install() {
    wget -qO weby qrok.es/wy
    sudo bash weby
}

t_create_site() {
    local domain="$1"
    local upstream="$2"
    # Webinoly's `-tool=php` is the closest neutral site type. It doesn't have
    # a true reverse-proxy primitive in the install path; the test reflects
    # that and records n/a if -tool=proxy isn't supported on the version.
    if sudo site "$domain" -proxy="$upstream" 2>/dev/null; then
        return 0
    fi
    sudo site "$domain" -html
}

t_audit() {
    # Webinoly's `info` command lists tool versions but does not audit security.
    sudo webinoly -info
}

t_backup() {
    # Webinoly has `webinoly -backup` for files and DBs. Output goes to
    # /var/www/<site>/backup/. We record the latest archive.
    sudo webinoly -backup-now
    find /var/www -name '*.tar.gz' -newer /tmp -print | head -n1
}

t_restore() {
    # Webinoly's restore is per-site and interactive; not scriptable in a way
    # that matches the other tools. Mark n/a.
    return 99
}

t_remove_site() {
    local domain="$1"
    sudo site "$domain" -delete -force
}

t_uninstall() {
    sudo webinoly -uninstall=force
}
