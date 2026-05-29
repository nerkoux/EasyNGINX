#!/usr/bin/env bash
# Scenario 04 — full backup tarball after sites exist.

set -euo pipefail

scenario_backup() {
    local t0 t1
    t0=$(date +%s%N)
    local archive=""
    if archive=$(t_backup 2>/var/log/bench-backup.log); then
        local ok=1
    else
        local rc=$?
        if [[ "$rc" == "99" ]]; then
            echo "${BENCH_TARGET},04-backup,${BENCH_RUN},0,0,0,n/a"
            return 0
        fi
        local ok=0
    fi
    t1=$(date +%s%N)
    local elapsed_ns=$(( t1 - t0 ))
    local elapsed_sec
    elapsed_sec=$(awk "BEGIN { printf \"%.3f\", $elapsed_ns / 1000000000 }")

    local size_kb=0
    if [[ "$ok" == "1" && -n "$archive" && -f "$archive" ]]; then
        size_kb=$(du -k "$archive" | awk '{print $1}')
    fi

    echo "${BENCH_TARGET},04-backup,${BENCH_RUN},${elapsed_sec},${size_kb},0,${ok}"
}
