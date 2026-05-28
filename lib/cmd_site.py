"""Per-site management commands: info, edit, logs, remove, clone, maintenance."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import ssl
import subprocess
import time
from pathlib import Path

import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from helpers import (
    open_in_editor,
    parse_logs_in_config,
    parse_site_summary,
    site_log_paths,
    systemctl,
)
from ui import Console


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

def _cert_expiry(cert_path: Path) -> tuple[str | None, int | None]:
    """Return (expiry_iso, days_remaining) for an x509 PEM."""
    if not cert_path.exists():
        return None, None
    try:
        with cert_path.open("rb") as fh:
            pem = fh.read()
    except OSError:
        return None, None

    try:
        # ssl module bundles an x509 parser in 3.10+, but it's clunky.
        # Falling back to `openssl x509` keeps things simple and portable.
        proc = subprocess.run(
            ["openssl", "x509", "-noout", "-enddate"],
            input=pem, check=False, capture_output=True,
        )
        if proc.returncode != 0:
            return None, None
        line = proc.stdout.decode("utf-8", "replace").strip()
        if "=" not in line:
            return None, None
        when = line.split("=", 1)[1]
        # OpenSSL prints "Jul 14 12:34:56 2026 GMT"
        dt = _dt.datetime.strptime(when, "%b %d %H:%M:%S %Y %Z")
        days = (dt - _dt.datetime.utcnow()).days
        return dt.isoformat(), days
    except (FileNotFoundError, ValueError):
        return None, None


def cmd_info(domain: str, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config found for {domain}.")

    text = files.available.read_text(errors="ignore")
    summary = parse_site_summary(text)
    enabled = (
        files.enabled and files.enabled.is_symlink()
        if cfg.paths.uses_sites_available
        else files.available.suffix == ".conf"
    )

    console.header(f"Site: {domain}")
    print(f"  config       : {files.available}")
    print(f"  enabled      : {'yes' if enabled else 'no'}")
    print(f"  type         : {summary['type']}")
    if summary["server_names"]:
        print(f"  server_name  : {' '.join(summary['server_names'])}")
    if summary["listens"]:
        print(f"  listens      : {', '.join(summary['listens'])}")
    if summary["proxies"]:
        print(f"  proxy_pass   : {', '.join(summary['proxies'])}")

    if summary["has_ssl"] and summary["ssl_cert"]:
        cert_path = Path(summary["ssl_cert"])
        expiry, days = _cert_expiry(cert_path)
        if expiry:
            tag = "ok"
            if days is not None and days < 14:
                tag = "warn"
            if days is not None and days < 0:
                tag = "expired"
            print(f"  ssl cert     : {cert_path}")
            print(f"  expires      : {expiry}  ({days} days, {tag})")
        else:
            print(f"  ssl cert     : {cert_path} (expiry unknown — install openssl)")
    else:
        print("  ssl          : no")

    # Logs
    cfg_access, cfg_error = parse_logs_in_config(text)
    default_access, default_error = site_log_paths(domain)
    print(f"  access log   : {cfg_access or default_access}")
    print(f"  error log    : {cfg_error or default_error}")

    # systemd state for nginx
    rc, out = systemctl("is-active", "nginx")
    print(f"  nginx state  : {out or 'unknown'}")

    return 0


# ---------------------------------------------------------------------------
# edit
# ---------------------------------------------------------------------------

def cmd_edit(domain: str, cfg: Config, console: Console, editor: str | None) -> int:
    ok, err = v.validate_domain(domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config found for {domain}.")

    backup_dir = cfg.config_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{files.available.name}.pre-edit-{int(time.time())}"
    shutil.copy2(files.available, backup_path)

    rc = open_in_editor(files.available, editor)
    if rc != 0:
        console.warn("Editor exited non-zero; leaving file as-is.")

    ok, output = v.nginx_test()
    if not ok:
        console.error("nginx -t failed after edit:")
        for line in output.splitlines():
            console.hint(line)
        shutil.copy2(backup_path, files.available)
        console.warn(f"Reverted to {backup_path}.")
        return 1

    console.ok("nginx -t passed. Reloading...")
    rc, out = nginx_mod.reload_nginx()
    if rc:
        console.ok("Reload complete.")
    else:
        console.warn(f"Reload reported issues: {out}")
    console.hint(f"Backup of pre-edit version: {backup_path}")
    return 0


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------

def _tail_files(paths: list[Path], lines: int, follow: bool, console: Console) -> int:
    args = ["tail"]
    if follow:
        args.append("-F")
    args.extend(["-n", str(lines)])
    for p in paths:
        if p.exists():
            args.append(str(p))
    if len(args) <= 4:
        console.warn("None of the log files exist yet.")
        return 1
    try:
        return subprocess.call(args)
    except KeyboardInterrupt:
        return 0


def cmd_logs(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config found for {args.domain}.")

    text = files.available.read_text(errors="ignore")
    cfg_access, cfg_error = parse_logs_in_config(text)
    default_access, default_error = site_log_paths(args.domain)
    access = Path(cfg_access or default_access)
    error = Path(cfg_error or default_error)

    targets: list[Path]
    if args.both:
        targets = [access, error]
    elif args.errors:
        targets = [error]
    else:
        targets = [access]

    follow = args.follow or os.isatty(1)
    console.info(f"Tailing: {', '.join(str(t) for t in targets)}")
    if follow:
        console.hint("Ctrl-C to stop.")
    return _tail_files(targets, args.lines, follow, console)


# ---------------------------------------------------------------------------
# remove (extended with cert deletion)
# ---------------------------------------------------------------------------

def cmd_remove(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    if not args.yes and not console.confirm(
        f"Remove {args.domain}? Files will be deleted.", default=False
    ):
        return 0

    nginx_mod.remove_site(args.domain, cfg)

    if not args.keep_cert:
        if shutil.which("certbot"):
            console.info("Removing certificate via certbot...")
            subprocess.run(
                ["certbot", "delete", "--cert-name", args.domain, "-n"],
                check=False, capture_output=True, text=True,
            )

    nginx_mod.reload_nginx()
    console.ok(f"Removed {args.domain}.")
    return 0


# ---------------------------------------------------------------------------
# clone
# ---------------------------------------------------------------------------

_SERVER_NAME_RE = re.compile(r"^(\s*server_name\s+)([^;]+);", re.MULTILINE)


def cmd_clone(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    src = args.source
    dst = args.destination
    for d in (src, dst):
        ok, err = v.validate_domain(d)
        if not ok:
            raise EasyNginxError(f"{d}: {err}")

    src_files = nginx_mod.site_paths(src, cfg)
    if not src_files.available.exists():
        raise EasyNginxError(f"Source site '{src}' not found.")

    dst_files = nginx_mod.site_paths(dst, cfg)
    if dst_files.available.exists():
        raise EasyNginxError(f"Destination '{dst}' already exists.")

    text = src_files.available.read_text()

    # Replace server_name lines and any leftover bare references to src.
    text = _SERVER_NAME_RE.sub(rf"\1{dst};", text)
    # Strip any ssl_certificate lines — the clone shouldn't reuse the cert.
    text = re.sub(r"^\s*ssl_certificate(_key)?\s+[^;]+;\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*include\s+/etc/letsencrypt/options-ssl-nginx\.conf;\n?", "",
                  text, flags=re.MULTILINE)
    text = re.sub(r"^\s*ssl_dhparam\s+[^;]+;\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*listen\s+(\[::\]:)?443[^;]*;\n?", "", text, flags=re.MULTILINE)

    # Add a clone marker comment for traceability.
    text = f"# Cloned by EasyNginx from {src}\n" + text

    nginx_mod.write_site(dst, text, cfg)
    nginx_mod.enable_site(dst, cfg)

    ok, output = v.nginx_test()
    if not ok:
        console.error("nginx -t failed for the clone:")
        for line in output.splitlines():
            console.hint(line)
        nginx_mod.remove_site(dst, cfg)
        raise EasyNginxError("Clone aborted; cleaned up.")

    nginx_mod.reload_nginx()
    console.ok(f"Cloned {src} → {dst}.")
    console.hint(f"Run `sudo easynginx cert renew {dst}` (or pass --no-ssl was set) "
                 "to issue a fresh certificate when DNS is in place.")
    return 0


# ---------------------------------------------------------------------------
# maintenance mode
# ---------------------------------------------------------------------------

MAINT_DIR = Path("/etc/easynginx/maintenance")
MAINT_DEFAULT = MAINT_DIR / "default.html"


def _ensure_maintenance_page(custom: str | None, cfg: Config) -> Path:
    MAINT_DIR.mkdir(parents=True, exist_ok=True)
    if custom:
        src = Path(custom)
        if not src.exists():
            raise EasyNginxError(f"Maintenance page not found: {custom}")
        dest = MAINT_DIR / src.name
        shutil.copy2(src, dest)
        return dest
    if not MAINT_DEFAULT.exists():
        # Try the bundled template (lives under templates/html_vendors/).
        for candidate in (
            cfg.paths.templates / "html_vendors" / "maintenance.html",
            cfg.paths.templates / "maintenance.html",  # legacy install fallback
        ):
            if candidate.exists():
                shutil.copy2(candidate, MAINT_DEFAULT)
                break
        else:
            MAINT_DEFAULT.write_text(
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                "<title>Maintenance</title></head><body>"
                "<h1>We'll be right back.</h1>"
                "<p>This site is undergoing maintenance.</p></body></html>",
                encoding="utf-8",
            )
    return MAINT_DEFAULT


def cmd_maintenance(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No config for {args.domain}.")

    text = files.available.read_text()
    marker_start = "# >>> easynginx-maintenance"
    marker_end = "# <<< easynginx-maintenance"
    block_re = re.compile(
        rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}\n?",
        re.DOTALL,
    )

    # Remove any prior maintenance block.
    text = block_re.sub("", text)

    if args.state == "on":
        page = _ensure_maintenance_page(args.page, cfg)
        block = (
            f"\n    {marker_start}\n"
            f"    error_page 503 /__easynginx_maintenance.html;\n"
            f"    location = /__easynginx_maintenance.html {{\n"
            f"        root {page.parent};\n"
            f"        try_files /{page.name} =503;\n"
            f"        internal;\n"
            f"    }}\n"
            f"    location / {{\n"
            f"        return 503;\n"
            f"    }}\n"
            f"    {marker_end}\n"
        )
        # Insert the block before the first `location /` we find, falling back
        # to before the closing brace of the first server { ... } block.
        idx = text.find("location /")
        if idx == -1:
            # Find last "}" — assume it closes the server block.
            idx = text.rfind("}")
            if idx == -1:
                raise EasyNginxError("Could not find a place to insert maintenance block.")
        text = text[:idx] + block + text[idx:]
        msg = f"Maintenance mode ON for {args.domain}."
    else:
        msg = f"Maintenance mode OFF for {args.domain}."

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        console.error("nginx -t failed; reverting.")
        # Quick revert — drop the block we just inserted.
        files.available.write_text(block_re.sub("", text), encoding="utf-8")
        raise EasyNginxError(output)
    nginx_mod.reload_nginx()
    console.ok(msg)
    return 0
