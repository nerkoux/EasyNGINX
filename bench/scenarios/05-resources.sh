#!/usr/bin/env bash
# Scenario 05 — measure tool footprint after install.

set -euo pipefail

scenario_resources() {
    # Disk usage by the tool itself (best effort: known install paths).
    local disk_kb=0
    case "${BENCH_TARGET}" in
        easynginx)
            disk_kb=$(du -sk /usr/local/share/easynginx /usr/local/bin/easynginx /etc/easynginx 2>/dev/null \
                      | awk '{ s += $1 } END { print s+0 }')
            ;;
        easyengine)
            disk_kb=$(du -sk /usr/local/bin/ee /opt/easyengine 2>/dev/null \
                      | awk '{ s += $1 } END { print s+0 }')
            ;;
        webinoly)
            disk_kb=$(du -sk /opt/webinoly /usr/local/bin/webinoly /usr/local/bin/site /usr/local/bin/stack 2>/dev/null \
                      | awk '{ s += $1 } END { print s+0 }')
            ;;
    esac

    # Persistent daemons added by the tool.
    local rss_kb=0
    case "${BENCH_TARGET}" in
        easyengine)
            # Sum RSS of dockerd + containerd + any per-site nginx.
            if command -v ps >/dev/null 2>&1; then
                rss_kb=$(ps -e -o rss=,comm= 2>/dev/null \
                         | awk '$2 ~ /(dockerd|containerd|nginx)/ { s += $1 } END { print s+0 }')
            fi
            ;;
        easynginx|webinoly)
            # No daemon added by the tool itself. nginx is shared baseline.
            rss_kb=0
            ;;
    esac

    echo "${BENCH_TARGET},05-resources,${BENCH_RUN},0,${disk_kb},${rss_kb},1"
}
