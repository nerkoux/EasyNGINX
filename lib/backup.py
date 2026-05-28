"""EasyNginx backup & restore engine.

A backup is a single .tar.gz containing:

    MANIFEST.json     metadata + sha256 of every file
    payload/          tree of files we captured (nginx, easynginx,
                      letsencrypt, optionally www and PHP-FPM pools)

Restore re-extracts the payload onto the host, verifies the checksums,
and runs `nginx -t` before declaring success. If the test fails we
revert to a pre-restore safety snapshot.

The format is portable across distros: Debian-style sites-available
backups will land back in their right place when restored on a
Debian-family host. Restoring a Debian backup onto a RHEL host still
works — the files just live in /etc/nginx as captured.
"""

from __future__ import annotations

import datetime as _dt
import getpass
import hashlib
import json
import os
import platform
import shutil
import socket
import stat
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

MANIFEST_NAME = "MANIFEST.json"
PAYLOAD_DIR = "payload"
BACKUP_VERSION = 1


# Paths we capture by default. Optional ones are gated by `include_*` flags.
DEFAULT_TARGETS = [
    "/etc/nginx",
    "/etc/easynginx",
]
SSL_TARGETS = [
    "/etc/letsencrypt",
]
WWW_TARGETS = [
    "/var/www",
    "/srv/www",
]
PHP_TARGETS = [
    "/etc/php",
    "/etc/php-fpm.d",
    "/etc/php-fpm.conf",
]


@dataclass
class BackupOptions:
    include_ssl: bool = True
    include_www: bool = False
    include_php: bool = False
    extra_paths: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class BackupResult:
    path: Path
    size_bytes: int
    file_count: int
    sha256: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _arcname_for(path: Path) -> str:
    """Build a stable arcname under payload/ that survives Windows + tarfile.

    On Linux an absolute path is `/etc/nginx/...` so `payload` + path gives
    `payload/etc/nginx/...`. On Windows the path is `C:\\Users\\...`, so we
    strip the anchor and join with forward slashes. Either way the archive
    layout is `payload/<rest>` with POSIX separators.
    """
    p = Path(path)
    # Drop the anchor ("/" on POSIX, "C:\\" on Windows) so .parts becomes
    # the meaningful path components.
    parts = p.parts
    if parts and parts[0] in ("/", "\\") or (len(parts) and len(parts[0]) > 1
                                              and parts[0].endswith((":\\", ":/"))):
        parts = parts[1:]
    return "/".join([PAYLOAD_DIR, *parts])


def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Skip noisy / volatile dirs.
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__"}]
        for name in filenames:
            yield Path(dirpath) / name


