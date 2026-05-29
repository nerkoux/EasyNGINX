# Benchmark methodology

The numbers in this suite are only useful if anyone can reproduce them. This file pins down the rules.

## Environment

Every target runs in an identical, freshly-built Ubuntu 22.04 container:

- 2 vCPU, 4 GB RAM (configurable in `run.sh`)
- Docker 24+ (rootful)
- Network: NAT bridge, internet reachable
- Apt cache: cold (image rebuilt before each tool)
- Time source: `date +%s%N` for nanosecond timing on the host
- Repeats: 3 runs per (target, scenario), reported as median

The `Dockerfile.ubuntu` contains the exact base — no surprise pre-installs.

## Tools under test

| Tool | Version | Source | Install command |
|---|---|---|---|
| EasyNginx | latest tag from `nerkoux/EasyNGINX` | curl-piped install | `curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh \| sudo bash` |
| EasyEngine | v4.x latest | upstream | `wget -qO ee https://rt.cx/ee4 && sudo bash ee` |
| Webinoly | latest stable | upstream | `wget -qO weby qrok.es/wy && sudo bash weby` |

We pin to the upstream's documented install method. If the upstream changes its install URL, this benchmark needs updating — file an issue.

## Scenarios

Each scenario is a single shell script in `scenarios/`. Each script writes a single CSV line:

```
target,scenario,run,wall_seconds,disk_added_kb,rss_added_kb,ok
easynginx,01-install,1,38.214,18432,0,1
```

### `01-install.sh`

Time from "container ready" to "tool reports installed". Disk growth measured by `du -sk /` before/after.

### `02-create-site.sh`

Time to create one reverse-proxy site `example.test` pointing at `http://127.0.0.1:8080`. SSL **off** for this scenario — Let's Encrypt's rate limits and DNS dependency would dominate the variance.

For tools that require WordPress as their default site type (EasyEngine), the equivalent reverse-proxy command is used. If a tool can't do reverse proxy without WP, the scenario records `ok=0` for that target.

### `03-audit.sh`

After 5 sites are created, time to run the tool's audit/info-equivalent command. EasyEngine and Webinoly don't have a dedicated audit, so they get `n/a`.

### `04-backup.sh`

Time to produce a full backup including site configs and (where the tool supports it) Let's Encrypt certs and content. Output size measured.

### `05-restore.sh`

Time to extract that backup onto a freshly-installed second container and run the tool's "verify" / "test" command. Records both wall time and whether nginx serves the test site afterwards.

### `06-resources.sh`

After all of the above, captures:

- Disk used by the tool itself (binaries + state, not site content).
- RSS of any persistent daemon added by the tool (Docker for EasyEngine, none for the others).
- Idle CPU usage over 60 seconds.

## What's measured and what isn't

**Measured:**
- Wall-clock time of the tool's operations.
- Disk and memory the tool itself adds.
- Whether the resulting nginx serves traffic.

**Deliberately not measured:**
- nginx request throughput. All three use the same nginx, so this would measure nginx, not the tool.
- WordPress page-load time. Same reason — that's PHP / DB / cache, not the tool.
- "Ease of use". Subjective; the matrix above is the closest objective proxy.

## Failure modes recorded

A scenario reports `ok=0` when:

- The command exits non-zero.
- The expected resource (site config, backup file, running container) doesn't exist after the command.
- A follow-up `nginx -t` fails.

We don't time failures — `wall_seconds` is set to the wall clock until the failure was detected, but the row is excluded from medians.

## Caveats and biases

This benchmark is run **by the EasyNginx maintainer**. To minimise bias:

- Every command for every tool is in `scripts/targets/<tool>.sh`. PRs to fix incorrect upstream usage are welcome and will be re-run before merge.
- We use each tool's documented "happy path" — no flags or tweaks that aren't in the upstream's quick-start.
- The matrix above lists what each tool does *better*, not just where EasyNginx wins.

## Reproducing on your hardware

```bash
git clone https://github.com/nerkoux/EasyNGINX
cd EasyNGINX/bench
./run.sh
cat results/*/summary.md
```

Open an issue with your `summary.md` if you see results meaningfully different from those published here.
