"""Firewall helpers.

The installer already opens 80/443; per-host calls here are best-effort
reminders so `easynginx create` can re-apply rules if the user has nuked them.
"""

from __future__ import annotations

import shutil
import subprocess


def open_http_https(tool: str) -> tuple[bool, str]:
    if tool == "ufw" and shutil.which("ufw"):
        out = []
        for rule in (["ufw", "allow", "80/tcp"], ["ufw", "allow", "443/tcp"]):
            r = subprocess.run(rule, check=False, capture_output=True, text=True)
            out.append(r.stdout + r.stderr)
        return True, "\n".join(out).strip()

    if tool == "firewalld" and shutil.which("firewall-cmd"):
        out = []
        for rule in (
            ["firewall-cmd", "--permanent", "--add-service=http"],
            ["firewall-cmd", "--permanent", "--add-service=https"],
            ["firewall-cmd", "--reload"],
        ):
            r = subprocess.run(rule, check=False, capture_output=True, text=True)
            out.append(r.stdout + r.stderr)
        return True, "\n".join(out).strip()

    return False, f"No supported firewall tool ({tool})."
