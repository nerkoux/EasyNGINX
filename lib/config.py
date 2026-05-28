"""Runtime configuration for EasyNginx.

The installer drops a JSON file at /etc/easynginx/config.json describing the
detected distro and tool choices. We load it here and expose helpful paths.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path(os.environ.get("EASYNGINX_CONFIG", "/etc/easynginx/config.json"))


@dataclass
class Paths:
    nginx_conf: Path
    sites_available: Path
    sites_enabled: Path
    backups: Path
    logs: Path
    templates: Path

    @property
    def uses_sites_available(self) -> bool:
        return self.sites_available != self.sites_enabled


@dataclass
class Config:
    distro_id: str
    distro_family: str
    package_manager: str
    firewall_tool: str
    share_dir: Path
    config_dir: Path
    log_dir: Path
    version: str
    paths: Paths


def _detect_nginx_paths(family: str, share_dir: Path, config_dir: Path,
                       log_dir: Path) -> Paths:
    """Return the right nginx layout for the distro family."""
    nginx_conf = Path("/etc/nginx")

    if family in ("debian", "arch"):
        sites_available = nginx_conf / "sites-available"
        sites_enabled = nginx_conf / "sites-enabled"
    else:
        # RHEL/Fedora/Alpine: single conf.d directory by default.
        sites_available = nginx_conf / "conf.d"
        sites_enabled = nginx_conf / "conf.d"

    return Paths(
        nginx_conf=nginx_conf,
        sites_available=sites_available,
        sites_enabled=sites_enabled,
        backups=config_dir / "backups",
        logs=log_dir,
        templates=share_dir / "templates",
    )


def load_config() -> Config:
    if not CONFIG_PATH.exists():
        # Allow running from a source checkout for development.
        dev_share = Path(__file__).resolve().parent.parent
        if (dev_share / "templates").is_dir():
            return Config(
                distro_id="dev",
                distro_family="debian",
                package_manager="apt-get",
                firewall_tool="none",
                share_dir=dev_share,
                config_dir=Path("/tmp/easynginx-dev"),
                log_dir=Path("/tmp/easynginx-dev/logs"),
                version="0.1.0-dev",
                paths=_detect_nginx_paths("debian", dev_share,
                                          Path("/tmp/easynginx-dev"),
                                          Path("/tmp/easynginx-dev/logs")),
            )
        raise FileNotFoundError(
            f"EasyNginx config not found at {CONFIG_PATH}. Re-run install.sh."
        )

    data = json.loads(CONFIG_PATH.read_text())
    share_dir = Path(data["share_dir"])
    config_dir = Path(data["config_dir"])
    log_dir = Path(data["log_dir"])
    family = data["distro_family"]

    return Config(
        distro_id=data["distro_id"],
        distro_family=family,
        package_manager=data["package_manager"],
        firewall_tool=data.get("firewall_tool", "none"),
        share_dir=share_dir,
        config_dir=config_dir,
        log_dir=log_dir,
        version=data.get("version", "0.0.0"),
        paths=_detect_nginx_paths(family, share_dir, config_dir, log_dir),
    )
