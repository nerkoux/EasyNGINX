"""Nginx file management: writing, enabling, disabling, removing sites.

The layout differs across distros:
  - Debian/Ubuntu/Arch: /etc/nginx/sites-available + /etc/nginx/sites-enabled
  - RHEL/Fedora/Alpine: /etc/nginx/conf.d (single dir; "disabled" = .disabled
    suffix)

This module hides those differences behind one API.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from config import Config


@dataclass
class SiteFiles:
    available: Path
    enabled: Path | None
    backup: Path


def _config_filename(domain: str) -> str:
    safe = domain.replace("/", "_")
    return f"{safe}.conf"


def site_paths(domain: str, cfg: Config) -> SiteFiles:
    fname = _config_filename(domain)
    available = cfg.paths.sites_available / fname
    enabled = (cfg.paths.sites_enabled / fname
               if cfg.paths.uses_sites_available else None)
    backup = cfg.paths.backups / f"{fname}.bak"
    return SiteFiles(available=available, enabled=enabled, backup=backup)


def list_sites(cfg: Config) -> list[dict]:
    """Return a list of {domain, path, enabled, has_ssl} dicts."""
    out: list[dict] = []
    seen: set[str] = set()
    base = cfg.paths.sites_available
    if not base.is_dir():
        return out

    for entry in sorted(base.iterdir()):
        if entry.is_dir():
            continue
        if entry.name in {"default", "default.conf"}:
            continue

        domain = entry.stem
        if entry.suffix == ".disabled":
            domain = entry.name[: -len(".disabled")]
            if domain.endswith(".conf"):
                domain = domain[: -len(".conf")]
        elif entry.suffix == ".conf":
            domain = entry.stem

        if domain in seen:
            continue
        seen.add(domain)

        if cfg.paths.uses_sites_available:
            enabled = (cfg.paths.sites_enabled / entry.name).is_symlink()
        else:
            enabled = entry.suffix == ".conf"

        text = ""
        try:
            text = entry.read_text(errors="ignore")
        except OSError:
            pass

        out.append({
            "domain": domain,
            "path": str(entry),
            "enabled": enabled,
            "has_ssl": "ssl_certificate" in text,
        })
    return out


def write_site(domain: str, content: str, cfg: Config) -> SiteFiles:
    """Write the site config and back up any prior version."""
    files = site_paths(domain, cfg)
    files.available.parent.mkdir(parents=True, exist_ok=True)
    files.backup.parent.mkdir(parents=True, exist_ok=True)

    if files.available.exists():
        shutil.copy2(files.available, files.backup)

    tmp = files.available.with_suffix(files.available.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, files.available)
    files.available.chmod(0o644)
    return files


def enable_site(domain: str, cfg: Config) -> None:
    files = site_paths(domain, cfg)

    if cfg.paths.uses_sites_available:
        if not files.available.exists():
            disabled = files.available.with_suffix(files.available.suffix + ".disabled")
            if disabled.exists():
                disabled.rename(files.available)
            else:
                raise FileNotFoundError(f"No config for {domain}.")
        cfg.paths.sites_enabled.mkdir(parents=True, exist_ok=True)
        link = cfg.paths.sites_enabled / files.available.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(files.available)
    else:
        disabled = files.available.with_suffix(files.available.suffix + ".disabled")
        if disabled.exists() and not files.available.exists():
            disabled.rename(files.available)


def disable_site(domain: str, cfg: Config) -> None:
    files = site_paths(domain, cfg)

    if cfg.paths.uses_sites_available:
        if files.enabled and (files.enabled.exists() or files.enabled.is_symlink()):
            files.enabled.unlink()
    else:
        if files.available.exists():
            disabled = files.available.with_suffix(files.available.suffix + ".disabled")
            if disabled.exists():
                disabled.unlink()
            files.available.rename(disabled)


def remove_site(domain: str, cfg: Config) -> None:
    files = site_paths(domain, cfg)
    disable_site(domain, cfg)

    for path in (files.available,
                 files.available.with_suffix(files.available.suffix + ".disabled")):
        if path.exists():
            path.unlink()


def restore_backup(domain: str, cfg: Config) -> bool:
    files = site_paths(domain, cfg)
    if not files.backup.exists():
        return False
    shutil.copy2(files.backup, files.available)
    return True


def reload_nginx() -> tuple[bool, str]:
    if shutil.which("systemctl"):
        proc = subprocess.run(
            ["systemctl", "reload", "nginx"],
            check=False, capture_output=True, text=True,
        )
        return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    if shutil.which("service"):
        proc = subprocess.run(
            ["service", "nginx", "reload"],
            check=False, capture_output=True, text=True,
        )
        return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    proc = subprocess.run(
        ["nginx", "-s", "reload"],
        check=False, capture_output=True, text=True,
    )
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
