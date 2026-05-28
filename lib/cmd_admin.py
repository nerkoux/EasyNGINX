"""Admin commands: reload, restart, status, test, self-update, uninstall."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from helpers import systemctl
from ui import Console


# ---------------------------------------------------------------------------
# nginx friendlies
# ---------------------------------------------------------------------------

def cmd_reload(console: Console) -> int:
    ok, output = nginx_mod.reload_nginx()
    if ok:
        console.ok("nginx reloaded.")
        return 0
    console.error("nginx reload failed:")
    for line in output.splitlines():
        console.hint(line)
    return 1


def cmd_restart(console: Console) -> int:
    rc, out = systemctl("restart", "nginx")
    if rc == 0:
        console.ok("nginx restarted.")
        return 0
    console.error("nginx restart failed:")
    for line in out.splitlines():
        console.hint(line)
    return 1


def cmd_status(console: Console) -> int:
    rc, out = systemctl("status", "nginx", "--no-pager")
    if out:
        for line in out.splitlines():
            print(f"  {line}")
    return rc


def cmd_test(console: Console) -> int:
    ok, output = v.nginx_test()
    if ok:
        console.ok("nginx -t passed.")
        for line in output.splitlines():
            console.hint(line)
        return 0
    console.error("nginx -t failed:")
    for line in output.splitlines():
        console.hint(line)
    return 1


# ---------------------------------------------------------------------------
# self-update
# ---------------------------------------------------------------------------

UPDATE_API = "https://api.github.com/repos/nerkoux/EasyNGINX/releases/latest"
RAW_BASE   = "https://raw.githubusercontent.com/nerkoux/EasyNGINX"


# ---------------------------------------------------------------------------
# self-update — kept for back-compat only; main dispatches to cmd_update now.
# ---------------------------------------------------------------------------

UPDATE_API = "https://api.github.com/repos/nerkoux/EasyNGINX/releases/latest"
RAW_BASE   = "https://raw.githubusercontent.com/nerkoux/EasyNGINX"


def cmd_self_update(cfg: Config, console: Console) -> int:
    """Deprecated. Real implementation lives in cmd_update.py."""
    from cmd_update import cmd_install
    import argparse as _ap
    args = _ap.Namespace(target=None, force=False, yes=False)
    return cmd_install(args, console)


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

def cmd_uninstall(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    console.header("Uninstall EasyNginx")
    if not args.yes and not console.confirm(
        "This removes the easynginx CLI and engine. Continue?", default=False
    ):
        return 0

    paths_to_remove = [
        Path("/usr/local/bin/easynginx"),
        cfg.share_dir,
    ]
    if args.purge:
        paths_to_remove.append(cfg.config_dir)
        paths_to_remove.append(cfg.log_dir)
    else:
        console.hint("Configs and backups preserved at /etc/easynginx (use --purge to delete).")

    for p in paths_to_remove:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists() or p.is_symlink():
                p.unlink()
            console.ok(f"Removed {p}")
        except OSError as exc:
            console.warn(f"Could not remove {p}: {exc}")

    console.ok("EasyNginx removed. nginx itself was left installed and running.")
    return 0
