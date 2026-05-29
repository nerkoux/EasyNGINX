#!/usr/bin/env bash
# Scenario 03 — run the tool's audit/info equivalent.
# Relies on at least 1 site existing from scenario 02. We add 4 more so audit
# has something realistic to scan.

set -euo pipefail

scenario_audit() {
    for i in 2 3 4 5; do
        t_create_site "bench-${i}.test" "http://127.0.0.1:8080" >/dev/null 2>&1 || true
    done

    local t0 t1
    t0=$(date +%s%N)
    if t_audit >/var/log/bench-audit.log 2>&1; then
        local ok=1
    else
        local rc=$?
        if [[ "$rc" == "99" ]]; then
            echo "${BENCH_TARGET},03-audit,${BENCH_RUN},0,0,0,n/a"
            return 0
        fi
        local ok=0
    fi
    t1=$(date +%s%N)

    local elapsed_ns=$(( t1 - t0 ))
    local elapsed_sec
    elapsed_sec=$(awk "BEGIN { printf \"%.3f\", $elapsed_ns / 1000000000 }")

    echo "${BENCH_TARGET},03-audit,${BENCH_RUN},${elapsed_sec},0,0,${ok}"
}
