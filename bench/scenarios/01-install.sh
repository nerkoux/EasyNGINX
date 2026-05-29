#!/usr/bin/env bash
# Scenario 01 — install the tool from a cold container.
# Sourced by run.sh; expects $TARGET to be loaded so $t_install is defined.

set -euo pipefail

scenario_install() {
    local before_disk
    before_disk=$(du -sk / 2>/dev/null | awk '{print $1}')

    local t0=$(date +%s%N)
    if t_install >/var/log/bench-install.log 2>&1; then
        local ok=1
    else
        local ok=0
    fi
    local t1=$(date +%s%N)
    local elapsed_ns=$(( t1 - t0 ))
    local elapsed_sec
    elapsed_sec=$(awk "BEGIN { printf \"%.3f\", $elapsed_ns / 1000000000 }")

    local after_disk
    after_disk=$(du -sk / 2>/dev/null | awk '{print $1}')
    local disk_added=$(( after_disk - before_disk ))

    echo "${BENCH_TARGET},01-install,${BENCH_RUN},${elapsed_sec},${disk_added},0,${ok}"
}
