"""Update commands: check, install, rollback, snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from commands import EasyNginxError
from config import Config
from ui import Console
from updater import (
    UpdateInfo,
    check_for_update,
    is_newer,
    list_snapshots,
    perform_update,
    rollback_last_update,
)
from version import __version__


def _human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(n)
    for u in units:
        if size < 1024 or u == units[-1]:
            return f"{size:.1f} {u}"
        size /= 1024
    return f"{size:.1f} GB"


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace, console: Console) -> int:
    info = check_for_update(force=True)
    if getattr(args, "json", False):
        payload = info.to_dict()
        payload["installed_version"] = __version__
        payload["update_available"] = info.has_update
        print(json.dumps(payload, indent=2))
        return 0 if not info.has_update else 1

    console.header("EasyNginx update check")
    print(f"  installed   : {__version__}")
    if not info.latest_version:
        console.warn("Could not reach GitHub. Check network connectivity.")
        console.hint("Set EASYNGINX_NO_UPDATE_CHECK=1 to silence the daily check.")
        return 2

    print(f"  latest      : {info.latest_version}")
    print(f"  source      : {info.source}")
    print(f"  checked     : {info.checked_at}")
    if info.release_url:
        print(f"  details     : {info.release_url}")

    if info.has_update:
        console.warn(f"An update is available: {__version__} -> {info.latest_version}")
        if info.release_notes:
            console.header("Release notes (excerpt)")
            for line in info.release_notes.splitlines()[:25]:
                console.hint(line)
            if len(info.release_notes.splitlines()) > 25:
                console.hint("... (truncated)")
        console.info("Install with:  sudo easynginx update install")
        return 1
    if is_newer(__version__, info.latest_version):
        console.ok(f"You're ahead of the latest release ({__version__} > "
                   f"{info.latest_version}). Probably running from main.")
    else:
        console.ok("You're up to date.")
    return 0


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace, console: Console) -> int:
    info = check_for_update(force=True)
    target = getattr(args, "target", None)

    console.header("EasyNginx update install")
    print(f"  installed   : {__version__}")
    if info.latest_version:
        print(f"  latest      : {info.latest_version}")
        if info.release_url:
            print(f"  details     : {info.release_url}")
    if target:
        print(f"  target ref  : {target}")

    if not args.force and not target and not info.has_update:
        console.ok("Already on the latest version. Nothing to do.")
        console.hint("Use --force to reinstall, or --target <ref> to install a specific version.")
        return 0

    if not args.yes:
        if not console.confirm(
            "Proceed with update? Engine files will be replaced atomically; "
            "your nginx configs and certs will not be touched.",
            default=True,
        ):
            console.warn("Update cancelled.")
            return 0

    console.info("Downloading and verifying engine files...")
    try:
        result = perform_update(target=target, force=args.force or bool(target))
    except RuntimeError as exc:
        raise EasyNginxError(str(exc)) from exc

    if result.from_version == result.to_version and not result.files_updated:
        console.ok("No changes applied.")
        return 0

    console.ok(f"Updated {result.from_version} -> {result.to_version}")
    if result.snapshot_path:
        size = result.snapshot_path.stat().st_size if result.snapshot_path.exists() else 0
        console.hint(f"snapshot : {result.snapshot_path}  ({_human_size(size)})")
    console.hint(f"files    : {len(result.files_updated)}")
    console.info("Roll back any time with:  sudo easynginx update rollback")
    return 0


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------

def cmd_rollback(args: argparse.Namespace, console: Console) -> int:
    console.header("Rolling back to previous engine snapshot")
    try:
        snap = rollback_last_update()
    except RuntimeError as exc:
        raise EasyNginxError(str(exc)) from exc
    console.ok(f"Restored from {snap}")
    console.hint("If you want to roll back further, extract an older snapshot manually:")
    console.hint("  sudo easynginx update snapshots")
    return 0


# ---------------------------------------------------------------------------
# snapshots
# ---------------------------------------------------------------------------

def cmd_snapshots(args: argparse.Namespace, console: Console) -> int:
    snaps = list_snapshots()
    if not snaps:
        console.info("No update snapshots found.")
        return 0
    console.header("Update snapshots (newest first)")
    for snap in snaps:
        size = snap.stat().st_size if snap.exists() else 0
        print(f"  {snap.name}    {_human_size(size)}")
        console.hint(str(snap))
    console.hint("Most recent is restored by:  sudo easynginx update rollback")
    return 0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "update_action", None) or "check"
    if action == "check":
        return cmd_check(args, console)
    if action == "install":
        return cmd_install(args, console)
    if action == "rollback":
        return cmd_rollback(args, console)
    if action == "snapshots":
        return cmd_snapshots(args, console)
    raise EasyNginxError(f"Unknown update action: {action}")