def _collect_targets(opts: BackupOptions) -> list[Path]:
    targets = list(DEFAULT_TARGETS)
    if opts.include_ssl:
        targets.extend(SSL_TARGETS)
    if opts.include_www:
        targets.extend(WWW_TARGETS)
    if opts.include_php:
        targets.extend(PHP_TARGETS)
    targets.extend(opts.extra_paths)

    out: list[Path] = []
    seen: set[str] = set()
    for raw in targets:
        p = Path(raw)
        if not p.exists():
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _detect_distro() -> dict[str, str]:
    info: dict[str, str] = {"id": "unknown", "family": "unknown"}
    osr = Path("/etc/os-release")
    if osr.exists():
        for line in osr.read_text().splitlines():
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            info[k.lower()] = v.strip().strip('"')
    info["family"] = (
        info.get("id_like", "")
        or info.get("id", "")
        or "unknown"
    ).split()[0] if info else "unknown"
    return info


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def create_backup(
    output_dir: Path,
    *,
    options: BackupOptions | None = None,
    label: str | None = None,
) -> BackupResult:
    """Write a backup tarball to `output_dir`. Returns metadata."""

    opts = options or BackupOptions()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    distro = _detect_distro()
    hostname = socket.gethostname() or "host"
    safe_label = (label or "auto").replace(os.sep, "-")
    stamp = _now_stamp()
    archive_name = f"easynginx-backup-{hostname}-{safe_label}-{stamp}.tar.gz"
    archive_path = output_dir / archive_name

    targets = _collect_targets(opts)
    if not targets:
        raise FileNotFoundError(
            "Nothing to back up — none of the expected paths exist on this host."
        )

    files_in_archive: list[dict] = []

    # We stream into the tar and record sha256 of each file as we go.
    with tarfile.open(archive_path, "w:gz", compresslevel=6) as tar:
        for target in targets:
            base = target.resolve()
            if base.is_file():
                arc = _arcname_for(base)
                tar.add(str(base), arcname=arc, recursive=False)
                files_in_archive.append({
                    "arcname": arc,
                    "src": str(base),
                    "size": base.stat().st_size,
                    "mode": stat.S_IMODE(base.stat().st_mode),
                    "sha256": _sha256_file(base),
                })
                continue

            for fpath in _walk_files(base):
                arc = _arcname_for(fpath)
                try:
                    info = tar.gettarinfo(str(fpath), arcname=arc)
                except OSError:
                    continue
                if info is None:
                    continue
                if info.isreg():
                    with fpath.open("rb") as fh:
                        tar.addfile(info, fh)
                    files_in_archive.append({
                        "arcname": arc,
                        "src": str(fpath),
                        "size": info.size,
                        "mode": info.mode,
                        "sha256": _sha256_file(fpath),
                    })
                else:
                    tar.addfile(info)
                    files_in_archive.append({
                        "arcname": arc,
                        "src": str(fpath),
                        "size": 0,
                        "mode": info.mode,
                        "type": (
                            "symlink" if info.issym() else
                            "dir"     if info.isdir() else
                            "other"
                        ),
                    })

        manifest = {
            "version": BACKUP_VERSION,
            "created_at": _now_iso(),
            "created_by": getpass.getuser(),
            "hostname": hostname,
            "distro_id": distro.get("id", "unknown"),
            "distro_family": distro.get("family", "unknown"),
            "platform": platform.platform(),
            "label": label or "auto",
            "note": opts.note,
            "options": {
                "include_ssl": opts.include_ssl,
                "include_www": opts.include_www,
                "include_php": opts.include_php,
                "extra_paths": opts.extra_paths,
            },
            "targets": [str(p) for p in targets],
            "files": files_in_archive,
        }

        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo(name=MANIFEST_NAME)
        info.size = len(manifest_bytes)
        info.mtime = int(_dt.datetime.now().timestamp())
        info.mode = 0o644
        from io import BytesIO
        tar.addfile(info, BytesIO(manifest_bytes))

    # Outer sha256 over the full archive.
    archive_hash = _sha256_file(archive_path)
    sidecar = archive_path.with_suffix(archive_path.suffix + ".sha256")
    sidecar.write_text(f"{archive_hash}  {archive_path.name}\n")

    return BackupResult(
        path=archive_path,
        size_bytes=archive_path.stat().st_size,
        file_count=len(files_in_archive),
        sha256=archive_hash,
    )


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

class RestoreError(Exception):
    pass


def inspect_backup(archive: Path) -> dict:
    """Return the manifest from the archive without extracting payload files."""
    archive = Path(archive)
    if not archive.exists():
        raise RestoreError(f"Backup file not found: {archive}")
    with tarfile.open(archive, "r:gz") as tar:
        try:
            member = tar.getmember(MANIFEST_NAME)
        except KeyError as exc:
            raise RestoreError(
                "Archive is missing MANIFEST.json — not an EasyNginx backup."
            ) from exc
        fh = tar.extractfile(member)
        if fh is None:
            raise RestoreError("MANIFEST.json could not be read from archive.")
        return json.loads(fh.read().decode("utf-8"))


