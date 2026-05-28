"""Helper called from install.sh to perform an early restore.

Usage:
    python3 bootstrap_restore.py find
    python3 bootstrap_restore.py restore <archive>

The installer uses `find` to enumerate available backups and `restore`
to extract one before the rest of EasyNginx is laid down. We keep this
file deliberately lightweight so it works even if the share dir hasn't
been populated yet (it only depends on `backup.py`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup as backup_mod  # noqa: E402


def _print_human(found: list[Path]) -> None:
    for i, path in enumerate(found, 1):
        try:
            mf = backup_mod.inspect_backup(path)
            print(f"{i}\t{path}\t{mf.get('created_at', '?')}"
                  f"\t{mf.get('hostname', '?')}\t{mf.get('label', '')}")
        except backup_mod.RestoreError:
            print(f"{i}\t{path}\t-\t-\t(unreadable)")


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: bootstrap_restore.py find|restore [args]", file=sys.stderr)
        return 2

    cmd = argv[0]

    if cmd == "find":
        found = backup_mod.find_backups()
        if "--json" in argv:
            data = []
            for path in found:
                try:
                    mf = backup_mod.inspect_backup(path)
                except backup_mod.RestoreError:
                    mf = {}
                data.append({
                    "path": str(path),
                    "created_at": mf.get("created_at"),
                    "hostname": mf.get("hostname"),
                    "label": mf.get("label"),
                    "distro_family": mf.get("distro_family"),
                })
            print(json.dumps(data, indent=2))
        else:
            _print_human(found)
        return 0

    if cmd == "restore":
        if len(argv) < 2:
            print("usage: bootstrap_restore.py restore <archive>", file=sys.stderr)
            return 2
        archive = Path(argv[1])
        if not archive.exists():
            print(f"Archive not found: {archive}", file=sys.stderr)
            return 1
        try:
            result = backup_mod.restore_backup(
                archive,
                safety_snapshot_dir=Path("/etc/easynginx/backups/snapshots"),
                overwrite=True,
                skip_verify=False,
            )
        except backup_mod.RestoreError as exc:
            print(f"Restore failed: {exc}", file=sys.stderr)
            return 1
        print(f"Restored from {archive}")
        if result.get("snapshot_path"):
            print(f"Safety snapshot: {result['snapshot_path']}")
        return 0

    if cmd == "inspect":
        if len(argv) < 2:
            return 2
        try:
            mf = backup_mod.inspect_backup(Path(argv[1]))
        except backup_mod.RestoreError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(mf, indent=2))
        return 0

    print(f"Unknown subcommand: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
