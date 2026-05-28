"""Thin wrapper around the certbot CLI.

We use the nginx authenticator+installer plugin so certbot edits the same
config we just wrote. EasyNginx prepares the server block, runs certbot in
non-interactive mode, then trusts certbot to add ssl_certificate directives.
"""

from __future__ import annotations

import shutil
import subprocess


def is_available() -> bool:
    return shutil.which("certbot") is not None


def issue(
    domain: str,
    email: str,
    *,
    staging: bool = False,
    redirect: bool = True,
) -> tuple[bool, str]:
    """Issue/install a cert for `domain`. Returns (ok, output)."""
    if not is_available():
        return False, "certbot is not installed."

    cmd = [
        "certbot", "--nginx",
        "-n",
        "--agree-tos",
        "--email", email,
        "-d", domain,
    ]
    cmd.append("--redirect" if redirect else "--no-redirect")
    if staging:
        cmd.append("--staging")

    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        return False, f"Failed to invoke certbot: {exc}"

    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def renew() -> tuple[bool, str]:
    if not is_available():
        return False, "certbot is not installed."
    proc = subprocess.run(
        ["certbot", "renew", "--quiet"],
        check=False, capture_output=True, text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()
