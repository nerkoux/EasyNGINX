"""Shared helpers used across command modules."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def systemctl(*args: str, capture: bool = True) -> tuple[int, str]:
    """Run systemctl. Returns (returncode, combined_output)."""
    if not shutil.which("systemctl"):
        return 127, "systemctl not available on this system."
    proc = subprocess.run(
        ["systemctl", *args],
        check=False,
        capture_output=capture,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def run(cmd: list[str], *, check: bool = False) -> tuple[int, str]:
    proc = subprocess.run(cmd, check=check, capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def site_log_paths(domain: str) -> tuple[Path, Path]:
    """Return (access_log, error_log) for a domain following nginx defaults.

    Sites we generated don't set access/error_log directly, so they end up
    in the global /var/log/nginx/access.log + error.log. We surface those
    by default; if a site has overridden them in its own config block, the
    parser elsewhere catches it.
    """
    return Path("/var/log/nginx/access.log"), Path("/var/log/nginx/error.log")


def parse_logs_in_config(config_text: str) -> tuple[Optional[str], Optional[str]]:
    """Look for `access_log <path>` and `error_log <path>` inside a config."""
    access = None
    error = None
    for line in config_text.splitlines():
        s = line.strip()
        if s.startswith("access_log") and not s.startswith("access_log off"):
            parts = s.split()
            if len(parts) >= 2:
                access = parts[1].rstrip(";")
        elif s.startswith("error_log"):
            parts = s.split()
            if len(parts) >= 2:
                error = parts[1].rstrip(";")
    return access, error


_SERVER_NAME_RE = re.compile(r"^\s*server_name\s+([^;]+);", re.MULTILINE)
_PROXY_PASS_RE = re.compile(r"^\s*proxy_pass\s+([^;]+);", re.MULTILINE)
_LISTEN_RE = re.compile(r"^\s*listen\s+([^;]+);", re.MULTILINE)
_SSL_CERT_RE = re.compile(r"^\s*ssl_certificate\s+([^;]+);", re.MULTILINE)


def parse_site_summary(config_text: str) -> dict:
    """Best-effort parse of an nginx server block for `info`."""
    server_names: list[str] = []
    for m in _SERVER_NAME_RE.finditer(config_text):
        server_names.extend(m.group(1).split())
    listens = [m.group(1).strip() for m in _LISTEN_RE.finditer(config_text)]
    proxies = [m.group(1).strip() for m in _PROXY_PASS_RE.finditer(config_text)]
    cert = None
    cm = _SSL_CERT_RE.search(config_text)
    if cm:
        cert = cm.group(1).strip()

    type_hint = "static"
    if proxies:
        if "$easy_" in config_text and "Upgrade" in config_text:
            type_hint = "websocket"
        elif "upstream easy_" in config_text:
            type_hint = "load-balancer"
        else:
            type_hint = "reverse-proxy"
    elif "fastcgi_pass" in config_text:
        type_hint = "php"
    elif "return 301" in config_text and len(listens) <= 2:
        type_hint = "redirect"

    return {
        "server_names": sorted(set(server_names)),
        "listens": listens,
        "proxies": proxies,
        "ssl_cert": cert,
        "has_ssl": cert is not None or "ssl_certificate" in config_text,
        "type": type_hint,
    }


def open_in_editor(path: Path, editor: Optional[str]) -> int:
    """Open `path` in the user's editor and return the exit code."""
    chosen = editor
    if not chosen:
        for candidate in ("nano", "vim", "vi", "ed"):
            if shutil.which(candidate):
                chosen = candidate
                break
    if not chosen:
        raise RuntimeError(
            "No editor found. Set $EDITOR or install nano/vim."
        )
    proc = subprocess.run([chosen, str(path)])
    return proc.returncode


_CC_RE = re.compile(r"^[A-Za-z]{2}$")


def normalize_country_codes(spec: str) -> list[str]:
    out = []
    for raw in spec.split(","):
        code = raw.strip().upper()
        if not code:
            continue
        if not _CC_RE.match(code):
            raise ValueError(f"Invalid country code: {code!r}")
        out.append(code)
    return out
