#!/usr/bin/env bash
# Scenario 02 — create one reverse-proxy site, no SSL.
# We avoid Let's Encrypt here because issuance time and rate limits would
# dominate the variance and we'd be benchmarking ACME, not the tool.

set -euo pipefail

scenario_create_site() {
    local before_disk
    before_disk=$(du -sk / 2>/dev/null | awk '{print $1}')

    local t0=$(date +%s%N)
    if t_create_site "bench-1.test" "http://127.0.0.1:8080" >/var/log/bench-create.log 2>&1; then
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

    echo "${BENCH_TARGET},02-create-site,${BENCH_RUN},${elapsed_sec},${disk_added},0,${ok}"
}
