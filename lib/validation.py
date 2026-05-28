"""Input validation and environment checks for EasyNginx.

Everything here returns either a (True, "") tuple for ok or (False, reason).
The interactive prompts re-ask on failure; non-interactive runs surface the
reason directly to the user.
"""

from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse


# RFC 1035-ish domain regex (allows wildcards for SAN later).
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:\*\.)?"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}$",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Reserved names we never want to use for site files.
RESERVED_FILENAMES = {"default", "default.conf", "nginx.conf"}


def validate_domain(domain: str) -> tuple[bool, str]:
    if not domain:
        return False, "Domain is required."
    domain = domain.strip().rstrip(".")
    if len(domain) > 253:
        return False, "Domain is longer than 253 characters."
    if not _DOMAIN_RE.match(domain):
        return False, "Domain doesn't look like a valid hostname."
    if domain.lower() in RESERVED_FILENAMES:
        return False, f"'{domain}' is reserved."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    if not _EMAIL_RE.match(email or ""):
        return False, "That doesn't look like a valid email."
    return True, ""


def validate_url(value: str) -> tuple[bool, str]:
    if not value:
        return False, "URL is required."
    try:
        parsed = urlparse(value)
    except Exception as exc:  # noqa: BLE001
        return False, f"Could not parse URL: {exc}"
    if parsed.scheme not in ("http", "https"):
        return False, "URL must start with http:// or https://"
    if not parsed.hostname:
        return False, "URL is missing a host."
    if parsed.port is not None and not (1 <= parsed.port <= 65535):
        return False, "Port must be between 1 and 65535."
    return True, ""


def validate_path(value: str, must_exist: bool = False) -> tuple[bool, str]:
    if not value:
        return False, "Path is required."
    if not value.startswith("/"):
        return False, "Use an absolute path (starting with /)."
    if must_exist and not Path(value).exists():
        return False, f"Path {value} does not exist."
    return True, ""


def validate_upstream_list(value: str) -> tuple[bool, str]:
    items = [v.strip() for v in value.split(",") if v.strip()]
    if len(items) < 2:
        return False, "Provide at least two comma-separated upstream URLs."
    for item in items:
        ok, err = validate_url(item)
        if not ok:
            return False, f"{item}: {err}"
    return True, ""


# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------

def resolve_dns(domain: str) -> list[str]:
    """Return list of A/AAAA addresses for `domain`, empty on failure."""
    addrs: list[str] = []
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            infos = socket.getaddrinfo(domain, None, family)
            addrs.extend(sorted({info[4][0] for info in infos}))
        except socket.gaierror:
            continue
    return addrs


def public_addresses() -> list[str]:
    """Best-effort list of this host's outward-facing IPs."""
    out: set[str] = set()

    # UDP socket trick — picks the IP that would be used for outbound.
    for family, target in ((socket.AF_INET, ("8.8.8.8", 80)),
                           (socket.AF_INET6, ("2001:4860:4860::8888", 80))):
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as s:
                s.connect(target)
                out.add(s.getsockname()[0])
        except OSError:
            continue

    # Fall back to whatever the kernel knows.
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            try:
                ipaddress.ip_address(ip)
                out.add(ip)
            except ValueError:
                pass
    except socket.gaierror:
        pass

    return sorted(out)


def dns_points_here(domain: str) -> tuple[bool, list[str], list[str]]:
    """Return (matches, dns_addrs, local_addrs)."""
    dns = resolve_dns(domain)
    local = public_addresses()
    if not dns:
        return False, dns, local
    return any(addr in local for addr in dns), dns, local


def port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if a TCP listener answers on host:port."""
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except (OSError, socket.timeout):
        return False


def port_free(port: int) -> bool:
    """True if we can bind to 0.0.0.0:port — i.e. nobody is listening."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False


def upstream_reachable(url: str) -> bool:
    """TCP-only reachability check for an upstream URL."""
    parsed = urlparse(url)
    host = parsed.hostname
    if host is None:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except (OSError, socket.timeout):
        return False


def nginx_test() -> tuple[bool, str]:
    """Run `nginx -t` and return (ok, combined_output)."""
    if not shutil.which("nginx"):
        return False, "nginx binary not found on PATH."
    try:
        proc = subprocess.run(
            ["nginx", "-t"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, f"Could not run nginx -t: {exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()
