#!/usr/bin/env bash
# bench/run.sh — orchestrator for the EasyNginx vs. EasyEngine vs. Webinoly suite.
#
# For each (target, run), one container is spun up. Inside it, every
# scenario runs in order so state from earlier scenarios (the tool being
# installed, sites existing, etc.) is available to later ones.
#
# Usage:
#   ./run.sh                           # all targets, 3 runs each
#   ./run.sh --target easynginx        # one tool only
#   ./run.sh --runs 1                  # quick smoke
#   ./run.sh --keep                    # don't auto-remove containers (debugging)
#
# Output: results/<UTC-stamp>/raw.csv plus a markdown summary.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGETS=(easynginx easyengine webinoly)
SCENARIOS=(01-install 02-create-site 03-audit 04-backup 05-resources)
RUNS=3
IMG_TAG="easynginx-bench:ubuntu-22.04"
KEEP=0

usage() { sed -n '2,16p' "$0"; exit 0; }

want_target=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)   want_target="$2"; shift 2 ;;
        --runs)     RUNS="$2";        shift 2 ;;
        --keep)     KEEP=1;           shift   ;;
        -h|--help)  usage ;;
        *)          echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

[[ -n "$want_target" ]] && TARGETS=("$want_target")

if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required." >&2
    exit 1
fi

# EasyEngine spawns Docker-in-Docker for its sites; needs --privileged.
docker_flags_for() {
    case "$1" in
        easyengine) echo "--privileged" ;;
        *)          echo "" ;;
    esac
}

stamp="$(date -u +%Y%m%d-%H%M%S)"
out_dir="$ROOT/results/$stamp"
mkdir -p "$out_dir"
csv="$out_dir/raw.csv"
log="$out_dir/run.log"
echo "target,scenario,run,wall_seconds,disk_added_kb,rss_added_kb,ok" > "$csv"

echo "==> building benchmark image: $IMG_TAG"
docker build -q -t "$IMG_TAG" -f "$ROOT/Dockerfile.ubuntu" "$ROOT" >/dev/null

# Driver script we feed into the container. It sources every scenario
# and target file from /work and runs them in order, emitting one CSV
# line per scenario to stdout.
driver() {
    cat <<'BASH'
set -uo pipefail

# shellcheck disable=SC1091
source "/work/targets/${BENCH_TARGET}.sh"

run_scenario() {
    local sc="$1"
    # shellcheck disable=SC1090
    source "/work/scenarios/${sc}.sh"
    # Function name is "scenario_<short>" where <short> drops the "NN-"
    # prefix and replaces "-" with "_".
    local short fn
    short="${sc#[0-9][0-9]-}"
    fn="scenario_${short//-/_}"
    if declare -F "$fn" >/dev/null; then
        "$fn"
    else
        echo "${BENCH_TARGET},${sc},${BENCH_RUN},0,0,0,0" >&2
        return 1
    fi
}

for sc in 01-install 02-create-site 03-audit 04-backup 05-resources; do
    run_scenario "$sc"
done
BASH
}

for target in "${TARGETS[@]}"; do
    flags=$(docker_flags_for "$target")
    for run in $(seq 1 "$RUNS"); do
        echo "==> $target / run $run" | tee -a "$log"
        # Each (target, run) gets its own container. Scenarios run in order,
        # sharing state — install once, then create site, then audit etc.
        # Mounted /work is read-only; results stream out via stdout.
        docker run --rm $flags \
            -v "$ROOT:/work:ro" \
            -e BENCH_TARGET="$target" \
            -e BENCH_RUN="$run" \
            "$IMG_TAG" \
            bash -c "$(driver)" \
            >> "$csv" 2>>"$log" || {
                echo "  [warn] container exited non-zero; partial results may be missing" \
                    | tee -a "$log"
            }
    done
done

echo
echo "==> aggregating"
python3 "$ROOT/aggregate.py" "$csv" > "$out_dir/summary.md"
echo
echo "Done."
echo "  Raw CSV: $csv"
echo "  Summary: $out_dir/summary.md"
echo "  Logs:    $log"
