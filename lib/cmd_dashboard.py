"""Local web dashboard.

A small stdlib-only HTTP server bound to 127.0.0.1 by default. Token-gated
read-only access to the EasyNginx engine. The server is launched as a
detached subprocess so the CLI can return immediately; the actual handler
lives in `dashboard_server.py`.
"""

from __future__ import annotations

import argparse
import os
import secrets
import signal
import subprocess
import sys
from pathlib import Path

from commands import EasyNginxError
from config import Config
from helpers import systemctl
from ui import Console


PID_FILE = Path("/run/easynginx-dashboard.pid")
TOKEN_FILE = Path("/etc/easynginx/dashboard-token")
SERVICE_NAME = "easynginx-dashboard"


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_running() -> bool:
    pid = _read_pid()
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _ensure_token() -> str:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return token


def _start(cfg: Config, console: Console) -> int:
    if _is_running():
        console.warn("Dashboard already running.")
        return 0
    token = _ensure_token()
    server_path = cfg.share_dir / "lib" / "dashboard_server.py"
    if not server_path.exists():
        raise EasyNginxError(f"Server module missing: {server_path}")

    env = os.environ.copy()
    env["EASYNGINX_DASH_TOKEN"] = token
    env["EASYNGINX_SHARE"] = str(cfg.share_dir)
    log = open("/var/log/easynginx/dashboard.log", "a", buffering=1)
    proc = subprocess.Popen(
        [sys.executable, str(server_path)],
        env=env, stdout=log, stderr=log, start_new_session=True,
    )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))
    console.ok(f"Dashboard started on http://127.0.0.1:9088 (pid {proc.pid}).")
    console.hint(f"Token: {token}")
    console.hint("Use header `X-EasyNginx-Token: <token>` or query param `?token=<token>`.")
    return 0


def _stop(console: Console) -> int:
    pid = _read_pid()
    if not pid:
        console.info("Dashboard is not running.")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        console.warn(f"Could not signal pid {pid}: {exc}")
    PID_FILE.unlink(missing_ok=True)  # type: ignore[arg-type]
    console.ok("Dashboard stopped.")
    return 0


def _status(console: Console) -> int:
    if _is_running():
        console.ok(f"Running (pid {_read_pid()}) on http://127.0.0.1:9088")
        return 0
    console.info("Dashboard is not running.")
    return 1


def _enable(cfg: Config, console: Console) -> int:
    """Install a systemd unit so the dashboard survives reboots."""
    unit = f"""\
[Unit]
Description=EasyNginx Dashboard
After=network.target

[Service]
Type=simple
Environment=EASYNGINX_SHARE={cfg.share_dir}
EnvironmentFile=/etc/easynginx/dashboard.env
ExecStart={sys.executable} {cfg.share_dir}/lib/dashboard_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    Path(f"/etc/systemd/system/{SERVICE_NAME}.service").write_text(unit, encoding="utf-8")

    token = _ensure_token()
    Path("/etc/easynginx/dashboard.env").write_text(
        f"EASYNGINX_DASH_TOKEN={token}\n", encoding="utf-8"
    )
    systemctl("daemon-reload")
    systemctl("enable", "--now", SERVICE_NAME)
    console.ok(f"Dashboard enabled as systemd service ({SERVICE_NAME}).")
    return 0


def _disable(console: Console) -> int:
    systemctl("disable", "--now", SERVICE_NAME)
    Path(f"/etc/systemd/system/{SERVICE_NAME}.service").unlink(missing_ok=True)  # type: ignore[arg-type]
    systemctl("daemon-reload")
    console.ok("Dashboard service disabled.")
    return 0


def _show_token(console: Console) -> int:
    token = _ensure_token()
    print(token)
    return 0


def dispatch(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = args.action
    if action == "start":   return _start(cfg, console)
    if action == "stop":    return _stop(console)
    if action == "status":  return _status(console)
    if action == "enable":  return _enable(cfg, console)
    if action == "disable": return _disable(console)
    if action == "token":   return _show_token(console)
    return 1
