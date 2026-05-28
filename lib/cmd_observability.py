"""Observability commands: metrics, stats, healthz."""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from collections import Counter
from pathlib import Path

import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from helpers import parse_logs_in_config, site_log_paths
from ui import Console


METRICS_CONF = Path("/etc/nginx/conf.d/easynginx-metrics.conf")
METRICS_BODY = """\
# EasyNginx — local metrics endpoint
server {
    listen 127.0.0.1:9080;
    server_name 127.0.0.1;

    location /stub_status {
        stub_status;
        allow 127.0.0.1;
        allow ::1;
        deny all;
    }
}
"""


def cmd_metrics(state: str, cfg: Config, console: Console) -> int:
    if state == "status":
        if METRICS_CONF.exists():
            console.ok(f"Enabled at http://127.0.0.1:9080/stub_status ({METRICS_CONF})")
        else:
            console.info("Disabled.")
        return 0
    if state == "enable":
        METRICS_CONF.write_text(METRICS_BODY, encoding="utf-8")
        ok, output = v.nginx_test()
        if not ok:
            METRICS_CONF.unlink(missing_ok=True)  # type: ignore[arg-type]
            raise EasyNginxError(f"nginx -t failed: {output}")
        nginx_mod.reload_nginx()
        console.ok("Metrics enabled at http://127.0.0.1:9080/stub_status")
        return 0
    if state == "disable":
        if METRICS_CONF.exists():
            METRICS_CONF.unlink()
        nginx_mod.reload_nginx()
        console.ok("Metrics disabled.")
        return 0
    return 0


# ---------------------------------------------------------------------------
# stats — quick analyzer over an access log
# ---------------------------------------------------------------------------

# Combined log format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent ...
LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d+) (?P<bytes>\d+|-)'
    r'(?: "[^"]*" "[^"]*")?'
    r'(?: (?P<rt>\d+\.\d+))?'
)


def _parse_log(path: Path, since: _dt.datetime) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = LOG_RE.match(line)
                if not m:
                    continue
                try:
                    when = _dt.datetime.strptime(
                        m.group("time").split()[0], "%d/%b/%Y:%H:%M:%S"
                    )
                except ValueError:
                    continue
                if when < since:
                    continue
                rows.append({
                    "ip": m.group("ip"),
                    "path": m.group("path"),
                    "status": int(m.group("status")),
                    "rt": float(m.group("rt") or 0.0),
                })
    except OSError:
        return []
    return rows


def cmd_stats(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config for {args.domain}.")

    text = files.available.read_text(errors="ignore")
    cfg_access, _ = parse_logs_in_config(text)
    default_access, _ = site_log_paths(args.domain)
    log_path = Path(cfg_access or default_access)

    since = _dt.datetime.utcnow() - _dt.timedelta(hours=args.hours)
    rows = _parse_log(log_path, since)

    console.header(f"Stats for {args.domain} (last {args.hours}h)")
    print(f"  log file : {log_path}")
    print(f"  requests : {len(rows)}")
    if not rows:
        if not log_path.exists():
            console.warn("Log file does not exist yet.")
        else:
            console.hint("No requests in this window. nginx may write to a different log.")
        return 0

    # Status code breakdown
    statuses = Counter(r["status"] for r in rows)
    print("  statuses :")
    for status, count in sorted(statuses.items()):
        print(f"    {status}: {count}")

    # Top IPs
    ips = Counter(r["ip"] for r in rows).most_common(10)
    print("  top IPs  :")
    for ip, count in ips:
        print(f"    {count:6}  {ip}")

    # Top paths
    paths = Counter(r["path"] for r in rows).most_common(10)
    print("  top paths:")
    for p, count in paths:
        print(f"    {count:6}  {p}")

    # Slowest URLs (only if request_time was logged)
    timed = [r for r in rows if r["rt"] > 0]
    if timed:
        timed.sort(key=lambda r: r["rt"], reverse=True)
        print("  slowest  :")
        for r in timed[:10]:
            print(f"    {r['rt']:6.2f}s  {r['path']}")
    return 0


# ---------------------------------------------------------------------------
# /healthz endpoint
# ---------------------------------------------------------------------------

def cmd_healthz(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config for {args.domain}.")

    text = files.available.read_text()
    marker = "# >>> easynginx-healthz"
    end = "# <<< easynginx-healthz"
    block_re = re.compile(rf"{re.escape(marker)}.*?{re.escape(end)}\n?", re.DOTALL)
    text = block_re.sub("", text)

    if args.state == "on":
        if args.upstream:
            block = (
                f"\n    {marker}\n"
                f"    location = /healthz {{\n"
                f"        access_log off;\n"
                f"        proxy_pass {args.upstream};\n"
                f"        proxy_connect_timeout 2s;\n"
                f"        proxy_read_timeout 5s;\n"
                f"    }}\n"
                f"    {end}\n"
            )
        else:
            block = (
                f"\n    {marker}\n"
                f"    location = /healthz {{\n"
                f"        access_log off;\n"
                f"        return 200 \"ok\\n\";\n"
                f"        add_header Content-Type text/plain;\n"
                f"    }}\n"
                f"    {end}\n"
            )
        idx = text.find("location /")
        if idx == -1:
            idx = text.rfind("}")
        text = text[:idx] + block + text[idx:]

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"/healthz {args.state} for {args.domain}.")
    return 0
