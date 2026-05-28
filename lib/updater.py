"""Update system for EasyNginx.

Responsibilities split into three layers:

    check_for_update()       — non-blocking, cached (24h). Compares the
                                installed __version__ against the latest
                                tag on GitHub.
    perform_update()         — atomic update of engine files only. User
                                data, site configs, certs, and EasyNginx
                                state are NEVER touched.
    rollback_last_update()   — restore the previous engine from the
                                snapshot taken before the last update.

The on-disk cache lives at /etc/easynginx/version-cache.json:

    {
      "checked_at"     : "2026-05-28T15:00:00Z",
      "latest_version" : "0.3.1",
      "latest_tag"     : "v0.3.1",
      "release_url"    : "https://github.com/...",
      "release_notes"  : "...",
      "source"         : "release|tag|commit"
    }
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from version import (
    GITHUB_BRANCH,
    __version__,
    github_api_base,
    github_raw_base,
)

# ---------------------------------------------------------------------------
# Paths and tunables
# ---------------------------------------------------------------------------

CACHE_PATH = Path("/etc/easynginx/version-cache.json")
SHARE_DIR = Path("/usr/local/share/easynginx")
LIB_DIR = SHARE_DIR / "lib"
TEMPLATES_DIR = SHARE_DIR / "templates"
BIN_PATH = Path("/usr/local/bin/easynginx")
CONFIG_PATH = Path("/etc/easynginx/config.json")
SNAPSHOT_DIR = Path("/etc/easynginx/backups/updates")

CHECK_INTERVAL_SECONDS = 24 * 60 * 60   # one day
NETWORK_TIMEOUT = 8                      # seconds for any single HTTP call

USER_AGENT = f"easynginx/{__version__} (+https://github.com/nerkoux/EasyNGINX)"


# ---------------------------------------------------------------------------
# Files we own and may overwrite during an update.
# Anything not in this list is left alone, period.
# ---------------------------------------------------------------------------

ENGINE_FILES = [
    # CLI binary
    ("easynginx", BIN_PATH, 0o755),

    # Engine modules
    ("lib/main.py",                LIB_DIR / "main.py",                0o644),
    ("lib/commands.py",            LIB_DIR / "commands.py",            0o644),
    ("lib/cmd_site.py",            LIB_DIR / "cmd_site.py",            0o644),
    ("lib/cmd_admin.py",           LIB_DIR / "cmd_admin.py",           0o644),
    ("lib/cmd_cert.py",            LIB_DIR / "cmd_cert.py",            0o644),
    ("lib/cmd_security.py",        LIB_DIR / "cmd_security.py",        0o644),
    ("lib/cmd_observability.py",   LIB_DIR / "cmd_observability.py",   0o644),
    ("lib/cmd_preset.py",          LIB_DIR / "cmd_preset.py",          0o644),
    ("lib/cmd_cluster.py",         LIB_DIR / "cmd_cluster.py",         0o644),
    ("lib/cmd_dashboard.py",       LIB_DIR / "cmd_dashboard.py",       0o644),
    ("lib/dashboard_server.py",    LIB_DIR / "dashboard_server.py",    0o644),
    ("lib/backup.py",              LIB_DIR / "backup.py",              0o644),
    ("lib/bootstrap_restore.py",   LIB_DIR / "bootstrap_restore.py",   0o644),
    ("lib/certbot.py",             LIB_DIR / "certbot.py",             0o644),
    ("lib/config.py",              LIB_DIR / "config.py",              0o644),
    ("lib/firewall.py",            LIB_DIR / "firewall.py",            0o644),
    ("lib/helpers.py",             LIB_DIR / "helpers.py",             0o644),
    ("lib/nginx.py",               LIB_DIR / "nginx.py",               0o644),
    ("lib/templates.py",           LIB_DIR / "templates.py",           0o644),
    ("lib/ui.py",                  LIB_DIR / "ui.py",                  0o644),
    ("lib/updater.py",             LIB_DIR / "updater.py",             0o644),
    ("lib/validation.py",          LIB_DIR / "validation.py",          0o644),
    ("lib/version.py",             LIB_DIR / "version.py",             0o644),

    # Templates
    ("templates/reverse_proxy.conf", TEMPLATES_DIR / "reverse_proxy.conf", 0o644),
    ("templates/static_site.conf",   TEMPLATES_DIR / "static_site.conf",   0o644),
    ("templates/php_site.conf",      TEMPLATES_DIR / "php_site.conf",      0o644),
    ("templates/websocket.conf",     TEMPLATES_DIR / "websocket.conf",     0o644),
    ("templates/redirect.conf",      TEMPLATES_DIR / "redirect.conf",      0o644),
    ("templates/load_balancer.conf", TEMPLATES_DIR / "load_balancer.conf", 0o644),
    ("templates/maintenance.html",   TEMPLATES_DIR / "html_vendors" / "maintenance.html",   0o644),
    ("templates/error_404.html",     TEMPLATES_DIR / "html_vendors" / "error_404.html",     0o644),
    ("templates/error_5xx.html",     TEMPLATES_DIR / "html_vendors" / "error_5xx.html",     0o644),
]


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

def _normalize(v: str) -> str:
    return v.strip().lstrip("vV ")


def parse_version(value: str) -> tuple[int, ...]:
    """Lenient semantic-ish version parser.

    "v0.3.1"        -> (0, 3, 1)
    "0.3.1-rc.2"    -> (0, 3, 1)   (suffix ignored for comparison)
    "1.0"           -> (1, 0)
    Anything we can't parse becomes (0,) so it loses comparisons.
    """
    raw = _normalize(value).split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for chunk in raw.split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            break
    return tuple(parts) or (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    return parse_version(remote) > parse_version(local)


# ---------------------------------------------------------------------------
# Network primitives
# ---------------------------------------------------------------------------

def _http_get(url: str, *, timeout: int = NETWORK_TIMEOUT,
              accept: str = "application/json") -> bytes:
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
    })
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

@dataclass
class UpdateInfo:
    latest_version: str = ""
    latest_tag: str = ""
    release_url: str = ""
    release_notes: str = ""
    source: str = ""           # "release" | "tag" | "commit"
    checked_at: str = ""

    def to_dict(self) -> dict:
        return {
            "latest_version": self.latest_version,
            "latest_tag":     self.latest_tag,
            "release_url":    self.release_url,
            "release_notes":  self.release_notes,
            "source":         self.source,
            "checked_at":     self.checked_at,
        }

    @property
    def has_update(self) -> bool:
        return bool(self.latest_version) and is_newer(self.latest_version)


def _cache_load() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, ValueError):
        return None


def _cache_save(info: UpdateInfo) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(info.to_dict(), indent=2))
        try:
            CACHE_PATH.chmod(0o644)
        except OSError:
            pass
    except OSError:
        # If we can't write the cache (e.g. running as a non-root one-off),
        # silently fall back to no-cache mode. The check still works, it just
        # repeats every invocation.
        pass


def _cache_age_seconds(cache: dict) -> float:
    when = cache.get("checked_at", "")
    if not when:
        return float("inf")
    try:
        dt = _dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return float("inf")
    return (_dt.datetime.utcnow() - dt).total_seconds()


# ---------------------------------------------------------------------------
# Remote version probe
# ---------------------------------------------------------------------------

def _probe_remote() -> UpdateInfo:
    """Try, in order: latest release → latest tag → tip of branch."""
    info = UpdateInfo(checked_at=_dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

    # 1. Latest GitHub release.
    try:
        data = json.loads(_http_get(f"{github_api_base()}/releases/latest"))
        tag = data.get("tag_name") or ""
        version = _normalize(tag)
        if version:
            info.latest_version = version
            info.latest_tag = tag
            info.release_url = data.get("html_url", "")
            info.release_notes = (data.get("body") or "").strip()
            info.source = "release"
            return info
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        pass

    # 2. Latest tag.
    try:
        data = json.loads(_http_get(f"{github_api_base()}/tags?per_page=1"))
        if isinstance(data, list) and data:
            tag = data[0].get("name") or ""
            version = _normalize(tag)
            if version:
                info.latest_version = version
                info.latest_tag = tag
                info.release_url = f"https://github.com/nerkoux/EasyNGINX/releases/tag/{tag}"
                info.source = "tag"
                return info
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        pass

    # 3. version.py on the default branch (ungated, always works as long
    #    as raw.githubusercontent.com is reachable).
    try:
        body = _http_get(
            f"{github_raw_base(GITHUB_BRANCH)}/lib/version.py",
            accept="text/plain",
        ).decode("utf-8", "replace")
        for line in body.splitlines():
            if line.strip().startswith("__version__"):
                _, _, val = line.partition("=")
                version = _normalize(val.strip().strip('"').strip("'"))
                if version:
                    info.latest_version = version
                    info.latest_tag = GITHUB_BRANCH
                    info.release_url = (
                        f"https://github.com/nerkoux/EasyNGINX/commits/{GITHUB_BRANCH}"
                    )
                    info.source = "commit"
                    return info
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        pass

    return info


# ---------------------------------------------------------------------------
# Public check API
# ---------------------------------------------------------------------------

def check_for_update(*, force: bool = False) -> UpdateInfo:
    """Return cached UpdateInfo unless `force` is set or the cache is stale."""
    cache = _cache_load()
    if cache and not force and _cache_age_seconds(cache) < CHECK_INTERVAL_SECONDS:
        return UpdateInfo(
            latest_version=cache.get("latest_version", ""),
            latest_tag=cache.get("latest_tag", ""),
            release_url=cache.get("release_url", ""),
            release_notes=cache.get("release_notes", ""),
            source=cache.get("source", ""),
            checked_at=cache.get("checked_at", ""),
        )
    info = _probe_remote()
    if info.latest_version:
        _cache_save(info)
    return info


def maybe_print_update_banner(stream=sys.stderr) -> None:
    """Print a one-line update notice if the cache says there's a newer version.

    This is called near the start of every CLI invocation. It only reads the
    cache file. Network refresh happens in a detached background process, so
    no command ever blocks waiting for GitHub.
    """
    if os.environ.get("EASYNGINX_NO_UPDATE_CHECK") == "1":
        return

    cache = _cache_load()

    # Schedule an async refresh if the cache is missing or stale.
    if not cache or _cache_age_seconds(cache) >= CHECK_INTERVAL_SECONDS:
        _spawn_background_refresh()

    if not cache:
        return
    latest = cache.get("latest_version") or ""
    if not latest or not is_newer(latest):
        return

    # Render the banner. Keep it short — it shows on every command.
    is_tty = stream.isatty()
    if is_tty:
        msg = (
            f"\033[33m[easynginx]\033[0m Update available: "
            f"\033[1m{__version__}\033[0m → \033[1m\033[32m{latest}\033[0m  "
            f"(run \033[1measynginx update\033[0m to install)\n"
        )
    else:
        msg = (
            f"[easynginx] Update available: {__version__} -> {latest}  "
            f"(run: easynginx update)\n"
        )
    try:
        stream.write(msg)
    except (BrokenPipeError, OSError):
        pass


def _spawn_background_refresh() -> None:
    """Fire-and-forget: refresh the cache in a detached subprocess."""
    if os.environ.get("EASYNGINX_NO_UPDATE_CHECK") == "1":
        return
    try:
        subprocess.Popen(  # noqa: S603
            [sys.executable, "-c",
             "import sys, pathlib; sys.path.insert(0, str(pathlib.Path('"
             + str(LIB_DIR) + "'))); "
             "import updater; updater.check_for_update(force=True)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        # Refresh-on-best-effort; if we can't fork (e.g. inside a tightly
        # sandboxed container), just skip.
        pass


# ---------------------------------------------------------------------------
# Update install
# ---------------------------------------------------------------------------

@dataclass
class UpdateResult:
    from_version: str
    to_version: str
    snapshot_path: Path | None
    files_updated: list[str] = field(default_factory=list)


def _resolve_target_ref(target: str | None, info: UpdateInfo) -> str:
    """Decide which git ref to download from."""
    if target:
        return target
    if info.latest_tag:
        return info.latest_tag
    return GITHUB_BRANCH


def _stage_engine(ref: str, dest: Path) -> list[str]:
    """Download every engine file into `dest`. Returns relative paths fetched."""
    base = github_raw_base(ref)
    fetched: list[str] = []
    for rel, _, _ in ENGINE_FILES:
        url = f"{base}/{rel}"
        try:
            data = _http_get(url, accept="text/plain")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # Some files may not exist in older refs; that's fine. But
            # everything in the current ref must download or we abort.
            raise RuntimeError(f"Could not download {url}: {exc}") from exc
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        fetched.append(rel)
    return fetched


def _python_compiles(staging: Path) -> tuple[bool, str]:
    """Compile every staged .py file. If any fails, the staged tree is bad."""
    bad: list[str] = []
    import py_compile
    for rel, _, _ in ENGINE_FILES:
        if not rel.endswith(".py"):
            continue
        path = staging / rel
        try:
            py_compile.compile(str(path), doraise=True)
        except (py_compile.PyCompileError, SyntaxError, OSError) as exc:
            bad.append(f"{rel}: {exc}")
    if bad:
        return False, "\n".join(bad)
    return True, ""


def _snapshot_current() -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"engine-before-{__version__}-{stamp}.tar.gz"

    with tarfile.open(snap, "w:gz", compresslevel=3) as tar:
        for rel, dest, _ in ENGINE_FILES:
            if dest.exists():
                tar.add(str(dest), arcname=rel)
        if CONFIG_PATH.exists():
            tar.add(str(CONFIG_PATH), arcname="config.json")
    return snap


def _atomic_install(staging: Path) -> list[str]:
    """Move staged files into their final places. os.replace is atomic
    on the same filesystem, which all these paths are."""
    placed: list[str] = []
    for rel, dest, mode in ENGINE_FILES:
        src = staging / rel
        if not src.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Write to a sibling tmp file then rename — on POSIX this is atomic.
        tmp = dest.with_suffix(dest.suffix + ".upd")
        shutil.copy2(src, tmp)
        try:
            os.chmod(tmp, mode)
        except OSError:
            pass
        os.replace(tmp, dest)
        placed.append(str(dest))
    return placed


def _bump_config_version(new_version: str) -> None:
    if not CONFIG_PATH.exists():
        return
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return
    data["version"] = new_version
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2))
        CONFIG_PATH.chmod(0o644)
    except OSError:
        pass


def perform_update(*, target: str | None = None,
                   force: bool = False) -> UpdateResult:
    """Atomically update engine files. NEVER touches user data.

    Steps:
      1. Probe remote for the latest version.
      2. If we're already on it (or newer) and force is False, no-op.
      3. Download every engine file into a staging directory.
      4. Compile every staged Python module — abort if any fails to parse.
      5. Snapshot the current engine + config to backups/updates/.
      6. Atomically replace each engine file with `os.replace`.
      7. Bump version in /etc/easynginx/config.json.

    Returns UpdateResult with from/to versions and the snapshot path.
    """
    info = check_for_update(force=True)
    if not info.latest_version:
        raise RuntimeError(
            "Could not determine the latest version. Check your network or "
            "run with --target <tag-or-branch> to install a specific ref."
        )

    if not force and not info.has_update and not target:
        return UpdateResult(
            from_version=__version__,
            to_version=__version__,
            snapshot_path=None,
            files_updated=[],
        )

    ref = _resolve_target_ref(target, info)

    with tempfile.TemporaryDirectory(prefix="easynginx-update-") as tmp:
        staging = Path(tmp)
        _stage_engine(ref, staging)

        ok, err = _python_compiles(staging)
        if not ok:
            raise RuntimeError(
                "Downloaded engine failed Python syntax check; nothing was "
                "installed.\n" + err
            )

        snap = _snapshot_current()
        placed = _atomic_install(staging)

    _bump_config_version(info.latest_version or __version__)

    return UpdateResult(
        from_version=__version__,
        to_version=info.latest_version or ref,
        snapshot_path=snap,
        files_updated=placed,
    )


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def list_snapshots() -> list[Path]:
    if not SNAPSHOT_DIR.is_dir():
        return []
    return sorted(SNAPSHOT_DIR.glob("engine-before-*.tar.gz"), reverse=True)


def rollback_last_update() -> Path:
    """Restore the most recent engine snapshot."""
    snaps = list_snapshots()
    if not snaps:
        raise RuntimeError("No update snapshots found to roll back to.")
    snap = snaps[0]

    with tarfile.open(snap, "r:gz") as tar:
        # Sanity-check: refuse anything outside our owned paths.
        owned = {rel for rel, _, _ in ENGINE_FILES} | {"config.json"}
        for member in tar.getmembers():
            if member.name not in owned:
                raise RuntimeError(
                    f"Snapshot contains unexpected member '{member.name}'; refusing."
                )

        with tempfile.TemporaryDirectory(prefix="easynginx-rollback-") as tmp:
            tar.extractall(tmp)  # noqa: S202 (members validated above)
            staging = Path(tmp)
            _atomic_install(staging)
            cfg_src = staging / "config.json"
            if cfg_src.exists():
                shutil.copy2(cfg_src, CONFIG_PATH)
                try:
                    CONFIG_PATH.chmod(0o644)
                except OSError:
                    pass

    return snap