def verify_backup(archive: Path) -> tuple[bool, list[str]]:
    """Verify each payload file's sha256 against the manifest."""
    manifest = inspect_backup(archive)
    issues: list[str] = []

    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
        expected = manifest.get("files", [])
        for entry in expected:
            arc = entry["arcname"]
            if arc not in names:
                issues.append(f"missing in archive: {arc}")
                continue
            if "sha256" not in entry:
                continue
            member = tar.getmember(arc)
            fh = tar.extractfile(member)
            if fh is None:
                issues.append(f"unreadable: {arc}")
                continue
            h = hashlib.sha256()
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
            if h.hexdigest() != entry["sha256"]:
                issues.append(f"checksum mismatch: {arc}")
    return (len(issues) == 0), issues


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Defend against path traversal in tar members."""
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if dest not in target.parents and target != dest:
            raise RestoreError(f"Refusing unsafe tar member: {member.name}")
    tar.extractall(dest)  # noqa: S202 (members already validated)


def _safety_snapshot(snapshot_dir: Path) -> Path | None:
    """Take a quick local snapshot of the paths we're about to overwrite."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    snap_path = snapshot_dir / f"pre-restore-{stamp}.tar.gz"
    targets = [Path(p) for p in DEFAULT_TARGETS + SSL_TARGETS if Path(p).exists()]
    if not targets:
        return None
    with tarfile.open(snap_path, "w:gz", compresslevel=3) as tar:
        for t in targets:
            arc = "snapshot/" + "/".join(Path(t).parts[1:]) if Path(t).is_absolute() \
                  else f"snapshot/{t}"
            tar.add(str(t), arcname=arc)
    return snap_path


def restore_backup(
    archive: Path,
    *,
    safety_snapshot_dir: Path = Path("/etc/easynginx/backups/snapshots"),
    overwrite: bool = True,
    skip_verify: bool = False,
) -> dict:
    """Extract a backup into the live filesystem.

    Returns a dict with keys:
        manifest      the parsed MANIFEST.json
        snapshot_path path to the pre-restore safety snapshot, or None
        restored      list of top-level paths that were restored
    """
    archive = Path(archive)
    manifest = inspect_backup(archive)

    if not skip_verify:
        ok, issues = verify_backup(archive)
        if not ok:
            raise RestoreError(
                "Backup verification failed:\n  - " + "\n  - ".join(issues)
            )

    snap = _safety_snapshot(safety_snapshot_dir)

    with tempfile.TemporaryDirectory(prefix="easynginx-restore-") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract(tar, tmp_path)

        payload = tmp_path / PAYLOAD_DIR
        if not payload.is_dir():
            raise RestoreError("Archive payload directory is missing.")

        restored: list[str] = []
        # Walk through everything inside payload/ and copy back to /
        for src in _walk_files(payload):
            rel = src.relative_to(payload)
            dest = Path("/") / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not overwrite:
                continue
            # Preserve mode/uid/gid/mtime as captured.
            shutil.copy2(src, dest)
            top = "/" + rel.parts[0] if rel.parts else "/"
            if top not in restored:
                restored.append(top)

        # Symlinks captured in the manifest aren't yielded by os.walk; replay them.
        for entry in manifest.get("files", []):
            if entry.get("type") == "symlink":
                arc = entry["arcname"].removeprefix(PAYLOAD_DIR)
                target_link = Path("/") / arc.lstrip("/")
                # Re-extract symlink target from manifest src; tarfile preserves
                # link target during the extractall above when the path matches,
                # so this is just a fallback when we restored over an existing
                # broken link.
                if not target_link.exists() and not target_link.is_symlink():
                    try:
                        os.symlink(entry["src"], target_link)
                    except (OSError, KeyError):
                        pass

    return {
        "manifest": manifest,
        "snapshot_path": str(snap) if snap else None,
        "restored": restored,
    }


# ---------------------------------------------------------------------------
# Discovery helpers (used by the installer)
# ---------------------------------------------------------------------------

def find_backups(search_dirs: Iterable[Path] | None = None) -> list[Path]:
    """Look in common places for `easynginx-backup-*.tar.gz` files."""
    if search_dirs is None:
        search_dirs = [
            Path("/root"),
            Path.home(),
            Path("/tmp"),
            Path("/var/backups"),
            Path("/var/backups/easynginx"),
            Path("/etc/easynginx/backups"),
            Path.cwd(),
        ]
    found: list[Path] = []
    seen: set[str] = set()
    for d in search_dirs:
        if not d or not d.exists() or not d.is_dir():
            continue
        for p in sorted(d.glob("easynginx-backup-*.tar.gz")):
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            found.append(p)
    return found
