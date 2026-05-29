#!/usr/bin/env bash
# Minimal systemctl stub for benchmark containers.
# Records every call into /var/log/systemctl-stub.log and returns 0.
# Real systemd unit start/stop is impossible in this container, but every
# tool we benchmark only uses systemctl to enable/disable/reload, which
# we simulate by logging.

set -euo pipefail
mkdir -p /var/log
echo "[$(date -Iseconds)] systemctl $*" >> /var/log/systemctl-stub.log

case "${1:-}" in
    is-active|is-enabled)
        # Pretend nginx is active so audit-style commands don't bail out.
        echo "active"
        ;;
    status)
        echo "● nginx.service - A high performance web server"
        echo "     Loaded: loaded"
        echo "     Active: active (running) since now"
        ;;
    *)
        ;;
esac
exit 0
